import math
import httpx
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query, Request
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
import joblib
import pandas as pd
import numpy as np

# db.database 모듈에서 엔진과 세션 의존성 주입 함수 가져오기
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from contextlib import asynccontextmanager
from db.database import engine, get_db, SessionLocal
from db.redis_db import get_redis_conn # Redis 의존성 추가
from services.route_service import RouteService
from services.prediction_service import HybridPredictor # 하이브리드 예측 서비스 임포트
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


# --- 모델 및 서비스 라이프사이클 관리 ---
# 서버 시작 시 모델/서비스를 로드하고, 종료 시 정리합니다.
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 서버 시작: 하이브리드 예측 모델을 로딩합니다...")
    # 데이터베이스 세션을 생성하여 예측 서비스에 전달
    db = SessionLocal()
    try:
        # HybridPredictor 인스턴스를 생성하고 앱 상태에 저장
        app.state.predictor = HybridPredictor(db)
        print("✅ 하이브리드 예측 서비스가 성공적으로 초기화되었습니다.")
    finally:
        db.close()
    
    yield # 애플리케이션 실행
    
    print(" shutting down...")
    # 정리 코드 (필요한 경우)


# FastAPI 앱 인스턴스 생성 및 라이프사이클 연결
app = FastAPI(lifespan=lifespan)


