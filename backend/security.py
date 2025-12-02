import os
import bcrypt # Add this import
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# --- JWT 설정 ---
# .env 파일에서 시크릿 키, 알고리즘, 만료 시간 가져오기
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

if not SECRET_KEY:
    raise ValueError("SECRET_KEY가 .env 파일에 설정되지 않았습니다.")

# Bcrypt 알고리즘을 사용하는 암호화 컨텍스트 생성
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    일반 텍스트 비밀번호와 해시된 비밀번호를 비교하여 일치하는지 확인합니다.
    """
    # bcrypt 라이브러리를 직접 사용하여 비밀번호를 검증합니다.
    return bcrypt.checkpw(
        plain_password.encode('utf-8')[:72],
        hashed_password.encode('utf-8')
    )

def get_password_hash(password: str) -> str:
    """
    일반 텍스트 비밀번호를 해시 처리하여 반환합니다.
    Bcrypt는 최대 72바이트까지 처리하므로, 그 길이에 맞게 자릅니다.
    """
    return pwd_context.hash(password.encode('utf-8')[:72])

def create_access_token(data: dict, expires_delta: timedelta | None = None):

    """

    주어진 데이터로 JWT 액세스 토큰을 생성합니다.

    """

    to_encode = data.copy()

    if expires_delta:

        expire = datetime.now(timezone.utc) + expires_delta

    else:

        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt



# --- 사용자 인증 함수 ---



from typing import Optional

from fastapi import Depends, HTTPException, status

from fastapi.security import OAuth2PasswordBearer

from sqlalchemy.orm import Session



# 현재 프로젝트의 다른 모듈에서 필요한 것들을 가져옵니다.

# sys.path 조작이 이미 app.py 등 상위 모듈에서 처리되었다고 가정합니다.

from db.database import get_db

from backend.crud import user_crud

from backend.schemas.user_schemas import User



# 'token' 엔드포인트에서 토큰을 가져오는 OAuth2 스키마 정의

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")



credentials_exception = HTTPException(

    status_code=status.HTTP_401_UNAUTHORIZED,

    detail="Could not validate credentials",

    headers={"WWW-Authenticate": "Bearer"},

)



def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:

    """

    JWT 토큰을 디코딩하고 유효성을 검사하여 현재 사용자를 반환합니다.

    """

    try:

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        username: str = payload.get("sub")

        if username is None:

            raise credentials_exception

    except JWTError:

        raise credentials_exception

    

    user = user_crud.get_user_by_username(db, username=username)

    if user is None:

        raise credentials_exception

    

    # Pydantic 모델이 아닌 SQLAlchemy 모델 User 객체를 반환할 수도 있습니다.

    # 스키마 변환이 필요하다면 UserResponse.from_orm(user) 등을 사용합니다.

    # 여기서는 User 모델 객체를 그대로 사용합니다.

    return user


