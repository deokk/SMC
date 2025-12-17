# xgboost_model_trainer.py
# This script will be developed step-by-step according to the blueprint.

import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.multioutput import MultiOutputRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
import os
import math # For cyclical features

# --- Global Constants ---
DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# --- 0. Setup and Initial Data Loading ---

def load_data():
    """
    Loads the Gwangjin-gu 2024 data, renames columns, creates timestamp,
    and reindexes to ensure a continuous hourly time series for each station.
    """
    file_path = os.path.join(DATA_DIR, 'gwangjin_2024_data.csv')
    
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found. Please ensure the file exists.")
        return None
        
    try:
        df = pd.read_csv(file_path, encoding='cp949')
        print("Successfully loaded gwangjin_2024_data.csv")
        
        # Rename columns to be usable based on previous inspection
        df.columns = ['date', 'station_id', 'station_name', 'hour', 'bike_count']
        
        # Combine 'date' and 'hour' to create a proper timestamp
        df['timestamp'] = pd.to_datetime(df['date']) + pd.to_timedelta(df['hour'], unit='h')
        
        # Convert bike_count to numeric, coercing errors
        df['bike_count'] = pd.to_numeric(df['bike_count'], errors='coerce')
        
        # --- Debugging Non-Unique Multi-Index ---
        # Before setting the MultiIndex, check for duplicates in the (station_id, timestamp) pair.
        if df.duplicated(subset=['station_id', 'timestamp']).any():
            print("\n--- WARNING: Duplicate (station_id, timestamp) pairs found! ---")
            duplicates = df[df.duplicated(subset=['station_id', 'timestamp'], keep=False)].sort_values(by=['station_id', 'timestamp'])
            print(f"Total {len(duplicates)} duplicate rows found.")
            
            # Aggregate by taking the mean of bike_count for duplicate entries.
            df = df.groupby(['station_id', 'timestamp'], as_index=False)['bike_count'].mean()
            print("Duplicates resolved by aggregating 'bike_count' using mean.")

        # Set Multi-Index and sort
        df = df.set_index(['station_id', 'timestamp']).sort_index()
        
        # Create a full date range for the year
        date_range = pd.date_range(start=df.index.get_level_values('timestamp').min(), 
                                   end=df.index.get_level_values('timestamp').max(), 
                                   freq='h')
        all_stations = df.index.get_level_values('station_id').unique()
        
        # Create a multi-index of all stations and all hours
        multi_index = pd.MultiIndex.from_product([all_stations, date_range], names=['station_id', 'timestamp'])
        
        # Reindex the dataframe
        df_reindexed = df.reindex(multi_index)
        
        # Fill missing bike_count values due to reindexing
        # Changed method='time' to method='linear' as 'time' is not supported on MultiIndexes
        df_reindexed['bike_count'] = df_reindexed.groupby(level='station_id')['bike_count'].transform(lambda group: group.interpolate(method='linear', limit_direction='both'))
        df_reindexed['bike_count'] = df_reindexed['bike_count'].fillna(0) # Fill any remaining NaNs (e.g., at very beginning/end)
        
        # Ensure 'bike_count' is integer
        df_reindexed['bike_count'] = df_reindexed['bike_count'].astype(int)

        print("\n--- Data Loading and Initial Preparation Summary ---")
        print("Columns renamed and 'timestamp' index created.")
        print("Reindexed data to ensure continuous time series for each station.")
        print("Filled missing 'bike_count' values using linear interpolation and then 0.")
        print(f"Data time range: {df_reindexed.index.get_level_values('timestamp').min()} to {df_reindexed.index.get_level_values('timestamp').max()}")
        print(f"Number of unique stations: {len(all_stations)}")
        print("Shape after reindexing and interpolation:", df_reindexed.shape)
        print("First 5 rows of prepared data:")
        print(df_reindexed.head().to_string())

        return df_reindexed

    except Exception as e:
        print(f"An error occurred during data loading and preparation: {e}")
        return None

# --- 1. Data Preprocessing & Feature Engineering ---

