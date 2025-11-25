from passlib.context import CryptContext

# Bcrypt 알고리즘을 사용하는 암호화 컨텍스트 생성
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    일반 텍스트 비밀번호와 해시된 비밀번호를 비교하여 일치하는지 확인합니다.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    일반 텍스트 비밀번호를 해시 처리하여 반환합니다.
    Bcrypt는 최대 72바이트까지 처리하므로, 그 길이에 맞게 자릅니다.
    """
    return pwd_context.hash(password.encode('utf-8')[:72])
