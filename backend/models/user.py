from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
# Use the central Base from the database module
from db.database import Base

class User(Base):
    """
    데이터베이스의 'users' 테이블 모델 정의.
    사용자 인증 및 관리에 필요한 정보를 저장합니다.
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # 내가 친구로 추가한 관계 목록
    friends = relationship(
        "Friend", 
        foreign_keys="Friend.user_id", 
        back_populates="user", 
        cascade="all, delete-orphan"
    )
    # 나를 친구로 추가한 관계 목록
    friend_of = relationship(
        "Friend", 
        foreign_keys="Friend.friend_id", 
        back_populates="friend_user", 
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

# 이 모델이 데이터베이스에 테이블을 생성할 수 있도록
# db/create_tables.py에서 임포트되어 사용될 예정입니다.