def create_features(df):
    """
    Creates cyclical time features, lag features, and rolling window features.
    All operations are performed per station_id.
    """
    print("\n--- Starting Feature Engineering ---")

    df_features = df.copy() # Work on a copy

    # Ensure timestamp is accessible for time-based features
    df_features = df_features.reset_index()
    
    # Cyclical Time Features (시간 변수)
    # Hour (0-23)
    df_features['hour'] = df_features['timestamp'].dt.hour
    df_features['hour_sin'] = np.sin(2 * np.pi * df_features['hour'] / 24)
    df_features['hour_cos'] = np.cos(2 * np.pi * df_features['hour'] / 24)

    # Day of Week (0=Monday, 6=Sunday)
    df_features['day_of_week'] = df_features['timestamp'].dt.dayofweek
    df_features['day_of_week_sin'] = np.sin(2 * np.pi * df_features['day_of_week'] / 7)
    df_features['day_of_week_cos'] = np.cos(2 * np.pi * df_features['day_of_week'] / 7)

    # Other useful time features (not cyclical but important)
    df_features['day_of_year'] = df_features['timestamp'].dt.dayofyear
    df_features['month'] = df_features['timestamp'].dt.month
    df_features['year'] = df_features['timestamp'].dt.year # Will be constant 2024

    # Set multi-index back for groupby operations
    df_features = df_features.set_index(['station_id', 'timestamp']).sort_index()

    # Lag Features (핵심 변수) - Groupby station_id
    # Data is hourly, so lags are in hours
    print("Creating Lag Features...")
    lags = [1, 2, 3, 24, 168] # 1h, 2h, 3h, 24h (daily), 168h (weekly)
    for lag in lags:
        df_features[f'bike_count_lag_{lag}h'] = df_features.groupby(level='station_id')['bike_count'].shift(lag)

    # Rolling Window Features (추가 변수) - Groupby station_id
    print("Creating Rolling Window Features...")
    rolling_windows = [3, 24] # 3h, 24h rolling mean
    for window in rolling_windows:
        df_features[f'bike_count_rolling_mean_{window}h'] = df_features.groupby(level='station_id')['bike_count'].transform(lambda x: x.rolling(window=window, min_periods=1).mean())

    # Final Cleanup: Drop NaN rows created by lag features
    initial_rows = len(df_features)
    df_features = df_features.dropna()
    print(f"Dropped {initial_rows - len(df_features)} rows containing NaN values (due to lags).")

    print("\n--- Feature Engineering Summary ---")
    print("Added cyclical time features (hour_sin/cos, day_of_week_sin/cos).")
    print(f"Added lag features for {lags} hours.")
    print(f"Added rolling mean features for {rolling_windows} hours.")
    print("Shape after feature engineering and NaN removal:", df_features.shape)
    print("First 5 rows after feature engineering:")
    print(df_features.head().to_string())
    print("Last 5 rows after feature engineering (to see full feature set):")
    print(df_features.tail().to_string())

    return df_features

# --- 2. Model Training ---

