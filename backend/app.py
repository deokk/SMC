import math
import httpx
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import select, Table, MetaData, func, String
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta, date
from pydantic import BaseModel, Field, EmailStr
import logging
import redis
import json
import asyncio


# db.database 모듈에서 엔진과 세션 의존성 주입 함수 가져오기
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from db.database import engine, get_db
from db.redis_db import get_redis_conn # Redis 의존성 추가
from services.route_service import RouteService
from backend import security
from backend.crud import user_crud
from backend.schemas.user_schemas import (
    User, 
    UserCreate, 
    UserResponse, 
    RouteRequest, 
    RouteResponse, 
    PersonalizedPatternResponse,
    RiderLocation,
    NearestStationInfo,
    RouteSegment
)
from backend.schemas.ride_schemas import RideStartRequest, RideEndRequest, RideResponse
from backend.crud import ride_crud
from backend.models.ride import UserRideHistory # For type hinting and ORM operations

# FastAPI 앱 인스턴스 생성
app = FastAPI()

# --- CORS 미들웨어 설정 ---
# 개발 환경에서는 모든 오리진을 허용합니다.
# 프로덕션 환경에서는 특정 프론트엔드 주소만 허용하도록 변경해야 합니다.
origins = [
    "http://localhost",
    "http://localhost:3000", # React 기본 포트
    "http://localhost:8080", # Vue 기본 포트
    "http://localhost:4200", # Angular 기본 포트
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- 환경 변수 로드 ---
MAP_API_KEY = os.getenv("MAP_API_KEY")


# --- 모든 Pydantic 모델 정의 ---

class Token(BaseModel):
    access_token: str
    token_type: str

class LocationUpdate(BaseModel):
    """라이더 위치 업데이트 요청을 위한 모델"""
    latitude: float = Field(..., example=37.5665)
    longitude: float = Field(..., example=126.9780)

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
    db_user_by_username = user_crud.get_user_by_username(db, username=user.username)
    if db_user_by_username:
        raise HTTPException(status_code=400, detail="이미 등록된 사용자 이름입니다.")
    
    db_user_by_email = user_crud.get_user_by_email(db, email=user.email)
    if db_user_by_email:
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")
        
    created_user = user_crud.create_user(db=db, user=user)
    return created_user

@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    user = user_crud.get_user_by_username(db, username=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/riders/{rider_id}/location", status_code=204)
async def update_rider_location(
    rider_id: str,
    location: LocationUpdate,
    redis_conn: redis.Redis = Depends(get_redis_conn)
):
    key = f"rider_location:{rider_id}"
    data = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "timestamp": datetime.now().isoformat()
    }
    redis_conn.setex(key, timedelta(hours=1), json.dumps(data))
    return None

@app.get("/riders/{rider_id}/track", response_model=RiderLocation)
async def track_rider(rider_id: str, redis_conn: redis.Redis = Depends(get_redis_conn)):
    key = f"rider_location:{rider_id}"
    data = redis_conn.get(key)
    
    if not data:
        raise HTTPException(status_code=404, detail="Rider location not found.")
    
    location_data = json.loads(data)
    
    return RiderLocation(
        rider_id=rider_id,
        latitude=location_data["latitude"],
        longitude=location_data["longitude"],
        timestamp=datetime.fromisoformat(location_data["timestamp"])
    )

@app.websocket("/ws/track/{rider_id}")
async def websocket_track_rider(
    websocket: WebSocket,
    rider_id: str,
    redis_conn: redis.Redis = Depends(get_redis_conn)
):
    await websocket.accept()
    last_timestamp = None
    key = f"rider_location:{rider_id}"
    
    try:
        while True:
            data = redis_conn.get(key)
            if data:
                location_data = json.loads(data)
                current_timestamp = location_data["timestamp"]
                
                if current_timestamp != last_timestamp:
                    await websocket.send_json(location_data)
                    last_timestamp = current_timestamp
            
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        print(f"Client {websocket.client} disconnected from tracking rider {rider_id}")
    except Exception as e:
        print(f"An error occurred in websocket for rider {rider_id}: {e}")
    finally:
        await websocket.close()

@app.get("/users/{user_id}/patterns", response_model=PersonalizedPatternResponse)
def get_user_patterns(user_id: int, db: Session = Depends(get_db)):
    return PersonalizedPatternResponse(
        message="Personalized pattern analysis is under development.",
        favorite_station_id="ST-509",
        avg_duration_minutes=15.5,
        total_trips=42
    )

@app.post("/rides/start", response_model=RideResponse)
def start_ride(
    ride_request: RideStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(security.get_current_user)
):
    """
    사용자의 새로운 운행을 시작합니다.
    """
    active_ride = ride_crud.get_active_ride_by_user(db, user_id=current_user.id)
    if active_ride:
        raise HTTPException(status_code=400, detail="이미 운행 중인 기록이 있습니다. 기존 운행을 먼저 종료해주세요.")

    nearest_station = find_nearest_station(ride_request.latitude, ride_request.longitude, db)
    if not nearest_station:
        raise HTTPException(status_code=404, detail="시작 지점 근처의 따릉이 대여소를 찾을 수 없습니다.")
    
    db_ride = ride_crud.create_ride(
        db=db,
        user_id=current_user.id,
        start_station_id=nearest_station.station_id,
        start_time=datetime.now()
    )
    return db_ride

@app.post("/rides/end", response_model=RideResponse)
def end_ride(
    ride_request: RideEndRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(security.get_current_user)
):
    """
    사용자의 현재 운행을 종료합니다.
    """
    active_ride = ride_crud.get_active_ride_by_user(db, user_id=current_user.id)
    if not active_ride:
        raise HTTPException(status_code=400, detail="현재 운행 중인 기록이 없습니다. 먼저 운행을 시작해주세요.")

    nearest_station = find_nearest_station(ride_request.latitude, ride_request.longitude, db)
    if not nearest_station:
        raise HTTPException(status_code=404, detail="종료 지점 근처의 따릉이 대여소를 찾을 수 없습니다.")

    db_ride = ride_crud.end_ride(
        db=db,
        ride_id=active_ride.id,
        end_station_id=nearest_station.station_id,
        end_time=datetime.now()
    )
    if not db_ride:
        raise HTTPException(status_code=500, detail="운행 기록을 업데이트하는 데 실패했습니다.")
    
    return db_ride

@app.get("/users/me/rides", response_model=List[RideResponse])
def get_my_ride_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(security.get_current_user)
):
    """
    현재 로그인된 사용자의 모든 운행 기록을 조회합니다.
    """
    rides = ride_crud.get_rides_by_user(db, user_id=current_user.id)
    return [RideResponse.model_validate(ride) for ride in rides]

