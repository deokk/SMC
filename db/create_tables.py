# db/create_tables.py
import sys
import os
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    String,
    DateTime,
    Float,
    Integer,
    PrimaryKeyConstraint
)

# Add the parent directory to the path to allow imports from db
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
# Import the central engine and Base
from db.database import engine, Base

# Import all ORM models to register them with the Base's metadata
from backend.models.user import User
from backend.models.ride import UserRideHistory
from backend.models.friend import Friend

metadata = MetaData()

# Define the schema for bike_availability_realtime
bike_availability_realtime = Table(
    "bike_availability_realtime",
    metadata,
    Column("station_id", String, primary_key=True),
    Column("station_number", Integer),
    Column("station_display_name", String),
    Column("timestamp", DateTime, primary_key=True),
    Column("latitude", Float),
    Column("longitude", Float),
    Column("available_bikes", Integer),
    Column("station_capacity", Integer),
    Column("available_racks", Integer),
    Column("is_stockout", Integer),
    Column("hour", Integer),
    Column("day_of_week", Integer),
    Column("is_weekend", Integer),
    Column("air_quality_pm10", Integer, nullable=True),
    Column("air_quality_pm25", Integer, nullable=True),
    Column("air_quality_o3", Float, nullable=True),
    Column("air_quality_no2", Float, nullable=True),
    Column("air_quality_co", Float, nullable=True),
    Column("air_quality_so2", Float, nullable=True),
    Column("air_quality_data_time", String, nullable=True),
    Column("air_source", String, nullable=True),
    Column("temperature", Float, nullable=True),
    Column("humidity", Float, nullable=True),
    Column("precipitation", Float, nullable=True),
    Column("wind_speed", Float, nullable=True),
    Column("is_raining", Integer, nullable=True),
    Column("weather_severity", Integer, nullable=True),
    Column("weather_timestamp", DateTime, nullable=True),
    Column("weather_source", String, nullable=True),
)

# Define the schema for bike_availability_historical
bike_availability_historical = Table(
    "bike_availability_historical",
    metadata,
    Column("station_id", String, primary_key=True),
    Column("station_number", Integer),
    Column("station_display_name", String),
    Column("timestamp", DateTime, primary_key=True),
    Column("latitude", Float),
    Column("longitude", Float),
    Column("available_bikes", Integer),
    Column("station_capacity", Integer),
    Column("available_racks", Integer),
    Column("is_stockout", Integer),
    Column("hour", Integer),
    Column("day_of_week", Integer),
    Column("is_weekend", Integer),
    Column("air_quality_pm10", Integer, nullable=True),
    Column("air_quality_pm25", Integer, nullable=True),
    Column("air_quality_o3", Float, nullable=True),
    Column("air_quality_no2", Float, nullable=True),
    Column("air_quality_co", Float, nullable=True),
    Column("air_quality_so2", Float, nullable=True),
    Column("air_quality_data_time", String, nullable=True),
    Column("air_source", String, nullable=True),
    Column("temperature", Float, nullable=True),
    Column("humidity", Float, nullable=True),
    Column("precipitation", Float, nullable=True),
    Column("wind_speed", Float, nullable=True),
    Column("is_raining", Integer, nullable=True),
    Column("weather_severity", Integer, nullable=True),
    Column("weather_timestamp", DateTime, nullable=True),
    Column("weather_source", String, nullable=True),
)

# Define the schema for stations_gwangjin
stations_gwangjin = Table(
    "stations_gwangjin",
    metadata,
    Column("station_number", Integer, primary_key=True),
    Column("station_name", String),
    Column("district", String),
    Column("address", String),
    Column("latitude", Float), # Add latitude
    Column("longitude", Float), # Add longitude
)

# Define the schema for transit_stops
transit_stops = Table(
    "transit_stops",
    metadata,
    Column("stop_id", String, primary_key=True),
    Column("stop_name", String),
    Column("stop_type", String), # e.g., 'subway', 'bus'
    Column("latitude", Float),
    Column("longitude", Float),
)


def create_tables():
    """
    Connects to the database and creates all necessary tables if they don't exist.
    """
    try:
        print("Creating tables in the database if they don't exist...")
        # Create all tables defined via declarative_base (User, UserRideHistory, Friend)
        # By importing them, they are registered with the central Base metadata.
        Base.metadata.create_all(engine, checkfirst=True)
        
        # Create tables defined manually via MetaData
        metadata.create_all(engine, checkfirst=True)
        print("Tables created successfully (if they didn't already exist).")
    except Exception as e:
        print(f"An error occurred during table creation: {e}")

if __name__ == "__main__":
    create_tables()
