from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from .user import Base  # 'user' 모델에서 Base를 가져옵니다.

class UserRideHistory(Base):
    """
    사용자의 따릉이 운행 기록을 저장하는 테이블 모델.
    """
    __tablename__ = 'user_ride_history'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    start_station_id = Column(String, nullable=True)
    end_station_id = Column(String, nullable=True)
    
    start_time = Column(DateTime, nullable=False, server_default=func.now())
    end_time = Column(DateTime, nullable=True)
    
    duration_minutes = Column(Integer, nullable=True)
    
    # 'active', 'completed' 등의 상태를 저장
    status = Column(String, nullable=False, default='active', index=True)

    # User 모델과의 관계 설정
    user = relationship("User")

    def __repr__(self):
        return (
            f"<UserRideHistory(id={self.id}, user_id={self.user_id}, "
            f"start_time='{self.start_time}', status='{self.status}')>"
        )
