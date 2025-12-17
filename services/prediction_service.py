# services/prediction_service.py
import os
import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import math
import random
from datetime import datetime, timedelta
import tensorflow as tf
from sqlalchemy.orm import Session
from sqlalchemy import text

# Project-specific imports
from db.database import SessionLocal

# --- Global Constants ---
# Updated to use the project's model directory
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'models')

# XGBoost Model Constants
XGB_MODEL_PATH = os.path.join(MODEL_DIR, 'xgboost_multioutput_model.joblib')
XGB_FEATURES_PATH = os.path.join(MODEL_DIR, 'feature_columns.joblib')

# LSTM Model Constants
LSTM_MODEL_PATH = os.path.join(MODEL_DIR, 'lstm_model.h5')
LSTM_SCALER_PATH = os.path.join(MODEL_DIR, 'scaler.pkl')
LSTM_INPUT_SEQUENCE_LENGTH = 168  # 7 days
LSTM_OUTPUT_SEQUENCE_LENGTH = 96  # 4 days


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==============================================================================
# 1. SHORT-TERM PREDICTOR (XGBoost)
# ==============================================================================
class XGBoostPredictor:
    """Handles short-term (0-6 hour) predictions using the XGBoost model."""
    
    def __init__(self, db: Session):
        print("Initializing XGBoostPredictor...")
        self.model = joblib.load(XGB_MODEL_PATH)
        self.feature_columns = joblib.load(XGB_FEATURES_PATH)
        self.df_features = self._prepare_features(db)
        self.station_ids = self.df_features.index.get_level_values('station_id').unique().tolist()
        print(f"XGBoostPredictor initialized successfully for {len(self.station_ids)} stations.")

    def _prepare_features(self, db: Session):
        """
        Loads historical data from the database and creates lag/rolling features for XGBoost.
        """
        print("XGBoost: Preparing features from database...")
        query = text("""
            SELECT station_id, timestamp, available_bikes AS bike_count
            FROM bike_availability_historical_gwangjin
            ORDER BY station_id, timestamp;
        """)
        df = pd.read_sql(query, db.connection())

        # Convert station_id from 'ST-xxxx' to integer xxxx
        df['station_id'] = df['station_id'].str.replace('ST-', '').astype(int)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        df = df.groupby(['station_id', 'timestamp'], as_index=False)['bike_count'].mean()
        df = df.set_index(['station_id', 'timestamp']).sort_index()

        # Reindexing to fill missing hourly data
        date_range = pd.date_range(start=df.index.get_level_values('timestamp').min(), end=df.index.get_level_values('timestamp').max(), freq='h')
        all_stations = df.index.get_level_values('station_id').unique()
        multi_index = pd.MultiIndex.from_product([all_stations, date_range], names=['station_id', 'timestamp'])
        df_reindexed = df.reindex(multi_index)
        
        # Interpolate and fill NaNs
        df_reindexed['bike_count'] = df_reindexed.groupby(level='station_id')['bike_count'].transform(lambda group: group.interpolate(method='linear', limit_direction='both'))
        df_reindexed['bike_count'] = df_reindexed['bike_count'].fillna(0)
        df_reindexed['bike_count'] = df_reindexed['bike_count'].astype(int)

        df_features = df_reindexed.reset_index()
        
        # Create time-based features
        df_features['hour'] = df_features['timestamp'].dt.hour
        df_features['hour_sin'] = np.sin(2 * np.pi * df_features['hour'] / 24)
        df_features['hour_cos'] = np.cos(2 * np.pi * df_features['hour'] / 24)
        df_features['day_of_week'] = df_features['timestamp'].dt.dayofweek
        df_features['day_of_week_sin'] = np.sin(2 * np.pi * df_features['day_of_week'] / 7)
        df_features['day_of_week_cos'] = np.cos(2 * np.pi * df_features['day_of_week'] / 7)
        df_features['day_of_year'] = df_features['timestamp'].dt.dayofyear
        df_features['month'] = df_features['timestamp'].dt.month
        df_features['year'] = df_features['timestamp'].dt.year
        df_features = df_features.set_index(['station_id', 'timestamp']).sort_index()

        # Create lag and rolling features
        for lag in [1, 2, 3, 24, 168]:
            df_features[f'bike_count_lag_{lag}h'] = df_features.groupby(level='station_id')['bike_count'].shift(lag)
        for window in [3, 24]:
            df_features[f'bike_count_rolling_mean_{window}h'] = df_features.groupby(level='station_id')['bike_count'].transform(lambda x: x.rolling(window=window, min_periods=1).mean())
        
        print("XGBoost: Feature preparation complete.")
        return df_features.dropna()

    def predict(self, station_id: int, n_minutes: int, real_time_bike_count: int):
        if station_id not in self.station_ids:
            raise ValueError(f"Station ID {station_id} not found in XGBoost historical data.")

        # Find the latest available data for the station to use as a feature vector
        latest_features_row = self.df_features.loc[station_id].iloc[-1]
        feature_vector = latest_features_row[self.feature_columns].values.reshape(1, -1)
        
        # Predict the next 6 hours
        hourly_predictions = self.model.predict(feature_vector)[0]
        
        if n_minutes == 0:
            return int(max(0, round(real_time_bike_count)))

        # Interpolate between hours for a minute-level prediction
        lower_bound_h = math.floor(n_minutes / 60)
        upper_bound_h = math.ceil(n_minutes / 60)

        if lower_bound_h == 0:
            val1_time_min, val1_bike_count = 0, real_time_bike_count
            val2_time_min, val2_bike_count = 60, hourly_predictions[0]
        else:
            val1_time_min = lower_bound_h * 60
            val1_bike_count = hourly_predictions[lower_bound_h - 1]
            val2_time_min = upper_bound_h * 60
            if upper_bound_h > 6: # Cap prediction at the 6th hour
                return int(max(0, round(hourly_predictions[5])))
            val2_bike_count = hourly_predictions[upper_bound_h - 1]

        if val2_time_min == val1_time_min:
            return int(max(0, round(val1_bike_count)))
        
        # Linear interpolation
        interpolated_bike_count = val1_bike_count + \
                                  ((val2_bike_count - val1_bike_count) / (val2_time_min - val1_time_min)) * \
                                  (n_minutes - val1_time_min)
        return int(max(0, round(interpolated_bike_count)))


