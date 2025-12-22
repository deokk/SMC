from sqlalchemy.orm import Session
from sqlalchemy import text, func
from datetime import datetime, timedelta
from typing import List, Optional, Dict

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

def get_rides_by_user(db: Session, user_id: int) -> List[dict]:
    """
    특정 사용자의 모든 운행 기록을 대여소 이름과 함께 조회합니다.
    """
    sql_query = text("""
        SELECT
            h.id,
            h.user_id,
            h.start_station_id,
            h.end_station_id,
            ssm.address1 AS start_station_name,
            esm.address1 AS end_station_name,
            h.start_time,
            h.end_time,
            h.duration_minutes,
            h.status
        FROM user_ride_history AS h
        LEFT JOIN stations_master AS ssm ON h.start_station_id = ssm.station_id
        LEFT JOIN stations_master AS esm ON h.end_station_id = esm.station_id
        WHERE h.user_id = :user_id
        ORDER BY h.start_time DESC
    """)
    
    result = db.execute(sql_query, {'user_id': user_id})
    return result.mappings().all()

def get_pattern_stats_by_user(db: Session, user_id: int) -> Dict:
    """
    사용자의 주행 기록을 분석하여 통계 패턴을 반환합니다.
    """
    # 1. 기본 통계 (총 주행, 총 시간, 평균 시간)
    base_stats_query = db.query(
        func.count(UserRideHistory.id),
        func.sum(UserRideHistory.duration_minutes),
        func.avg(UserRideHistory.duration_minutes)
    ).filter(
        UserRideHistory.user_id == user_id,
        UserRideHistory.status == 'completed'
    )
    total_trips, total_duration, avg_duration = base_stats_query.one()

    # 주행 기록이 없을 경우
    if total_trips == 0:
        return {
            "total_trips": 0,
            "total_duration_minutes": 0,
            "average_duration_minutes": 0,
            "favorite_start_station_id": None,
            "favorite_end_station_id": None,
            "most_active_day": None,
        }

    # 2. 최애 출발 대여소
    fav_start_station = db.query(
        UserRideHistory.start_station_id,
        func.count(UserRideHistory.start_station_id).label('count')
    ).filter(
        UserRideHistory.user_id == user_id,
        UserRideHistory.status == 'completed',
        UserRideHistory.start_station_id.isnot(None)
    ).group_by(
        UserRideHistory.start_station_id
    ).order_by(
        func.count(UserRideHistory.start_station_id).desc()
    ).first()

    # 3. 최애 도착 대여소
    fav_end_station = db.query(
        UserRideHistory.end_station_id,
        func.count(UserRideHistory.end_station_id).label('count')
    ).filter(
        UserRideHistory.user_id == user_id,
        UserRideHistory.status == 'completed',
        UserRideHistory.end_station_id.isnot(None)
    ).group_by(
        UserRideHistory.end_station_id
    ).order_by(
        func.count(UserRideHistory.end_station_id).desc()
    ).first()
    
    # 4. 가장 활발한 요일 (0=월요일, 1=화요일, ..., 6=일요일 for DOW)
    # PostgreSQL의 EXTRACT(isodow FROM ...)는 1(월)~7(일)을 반환
    most_active_day_query = db.query(
        func.extract('isodow', UserRideHistory.start_time).label('dow'),
        func.count(UserRideHistory.id).label('count')
    ).filter(
        UserRideHistory.user_id == user_id,
        UserRideHistory.status == 'completed'
    ).group_by('dow').order_by(func.count(UserRideHistory.id).desc()).first()

    day_map = {1: '월요일', 2: '화요일', 3: '수요일', 4: '목요일', 5: '금요일', 6: '토요일', 7: '일요일'}
    most_active_day = day_map.get(most_active_day_query.dow) if most_active_day_query else None

    return {
        "total_trips": total_trips or 0,
        "total_duration_minutes": int(total_duration) if total_duration else 0,
        "average_duration_minutes": float(avg_duration) if avg_duration else 0.0,
        "favorite_start_station_id": fav_start_station.start_station_id if fav_start_station else None,
        "favorite_end_station_id": fav_end_station.end_station_id if fav_end_station else None,
        "most_active_day": most_active_day,
    }


def get_ride_by_id(db: Session, ride_id: int) -> Optional[UserRideHistory]:
    """
    주어진 ride_id로 단일 운행 기록을 조회합니다.
    """
    return db.query(UserRideHistory).filter(UserRideHistory.id == ride_id).first()
