from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, Table, MetaData, func, String
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, date
from pydantic import BaseModel, Field
import logging


# db.database 모듈에서 엔진과 세션 의존성 주입 함수 가져오기
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from db.database import engine, get_db
from services.route_service import RouteService
from backend.crud import user_crud
from backend.schemas.user_schemas import (
    User, 
    UserCreate, 
    UserResponse, 
    RouteRequest, 
    RouteResponse, 
    PersonalizedPatternResponse
)

# FastAPI 앱 인스턴스 생성
app = FastAPI()

# --- 모든 Pydantic 모델 정의 ---

class StationRealtime(BaseModel):
    station_id: str
    station_number: Optional[int] = None
    station_display_name: Optional[str] = None
    timestamp: datetime
    latitude: float
    longitude: float
    available_bikes: int
    station_capacity: int
    available_racks: int
    is_stockout: int
    hour: int
    day_of_week: int
    is_weekend: int
    air_quality_pm10: Optional[int] = None
    air_quality_pm25: Optional[int] = None
    air_quality_o3: Optional[float] = None
    air_quality_no2: Optional[float] = None
    air_quality_co: Optional[float] = None
    air_quality_so2: Optional[float] = None
    air_quality_data_time: Optional[str] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    precipitation: Optional[float] = None
    wind_speed: Optional[float] = None
    is_raining: Optional[int] = None
    weather_severity: Optional[int] = None
    weather_timestamp: Optional[datetime] = None
    weather_source: Optional[str] = None

    class Config:
        from_attributes = True

class HistoricalDataPoint(BaseModel):
    timestamp: datetime
    avg_available_bikes: float

class HourlyComparisonPoint(BaseModel):
    hour: int
    timestamp: datetime
    avg_available_bikes: float

class DailyHourlyComparisonResponse(BaseModel):
    date: date
    hourly_data: List[HourlyComparisonPoint]

class HistoricalComparisonResult(BaseModel):
    today: Optional[DailyHourlyComparisonResponse] = None
    yesterday: Optional[DailyHourlyComparisonResponse] = None
    two_days_ago: Optional[DailyHourlyComparisonResponse] = None
    last_week: Optional[DailyHourlyComparisonResponse] = None

# --- SQLAlchemy 테이블 리플렉션 ---
metadata = MetaData()
BikeAvailabilityRealtime = Table("bike_availability_realtime", metadata, autoload_with=engine)
BikeAvailabilityHistorical = Table("bike_availability_historical", metadata, autoload_with=engine)
try:
    StationsGwangjin = Table("stations_gwangjin", metadata, autoload_with=engine)
    TransitStops = Table("transit_stops", metadata, autoload_with=engine)
except Exception as e:
    StationsGwangjin = None
    TransitStops = None
    print(f"Warning: Could not reflect tables. {e}")


# --- API 엔드포인트 정의 ---

@app.get("/")
def read_root():
    return {"message": "SMC 프로젝트 백엔드 서버에 오신 것을 환영합니다!"}

