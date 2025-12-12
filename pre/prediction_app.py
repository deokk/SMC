import os
import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import math
import random
from datetime import datetime, timedelta
import json
import tensorflow as tf

# --- Global Constants ---
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORICAL_DATA_PATH = os.path.join(DATA_DIR, 'gwangjin_2024_data.csv')
REAL_TIME_DATA_PATH = os.path.join(DATA_DIR, 'bike_data.txt')

# XGBoost Model Constants
XGB_MODEL_PATH = os.path.join(DATA_DIR, 'xgboost_multioutput_model.joblib')
XGB_FEATURES_PATH = os.path.join(DATA_DIR, 'feature_columns.joblib')

# LSTM Model Constants
LSTM_MODEL_PATH = os.path.join(DATA_DIR, 'AI/models/lstm_model.h5')
LSTM_SCALER_PATH = os.path.join(DATA_DIR, 'AI/models/scaler.pkl')
LSTM_INPUT_SEQUENCE_LENGTH = 168  # 7 days
LSTM_OUTPUT_SEQUENCE_LENGTH = 96  # 4 days


# ==============================================================================
# 1. SHORT-TERM PREDICTOR (XGBoost)
# ==============================================================================
class XGBoostPredictor:
    """Handles short-term (0-6 hour) predictions using the XGBoost model."""
    
    def __init__(self):
        print("Initializing XGBoostPredictor...")
        self.model = joblib.load(XGB_MODEL_PATH)
        self.feature_columns = joblib.load(XGB_FEATURES_PATH)
        self.df_features = self._prepare_features()
        self.station_ids = self.df_features.index.get_level_values('station_id').unique().tolist()
        print("XGBoostPredictor initialized successfully.")

    def _prepare_features(self):
        # This function is the same as the original BikePredictor's _prepare_features
        # It loads historical data and creates lag/rolling features for XGBoost.
        df = pd.read_csv(HISTORICAL_DATA_PATH, encoding='cp949')
        df.columns = ['date', 'station_id', 'station_name', 'hour', 'bike_count']
        df['timestamp'] = pd.to_datetime(df['date']) + pd.to_timedelta(df['hour'], unit='h')
        df['bike_count'] = pd.to_numeric(df['bike_count'], errors='coerce')
        df = df.groupby(['station_id', 'timestamp'], as_index=False)['bike_count'].mean()
        df = df.set_index(['station_id', 'timestamp']).sort_index()

        date_range = pd.date_range(start=df.index.get_level_values('timestamp').min(), end=df.index.get_level_values('timestamp').max(), freq='h')
        all_stations = df.index.get_level_values('station_id').unique()
        multi_index = pd.MultiIndex.from_product([all_stations, date_range], names=['station_id', 'timestamp'])
        df_reindexed = df.reindex(multi_index)
        df_reindexed['bike_count'] = df_reindexed.groupby(level='station_id')['bike_count'].transform(lambda group: group.interpolate(method='linear', limit_direction='both'))
        df_reindexed['bike_count'] = df_reindexed['bike_count'].fillna(0)
        df_reindexed['bike_count'] = df_reindexed['bike_count'].astype(int)

        df_features = df_reindexed.reset_index()
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

        for lag in [1, 2, 3, 24, 168]:
            df_features[f'bike_count_lag_{lag}h'] = df_features.groupby(level='station_id')['bike_count'].shift(lag)
        for window in [3, 24]:
            df_features[f'bike_count_rolling_mean_{window}h'] = df_features.groupby(level='station_id')['bike_count'].transform(lambda x: x.rolling(window=window, min_periods=1).mean())
        
        return df_features.dropna()

    def predict(self, station_id, n_minutes, real_time_bike_count):
        if station_id not in self.station_ids:
            raise ValueError(f"Station ID {station_id} not found in XGBoost historical data.")

        latest_features_row = self.df_features.loc[station_id].iloc[-1]
        feature_vector = latest_features_row[self.feature_columns].values.reshape(1, -1)
        hourly_predictions = self.model.predict(feature_vector)[0]
        
        if n_minutes == 0:
            return int(max(0, round(real_time_bike_count)))

        lower_bound_h = math.floor(n_minutes / 60)
        upper_bound_h = math.ceil(n_minutes / 60)

        if lower_bound_h == 0:
            val1_time_min, val1_bike_count = 0, real_time_bike_count
            val2_time_min, val2_bike_count = 60, hourly_predictions[0]
        else:
            val1_time_min = lower_bound_h * 60
            val1_bike_count = hourly_predictions[lower_bound_h - 1]
            val2_time_min = upper_bound_h * 60
            if upper_bound_h > 6:
                return int(max(0, round(hourly_predictions[5])))
            val2_bike_count = hourly_predictions[upper_bound_h - 1]

        if val2_time_min == val1_time_min:
            return int(max(0, round(val1_bike_count)))
        
        interpolated_bike_count = val1_bike_count + \
                                  ((val2_bike_count - val1_bike_count) / (val2_time_min - val1_time_min)) * \
                                  (n_minutes - val1_time_min)
        return int(max(0, round(interpolated_bike_count)))


