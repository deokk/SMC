# db/redis_db.py
import os
import redis
from dotenv import load_dotenv

# .env 파일 경로를 지정하여 환경 변수 로드
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env') # 현재 파일 위치 기준 상위 폴더의 .env
load_dotenv(dotenv_path=dotenv_path)

# .env 파일에서 Redis 연결 정보 가져오기
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

try:
    # Redis 연결 풀 생성
    redis_pool = redis.ConnectionPool(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True  # 응답을 자동으로 UTF-8로 디코딩
    )

    # 연결 테스트
    r = redis.Redis(connection_pool=redis_pool)
    r.ping()
    print("✅ Redis 연결에 성공했습니다.")

except redis.exceptions.ConnectionError as e:
    print(f"❌ Redis 연결 실패: {e}")
    print("   - .env 파일에 REDIS_HOST, REDIS_PORT, REDIS_DB 변수가 올바르게 설정되었는지 확인해주세요.")
    print("   - Redis 서버가 실행 중인지 확인해주세요.")
    redis_pool = None

def get_redis_conn():
    """FastAPI에서 사용할 Redis 커넥션 의존성 주입 함수"""
    if not redis_pool:
        raise ConnectionError("Redis connection pool is not available.")
    r = redis.Redis(connection_pool=redis_pool)
    try:
        yield r
    finally:
        # Connection from pool is automatically released
        pass
