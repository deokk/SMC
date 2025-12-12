# lstm_model_trainer.py
import os
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import tensorflow as tf
from tensorflow.keras.models import Model
from tensorflow.keras.layers import LSTM, Input, Dense
from tensorflow.keras.callbacks import EarlyStopping
import joblib

# --- 1. Configuration & Constants ---
# Use a smaller subset of stations and shorter time period for faster development/testing
# Set to False to use all data
IS_DEV_MODE = False

# Path settings
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(DATA_DIR, 'gwangjin_2024_data.csv')
MODEL_SAVE_PATH = os.path.join(DATA_DIR, 'AI/models/lstm_model.h5')
SCALER_SAVE_PATH = os.path.join(DATA_DIR, 'AI/models/scaler.pkl')

# Model & Data sequence settings
INPUT_SEQUENCE_LENGTH = 168  # 7 days of hourly data
OUTPUT_SEQUENCE_LENGTH = 96   # 4 days of hourly data

# --- 2. Data Loading & Preprocessing ---
def load_and_preprocess_data():
    """
    Loads and preprocesses the raw bike count data.
    - Creates a continuous hourly time series for each station.
    - Fills missing values.
    - Adds time-based cyclical features.
    """
    print("Step 2: Loading and preprocessing data...")
    df = pd.read_csv(DATA_PATH, encoding='cp949')

    # Basic renaming and type conversion
    df.columns = ['date', 'station_id', 'station_name', 'hour', 'bike_count']
    df['timestamp'] = pd.to_datetime(df['date']) + pd.to_timedelta(df['hour'], unit='h')
    df['bike_count'] = pd.to_numeric(df['bike_count'], errors='coerce')

    # Handle duplicates
    df = df.groupby(['station_id', 'timestamp'], as_index=False).agg({
        'bike_count': 'mean',
        'station_name': 'first' 
    }).dropna(subset=['station_id'])
    
    df['station_id'] = df['station_id'].astype(int)

    # In DEV_MODE, use only a few stations for speed
    if IS_DEV_MODE:
        unique_stations = df['station_id'].unique()
        if len(unique_stations) > 5:
            df = df[df['station_id'].isin(unique_stations[:5])]
        print(f"--- DEVELOPMENT MODE: Using {len(df['station_id'].unique())} stations ---")


    # Create a complete time-series index for each station
    df = df.set_index(['station_id', 'timestamp']).sort_index()
    
    start_date = df.index.get_level_values('timestamp').min()
    end_date = df.index.get_level_values('timestamp').max()

    # If in DEV_MODE, shorten the date range to speed up processing
    if IS_DEV_MODE:
        end_date = start_date + pd.Timedelta(days=30)
        df = df.loc[(slice(None), slice(start_date, end_date)), :]
        print(f"--- DEVELOPMENT MODE: Using data from {start_date} to {end_date} ---")


    full_index = pd.MultiIndex.from_product(
        [df.index.get_level_values('station_id').unique(),
         pd.date_range(start=start_date, end=end_date, freq='h')],
        names=['station_id', 'timestamp']
    )
    df = df.reindex(full_index)

    # Interpolate missing values and fill the rest
    df['bike_count'] = df.groupby(level='station_id')['bike_count'].transform(
        lambda x: x.interpolate(method='linear', limit_direction='both')
    )
    df['bike_count'] = df['bike_count'].fillna(0)

    # Feature Engineering: Add cyclical time features
    df_features = df.reset_index()
    df_features['hour_sin'] = np.sin(2 * np.pi * df_features['timestamp'].dt.hour / 24)
    df_features['hour_cos'] = np.cos(2 * np.pi * df_features['timestamp'].dt.hour / 24)
    df_features['day_of_week_sin'] = np.sin(2 * np.pi * df_features['timestamp'].dt.dayofweek / 7)
    df_features['day_of_week_cos'] = np.cos(2 * np.pi * df_features['timestamp'].dt.dayofweek / 7)
    
    # The features to be used by the model
    feature_cols = ['bike_count', 'hour_sin', 'hour_cos', 'day_of_week_sin', 'day_of_week_cos']
    df_final = df_features[['station_id', 'timestamp'] + feature_cols]
    
    print("Data preprocessing complete.")
    return df_final, feature_cols

