import os
import requests
import pandas as pd
from datetime import datetime
import logging
import time
from dotenv import load_dotenv

# --- 경로 설정 ---
# 상위 디렉토리를 sys.path에 추가하여 db 모듈을 찾을 수 있도록 함
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# .env 파일에서 환경 변수 로드
# 이 스크립트는 data/ 디렉토리에 있으므로, 상위 디렉토리의 backend/.env 파일을 지정합니다.
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

class RealtimeBikeCollector:
    """서울시 열린데이터광장 API로부터 실시간 따릉이 현황을 수집합니다."""

    def __init__(self):
        """API 키와 기본 URL 등 초기 설정을 로드합니다."""
        self.api_key = os.getenv("BIKE_API_KEY")
        if not self.api_key:
            raise ValueError("BIKE_API_KEY가 .env 파일에 설정되지 않았습니다.")
        self.base_url = "http://openapi.seoul.go.kr:8088"
        self.service = "bikeList"
        self.max_records_per_request = 1000  # API가 한 번에 반환하는 최대 레코드 수

    def _build_url(self, start_idx: int, end_idx: int) -> str:
        """API 요청을 위한 URL을 생성합니다."""
        return f"{self.base_url}/{self.api_key}/json/{self.service}/{start_idx}/{end_idx}/"

    def fetch_all_stations(self) -> pd.DataFrame:
        """페이지네이션을 통해 모든 대여소의 데이터를 수집하고 데이터프레임으로 반환합니다."""
        all_stations = []
        start_idx = 1

        while True:
            end_idx = start_idx + self.max_records_per_request - 1
            url = self._build_url(start_idx, end_idx)
            logging.info(f"데이터 수집 시도: {start_idx}부터 {end_idx}까지")

            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                response.encoding = 'utf-8'
                data = response.json()

                if 'rentBikeStatus' not in data:
                    logging.warning(f"페이지 {start_idx}-{end_idx} 응답에 'rentBikeStatus'가 없습니다. 수집을 중단합니다.")
                    break

                bike_data = data['rentBikeStatus']
                result = bike_data.get('RESULT', {})
                if result.get('CODE') not in ['INFO-000', 'INFO-200']:
                    logging.warning(f"페이지 {start_idx}-{end_idx} API 에러: {result.get('MESSAGE', '알 수 없는 오류')}. 수집을 중단합니다.")
                    break
                
                stations = bike_data.get('row', [])
                if not stations:
                    logging.info("더 이상 수집할 데이터가 없습니다. 수집을 완료합니다.")
                    break

                for station in stations:
                    station_id = str(station.get('stationId', ''))
                    if station_id.startswith('ST-') and station_id.split('-')[1].isdigit():
                        num_part = int(station_id.split('-')[1])
                        station_id = f"ST-{num_part:03d}"
                    all_stations.append({
                        'station_id': station_id,
                        'station_name': station.get('stationName', ''),
                        'available_bikes': int(station.get('parkingBikeTotCnt', 0)),
                        'station_capacity': int(station.get('rackTotCnt', 0)),
                        'latitude': float(station.get('stationLatitude', 0)),
                        'longitude': float(station.get('stationLongitude', 0)),
                        'timestamp': datetime.now()
                    })
                
                # 다음 페이지로 이동
                start_idx += self.max_records_per_request
                time.sleep(0.5)

            except requests.exceptions.RequestException as e:
                logging.error(f"API 요청 중 에러 발생 (페이지 {start_idx}-{end_idx}): {e}. 수집을 중단합니다.")
                break
            except Exception as e:
                logging.error(f"데이터 처리 중 예기치 않은 에러 발생 (페이지 {start_idx}-{end_idx}): {e}. 수집을 중단합니다.")
                break
        
        if all_stations:
            df = pd.DataFrame(all_stations)
            df = df.drop_duplicates(subset=['station_id'], keep='last')
            logging.info(f"총 {len(df)}개의 고유한 대여소 데이터를 성공적으로 수집했습니다.")
            return df
        else:
            logging.warning("수집된 데이터가 없습니다.")
            return pd.DataFrame()

