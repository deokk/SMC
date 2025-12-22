import os
import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
import math
import random
from datetime import datetime
import json
# --- Global Constants ---
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(DATA_DIR, 'xgboost_multioutput_model.joblib')
FEATURES_PATH = os.path.join(DATA_DIR, 'feature_columns.joblib')
HISTORICAL_DATA_PATH = os.path.join(DATA_DIR, 'gwangjin_2024_data.csv')
REAL_TIME_DATA_PATH = os.path.join(DATA_DIR, 'bike_data.txt')


class BikePredictor:
    """
    A class to load the trained model and make bike count predictions.
    """
    def __init__(self):
        """
        Initializes the predictor by loading the model, feature columns,
        and preparing the historical data for feature lookup.
        """
        print("Initializing BikePredictor...")
        self.model = self._load_model()
        self.feature_columns = self._load_feature_columns()
        self.df_features = self._prepare_features()
        self.station_ids = self.df_features.index.get_level_values('station_id').unique().tolist()
        print("BikePredictor initialized successfully.")

    def _load_model(self):
        """Loads the trained XGBoost model."""
        try:
            model = joblib.load(MODEL_PATH)
            print(f"Model loaded from {MODEL_PATH}")
            return model
        except FileNotFoundError:
            print(f"Error: Model file not found at {MODEL_PATH}")
            return None

    def _load_feature_columns(self):
        """Loads the list of feature columns."""
        try:
            feature_columns = joblib.load(FEATURES_PATH)
            print(f"Feature columns loaded from {FEATURES_PATH}")
            return feature_columns
        except FileNotFoundError:
            print(f"Error: Feature columns file not found at {FEATURES_PATH}")
            return None

    def _prepare_features(self):
        """
        Loads and prepares the historical data to be used as a feature lookup table.
        This mirrors the logic from xgboost_model_trainer.py.
        """
        if not os.path.exists(HISTORICAL_DATA_PATH):
            print(f"Error: Historical data not found at {HISTORICAL_DATA_PATH}")
            return None
        
        print("Loading and preparing historical data for feature generation...")
        # Adapted from load_data() in trainer
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

        # Adapted from create_features() in trainer
        df_features = df_reindexed.copy()
        df_features = df_features.reset_index()
        
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

        lags = [1, 2, 3, 24, 168]
        for lag in lags:
            df_features[f'bike_count_lag_{lag}h'] = df_features.groupby(level='station_id')['bike_count'].shift(lag)

        rolling_windows = [3, 24]
        for window in rolling_windows:
            df_features[f'bike_count_rolling_mean_{window}h'] = df_features.groupby(level='station_id')['bike_count'].transform(lambda x: x.rolling(window=window, min_periods=1).mean())
        
        df_features = df_features.dropna()
        print("Feature preparation complete.")
        return df_features

    def get_real_time_bike_count_from_file(self, station_id):
        """
        Reads bike_data.txt to get the available_bikes for the given station_id.
        Falls back to a random count if the station is not found or file is unreadable.
        """
        try:
            with open(REAL_TIME_DATA_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for entry in data:
                # Convert "ST-XXX" to XXX
                file_station_id_str = entry.get("station_id")
                if file_station_id_str and file_station_id_str.startswith("ST-"):
                    file_station_id_int = int(file_station_id_str.split("-")[1])
                    if file_station_id_int == station_id:
                        return entry.get("available_bikes", random.randint(0, 40)) # Fallback if key missing
            
            # If station_id not found in file, return random
            return random.randint(0, 40)

        except FileNotFoundError:
            print(f"Warning: Real-time data file not found at {REAL_TIME_DATA_PATH}. Using random bike count for station {station_id}.")
            return random.randint(0, 40)
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from {REAL_TIME_DATA_PATH}. Using random bike count for station {station_id}.")
            return random.randint(0, 40)
        except Exception as e:
            print(f"An unexpected error occurred while reading real-time data for station {station_id}: {e}. Using random bike count.")
            return random.randint(0, 40)

    def predict(self, station_id, n_minutes, real_time_bike_count):
        """
        Predicts bike count for a specific station at n_minutes in the future.

        Args:
            station_id (int): The ID of the station to predict for.
            n_minutes (int): The number of minutes into the future to predict (0 to 360).
            real_time_bike_count (int): The current, real-time bike count for the station.

        Returns:
            int: Predicted bike count.
        """
        if self.model is None or self.feature_columns is None or self.df_features is None:
            raise RuntimeError("Predictor is not properly initialized. Check for loading errors.")

        if not (0 <= n_minutes <= 360):
            raise ValueError("n_minutes must be between 0 and 360 (6 hours).")
        
        if station_id not in self.station_ids:
            raise ValueError(f"Station ID {station_id} not found in historical data.")

        # Get the latest available feature set for the station from our historical data
        try:
            latest_features_row = self.df_features.loc[station_id].iloc[-1]
            feature_vector = latest_features_row[self.feature_columns].values.reshape(1, -1)
        except (KeyError, IndexError):
             raise ValueError(f"Could not retrieve latest feature vector for station {station_id}.")

        # The model predicts the next 6 hours based on the historical feature vector
        hourly_predictions = self.model.predict(feature_vector)[0]
        
        # We use the provided 'real_time_bike_count' as the starting point (t=0) for our interpolation.
        # This "anchors" the prediction to the most current known value.
        current_bike_count = real_time_bike_count

        if n_minutes == 0:
            return int(max(0, round(current_bike_count)))

        # Find the lower and upper bounds in hours for interpolation
        lower_bound_h = math.floor(n_minutes / 60)
        upper_bound_h = math.ceil(n_minutes / 60)

        # Get values for interpolation
        if lower_bound_h == 0: # Interpolate between current and +1h prediction
            val1_time_min, val1_bike_count = 0, current_bike_count
            val2_time_min, val2_bike_count = 60, hourly_predictions[0]
        else: # Interpolate between two model predictions
            val1_time_min = lower_bound_h * 60
            val1_bike_count = hourly_predictions[lower_bound_h - 1]
            val2_time_min = upper_bound_h * 60
            # Ensure we don't go out of bounds for the 6th hour prediction
            if upper_bound_h > 6:
                return int(max(0, round(hourly_predictions[5])))
            val2_bike_count = hourly_predictions[upper_bound_h - 1]

        # Linear Interpolation
        if val2_time_min == val1_time_min:
            interpolated_bike_count = val1_bike_count
        else:
            interpolated_bike_count = val1_bike_count + \
                                      ((val2_bike_count - val1_bike_count) / (val2_time_min - val1_time_min)) * \
                                      (n_minutes - val1_time_min)
                                      
        return int(max(0, round(interpolated_bike_count)))

    def predict_all_stations(self, n_minutes):
        """
        Predicts bike counts for all stations for a given future time.

        Args:
            n_minutes (int): The number of minutes into the future to predict.

        Returns:
            dict: A dictionary with station_id as key and predicted_count as value.
        """
        predictions = {}
        for station_id in self.station_ids:
            try:
                # Use the new function to get real-time count
                real_time_count = self.get_real_time_bike_count_from_file(station_id)
                predicted_count = self.predict(station_id, n_minutes, real_time_count)
                predictions[station_id] = predicted_count
            except ValueError as e:
                print(f"Could not generate prediction for station {station_id}: {e}")
        return predictions


if __name__ == '__main__':
    # --- Example Usage ---
    try:
        # 1. Initialize the predictor. This loads all necessary data and can take a moment.
        predictor = BikePredictor()

        # 2. Set the desired prediction time in minutes.
        prediction_minutes = 30 

        # 3. Request predictions for all stations for the specified time.
        print(f"\n--- Requesting predictions for all Gwangjin-gu stations in {prediction_minutes} minutes ---")
        all_predictions = predictor.predict_all_stations(prediction_minutes)

        if all_predictions:
            print(f"Successfully generated predictions for {len(all_predictions)} stations.")
            print("Showing predictions for the first 10 stations:")
            
            # Print the first 10 items
            count = 0
            for station_id, predicted_count in all_predictions.items():
                if count < 10:
                    print(f"  - Station ID {station_id}: {predicted_count} bikes")
                    count += 1
                else:
                    break
        else:
            print("No predictions were generated.")

    except (RuntimeError, ValueError) as e:
        print(f"\nAn error occurred during the prediction process: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
