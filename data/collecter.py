"""
SMC 프로젝트를 위한 실시간 따릉이 데이터 수집기
"""
import os
import requests
import pandas as pd
from datetime import datetime
import logging
import time
from dotenv import load_dotenv

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
        return f"{self.base_url}/{self.api_key}/json/{self.service}/{start_idx}/{end_idx}"

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
                response.raise_for_status()  # HTTP 에러 발생 시 예외 처리
                response.encoding = 'utf-8'

                data = response.json()

                # API 응답 구조 확인
                if 'rentBikeStatus' not in data:
                    logging.error(f"API 응답에 'rentBikeStatus'가 없습니다: {data}")
                    break

                bike_data = data['rentBikeStatus']
                
                # API 자체 에러 코드 확인
                result = bike_data.get('RESULT', {})
                if result.get('CODE') not in ['INFO-000', 'INFO-200']:
                    logging.error(f"API 에러 발생: {result.get('MESSAGE', '알 수 없는 오류')}")
                    break
                
                stations = bike_data.get('row', [])
                if not stations:
                    logging.info("더 이상 수집할 데이터가 없습니다.")
                    break

                for station in stations:
                    # stationId 형식 통일 (예: 'ST-4' -> 'ST-004')
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

                # 마지막 페이지인 경우 루프 종료
                if len(stations) < self.max_records_per_request:
                    break
                
                start_idx = end_idx + 1
                time.sleep(0.5)  # API 서버 부하 감소를 위한 지연

            except requests.exceptions.RequestException as e:
                logging.error(f"API 요청 중 에러 발생: {e}")
                break
            except Exception as e:
                logging.error(f"데이터 처리 중 예기치 않은 에러 발생: {e}")
                break
        
        if all_stations:
            df = pd.DataFrame(all_stations)
            logging.info(f"총 {len(df)}개의 대여소 데이터를 성공적으로 수집했습니다.")
            return df
        else:
            logging.warning("수집된 데이터가 없습니다.")
            return pd.DataFrame()

if __name__ == "__main__":
    # .env 파일에 BIKE_API_KEY와 WEATHER_API_KEY가 설정되어 있는지 확인하세요.
    from bike_availability_cleaner import BikeDataCleaner
    from weather_collector import RealtimeWeatherCollector # 날씨 수집 모듈 임포트
    from air_quality_collector import AirQualityCollector # 대기질 수집 모듈 임포트

    # 1. 데이터 수집
    logging.info("--- 1. 따릉이 데이터 수집 시작 ---")
    bike_collector = RealtimeBikeCollector()
    raw_bike_df = bike_collector.fetch_all_stations()

    if not raw_bike_df.empty:
        # 2. 데이터 정제 및 특성 추가
        logging.info("--- 2. 따릉이 데이터 정제 및 특성 추가 시작 ---")
        bike_cleaner = BikeDataCleaner()
        enriched_bike_df = bike_cleaner.clean_and_enrich(raw_bike_df)
        logging.info("따릉이 데이터 정제 완료.")

        # 3. 날씨 데이터 수집
        logging.info("--- 3. 날씨 데이터 수집 시작 ---")
        time.sleep(1) # Add a small delay before calling weather collector
        weather_collector = RealtimeWeatherCollector()
        current_weather = weather_collector.fetch_current_weather()

        # 4. 대기질 데이터 수집
        logging.info("--- 4. 대기질 데이터 수집 시작 ---")
        air_quality_collector = AirQualityCollector()
        current_air_quality = air_quality_collector.fetch_air_quality()

        # 5. 데이터 통합
        logging.info("--- 5. 따릉이, 날씨, 대기질 데이터 통합 시작 ---")
        final_df = enriched_bike_df.copy()

        # 날씨 데이터 통합 로직
        if current_weather:
            for key, value in current_weather.items():
                final_df[key] = value
        else:
            logging.warning("날씨 데이터 수집에 실패하여 통합을 건너킵니다.")

        # 대기질 데이터 통합 로직
        if current_air_quality:
            for key, value in current_air_quality.items():
                final_df[key] = value
        else:
            logging.warning("대기질 데이터 수집에 실패하여 통합을 건너킵니다.")

        logging.info("데이터 통합 완료.")
            
        # 6. 데이터베이스에 저장
        logging.info("--- 6. 데이터베이스에 저장 시작 ---")
        try:
            # db.database 모듈에서 데이터베이스 엔진 가져오기
            # sys.path에 상위 디렉토리 추가 필요
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
            from db.database import engine

            if engine is not None:
                table_name = "bike_availability_realtime"
                final_df.to_sql(table_name, con=engine, if_exists='replace', index=False)
                logging.info(f"데이터가 '{table_name}' 테이블에 성공적으로 저장되었습니다.")
            else:
                logging.error("데이터베이스 엔진이 없어 저장을 건너뜁니다.")

        except Exception as e:
            logging.error(f"데이터베이스 저장 중 오류 발생: {e}")



    # 7. 최종 결과 확인 (수집 성공 여부와 관계없이 실행)
    print("\n[통합된 최종 데이터 샘플]")
    if 'final_df' in locals() and not final_df.empty:
        print(final_df.head())
        print(f"\n최종 데이터 컬럼 수: {len(final_df.columns)}")
        print(final_df.columns.tolist())
    elif not raw_bike_df.empty:
        print("따릉이 원본 데이터만 수집되었습니다.")
        print(raw_bike_df.head())
    else:
        print("데이터 수집에 실패했습니다.")

    print(f"\n수집된 총 대여소 수: {len(raw_bike_df) if not raw_bike_df.empty else 0}")