@app.post("/users/register", response_model=UserResponse)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    새로운 사용자를 등록합니다.
    - 사용자 이름 또는 이메일이 이미 존재하면 400 에러를 반환합니다.
    """
    db_user_by_username = user_crud.get_user_by_username(db, username=user.username)
    if db_user_by_username:
        raise HTTPException(status_code=400, detail="이미 등록된 사용자 이름입니다.")
    
    db_user_by_email = user_crud.get_user_by_email(db, email=user.email)
    if db_user_by_email:
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")
        
    created_user = user_crud.create_user(db=db, user=user)
    return created_user

@app.get("/users/{user_id}/patterns", response_model=PersonalizedPatternResponse)
def get_user_patterns(user_id: int, db: Session = Depends(get_db)):
    """
    사용자의 개인화된 라이딩 패턴을 반환합니다. (현재는 플레이스홀더)
    - TODO: 실제 사용자 데이터 기반 분석 로직 구현 필요
    """
    # Check if user exists
    db_user = user_crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return PersonalizedPatternResponse(
        message="Personalized pattern analysis is under development.",
        favorite_station_id="ST-509",
        avg_duration_minutes=15.5,
        total_trips=42
    )

@app.post("/route/optimized", response_model=RouteResponse)
async def get_optimized_route(request: RouteRequest, db: Session = Depends(get_db)):
    """
    출발지와 도착지를 받아 최적화된 경로를 반환합니다. (현재는 플레이스홀더)
    - TODO: 실제 경로 탐색 및 대중교통 API 연동 로직 구현 필요
    """
    return RouteResponse(
        message="Route optimization is under development.",
        path=[
            {"type": "WALK", "duration": "5 mins", "distance": "400m"},
            {"type": "BIKE", "station_id": "ST-123", "duration": "10 mins", "distance": "1.5km"},
            {"type": "WALK", "duration": "3 mins", "distance": "250m"}
        ]
    )


@app.get("/stations/realtime", response_model=List[StationRealtime])
def get_realtime_stations(
    db: Session = Depends(get_db),
    station_id: Optional[str] = None,
    station_number: Optional[str] = None,
    station_display_name: Optional[str] = None
):
    query = select(BikeAvailabilityRealtime)
    
    if station_id:
        query = query.where(BikeAvailabilityRealtime.c.station_id == station_id)
    if station_number:
        query = query.where(BikeAvailabilityRealtime.c.station_number.cast(String).ilike(f"%{station_number}%"))
    if station_display_name:
        query = query.where(BikeAvailabilityRealtime.c.station_display_name.ilike(f"%{station_display_name}%"))

    result = db.execute(query).fetchall()
    
    response_data = [StationRealtime.model_validate(row._asdict()) for row in result]
    return response_data

@app.get("/stations/{station_id}/hourly_comparison", response_model=HistoricalComparisonResult)
def get_hourly_comparison_data(
    station_id: str,
    db: Session = Depends(get_db)
):
    try:
        result = HistoricalComparisonResult()
        now = datetime.now()

        comparison_dates = {
            "today": now,
            "yesterday": now - timedelta(days=1),
            "two_days_ago": now - timedelta(days=2),
            "last_week": now - timedelta(weeks=1)
        }

        for period_name, target_datetime in comparison_dates.items():
            table_to_query = BikeAvailabilityRealtime if period_name == "today" else BikeAvailabilityHistorical
            start_of_day = target_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = target_datetime.replace(hour=23, minute=59, second=59, microsecond=999999)

            query = (
                select(
                    func.date_trunc('hour', table_to_query.c.timestamp).label('hour_timestamp'),
                    func.avg(table_to_query.c.available_bikes).label('avg_bikes')
                )
                .where(table_to_query.c.station_id == station_id)
                .where(table_to_query.c.timestamp >= start_of_day)
                .where(table_to_query.c.timestamp <= end_of_day)
                .group_by('hour_timestamp')
                .order_by('hour_timestamp')
            )
            
            hourly_data_raw = db.execute(query).fetchall()
            
            if hourly_data_raw:
                hourly_comparison_points = [
                    HourlyComparisonPoint(
                        hour=row.hour_timestamp.hour,
                        timestamp=row.hour_timestamp,
                        avg_available_bikes=round(row.avg_bikes, 2)
                    ) for row in hourly_data_raw
                ]
                
                daily_hourly_response = DailyHourlyComparisonResponse(
                    date=target_datetime.date(),
                    hourly_data=hourly_comparison_points
                )
                setattr(result, period_name, daily_hourly_response)
        
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@app.get("/stations/{station_id}/historical", response_model=List[HistoricalDataPoint])
def get_station_historical_data(
    station_id: str,
    period: str,
    db: Session = Depends(get_db)
):
    now = datetime.now()
    if period == 'yesterday':
        start_time = now - timedelta(days=1)
    elif period == '2days':
        start_time = now - timedelta(days=2)
    elif period == 'week':
        start_time = now - timedelta(days=7)
    else:
        raise HTTPException(status_code=400, detail="Invalid period specified. Use 'yesterday', '2days', or 'week'.")
    end_time = now

    query = (
        select(
            func.date_trunc('hour', BikeAvailabilityHistorical.c.timestamp).label('hour_timestamp'),
            func.avg(BikeAvailabilityHistorical.c.available_bikes).label('avg_bikes')
        )
        .where(BikeAvailabilityHistorical.c.station_id == station_id)
        .where(BikeAvailabilityHistorical.c.timestamp >= start_time)
        .where(BikeAvailabilityHistorical.c.timestamp <= end_time)
        .group_by('hour_timestamp')
        .order_by('hour_timestamp')
    )

    result = db.execute(query).fetchall()

    return [
        HistoricalDataPoint(
            timestamp=row.hour_timestamp,
            avg_available_bikes=round(row.avg_bikes, 2)
        ) for row in result
    ] if result else []

@app.get("/stations/realtime/raw", response_model=List[StationRealtime])
def get_raw_realtime_stations(
    db: Session = Depends(get_db),
    station_id: Optional[str] = None
):
    query = select(BikeAvailabilityRealtime)
    
    if station_id:
        query = query.where(BikeAvailabilityRealtime.c.station_id == station_id)

    result = db.execute(query).fetchall()
    
    response_data = [StationRealtime.model_validate(row._asdict()) for row in result]
    return response_data