def train_model(df_features):
    """
    Prepares data for training, splits into train/test, trains an XGBoost MultiOutputRegressor,
    evaluates, and saves the model.
    """
    print("\n--- Starting Model Training ---")

    # Define features (X) and target (y)
    feature_cols = [col for col in df_features.columns if col not in ['bike_count']]
    
    # Target variables: bike_count for the next 1, 2, 3, 4, 5, 6 hours
    # Shift bike_count upwards (negative shift) to get future values
    target_lags = [-1, -2, -3, -4, -5, -6] # For t+1h, t+2h, ..., t+6h
    target_cols = [f'target_bike_count_t_{abs(lag)}h' for lag in target_lags]

    df_target = df_features.copy() # Create a copy for target generation
    for lag_val, target_col_name in zip(target_lags, target_cols):
        df_target[target_col_name] = df_target.groupby(level='station_id')['bike_count'].shift(lag_val)
    
    # Drop NaNs introduced by target shifting (last 6 hours of data for each station will have NaNs)
    df_target = df_target.dropna()

    # Align X and y after target shifting
    X = df_target[feature_cols]
    y = df_target[target_cols]

    print(f"Features (X) shape: {X.shape}")
    print(f"Targets (y) shape: {y.shape}")
    print("Target columns:", y.columns.tolist())

    # Split Data: Last 20% for testing, no shuffling
    # We need to ensure the split is done per station to maintain time series integrity.
    # However, for MultiIndex, splitting by index can be complex.
    # A simpler approach for time series: find the split point by timestamp.
    
    # Get unique timestamps and find the split point
    unique_timestamps = df_target.index.get_level_values('timestamp').unique().sort_values()
    split_point_idx = int(len(unique_timestamps) * 0.8)
    split_date = unique_timestamps[split_point_idx]

    X_train = X[X.index.get_level_values('timestamp') < split_date]
    y_train = y[y.index.get_level_values('timestamp') < split_date]
    X_test = X[X.index.get_level_values('timestamp') >= split_date]
    y_test = y[y.index.get_level_values('timestamp') >= split_date]

    print(f"Train data split date: {split_date}")
    print(f"X_train shape: {X_train.shape}, y_train shape: {y_train.shape}")
    print(f"X_test shape: {X_test.shape}, y_test shape: {y_test.shape}")

    # Build and Train Model
    print("Building and training XGBoost MultiOutputRegressor...")
    # Using a simple XGBoostRegressor. Hyperparameters can be tuned later.
    xgb_model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, random_state=42, n_jobs=-1)
    multi_output_model = MultiOutputRegressor(xgb_model)

    multi_output_model.fit(X_train, y_train)
    print("Model training complete.")

    # Evaluate Model
    print("\nEvaluating Model...")
    y_pred = multi_output_model.predict(X_test)
    
    # Convert predictions to DataFrame for easier evaluation
    y_pred_df = pd.DataFrame(y_pred, columns=y_test.columns, index=y_test.index)

    for i, col in enumerate(y_test.columns):
        mae = mean_absolute_error(y_test[col], y_pred_df[col])
        rmse = np.sqrt(mean_squared_error(y_test[col], y_pred_df[col]))
        print(f"  {col}: MAE = {mae:.2f}, RMSE = {rmse:.2f}")

    # Save Model
    model_output_path = os.path.join(DATA_DIR, 'xgboost_multioutput_model.joblib')
    feature_cols_path = os.path.join(DATA_DIR, 'feature_columns.joblib')
    
    joblib.dump(multi_output_model, model_output_path)
    joblib.dump(feature_cols, feature_cols_path) # Save feature column names for inference
    print(f"\nModel saved to '{model_output_path}'.")
    print(f"Feature columns saved to '{feature_cols_path}'.")

    return multi_output_model, feature_cols

# --- 3. Inference Function ---

