# db/archive.py
import sys
import os
import logging
import pandas as pd
from sqlalchemy import create_engine, text

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 상위 디렉토리를 경로에 추가하여 db.database 모듈 임포트
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from db.database import engine

def archive_realtime_data():
    """
    'bike_availability_realtime' 테이블의 데이터를 'bike_availability_historical' 테이블로 옮깁니다.
    중복을 방지하기 위해 'historical' 테이블에 존재하지 않는 데이터만 추가합니다.
    """
    logging.info("실시간 데이터 아카이빙 시작...")

    # 'historical' 테이블에 없는 'realtime' 테이블의 데이터를 선택하는 SQL 쿼리
    # station_id와 timestamp를 복합 키로 사용하여 중복을 확인합니다.
    query = """
    INSERT INTO bike_availability_historical
    SELECT r.*
    FROM bike_availability_realtime r
    LEFT JOIN bike_availability_historical h
        ON r.station_id = h.station_id AND r.timestamp = h.timestamp
    WHERE h.station_id IS NULL;
    """

    try:
        with engine.connect() as connection:
            # 트랜잭션 시작
            with connection.begin() as transaction:
                try:
                    result = connection.execute(text(query))
                    logging.info(f"{result.rowcount}개의 새로운 레코드가 'bike_availability_historical' 테이블에 추가되었습니다.")
                    # 트랜잭션 커밋은 with 블록이 성공적으로 끝나면 자동으로 이루어집니다.
                except Exception as e:
                    logging.error(f"아카이빙 쿼리 실행 중 오류 발생: {e}")
                    # 오류 발생 시 트랜잭션 롤백
                    transaction.rollback()
                    raise

    except Exception as e:
        logging.error(f"데이터베이스 연결 또는 트랜잭션 중 오류 발생: {e}")

if __name__ == "__main__":
    archive_realtime_data()
