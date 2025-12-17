from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class RideStartRequest(BaseModel):
    """
    운행 시작 시 필요한 정보 모델.
    """
    latitude: float = Field(..., description="운행 시작 위도")
    longitude: float = Field(..., description="운행 시작 경도")

class RideEndRequest(BaseModel):
    """
    운행 종료 시 필요한 정보 모델.
    """
    latitude: float = Field(..., description="운행 종료 위도")
    longitude: float = Field(..., description="운행 종료 경도")

class RideResponse(BaseModel):
    """
    운행 기록의 응답 모델.
    """
    id: int
    user_id: int
    start_station_id: Optional[str] = None
    end_station_id: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    status: str

    class Config:
        from_attributes = True # SQLAlchemy ORM 모델과 호환되도록 설정
