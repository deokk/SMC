import os
import pandas as pd
import logging
from dotenv import load_dotenv

# --- 경로 및 환경 설정 ---
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from db.database import engine

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# .env 파일에서 환경 변수 로드
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)


class StationUpdater:
    """
    로컬 Excel 파일('station_info.xlsx')에서 대여소 마스터 정보를 읽어,
    특정 자치구의 데이터만 필터링하여 데이터베이스에 업데이트합니다.
    """

    def read_station_info_from_csv(self, file_path: str) -> pd.DataFrame:
        """
        CSV 파일에서 대여소 정보를 읽어옵니다.
        """
        if not os.path.exists(file_path):
            logging.error(f"파일을 찾을 수 없습니다: {file_path}")
            return pd.DataFrame()

        logging.info(f"CSV 파일 읽기 시작: {file_path}")
        
        try:
            # 헤더가 없으므로 header=None으로 읽어옴
            df = pd.read_csv(file_path, header=None)
            logging.info(f"CSV 파일에서 {len(df)}개의 행을 읽었습니다.")
            return df
        except Exception as e:
            logging.error(f"CSV 파일 읽기 중 오류 발생: {e}")
            return pd.DataFrame()

    def filter_and_prepare_data(self, df: pd.DataFrame, district: str) -> pd.DataFrame:
        """컬럼 위치를 기준으로 특정 자치구의 데이터만 필터링하고 DB 저장을 위해 데이터를 준비합니다."""
        if df.empty:
            return pd.DataFrame()

        # 컬럼 인덱스: A=0, B=1, C=2, D=3 ...
        COL_IDX_NUMBER = 0 # A열: 대여소번호
        COL_IDX_NAME = 1   # B열: 대여소명
        COL_IDX_DISTRICT = 2 # C열: 자치구
        COL_IDX_ADDRESS = 3 # D열: 상세주소

        logging.info(f"'{district}'에 해당하는 대여소 필터링 시작 (C열 기준)...")
        
        # C열(인덱스 2)의 값이 '광진구'인 행만 필터링
        # 데이터에 공백이 있을 수 있으므로 .str.contains 사용
        filtered_df = df[df[COL_IDX_DISTRICT].astype(str).str.contains(district, na=False)].copy()
        
        if filtered_df.empty:
            logging.warning(f"'{district}'에 해당하는 대여소를 찾지 못했습니다.")
            return pd.DataFrame()

        logging.info(f"총 {len(filtered_df)}개의 '{district}' 대여소를 찾았습니다.")

        # 필요한 데이터 추출 및 새 데이터프레임 생성
        final_df = pd.DataFrame({
            'station_number': filtered_df[COL_IDX_NUMBER],
            'station_name': filtered_df[COL_IDX_NAME],
            'district': filtered_df[COL_IDX_DISTRICT],
            'address': filtered_df[COL_IDX_ADDRESS]
        })

        # station_number가 유효하지 않은 행(예: 헤더 행) 제거
        final_df = final_df.dropna(subset=['station_number'])
        final_df = final_df[pd.to_numeric(final_df['station_number'], errors='coerce').notna()]
        final_df['station_number'] = final_df['station_number'].astype(int)

        return final_df

    def save_to_db(self, df: pd.DataFrame, table_name: str):
        """데이터프레임을 데이터베이스 테이블에 저장합니다."""
        if df.empty:
            logging.warning("저장할 데이터가 없어 DB 작업을 건너뜁니다.")
            return

        if engine is None:
            logging.error("데이터베이스 엔진이 설정되지 않아 저장을 중단합니다.")
            return

        try:
            with engine.connect() as connection:
                logging.info(f"DB 테이블 '{table_name}'에 데이터 저장 시작...")
                df.to_sql(
                    name=table_name,
                    con=connection,
                    if_exists='replace', # 실행할 때마다 테이블을 새로 만듦
                    index=False
                )
                logging.info(f"'{table_name}' 테이블에 {len(df)}개의 레코드를 성공적으로 저장했습니다.")
        except Exception as e:
            logging.error(f"DB 저장 중 오류 발생: {e}")


if __name__ == "__main__":
    updater = StationUpdater()
    csv_file_path = 'station_info.csv' # 프로젝트 루트에 있는 파일
    
    # 1. CSV에서 모든 대여소 정보 가져오기
    all_stations_df = updater.read_station_info_from_csv(csv_file_path)
    
    # 2. '광진구' 데이터만 필터링 및 가공
    gwangjin_stations_df = updater.filter_and_prepare_data(all_stations_df, district='광진구')
    
    # 3. DB에 저장
    if not gwangjin_stations_df.empty:
        updater.save_to_db(gwangjin_stations_df, table_name='stations_gwangjin')
        print("\n[저장된 광진구 대여소 목록 샘플]")
        print(gwangjin_stations_df.head())
    else:
        print("\n광진구에 해당하는 대여소 데이터를 찾지 못했거나 수집에 실패했습니다.")