# --- 경로 최적화 도우미 함수 ---

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371e3
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def find_nearest_station(latitude: float, longitude: float, db: Session) -> Optional[NearestStationInfo]:
    stations_query = select(
        BikeAvailabilityRealtime.c.station_id,
        BikeAvailabilityRealtime.c.station_display_name,
        BikeAvailabilityRealtime.c.latitude,
        BikeAvailabilityRealtime.c.longitude,
        BikeAvailabilityRealtime.c.available_bikes
    )
    all_stations = db.execute(stations_query).fetchall()

    if not all_stations:
        return None

    stations_with_dist = [(s, haversine_distance(latitude, longitude, s.latitude, s.longitude)) for s in all_stations]
    stations_with_dist.sort(key=lambda x: x[1])

    for station, dist in stations_with_dist:
        if station.available_bikes > 0:
            return NearestStationInfo(
                station_id=station.station_id,
                station_display_name=station.station_display_name,
                latitude=station.latitude,
                longitude=station.longitude,
                distance_m=round(dist)
            )
    return None

async def get_kakao_directions(start_lon: float, start_lat: float, end_lon: float, end_lat: float, api_key: str) -> Optional[Dict[str, Any]]:
    """카카오 모빌리티 API를 호출하여 대중교통 길찾기 결과를 가져옵니다."""
    url = "https://apis-navi.kakaomobility.com/v1/directions"
    headers = {"Authorization": f"KakaoAK {api_key}"}
    params = {
        "origin": f"{start_lon},{start_lat}",
        "destination": f"{end_lon},{end_lat}",
        "alternatives": "false" # 가장 좋은 경로 1개만 받기
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logging.error(f"Kakao API request failed: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logging.error(f"An unexpected error occurred during Kakao API call: {e}")
            return None

@app.post("/route/optimized", response_model=RouteResponse)
async def get_optimized_route(request: RouteRequest, db: Session = Depends(get_db)):
    if not MAP_API_KEY:
        raise HTTPException(status_code=500, detail="MAP_API_KEY is not configured on the server.")

    # 1. 카카오 API로 대중교통 경로 조회
    kakao_data = await get_kakao_directions(request.start_lon, request.start_lat, request.end_lon, request.end_lat, MAP_API_KEY)
    
    if not kakao_data or not kakao_data.get("routes"):
        raise HTTPException(status_code=503, detail="Could not retrieve route from external API.")

    # 2. 대중교통 승하차 지점 좌표 추출
    sections = kakao_data["routes"][0].get("sections", [])
    # 'mode'가 'BUS' 또는 'SUBWAY'인 section만 대중교통 구간으로 간주
    transit_sections = [s for s in sections if s.get("mode") in ["BUS", "SUBWAY"]]
    
    if not transit_sections:
        # 대중교통 구간이 없는 경우 (도보 전용 경로 등)
        start_station = find_nearest_station(request.start_lat, request.start_lon, db)
        end_station = find_nearest_station(request.end_lat, request.end_lon, db)
        if not start_station or not end_station:
            raise HTTPException(status_code=404, detail="Could not find any nearby stations for this walking route.")
        
        # 이 경우, first_mile에 전체 구간의 대여소 정보를 담아 응답
        segment = RouteSegment(start_station=start_station, end_station=end_station)
        return RouteResponse(
            message="This is a walking-only route. Found nearest stations for the whole journey.",
            path=sections,
            first_mile=segment
        )

    # 대중교통 시작 지점과 끝 지점 좌표
    transit_start_lon, transit_start_lat = transit_sections[0]["guides"][0]["x"], transit_sections[0]["guides"][0]["y"]
    last_transit_section_guides = transit_sections[-1]["guides"]
    transit_end_lon, transit_end_lat = last_transit_section_guides[-1]["x"], last_transit_section_guides[-1]["y"]

    # 3. First-mile 및 Last-mile 대여소 찾기
    # First-mile: 사용자 출발지 -> 대중교통 승차지
    fm_start_station = find_nearest_station(request.start_lat, request.start_lon, db)
    fm_end_station = find_nearest_station(transit_start_lat, transit_start_lon, db)
    first_mile_segment = RouteSegment(start_station=fm_start_station, end_station=fm_end_station)

    # Last-mile: 대중교통 하차지 -> 최종 목적지
    lm_start_station = find_nearest_station(transit_end_lat, transit_end_lon, db)
    lm_end_station = find_nearest_station(request.end_lat, request.end_lon, db)
    last_mile_segment = RouteSegment(start_station=lm_start_station, end_station=lm_end_station)

    return RouteResponse(
        message="Successfully found nearest stations for first and last mile of the transit route.",
        path=sections, # 카카오가 제공한 전체 경로 정보
        first_mile=first_mile_segment,
        last_mile=last_mile_segment
    )

@app.get("/stations/realtime", response_model=List[StationRealtime])
def get_realtime_stations(
    db: Session = Depends(get_db),
    redis_conn: redis.Redis = Depends(get_redis_conn),
    station_id: Optional[str] = None,
    station_number: Optional[str] = None,
    station_display_name: Optional[str] = None
):
    # 필터가 있는 경우 캐시를 사용하지 않음
    if station_id or station_number or station_display_name:
        query = select(BikeAvailabilityRealtime)
        if station_id:
            query = query.where(BikeAvailabilityRealtime.c.station_id == station_id)
        if station_number:
            query = query.where(BikeAvailabilityRealtime.c.station_number.cast(String).ilike(f"%{station_number}%"))
        if station_display_name:
            query = query.where(BikeAvailabilityRealtime.c.station_display_name.ilike(f"%{station_display_name}%"))
        
        result = db.execute(query).fetchall()
        return [StationRealtime.model_validate(row._asdict()) for row in result]

    # 필터가 없는 경우 캐시 로직 적용
    CACHE_KEY = "realtime_stations_data"
    try:
        cached_data = redis_conn.get(CACHE_KEY)
        if cached_data:
            # 캐시 히트: Redis에서 데이터를 가져와 반환
            return json.loads(cached_data)
    except redis.RedisError as e:
        # 레디스 오류 발생 시, DB에서 직접 가져오도록 함
        logging.error(f"Redis error in get_realtime_stations: {e}")

    # 캐시 미스: DB에서 데이터를 가져와서 캐시에 저장
    query = select(BikeAvailabilityRealtime)
    result = db.execute(query).fetchall()
    
    response_data = [StationRealtime.model_validate(row._asdict()) for row in result]
    
    # Pydantic 모델 리스트를 JSON 직렬화 가능한 형태로 변환
    json_compatible_data = [model.model_dump(mode='json') for model in response_data]
    
    try:
        # 60초 TTL로 Redis에 캐시 저장
        redis_conn.setex(CACHE_KEY, 60, json.dumps(json_compatible_data))
    except redis.RedisError as e:
        logging.error(f"Failed to cache data in get_realtime_stations: {e}")
        
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