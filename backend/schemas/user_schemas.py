from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- 사용자 인증을 위한 Pydantic 스키마 ---

class UserBase(BaseModel):
    """사용자 모델의 기본 스키마"""
    username: str
    email: str

class UserCreate(UserBase):
    """사용자 생성을 위한 스키마 (비밀번호 포함)"""
    password: str

class User(UserBase):
    """API 응답을 위한 사용자 스키마 (비밀번호 제외)"""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserResponse(User):
    """사용자 정보 조회 응답을 위한 스키마"""
    pass

# --- 경로 최적화를 위한 스키마 ---

class RouteRequest(BaseModel):
    """경로 최적화 요청을 위한 모델"""
    start_lat: float = Field(..., example=37.54847, description="출발지 위도")
    start_lon: float = Field(..., example=127.07462, description="출발지 경도")
    end_lat: float = Field(..., example=37.55167, description="도착지 위도")
    end_lon: float = Field(..., example=127.07323, description="도착지 경도")

class RouteResponse(BaseModel):
    """경로 최적화 응답을 위한 모델"""
    message: str = Field(..., example="Route optimization is under development.")
    path: List[Dict[str, Any]] = Field(..., example=[
        {"type": "WALK", "duration": "5 mins", "distance": "400m"},
        {"type": "BIKE", "station_id": "ST-123", "duration": "10 mins", "distance": "1.5km"},
        {"type": "WALK", "duration": "3 mins", "distance": "250m"}
    ])

# --- 개인화된 패턴 분석을 위한 스키마 ---

class PersonalizedPatternResponse(BaseModel):
    """개인화된 라이딩 패턴 분석 응답을 위한 모델"""
    message: str = Field(..., example="Personalized pattern analysis is under development.")
    favorite_station_id: Optional[str] = Field("ST-509", description="가장 자주 이용하는 대여소 ID")
    avg_duration_minutes: Optional[float] = Field(15.5, description="평균 주행 시간(분)")
    total_trips: Optional[int] = Field(42, description="총 주행 횟수")

# --- 실시간 라이더 트래킹을 위한 스키마 ---

class RiderLocation(BaseModel):
    """실시간 라이더 위치 정보 모델"""
    rider_id: str = Field(..., example="rider_123", description="라이더 고유 ID")
    latitude: float = Field(..., example=37.5665, description="라이더 현재 위도")
    longitude: float = Field(..., example=126.9780, description="라이더 현재 경도")
    timestamp: datetime = Field(..., description="위치 정보 갱신 시간")
