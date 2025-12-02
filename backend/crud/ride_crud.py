from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional

from backend.models.ride import UserRideHistory
from backend.schemas.ride_schemas import RideResponse

def create_ride(db: Session, user_id: int, start_station_id: str, start_time: datetime) -> UserRideHistory:
    """
    새로운 운행 기록을 생성하고 'active' 상태로 설정합니다.
    """
    db_ride = UserRideHistory(
        user_id=user_id,
        start_station_id=start_station_id,
        start_time=start_time,
        status="active"
    )
    db.add(db_ride)
    db.commit()
    db.refresh(db_ride)
    return db_ride

def get_active_ride_by_user(db: Session, user_id: int) -> Optional[UserRideHistory]:
    """
    특정 사용자의 현재 활성화된 운행 기록을 찾습니다.
    """
    return db.query(UserRideHistory).filter(
        UserRideHistory.user_id == user_id,
        UserRideHistory.status == "active"
    ).first()

def end_ride(
    db: Session,
    ride_id: int,
    end_station_id: str,
    end_time: datetime
) -> Optional[UserRideHistory]:
    """
    활성화된 운행 기록을 'completed' 상태로 업데이트하고 종료 시간 및 정보를 채웁니다.
    """
    db_ride = db.query(UserRideHistory).filter(UserRideHistory.id == ride_id).first()
    if db_ride:
        db_ride.end_station_id = end_station_id
        db_ride.end_time = end_time
        db_ride.status = "completed"
        
        # Calculate duration_minutes
        if db_ride.start_time and db_ride.end_time:
            duration = db_ride.end_time - db_ride.start_time
            db_ride.duration_minutes = int(duration.total_seconds() / 60)
        else:
            db_ride.duration_minutes = 0 # Fallback if times are somehow missing
            
        db.commit()
        db.refresh(db_ride)
    return db_ride

def get_rides_by_user(db: Session, user_id: int) -> List[UserRideHistory]:
    """
    특정 사용자의 모든 운행 기록을 조회합니다.
    """
    return db.query(UserRideHistory).filter(UserRideHistory.user_id == user_id).order_by(
        UserRideHistory.start_time.desc()
    ).all()

def get_ride_by_id(db: Session, ride_id: int) -> Optional[UserRideHistory]:
    """
    주어진 ride_id로 단일 운행 기록을 조회합니다.
    """
    return db.query(UserRideHistory).filter(UserRideHistory.id == ride_id).first()
