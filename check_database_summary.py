
import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text

# Add the parent directory to the path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import engine

def check_database_summary():
    """
    Provides a summary of the historical data tables and saves a sample of Gwangjin data to a CSV file.
    """
    historical_table = "bike_availability_historical"
    gwangjin_table = "bike_availability_historical_gwangjin"
    output_csv_path = "gwangjin_sample.csv"

    print("Connecting to the database to generate a data summary...")

    with engine.connect() as connection:
        try:
            # 1. Check the original historical table
            print(f"\n--- Analyzing Original Table: {historical_table} ---")
            hist_count = connection.execute(text(f"SELECT COUNT(*) FROM {historical_table}")).scalar_one_or_none()
            print(f"Total rows: {hist_count}")

            if hist_count > 0:
                min_ts, max_ts = connection.execute(text(f"SELECT MIN(timestamp), MAX(timestamp) FROM {historical_table}")).one()
                print(f"Data time range: From '{min_ts}' To '{max_ts}'")
            else:
                print("Original historical table is empty.")

            # 2. Check the Gwangjin filtered table
            print(f"\n--- Analyzing Gwangjin Table: {gwangjin_table} ---")
            gwangjin_count = connection.execute(text(f"SELECT COUNT(*) FROM {gwangjin_table}")).scalar_one_or_none()
            print(f"Total rows: {gwangjin_count}")

            # 3. Save a sample of Gwangjin data to CSV
            if gwangjin_count > 0:
                print(f"\nSaving a sample of Gwangjin data to '{output_csv_path}'...")
                gwangjin_df = pd.read_sql(text(f"SELECT * FROM {gwangjin_table}"), connection)
                
                # Ensure correct encoding for Korean characters
                gwangjin_df.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
                print(f"Successfully saved {len(gwangjin_df)} rows to '{output_csv_path}'.")
                print("Please open this file to check the station names.")
            else:
                print(f"Gwangjin data table is empty, so no sample file was created.")

        except Exception as e:
            print(f"\nAn error occurred during the database summary check: {e}")
            print("It's possible the tables do not exist yet.")

if __name__ == "__main__":
    check_database_summary()
