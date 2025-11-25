import os
import requests
import logging
from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AirQualityCollector:
    """외부 API로부터 실시간 미세먼지 데이터를 수집합니다."""

    def __init__(self):
        """API 키와 기본 URL 등 초기 설정을 로드합니다."""
        load_dotenv()

        api_key_raw = os.getenv("AIR_QUALITY_API_KEY")
        self.api_key = api_key_raw.strip().replace('\n', '') if api_key_raw else None

        self.base_url = "https://apis.data.go.kr/B552584/ArpltnInforInqireSvc"
        self.service_url = f"{self.base_url}/getMsrstnAcctoRltmMesureDnsty"  # 측정소별 실시간 측정정보
        self.return_type = "json"
        self.page_no = 1
        self.ver = "1.3" # 측정소별 조회는 1.3 버전이 안정적일 수 있음

    def fetch_air_quality(self, station_name: str = "광진구") -> dict | None:
        """특정 측정소의 대기질 데이터를 수집하여 딕셔너리 형태로 반환합니다."""
        if not self.api_key:
            logging.warning("AIR_QUALITY_API_KEY가 .env 파일에 없습니다.")
            return None

        params = {
            "serviceKey": self.api_key,
            "returnType": self.return_type,
            "numOfRows": 10, # 특정 측정소는 데이터가 많지 않음
            "pageNo": self.page_no,
            "stationName": station_name,
            "dataTerm": "DAILY", # 일별 데이터 요청
            "ver": self.ver
        }


        #print(f"DEBUG: Requesting Air Quality API: {self.service_url}")
        #print(f"DEBUG: Params: {params}")

        try:
            response = requests.get(self.service_url, params=params, timeout=30)
            response.encoding = 'utf-8'
            response.raise_for_status()
            data = response.json()

            header = data.get("response", {}).get("header", {})
            result_code = header.get("resultCode")
            result_msg = header.get("resultMsg")

            if result_code != "00":
                logging.error(f"API 오류: {result_code}, 메시지: {result_msg}")
                return None

            items = data.get("response", {}).get("body", {}).get("items", [])
            if not items:
                logging.warning(f"'{station_name}' 측정소의 데이터가 비어 있음. 메시지: {result_msg}")
                return None

            # 가장 최신 데이터를 사용
            item = items[0]
            pm10_value = item.get("pm10Value")
            pm25_value = item.get("pm25Value")

            air_quality_data = {
                "air_quality_pm10": int(pm10_value) if pm10_value and pm10_value.isdigit() else None,
                "air_quality_pm25": int(pm25_value) if pm25_value and pm25_value.isdigit() else None,
                "air_quality_o3": item.get("o3Value"),
                "air_quality_data_time": item.get("dataTime"),
                "air_source": station_name  # 요청한 측정소 이름으로 명시
            }

            logging.info(f"대기질 데이터 수집 성공: {air_quality_data}")
            return air_quality_data

        except requests.exceptions.RequestException as e:
            logging.error(f"대기질 API 요청 에러: {e}")
            with open("air_quality_error.log", "w", encoding="utf-8") as f:
                f.write(str(e))
            return None
        except Exception as e:
            logging.error(f"데이터 처리 중 예외 발생: {e}")
            with open("air_quality_error.log", "w", encoding="utf-8") as f:
                f.write(str(e))
            return None


if __name__ == "__main__":
    collector = AirQualityCollector()
    if collector.api_key:
        result = collector.fetch_air_quality("광진구")
        if result:
            print("\n--- 최종 수집 데이터 ---")
            print(result)
        else:
            print("\n--- 데이터 수집 실패 ---")
    else:
        print("API 키가 설정되지 않았습니다. .env 파일을 확인하세요.")
