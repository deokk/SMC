from sqlalchemy.orm import Session
import sys
import os

# 경로 문제 해결을 위해 상위 디렉토리 추가
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from backend.models.user import User
from backend.schemas.user_schemas import UserCreate # Pydantic 스키마
from backend.security import get_password_hash

def get_user_by_email(db: Session, email: str):
    """이메일로 사용자를 조회합니다."""
    return db.query(User).filter(User.email == email).first()

def get_user_by_username(db: Session, username: str):
    """사용자 이름으로 사용자를 조회합니다."""
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, user: UserCreate):
    """새로운 사용자를 생성합니다."""
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