if __name__ == "__main__":
    from bike_availability_cleaner import BikeDataCleaner
    from weather_collector import RealtimeWeatherCollector
    from air_quality_collector import AirQualityCollector
    from db.database import engine
    from sqlalchemy import text

    def get_gwangjin_station_names() -> set:
        """DB에서 광진구 대여소 이름 목록을 가져옵니다."""
        if engine is None:
            logging.error("데이터베이스 엔진이 없어 광진구 대여소 목록을 가져올 수 없습니다.")
            return set()
        
        try:
            with engine.connect() as connection:
                result = connection.execute(text("SELECT station_name FROM stations_gwangjin"))
                names = {row[0].strip() for row in result}
                logging.info(f"DB에서 {len(names)}개의 광진구 대여소 이름을 성공적으로 가져왔습니다.")
                return names
        except Exception as e:
            logging.error(f"DB에서 광진구 대여소 이름 로드 중 오류 발생: {e}")
            return set()

    # 0. 필터링할 광진구 대여소 이름 목록 가져오기
    logging.info("--- 0. 필터링을 위한 광진구 대여소 이름 목록 로드 시작 ---")
    gwangjin_station_names = get_gwangjin_station_names()

    # 1. 데이터 수집
    logging.info("--- 1. 따릉이 데이터 수집 시작 ---")
    bike_collector = RealtimeBikeCollector()
    raw_bike_df = bike_collector.fetch_all_stations()

    # 1.5 (A). 필터링이 필요한 경우, 이름 정규화 및 필터링 수행
    if not raw_bike_df.empty and gwangjin_station_names:
        # 필터링을 위한 임시 '클린' 이름 컬럼 생성
        raw_bike_df['station_name_cleaned'] = raw_bike_df['station_name'].str.replace(r'^\d+\.\s*', '', regex=True).str.strip()
        
        original_count = len(raw_bike_df)
        # 임시 클린 이름 컬럼으로 필터링
        raw_bike_df = raw_bike_df[raw_bike_df['station_name_cleaned'].isin(gwangjin_station_names)]
        # 필터링 후 임시 컬럼 삭제
        raw_bike_df = raw_bike_df.drop(columns=['station_name_cleaned'])

        logging.info(f"광진구 필터링 완료: {original_count}개 -> {len(raw_bike_df)}개")
        
        if raw_bike_df.empty:
            logging.warning("광진구에 해당하는 실시간 대여소 정보를 찾지 못했습니다. DB의 station_name과 API의 station_name이 일치하는지 확인하세요.")
    
    # 1.5 (B). 필터링 목록이 없을 경우 경고
    elif not gwangjin_station_names:
        logging.warning("광진구 대여소 이름 목록이 없어 필터링을 건너뜁니다. 전체 데이터로 수집을 진행합니다.")


    # 2. 이후 로직은 필터링 되었거나, 전체 데이터인 raw_bike_df로 계속 진행
    if not raw_bike_df.empty:
        # 2. 데이터 정제 및 특성 추가
        logging.info("--- 2. 따릉이 데이터 정제 및 특성 추가 시작 ---")
        bike_cleaner = BikeDataCleaner()
        enriched_bike_df = bike_cleaner.clean_and_enrich(raw_bike_df)
        logging.info("따릉이 데이터 정제 완료.")

        # 3. 날씨 데이터 수집
        logging.info("--- 3. 날씨 데이터 수집 시작 ---")
        time.sleep(1)
        weather_collector = RealtimeWeatherCollector()
        current_weather = weather_collector.fetch_current_weather()

        # 4. 대기질 데이터 수집
        logging.info("--- 4. 대기질 데이터 수집 시작 ---")
        air_quality_collector = AirQualityCollector()
        current_air_quality = air_quality_collector.fetch_air_quality()

        # 5. 데이터 통합
        logging.info("--- 5. 따릉이, 날씨, 대기질 데이터 통합 시작 ---")
        final_df = enriched_bike_df.copy()

        if current_weather:
            for key, value in current_weather.items():
                final_df[key] = value
        else:
            logging.warning("날씨 데이터 수집에 실패하여 통합을 건너뜁니다.")

        if current_air_quality:
            for key, value in current_air_quality.items():
                final_df[key] = value
        else:
            logging.warning("대기질 데이터 수집에 실패하여 통합을 건너뜁니다.")

        logging.info("데이터 통합 완료.")
            
        # 6. 데이터베이스에 저장
        logging.info("--- 6. 데이터베이스에 저장 시작 ---")
        try:
            if engine is not None:
                table_name = "bike_availability_realtime"
                with engine.connect() as connection:
                    with connection.begin() as transaction:
                        try:
                            connection.execute(text(f"DELETE FROM {table_name}"))
                            logging.info(f"'{table_name}' 테이블의 기존 데이터를 모두 삭제했습니다.")
                            
                            final_df.to_sql(
                                table_name,
                                con=connection,
                                if_exists='append',
                                index=False
                            )
                            logging.info(f"'{table_name}' 테이블에 새로운 데이터를 성공적으로 추가했습니다.")
                            
                            transaction.commit()
                        except Exception as e:
                            logging.error(f"데이터 저장 중 오류 발생: {e}")
                            transaction.rollback()
            else:
                logging.error("데이터베이스 엔진이 없어 저장을 건너뜁니다.")

        except Exception as e:
            logging.error(f"데이터베이스 연결 또는 트랜잭션 중 오류 발생: {e}")

    # 8. 데이터 아카이빙
    logging.info("--- 8. 데이터 아카이빙 시작 ---")
    try:
        from db.archive import archive_realtime_data
        archive_realtime_data()
    except Exception as e:
        logging.error(f"데이터 아카이빙 중 오류 발생: {e}")

    # 7. 최종 결과 확인
    print("\n[통합된 최종 데이터 샘플]")
    if 'final_df' in locals() and not final_df.empty:
        print(final_df.head())
        print(f"\n최종 데이터 컬럼 수: {len(final_df.columns)}")
        print(final_df.columns.tolist())
    elif not raw_bike_df.empty:
        print("필터링된 따릉이 원본 데이터만 수집되었습니다.")
        print(raw_bike_df.head())
    else:
        print("데이터 수집에 실패했거나 필터링 후 남은 데이터가 없습니다.")

    print(f"\n수집된 총 대여소 수: {len(raw_bike_df) if 'raw_bike_df' in locals() and not raw_bike_df.empty else 0}")

