import os
import requests
import logging
from dotenv import load_dotenv

# --- 기본 설정 ---
# 로그 출력 형식 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- .env 파일에서 환경 변수 로드 ---
# 이 스크립트와 같은 위치에 .env 파일이 있다고 가정합니다.
load_dotenv()

def get_air_quality(station_name: str) -> dict | None:
    """
    Air Korea API로부터 지정된 측정소의 실시간 대기질 데이터를 수집합니다.

    Args:
        station_name (str): 데이터를 조회할 측정소 이름 (예: "종로구", "강남대로").

    Returns:
        dict: 수집된 대기질 데이터 (pm10, pm25, data_time) 또는 실패 시 None.
    """
    # 1. .env 파일에서 API 키 읽어오기
    api_key = os.getenv("AIR_QUALITY_API_KEY")
    if not api_key:
        logging.error("AIR_QUALITY_API_KEY가 .env 파일에 설정되지 않았습니다.")
        return None

    # 2. API 요청 주소 및 파라미터 설정
    base_url = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getMsrstnAcctoRltmMesureDnsty"
    params = {
        'serviceKey': api_key,
        'returnType': 'json',
        'stationName': station_name,
        'dataTerm': 'DAILY',
        'ver': '1.3'
    }

    logging.info(f"'{station_name}' 측정소의 대기질 데이터를 요청합니다...")

    # 3. API 요청 및 예외 처리
    try:
        # 타임아웃을 20초로 넉넉하게 설정
        response = requests.get(base_url, params=params, timeout=20)
        
        # HTTP 상태 코드가 200 (OK)가 아니면 에러 발생
        response.raise_for_status()
        data = response.json()

        # 4. 응답 데이터 파싱 (데이터 추출)
        items = data.get('response', {}).get('body', {}).get('items', [])
        if not items:
            # API 서버가 보내준 공식 에러 메시지 확인
            error_msg = data.get('response', {}).get('header', {}).get('resultMsg', '데이터 없음')
            logging.warning(f"API 응답에 데이터가 없습니다. (서버 메시지: {error_msg})")
            return None

        # 가장 최신 데이터는 첫 번째 항목
        latest_data = items[0]
        pm10_value = latest_data.get('pm10Value')
        pm25_value = latest_data.get('pm25Value')

        # API가 측정값 없음(-)을 보낼 수 있으므로, 숫자일 때만 변환
        air_quality_data = {
            "pm10": int(pm10_value) if pm10_value and pm10_value.isdigit() else None,
            "pm25": int(pm25_value) if pm25_value and pm25_value.isdigit() else None,
            "data_time": latest_data.get('dataTime')
        }

        logging.info(f"✅ 데이터 수집 성공: {air_quality_data}")
        return air_quality_data

    except requests.exceptions.Timeout:
        logging.error("API 요청 시간이 초과되었습니다. 서버가 매우 느리거나 점검 중일 수 있습니다.")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"API 요청 중 에러 발생: {e}")
        return None
    except Exception as e:
        logging.error(f"데이터 처리 중 알 수 없는 에러 발생: {e}")
        return None

# --- 메인 실행 부분 ---
if __name__ == "__main__":
    # '종로구' 측정소로 고정하여 테스트
    station_to_check = "종로구"
    air_data = get_air_quality(station_name=station_to_check)

    if air_data:
        print("\n--- 💨 수집된 대기질 정보 ---")
        print(f"측정소: {station_to_check}")
        print(f"측정 시각: {air_data['data_time']}")
        print(f"미세먼지(PM10): {air_data['pm10']} µg/m³")
        print(f"초미세먼지(PM2.5): {air_data['pm25']} µg/m³")
        print("--------------------------")
    else:
        print("\n❌ 대기질 정보를 가져오는 데 실패했습니다. 위의 로그 메시지를 확인해주세요.")