# ==============================================================================
# 2. LONG-TERM PREDICTOR (LSTM)
# ==============================================================================
class LSTMPredictor:
    """Handles long-term (6-96 hour) predictions using the LSTM model."""

    def __init__(self, db: Session):
        print("Initializing LSTMPredictor...")
        self.model = tf.keras.models.load_model(LSTM_MODEL_PATH, compile=False)
        self.model.compile(optimizer='adam', loss='mse')
        
        self.scalers = joblib.load(LSTM_SCALER_PATH)
        self.df_history = self._prepare_historical_data(db)
        self.station_ids = list(self.scalers.keys())
        print(f"LSTMPredictor initialized successfully for {len(self.station_ids)} stations.")

    def _prepare_historical_data(self, db: Session):
        """
        Loads historical data from the database, optimized for prediction.
        """
        print("LSTM: Preparing historical data from database...")
        # Fetch more data than needed to ensure we have enough for the last sequence
        query = text("""
            SELECT station_id, timestamp, available_bikes AS bike_count
            FROM bike_availability_historical_gwangjin
            ORDER BY timestamp DESC
            LIMIT 50000;
        """)
        df = pd.read_sql(query, db.connection())
        
        # Convert station_id and timestamp
        df['station_id'] = df['station_id'].str.replace('ST-', '').astype(int)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values(['station_id', 'timestamp'])
        print("LSTM: Historical data loaded.")
        
        # Add time features required by the model
        df_features = df.reset_index(drop=True)
        df_features['hour_sin'] = np.sin(2 * np.pi * df_features['timestamp'].dt.hour / 24)
        df_features['hour_cos'] = np.cos(2 * np.pi * df_features['timestamp'].dt.hour / 24)
        df_features['day_of_week_sin'] = np.sin(2 * np.pi * df_features['timestamp'].dt.dayofweek / 7)
        df_features['day_of_week_cos'] = np.cos(2 * np.pi * df_features['timestamp'].dt.dayofweek / 7)
        
        return df_features

    def predict(self, station_id: int):
        if station_id not in self.station_ids:
            raise ValueError(f"Station ID {station_id} not found in LSTM model scalers.")
        
        station_history = self.df_history[self.df_history['station_id'] == station_id]
        
        # Get the last 168 hours of data for the input sequence
        input_sequence_df = station_history.tail(LSTM_INPUT_SEQUENCE_LENGTH)
        if len(input_sequence_df) < LSTM_INPUT_SEQUENCE_LENGTH:
            raise ValueError(f"Not enough historical data for station {station_id} to make a long-term prediction.")
            
        feature_cols = ['bike_count', 'hour_sin', 'hour_cos', 'day_of_week_sin', 'day_of_week_cos']
        
        # Scale the input sequence using the station-specific scaler
        scaler = self.scalers[station_id]
        scaled_input = scaler.transform(input_sequence_df[feature_cols])
        
        # Reshape for the model: (1, sequence_length, n_features)
        scaled_input = scaled_input.reshape(1, LSTM_INPUT_SEQUENCE_LENGTH, len(feature_cols))
        
        # Make the prediction
        scaled_prediction = self.model.predict(scaled_input)[0]
        
        # Inverse transform the prediction to get the actual bike count
        dummy_features = np.zeros((len(scaled_prediction), len(feature_cols)))
        dummy_features[:, 0] = scaled_prediction
        inversed_prediction = scaler.inverse_transform(dummy_features)[:, 0]
        
        return np.maximum(0, np.round(inversed_prediction)).astype(int)

