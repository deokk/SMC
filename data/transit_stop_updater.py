# -*- coding: utf-8 -*-
import os
import requests
import pandas as pd
import logging
from dotenv import load_dotenv
import time

# --- 경로 및 환경 설정 ---
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from db.database import engine

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# .env 파일에서 환경 변수 로드
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

class TransitStopUpdater:
    """
    카카오 로컬 API를 사용하여 특정 지역의 대중교통 정류장(지하철, 버스) 정보를 수집하고 DB에 저장합니다.
    """
    def __init__(self):
        self.api_key = os.getenv("MAP_API_KEY")
        if not self.api_key:
            raise ValueError("MAP_API_KEY가 .env 파일에 설정되지 않았습니다.")
        self.base_url = "https://dapi.kakao.com/v2/local/search/category.json"
        # 광진구를 포함하는 대략적인 사각형 좌표 (min_lon, min_lat, max_lon, max_lat)
        self.gwangjin_rect = "127.06,37.52,127.13,37.57"

    def _fetch_category(self, category_group_code: str, rect: str) -> list:
        """지정된 카테고리와 사각 영역 내의 모든 장소를 페이지네이션을 통해 가져옵니다."""
        headers = {"Authorization": f"KakaoAK {self.api_key}"}
        params = {
            "category_group_code": category_group_code,
            "rect": rect,
            "page": 1,
            "size": 15
        }
        all_places = []
        
        while True:
            try:
                response = requests.get(self.base_url, headers=headers, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                places = data.get('documents', [])
                all_places.extend(places)
                
                if data['meta']['is_end']:
                    break
                
                params['page'] += 1
                time.sleep(0.2)

            except requests.exceptions.RequestException as e:
                logging.error(f"카카오 로컬 API 요청 중 오류 발생 ({category_group_code}): {e}")
                break
            except Exception as e:
                logging.error(f"카카오 로컬 API 응답 처리 중 오류 발생 ({category_group_code}): {e}")
                break
                
        logging.info(f"카테고리 '{category_group_code}'에서 {len(all_places)}개의 장소를 찾았습니다.")
        return all_places

    def fetch_all_stops(self) -> pd.DataFrame:
        """광진구 내의 지하철역과 버스정류장을 모두 수집합니다."""
        # 지하철역(SW8) 수집
        subway_stations = self._fetch_category('SW8', self.gwangjin_rect)
        # 버스정류장(AT4 - 관광명소 내 버스정류장, PO3 - 공공기관 내 버스정류장 등 다른 카테고리도 확인 필요)
        # 카카오 API에서 버스정류장만 정확히 필터링하는 category_group_code는 제공되지 않음.
        # 대신 키워드로 재검색하는 방식을 사용.
        
        df_subway = pd.DataFrame(subway_stations)
        if not df_subway.empty:
            df_subway['stop_type'] = 'subway'

        # TODO: 키워드 검색으로 버스 정류장 데이터 추가 구현
        
        return df_subway

    def prepare_and_save_to_db(self, df: pd.DataFrame, table_name: str):
        """데이터프레임을 정제하고 DB에 저장합니다."""
        if df.empty:
            logging.warning("저장할 정류장 데이터가 없습니다.")
            return

        # 필요한 컬럼만 선택 및 이름 변경
        df = df.rename(columns={
            'id': 'stop_id',
            'place_name': 'stop_name',
            'y': 'latitude',
            'x': 'longitude'
        })
        
        # 위도, 경도 타입을 float으로 변환
        df['latitude'] = df['latitude'].astype(float)
        df['longitude'] = df['longitude'].astype(float)
        
        final_df = df[['stop_id', 'stop_name', 'stop_type', 'latitude', 'longitude']]
        final_df = final_df.drop_duplicates(subset=['stop_id'])

        if engine is None:
            logging.error("데이터베이스 엔진이 설정되지 않아 저장을 중단합니다.")
            return

        try:
            with engine.connect() as connection:
                logging.info(f"DB 테이블 '{table_name}'에 데이터 저장 시작...")
                final_df.to_sql(
                    name=table_name,
                    con=connection,
                    if_exists='replace',
                    index=False
                )
                logging.info(f"'{table_name}' 테이블에 {len(final_df)}개의 레코드를 성공적으로 저장했습니다.")
        except Exception as e:
            logging.error(f"DB 저장 중 오류 발생: {e}")

if __name__ == '__main__':
    updater = TransitStopUpdater()
    
    # 1. 모든 정류장 정보 가져오기 (현재는 지하철역만)
    all_stops_df = updater.fetch_all_stops()
    
    # 2. DB에 저장
    if not all_stops_df.empty:
        updater.prepare_and_save_to_db(all_stops_df, table_name='transit_stops')
        print("\n[저장된 정류장 목록 샘플]")
        print(all_stops_df.head())
    else:
        print("\n수집된 정류장 데이터가 없습니다.")