def predict_user_time(model, feature_columns, df_last_hour_data, station_id, n_minutes):
    """
    Predicts bike count for a specific station at n_minutes in the future
    using the trained model and linear interpolation.

    Args:
        model: The trained MultiOutputRegressor model.
        feature_columns: List of feature columns used during training.
        df_last_hour_data (pd.DataFrame): DataFrame containing the *most recent* 
                                          features and actual bike_count for the given station.
                                          This should represent the "current state" for prediction.
                                          It should have a MultiIndex (station_id, timestamp)
                                          and contain the 'bike_count' and all feature columns needed.
        station_id (int): The ID of the station to predict for.
        n_minutes (int): The number of minutes into the future to predict (0 to 360, max 6 hours).

    Returns:
        int: Predicted bike count for the specified station and time.
    """
    if not (0 <= n_minutes <= 360): # 0 to 6 hours (360 minutes)
        raise ValueError("n_minutes must be between 0 and 360 (6 hours).")
    
    if station_id not in df_last_hour_data.index.get_level_values('station_id').unique():
        raise ValueError(f"Station ID {station_id} not found in the provided last hour data.")

    # Extract the last valid row for the specific station from df_last_hour_data
    # This row represents the "current" state for making the prediction
    current_data_point = df_last_hour_data.loc[station_id].sort_index().iloc[-1]
    current_bike_count = current_data_point['bike_count']
    
    # Create feature vector for prediction
    # Ensure the order of features matches the training data
    current_features = current_data_point[feature_columns].values.reshape(1, -1)
    
    # Make predictions (multi-hour output)
    hourly_predictions = model.predict(current_features)[0] # Array of 6 predictions: +1h, +2h, ..., +6h
    
    # Prediction intervals are 60 minutes apart
    # point_0_time = 0 minutes (current)
    # point_0_value = current_bike_count
    # point_1_time = 60 minutes
    # point_1_value = hourly_predictions[0]
    # ...
    # point_6_time = 360 minutes
    # point_6_value = hourly_predictions[5]

    if n_minutes == 0:
        return int(max(0, round(current_bike_count)))

    # Determine which two hourly predictions to interpolate between
    # Find the lower and upper bounds in hours
    lower_bound_h = math.floor(n_minutes / 60)
    upper_bound_h = math.ceil(n_minutes / 60)

    # Get values for interpolation
    if lower_bound_h == 0: # Interpolate between current and +1h prediction
        val1_time_min = 0
        val1_bike_count = current_bike_count
        val2_time_min = 60
        val2_bike_count = hourly_predictions[0]
    elif upper_bound_h > 6: # If predicting beyond 6 hours, just use the 6h prediction
        return int(max(0, round(hourly_predictions[5])))
    else: # Interpolate between two model predictions
        val1_time_min = lower_bound_h * 60
        val1_bike_count = hourly_predictions[lower_bound_h - 1] # -1 because array is 0-indexed for +1h, +2h...
        val2_time_min = upper_bound_h * 60
        val2_bike_count = hourly_predictions[upper_bound_h - 1]

    # Linear Interpolation
    # y = y1 + ((y2 - y1) / (x2 - x1)) * (x - x1)
    if val2_time_min == val1_time_min: # Should not happen unless n_minutes is exactly an hourly mark
        interpolated_bike_count = val1_bike_count
    else:
        interpolated_bike_count = val1_bike_count + \
                                  ((val2_bike_count - val1_bike_count) / (val2_time_min - val1_time_min)) * \
                                  (n_minutes - val1_time_min)
                                  
    return int(max(0, round(interpolated_bike_count)))


# --- Main execution block ---
if __name__ == '__main__':
    # Phase 1: Data Loading & Preprocessing
    df_preprocessed = load_data()
    if df_preprocessed is None:
        exit("Data loading failed.")
    
    # Phase 2: Feature Engineering
    df_features = create_features(df_preprocessed)
    if df_features is None: # Should not happen if df_preprocessed is not None, but for safety
        exit("Feature engineering failed.")

    # Phase 3: Model Training
    model, feature_cols = train_model(df_features)
    if model is None:
        exit("Model training failed.")

    print("\nAll phases complete: Data loading, preprocessing, feature engineering, and model training.")

    # --- Phase 4: Test Inference Function ---
    print("\n--- Testing Inference Function ---")
    
    # For testing, let's pick a random station and the last data point available after feature engineering
    # This simulates "current data" for prediction
    
    # Get all unique station_ids from the final feature DataFrame
    all_station_ids = df_features.index.get_level_values('station_id').unique().tolist()
    
    # Pick the first station ID for testing
    test_station_id = all_station_ids[0] 
    
    # Extract the full time series for the test station
    df_test_station = df_features.loc[test_station_id]

    # The predict_user_time function expects df_last_hour_data as a DataFrame
    # containing the *most recent* features and actual bike_count for the given station.
    # We will pass the full df_features for the test station, and the function
    # will internally select the last available data point.
    
    # Example predictions
    print(f"Test predictions for Station ID: {test_station_id}")
    
    for n_min in [0, 15, 30, 45, 60, 90, 120, 150, 180, 240, 300, 360]:
        try:
            predicted_bike_count = predict_user_time(model, feature_cols, df_features, test_station_id, n_min)
            print(f"  Predicted bike count for {n_min} minutes ahead: {predicted_bike_count}")
        except ValueError as ve:
            print(f"  Error predicting for {n_min} minutes: {ve}")
        except Exception as e:
            print(f"  An unexpected error occurred during prediction for {n_min} minutes: {e}")
