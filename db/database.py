# db/database.py (새 파일)
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base # Add this import
from dotenv import load_dotenv

# .env 파일 경로를 지정하여 환경 변수 로드
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env') # 현재 파일 위치 기준 상위 폴더의 .env
load_dotenv(dotenv_path=dotenv_path)

# .env 파일에서 데이터베이스 연결 URL 가져오기
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL이 .env 파일에 설정되지 않았습니다.")

# 데이터베이스 연결을 위한 엔진 생성
engine = create_engine(DATABASE_URL)

# 데이터베이스 세션을 생성하기 위한 SessionLocal 클래스
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 모든 SQLAlchemy ORM 모델이 상속할 Base 클래스
Base = declarative_base() # Add this line

def get_db():
    """FastAPI에서 사용할 데이터베이스 세션 의존성 주입 함수"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 연결 테스트
try:
    connection = engine.connect()
    print("데이터베이스 연결에 성공했습니다.")
    connection.close()
except Exception as e:
    print(f"데이터베이스 연결 실패: {repr(e)}")