# ==============================================================================
# 3. HYBRID PREDICTOR (Orchestrator)
# ==============================================================================
class HybridPredictor:
    """Orchestrates predictions between the short-term and long-term models."""

    def __init__(self, db: Session):
        self.db = db
        self.xgb_predictor = XGBoostPredictor(db)
        self.lstm_predictor = LSTMPredictor(db)
        self.station_ids = self.xgb_predictor.station_ids # Use common station IDs

    def get_real_time_bike_count(self, station_id: int):
        """
        Gets the most recent bike count for a station from the realtime table.
        """
        # Convert integer station_id back to string 'ST-xxxx' for DB query
        station_id_str = f"ST-{station_id}"
        query = text("""
            SELECT available_bikes FROM bike_availability_realtime
            WHERE station_id = :station_id
            ORDER BY timestamp DESC
            LIMIT 1;
        """ )
        result = self.db.execute(query, {'station_id': station_id_str}).fetchone()
        
        if result:
            return result[0]
        else:
            # Fallback if no realtime data is found
            print(f"Warning: No realtime data for station {station_id}, returning random fallback.")
            return random.randint(5, 20)

    def predict(self, station_id: int, n_minutes: int):
        """
        Routes the prediction request to the appropriate model based on the time horizon.
        """
        if not isinstance(n_minutes, int) or n_minutes < 0:
            raise ValueError("n_minutes must be a non-negative integer.")

        station_id_int = int(station_id)

        if n_minutes <= 360:  # 6 hours
            print(f"--- Firing SHORT-TERM model for {n_minutes} min prediction for station {station_id_int} ---")
            real_time_count = self.get_real_time_bike_count(station_id_int)
            return self.xgb_predictor.predict(station_id_int, n_minutes, real_time_count)
        
        elif 360 < n_minutes <= 5760:  # 6 hours to 4 days (96 * 60)
            print(f"--- Firing LONG-TERM model for {n_minutes} min prediction for station {station_id_int} ---")
            hourly_predictions_96 = self.lstm_predictor.predict(station_id_int)
            
            # The LSTM model predicts 96 hours (4 days) from the last point in the history.
            # We select the prediction corresponding to the requested hour.
            target_hour_index = math.ceil(n_minutes / 60) - 1 
            if target_hour_index < len(hourly_predictions_96):
                return hourly_predictions_96[target_hour_index]
            else:
                raise ValueError("Prediction time exceeds the 96-hour forecast range of the LSTM model.")
        
        else:
            raise ValueError("Prediction time exceeds the 4-day maximum forecast horizon.")

