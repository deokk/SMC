
import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text

# Add the parent directory to the path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.database import engine

def check_gwangjin_table():
    """
    Checks the contents of the bike_availability_historical_gwangjin table.
    """
    table_name = "bike_availability_historical_gwangjin"
    
    with engine.connect() as connection:
        try:
            # 1. Get the total row count
            count_query = text(f"SELECT COUNT(*) FROM {table_name}")
            result = connection.execute(count_query).scalar_one_or_none()
            print(f"Total rows in '{table_name}': {result}")

            if result is not None and result > 0:
                # 2. Fetch and display the first 10 rows
                print(f"\nFirst 10 rows from '{table_name}':")
                select_query = text(f"SELECT * FROM {table_name} LIMIT 10")
                df = pd.read_sql(select_query, connection)
                print(df.to_string())
            else:
                print(f"The table '{table_name}' is empty or does not exist.")

        except Exception as e:
            print(f"An error occurred while checking the table: {e}")

if __name__ == "__main__":
    check_gwangjin_table()