# --- CORS 미들웨어 설정 ---
# 개발 환경에서는 모든 오리진을 허용합니다.
# 프로덕션 환경에서는 특정 프론트엔드 주소만 허용하도록 변경해야 합니다.
origins = [
    "http://localhost",
    "http://localhost:3000", # React 기본 포트
    "http://localhost:5173", # Vite React 기본 포트 추가
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
ODSAY_API_KEY = os.getenv("ODSAY_API_KEY")


# --- 모든 Pydantic 모델 정의 ---

class Token(BaseModel):
    access_token: str
    token_type: str

class LocationUpdate(BaseModel):
    """라이더 위치 업데이트 요청을 위한 모델"""
    latitude: float = Field(..., example=37.5665)
    longitude: float = Field(..., example=126.9780)

class RouteStep(BaseModel):
    """경로의 각 단계를 나타내는 모델"""
    type: str = Field(..., description="이동 수단 (e.g., 'WALK', 'BUS', 'SUBWAY')")
    distance: int = Field(..., description="이동 거리 (미터)")
    duration: int = Field(..., description="소요 시간 (분)")
    name: Optional[str] = Field(None, description="버스 번호 또는 지하철 호선")
    start_name: Optional[str] = Field(None, description="출발 정류장/역")
    end_name: Optional[str] = Field(None, description="도착 정류장/역")
    polyline: Optional[List[Tuple[float, float]]] = Field(None, description="해당 구간의 경로선")

class RouteOption(BaseModel):
    """하나의 경로 옵션을 나타내는 모델"""
    mode: str = Field(..., description="경로의 대표 이동 수단 (e.g., 'TRANSIT', 'BIKE')")
    duration: int = Field(..., description="총 소요 시간 (분)")
    distance: int = Field(..., description="총 이동 거리 (미터)")
    fare: int = Field(..., description="예상 요금 (원)")
    steps: List[RouteStep]
    # polyline: Optional[List[Tuple[float, float]]] = Field(None, description="지도에 표시할 경로선 좌표 목록") # 이제 steps 안에 포함됨

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


# --- ML 예측 관련 모델 및 헬퍼 함수 ---

class PredictionResponse(BaseModel):
    """예측 결과 응답 모델"""
    station_id: str
    prediction_in_minutes: int
    predicted_bike_count: int
    model_loaded: bool


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

# --- 경로 최적화 로직 (ODsay 기반) ---

async def fetch_lane_data(client: httpx.AsyncClient, map_obj: str) -> Optional[List[Dict]]:
    """ODsay loadLane API를 호출하여 전체 경로의 상세 그래픽 데이터를 가져옵니다."""
    if not ODSAY_API_KEY or not map_obj:
        return None
    
    url = "https://api.odsay.com/v1/api/loadLane"
    params = {"apiKey": ODSAY_API_KEY, "mapObject": f"0:0@{map_obj}"}
    try:
        res = await client.get(url, params=params)
        res.raise_for_status()
        data = res.json()
        if "result" in data and "lane" in data["result"]:
            return data["result"]["lane"]
        return None
    except Exception as e:
        logging.error(f"ODsay loadLane API 호출 실패: {e}")
        return None

async def get_odsay_public_transit_route(
    sx: float, sy: float, ex: float, ey: float
) -> Optional[List[RouteOption]]:
    """ODsay API를 호출하여 대중교통 경로를 조회하고, 각 구간별 상세 Polyline을 포함하여 가공합니다."""
    if not ODSAY_API_KEY:
        logging.error("ODsay API 키가 설정되지 않았습니다.")
        return None

    url = "https://api.odsay.com/v1/api/searchPubTransPathR"
    params = {"apiKey": ODSAY_API_KEY, "SX": sx, "SY": sy, "EX": ex, "EY": ey}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if "result" not in data or "path" not in data["result"]:
                return []

            parsed_routes = []
            for path in data["result"]["path"]:
                if not isinstance(path, dict):
                    continue

                route_info = path.get("info", {})
                
                # 전체 경로의 상세 그래픽 데이터 미리 호출
                graphic_lanes = await fetch_lane_data(client, route_info.get("mapObj"))
                
                steps = []
                # subPath와 graphic_lanes를 매칭하기 위한 인덱스
                transit_index = 0

                for sub_path in path.get("subPath", []):
                    if not isinstance(sub_path, dict):
                        continue
                    
                    segment_polyline = None
                    traffic_type = sub_path.get("trafficType")
                    
                    if traffic_type == 3: # 도보
                        if "movePath" in sub_path:
                            coords = sub_path["movePath"]
                            segment_polyline = [(float(p.split(',')[1]), float(p.split(',')[0])) for p in coords.split(' ')]
                        elif all(k in sub_path for k in ['startX', 'startY', 'endX', 'endY']):
                            segment_polyline = [(sub_path['startY'], sub_path['startX']), (sub_path['endY'], sub_path['endX'])]
                    
                    elif traffic_type in [1, 2]: # 대중교통
                        if graphic_lanes and transit_index < len(graphic_lanes):
                            # 순서 기반으로 매칭 (대부분의 경우 잘 동작함)
                            lane_graphic = graphic_lanes[transit_index]
                            if lane_graphic and "section" in lane_graphic and lane_graphic["section"]:
                                coords = lane_graphic["section"][0].get("graphPos")
                                if coords:
                                    if isinstance(coords[0], dict):
                                        segment_polyline = [(point['y'], point['x']) for point in coords]
                                    else:
                                        segment_polyline = [(coords[i+1], coords[i]) for i in range(0, len(coords), 2)]
                            transit_index += 1
                        
                        # 그래픽 데이터가 없을 경우, 정류장/역 좌표를 연결하는 직선으로 대체
                        if not segment_polyline and "passStopList" in sub_path:
                             stations = sub_path["passStopList"].get("stations", [])
                             segment_polyline = [(float(s["y"]), float(s["x"])) for s in stations]

                    mode = "WALK"
                    lane_name = None
                    if traffic_type in [1, 2]:
                        mode = "SUBWAY" if traffic_type == 1 else "BUS"
                        lane_info = sub_path.get("lane", [{}])[0]
                        if mode == "BUS":
                            lane_name = lane_info.get("busNo")
                        elif mode == "SUBWAY":
                            lane_name = lane_info.get("subwayName")
                            if not lane_name:
                                subway_code = lane_info.get("subwayCode")
                                if subway_code:
                                    lane_name = f"{subway_code}호선"
                        
                    steps.append(RouteStep(
                        type=mode,
                        distance=sub_path.get("distance", 0),
                        duration=sub_path.get("sectionTime", 0),
                        name=lane_name,
                        start_name=sub_path.get("startName"),
                        end_name=sub_path.get("endName"),
                        polyline=segment_polyline
                    ))

                parsed_routes.append(RouteOption(
                    mode="TRANSIT",
                    duration=route_info.get("totalTime", 0),
                    distance=route_info.get("totalDistance", 0),
                    fare=route_info.get("payment", 0),
                    steps=steps,
                ))
            return parsed_routes
        except httpx.HTTPStatusError as e:
            logging.error(f"ODsay API 요청 실패: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logging.error(f"ODsay API 처리 중 예외 발생: {e}")
            return None


@app.post("/route/optimized", response_model=List[RouteOption])
async def get_optimized_route(request: RouteRequest, db: Session = Depends(get_db)):
    """
    출발지부터 도착지까지의 최적 경로를 ODsay API를 통해 조회합니다.
    현재는 대중교통 경로만 제공합니다.
    """
    transit_routes = await get_odsay_public_transit_route(
        sx=request.start_lon,
        sy=request.start_lat,
        ex=request.end_lon,
        ey=request.end_lat,
    )
    if transit_routes is None:
        raise HTTPException(status_code=503, detail="외부 길찾기 API 호출에 실패했습니다.")
    
    # TODO: 자전거 경로, 따릉이+대중교통 결합 경로 로직 추가
    return transit_routes

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


@app.get("/predict/hybrid/{station_id}", response_model=PredictionResponse)
def predict_bike_count_hybrid(
    request: Request,
    station_id: str,
    n_minutes: int = Query(..., ge=0, le=5760, description="0에서 5760분(4일) 사이의 예측 시간(분)"),
):
    """
    (신규) 하이브리드 모델을 사용하여 특정 대여소의 N분 후 자전거 대수를 예측합니다.
    - 0-6시간: XGBoost (단기)
    - 6시간-4일: LSTM (장기)
    """
    if not hasattr(request.app.state, 'predictor') or request.app.state.predictor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="예측 서비스가 초기화되지 않았습니다. 서버 로그를 확인해주세요."
        )
    
    try:
        # station_id 'ST-1234' -> 1234
        station_id_int = int(station_id.replace('ST-', ''))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="유효하지 않은 station_id 형식입니다. 'ST-xxxx' 형식을 사용해주세요.")

    try:
        predictor: HybridPredictor = request.app.state.predictor
        predicted_count = predictor.predict(station_id_int, n_minutes)
        
        return PredictionResponse(
            station_id=station_id,
            prediction_in_minutes=n_minutes,
            predicted_bike_count=predicted_count,
            model_loaded=True
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(f"하이브리드 예측 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="예측을 처리하는 중 서버에 오류가 발생했습니다.")


@app.get("/stations/{station_id}/predict", response_model=PredictionResponse, deprecated=True)
def predict_bike_count(
    request: Request,
    station_id: str,
    n_minutes: int = Query(..., ge=0, le=360, description="0에서 360분 사이의 예측 시간(분)"),
):
    """
    (구버전) 특정 대여소의 N분 후 자전거 대수를 예측합니다.
    이 엔드포인트는 새로운 /predict/hybrid/{station_id} 로 대체될 예정입니다.
    """
    if not hasattr(request.app.state, 'predictor') or request.app.state.predictor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="예측 서비스가 초기화되지 않았습니다. 서버 로그를 확인해주세요."
        )
    
    try:
        # station_id 'ST-1234' -> 1234
        station_id_int = int(station_id.replace('ST-', ''))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="유효하지 않은 station_id 형식입니다. 'ST-xxxx' 형식을 사용해주세요.")

    try:
        # 새로운 하이브리드 예측 서비스를 호출
        predictor: HybridPredictor = request.app.state.predictor
        predicted_count = predictor.predict(station_id_int, n_minutes)
        
        return PredictionResponse(
            station_id=station_id,
            prediction_in_minutes=n_minutes,
            predicted_bike_count=predicted_count,
            model_loaded=True
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logging.error(f"구버전 예측 API 처리 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="예측을 처리하는 중 서버에 오류가 발생했습니다.")