# ==============================================================================
# 2. LONG-TERM PREDICTOR (LSTM)
# ==============================================================================
class LSTMPredictor:
    """Handles long-term (6-96 hour) predictions using the LSTM model."""

    def __init__(self):
        print("Initializing LSTMPredictor...")
        # Load model without compiling, then compile manually to avoid deserialization errors.
        self.model = tf.keras.models.load_model(LSTM_MODEL_PATH, compile=False)
        self.model.compile(optimizer='adam', loss='mse')
        
        self.scalers = joblib.load(LSTM_SCALER_PATH)
        self.df_history = self._prepare_historical_data()
        self.station_ids = list(self.scalers.keys())
        print("LSTMPredictor initialized successfully.")

    def _prepare_historical_data(self):
        # This function is similar to the one in the LSTM trainer, but optimized for prediction.
        # It just needs to load, clean, and add time features. No sequencing is done here.
        df = pd.read_csv(HISTORICAL_DATA_PATH, encoding='cp949')
        df.columns = ['date', 'station_id', 'station_name', 'hour', 'bike_count']
        df['timestamp'] = pd.to_datetime(df['date']) + pd.to_timedelta(df['hour'], unit='h')
        df['bike_count'] = pd.to_numeric(df['bike_count'], errors='coerce')
        df = df.groupby(['station_id', 'timestamp'], as_index=False).agg({'bike_count': 'mean'}).dropna()
        df['station_id'] = df['station_id'].astype(int)

        df = df.set_index(['station_id', 'timestamp']).sort_index()

        df_features = df.reset_index()
        df_features['hour_sin'] = np.sin(2 * np.pi * df_features['timestamp'].dt.hour / 24)
        df_features['hour_cos'] = np.cos(2 * np.pi * df_features['timestamp'].dt.hour / 24)
        df_features['day_of_week_sin'] = np.sin(2 * np.pi * df_features['timestamp'].dt.dayofweek / 7)
        df_features['day_of_week_cos'] = np.cos(2 * np.pi * df_features['timestamp'].dt.dayofweek / 7)
        
        return df_features

    def predict(self, station_id):
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
        
        # The prediction is just the bike count. We need to inverse-transform it.
        # To do that, we need to reconstruct a dataframe with the shape the scaler expects.
        dummy_features = np.zeros((len(scaled_prediction), len(feature_cols)))
        dummy_features[:, 0] = scaled_prediction # Put the prediction in the 'bike_count' column
        
        inversed_prediction = scaler.inverse_transform(dummy_features)[:, 0] # Inverse and get only the bike_count
        
        return np.maximum(0, np.round(inversed_prediction)).astype(int)


