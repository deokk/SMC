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