# --- 3. Data Scaling & Sequencing ---
def scale_and_sequence_data(df, feature_cols):
    """
    Scales the data and creates input/output sequences for the LSTM model.
    """
    print("Step 3: Scaling data and creating sequences...")
    
    # We scale features per station to handle different scales of bike counts
    station_dfs = []
    scalers = {}
    
    for station_id, group in df.groupby('station_id'):
        scaler = MinMaxScaler()
        scaled_features = scaler.fit_transform(group[feature_cols])
        
        scaled_df = pd.DataFrame(scaled_features, columns=feature_cols, index=group.index)
        scaled_df['station_id'] = station_id
        station_dfs.append(scaled_df)
        scalers[station_id] = scaler

    df_scaled = pd.concat(station_dfs)

    # Create sequences
    X, y = [], []
    total_len = INPUT_SEQUENCE_LENGTH + OUTPUT_SEQUENCE_LENGTH
    
    for station_id, group in df_scaled.groupby('station_id'):
        data = group[feature_cols].values
        for i in range(len(data) - total_len + 1):
            X.append(data[i : i + INPUT_SEQUENCE_LENGTH])
            # Target is only the 'bike_count' column for the output sequence
            y.append(data[i + INPUT_SEQUENCE_LENGTH : i + total_len, 0])

    # Save the dictionary of scalers
    joblib.dump(scalers, SCALER_SAVE_PATH)
    print(f"Scalers saved to {SCALER_SAVE_PATH}")
    
    return np.array(X), np.array(y).reshape(-1, OUTPUT_SEQUENCE_LENGTH, 1)

# --- 4. Model Building ---
def build_lstm_model(n_features):
    """
    Builds the LSTM Encoder-Decoder (Seq2Seq) model.
    """
    print("Step 4: Building the LSTM model...")
    
    # Encoder
    encoder_inputs = Input(shape=(INPUT_SEQUENCE_LENGTH, n_features))
    # Using 64 units for the LSTM layer. This can be tuned.
    encoder_lstm = LSTM(64, return_state=True) 
    _, state_h, state_c = encoder_lstm(encoder_inputs)
    encoder_states = [state_h, state_c]

    # Decoder
    decoder_inputs = Input(shape=(None, 1)) # Decoder input shape
    decoder_lstm = LSTM(64, return_sequences=True, return_state=True)
    
    # For simplicity, we won't use a teacher-forcing setup here.
    # We will feed the encoder's final state to the decoder and predict 96 steps.
    # A more advanced approach would be to feed the output of each step back to the input of the next.
    # Here, we will use a simpler RepeatVector approach.
    
    # Let's simplify the model for this first pass to ensure it runs.
    # A simple LSTM that just outputs a Dense layer is easier to start with.
    
    inputs = Input(shape=(INPUT_SEQUENCE_LENGTH, n_features))
    # Using tanh activation (default and more stable for LSTMs) instead of relu
    lstm_out = LSTM(100)(inputs)
    outputs = Dense(OUTPUT_SEQUENCE_LENGTH)(lstm_out)
    
    model = Model(inputs=inputs, outputs=outputs)
    
    # Use an optimizer with gradient clipping to prevent exploding gradients
    optimizer = tf.keras.optimizers.Adam(clipvalue=1.0)
    
    model.compile(optimizer=optimizer, loss='mse')
    
    model.summary()
    return model

# --- 5. Main Execution ---
if __name__ == "__main__":
    print("--- Starting LSTM Model Training Pipeline ---")
    
    # Step 1 is implicit (running the script)
    df_processed, feature_cols = load_and_preprocess_data()
    
    if df_processed is not None and not df_processed.empty:
        X, y = scale_and_sequence_data(df_processed, feature_cols)
        
        # --- Data Integrity Check ---
        if np.isnan(X).any() or np.isinf(X).any() or np.isnan(y).any() or np.isinf(y).any():
            raise ValueError("NaN or Inf found in training data. Halting.")
            
        if X.shape[0] > 0:
            print(f"Created {X.shape[0]} sequences for training.")
            n_features = X.shape[2]
            
            model = build_lstm_model(n_features)
            
            print("\nStep 5: Training the model...")
            
            # Using a validation split and early stopping to prevent overfitting
            early_stopping = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)
            
            # Use a small number of epochs if in DEV_MODE
            epochs = 5 if IS_DEV_MODE else 50
            batch_size = 32
            
            model.fit(X, y, epochs=epochs, batch_size=batch_size, validation_split=0.2, callbacks=[early_stopping])
            
            # Ensure the target directory exists
            os.makedirs(os.path.dirname(MODEL_SAVE_PATH), exist_ok=True)
            
            model.save(MODEL_SAVE_PATH)
            print(f"--- Model training complete. Model saved to {MODEL_SAVE_PATH} ---")
            
        else:
            print("Could not create any training sequences. Check data size and sequence lengths.")
    else:
        print("Data loading failed. Halting pipeline.")