# ==============================================================================
# 3. HYBRID PREDICTOR (Orchestrator)
# ==============================================================================
class HybridPredictor:
    """Orchestrates predictions between the short-term and long-term models."""

    def __init__(self):
        self.xgb_predictor = XGBoostPredictor()
        self.lstm_predictor = LSTMPredictor()
        # Assume common station IDs for simplicity. A more robust solution would handle mismatches.
        self.station_ids = self.xgb_predictor.station_ids

    def get_real_time_bike_count(self, station_id):
        # This function is the same as the original get_real_time_bike_count_from_file
        try:
            with open(REAL_TIME_DATA_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for entry in data:
                file_station_id_str = entry.get("station_id")
                if file_station_id_str and file_station_id_str.startswith("ST-"):
                    if int(file_station_id_str.split("-")[1]) == station_id:
                        return entry.get("available_bikes", random.randint(5, 20))
            return random.randint(5, 20)
        except (FileNotFoundError, json.JSONDecodeError):
            return random.randint(5, 20)

    def predict(self, station_id, n_minutes):
        """
        Routes the prediction request to the appropriate model based on the time horizon.
        """
        if not isinstance(n_minutes, int) or n_minutes < 0:
            raise ValueError("n_minutes must be a non-negative integer.")

        if n_minutes <= 360:  # 6 hours
            print(f"--- Firing SHORT-TERM model for {n_minutes} min prediction ---")
            real_time_count = self.get_real_time_bike_count(station_id)
            return self.xgb_predictor.predict(station_id, n_minutes, real_time_count)
        
        elif 360 < n_minutes <= 5760:  # 6 hours to 4 days (96 * 60)
            print(f"--- Firing LONG-TERM model for {n_minutes} min prediction ---")
            # LSTM predicts 96 hours starting from the end of the historical data.
            # The first prediction corresponds to hour 1.
            hourly_predictions_96 = self.lstm_predictor.predict(station_id)
            
            # Find which hour to return.
            # e.g., n_minutes = 420 (7 hours). target_hour_index = floor(420/60) - 1 = 7 - 1 = 6
            # Note: This is a simplification. The LSTM model predicts from the last known point in the *history*.
            # For a true hybrid system, we might train the LSTM to predict from t+6 to t+102.
            # For now, we assume the LSTM's t+1 prediction is a reasonable proxy for the real t+6.
            target_hour_index = math.ceil(n_minutes / 60) - 1 # Get the corresponding hourly slot
            if target_hour_index < len(hourly_predictions_96):
                return hourly_predictions_96[target_hour_index]
            else:
                raise ValueError("Prediction time exceeds the 96-hour forecast range of the LSTM model.")
        
        else:
            raise ValueError("Prediction time exceeds the 4-day maximum forecast horizon.")


# ==============================================================================
# 4. MAIN EXECUTION BLOCK
# ==============================================================================
if __name__ == '__main__':
    import sys

    try:
        # 1. Initialize the main hybrid predictor
        print("Initializing Hybrid Predictor System...\n")
        hybrid_predictor = HybridPredictor()
        
        # 2. Check for command-line argument
        if len(sys.argv) > 1:
            # --- PREDICT FOR ALL STATIONS (as requested) ---
            try:
                n_minutes = int(sys.argv[1])
                print(f"--- Predicting total bike count for all Gwangjin-gu stations in {n_minutes} minutes ---")
                
                station_ids = hybrid_predictor.lstm_predictor.station_ids
                if not station_ids:
                    raise RuntimeError("No station IDs found. Cannot perform prediction.")

                total_predicted_bikes = 0
                
                # Use a simple progress indicator
                for i, station_id in enumerate(station_ids):
                    # Use carriage return and flush to show progress on a single line
                    progress_percent = (i + 1) / len(station_ids) * 100
                    sys.stdout.write(f"\rProcessing station {i+1}/{len(station_ids)} ({progress_percent:.1f}%)")
                    sys.stdout.flush()

                    try:
                        prediction = hybrid_predictor.predict(station_id, n_minutes)
                        total_predicted_bikes += prediction
                    except Exception as e:
                        # Print error for a specific station but continue with others
                        print(f"\nCould not predict for station {station_id}: {e}")
                
                print(f"\n\n✅ Predicted TOTAL bike count for Gwangjin-gu in {n_minutes} minutes: {total_predicted_bikes} bikes")

            except ValueError:
                print(f"❌ Error: Invalid input '{sys.argv[1]}'. Please provide an integer for the number of minutes.")
            except Exception as e:
                print(f"❌ An error occurred during prediction: {e}")

        else:
            # --- RUN DEMO FOR A SINGLE STATION (original behavior) ---
            print("--- No time specified. Running a default demo for a single random station. ---")
            print("--- To predict for all stations, run: python prediction_app.py <minutes> ---\n")

            testable_station_ids = hybrid_predictor.lstm_predictor.station_ids
            if not testable_station_ids:
                raise RuntimeError("LSTM Predictor has no stations loaded. Check the training process.")
            
            test_station_id = random.choice(testable_station_ids)
            print(f"--- Running Prediction Demo for station ID: {test_station_id} ---")

            short_term_minutes = 30
            try:
                prediction_short = hybrid_predictor.predict(test_station_id, short_term_minutes)
                print(f"✅ Result for {short_term_minutes} minutes: {prediction_short} bikes")
            except (ValueError, RuntimeError) as e:
                print(f"❌ Error during short-term prediction: {e}")

            long_term_minutes = 1440  # 24 hours
            try:
                prediction_long = hybrid_predictor.predict(test_station_id, long_term_minutes)
                print(f"✅ Result for {long_term_minutes} minutes (24 hours): {prediction_long} bikes")
            except (ValueError, RuntimeError) as e:
                print(f"❌ Error during long-term prediction: {e}")

    except Exception as e:
        print(f"\nAn unexpected error occurred during initialization or prediction: {e}")
