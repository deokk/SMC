import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError

# 출력 파일을 설정
output_file_path = os.path.join(os.path.dirname(__file__), 'db_status_output.txt')

# 기존 stdout을 저장하고 파일로 리디렉션
original_stdout = sys.stdout
sys.stdout = open(output_file_path, 'w', encoding='utf-8')

# .env 파일 로드 (프로젝트 루트 디렉토리의 .env 사용)
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path)

# 데이터베이스 연결 정보 가져오기
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL 환경 변수가 설정되지 않았습니다. .env 파일을 확인해주세요.")
    # 파일 출력 닫고 원본 stdout 복원
    sys.stdout.close()
    sys.stdout = original_stdout
    sys.exit(1)

# SQLAlchemy 엔진 생성
engine = None
try:
    engine = create_engine(DATABASE_URL)
    print(f"INFO: 데이터베이스 연결 시도: {DATABASE_URL.split('@')[-1]}") # 비밀번호 등 민감 정보 제외
except Exception as e:
    print(f"ERROR: 데이터베이스 엔진 생성 중 오류 발생: {e}")
    # 파일 출력 닫고 원본 stdout 복원
    sys.stdout.close()
    sys.stdout = original_stdout
    sys.exit(1)

def check_table_data(engine, table_name):
    """지정된 테이블의 데이터 존재 여부 및 일부 데이터를 확인합니다."""
    if engine is None:
        print("ERROR: 데이터베이스 엔진이 초기화되지 않았습니다.")
        return

    try:
        with engine.connect() as connection:
            inspector = inspect(engine)
            if not inspector.has_table(table_name):
                print(f"INFO: 테이블 '{table_name}'이(가) 데이터베이스에 존재하지 않습니다.")
                return

            # 테이블의 행 개수 확인
            count_query = text(f"SELECT COUNT(*) FROM {table_name}")
            row_count = connection.execute(count_query).scalar()
            print(f"INFO: 테이블 '{table_name}'에 총 {row_count}개의 행이 있습니다.")

            if row_count > 0:
                # 상위 5개 행 조회
                select_query = text(f"SELECT * FROM {table_name} LIMIT 5")
                result = connection.execute(select_query).fetchall()
                print(f"\nINFO: 테이블 '{table_name}'의 상위 5개 행:")
                
                # 컬럼 이름 출력 (첫 번째 행의 딕셔너리 표현에서 키를 가져옴)
                if result:
                    print("Columns:", list(result[0]._asdict().keys()))
                
                for row in result:
                    print(f"  station_id: {row.station_id}")
            else:
                print(f"INFO: 테이블 '{table_name}'에 데이터가 없습니다.")

    except OperationalError as e:
        print(f"ERROR: 데이터베이스 연결 또는 쿼리 실행 중 오류 발생: {e}")
    except Exception as e:
        print(f"ERROR: 테이블 데이터 확인 중 예기치 않은 오류 발생: {e}")

if __name__ == "__main__":
    print("--- 데이터베이스 테이블 데이터 확인 시작 ---")
    check_table_data(engine, "bike_availability_realtime")
    print("--- 데이터베이스 테이블 데이터 확인 완료 ---")

# 파일 출력 닫고 원본 stdout 복원
sys.stdout.close()
sys.stdout = original_stdout
