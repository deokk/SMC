import os
import sys
from sqlalchemy import text

# 광진구만 걸러주는 코드
# Add the parent directory to the path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import engine

def filter_data_with_join():
    """
    Filters historical bike data for Gwangjin-gu stations using a direct SQL JOIN
    and inserts the result into the 'bike_availability_historical_gwangjin' table.
    """
    source_table = "bike_availability_historical"
    gwangjin_stations_table = "stations_gwangjin"
    target_table = "bike_availability_historical_gwangjin"

    print("Starting data filtering process using SQL JOIN as instructed.")

    # This is the SQL query that performs the filtering using a JOIN.
    # It selects all records from the source table that have a matching
    # station_number in the gwangjin stations table.
    sql_query = f"""
        INSERT INTO {target_table}
        SELECT t1.*
        FROM {source_table} AS t1
        JOIN {gwangjin_stations_table} AS t2 ON t1.station_number = t2.station_number;
    """

    try:
        with engine.begin() as connection:
            # Step 1: Clear the target table to ensure no duplicate data
            print(f"Clearing existing data from the target table: '{target_table}'...")
            connection.execute(text(f"DELETE FROM {target_table}"))
            print("Target table cleared.")

            # Step 2: Execute the main INSERT...SELECT query
            print("Executing JOIN query to filter and insert Gwangjin data...")
            result = connection.execute(text(sql_query))
            
            # result.rowcount provides the number of rows affected by the INSERT
            inserted_count = result.rowcount
            print(f"Successfully inserted {inserted_count} rows of Gwangjin data into '{target_table}'.")

    except Exception as e:
        print(f"\nAn error occurred during the database operation: {e}")

if __name__ == "__main__":
    filter_data_with_join()