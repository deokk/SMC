"""
SMC 프로젝트를 위한 실시간 날씨 데이터 수집기 (공공데이터포털 기상청 API 사용)
- API: 초단기실황조회 (실시간 예측에 최적화)
- 위치: 위도/경도를 격자 좌표로 변환하여 사용
"""
import os
import requests
import logging
import math
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 인-메모리 캐시 변수
_weather_cache = {'data': None, 'timestamp': None}
_cache_duration = timedelta(minutes=30) # 캐시 유효 시간

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# .env 파일에서 환경 변수 로드 (경로는 실제 위치에 맞게 조정 필요)
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)


class RealtimeWeatherCollector:
    """
    공공데이터포털 기상청 '초단기실황조회' API로부터 특정 위치의 실시간 날씨 데이터를 수집합니다.
    """

    def __init__(self, lat: float = 37.5385, lon: float = 127.0725):
        """
        API 키와 초기 위치(위도/경도)를 설정합니다.
        기본 위치는 광진구입니다.
        """
        api_key_raw = os.getenv("WEATHER_API_KEY")
        self.api_key = api_key_raw.strip().replace('\n', '') if api_key_raw else None
        if not self.api_key:
            raise ValueError("WEATHER_API_KEY가 .env 파일에 설정되지 않았습니다.")

        # API 엔드포인트를 '초단기실황조회' 서비스로 변경
        self.base_url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
        
        # 입력받은 위도/경도를 기상청 격자 좌표로 변환
        self.nx, self.ny = self._lat_lon_to_grid(lat, lon)
        logging.info(f"위치 ({lat}, {lon}) -> 격자 좌표 ({self.nx}, {self.ny})로 변환 완료")

    def _lat_lon_to_grid(self, lat, lon):
        """위도, 경도를 기상청 격자 좌표(X, Y)로 변환하는 함수"""
        RE = 6371.00877  # 지구 반경(km)
        GRID = 5.0      # 격자 간격(km)
        SLAT1 = 30.0    # 투영 위도1(degree)
        SLAT2 = 60.0    # 투영 위도2(degree)
        OLON = 126.0    # 기준점 경도(degree)
        OLAT = 38.0     # 기준점 위도(degree)
        XO = 43         # 기준점 X좌표(GRID)
        YO = 136        # 기준점 Y좌표(GRID)
        
        DEGRAD = math.pi / 180.0
        
        re = RE / GRID
        slat1 = SLAT1 * DEGRAD
        slat2 = SLAT2 * DEGRAD
        olon = OLON * DEGRAD
        olat = OLAT * DEGRAD

        sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
        sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
        sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
        sf = (math.pow(sf, sn) * math.cos(slat1)) / sn
        ro = re * sf / math.pow(math.tan(math.pi * 0.25 + olat * 0.5), sn)

        ra = re * sf / math.pow(math.tan(math.pi * 0.25 + lat * DEGRAD * 0.5), sn)
        theta = lon * DEGRAD - olon
        if theta > math.pi:
            theta -= 2.0 * math.pi
        if theta < -math.pi:
            theta += 2.0 * math.pi
        theta *= sn

        nx = int(ra * math.sin(theta) + XO + 0.5)
        ny = int(ro - ra * math.cos(theta) + YO + 0.5)

        return nx, ny

    def _calculate_severity(self, precipitation: float, wind_speed: float, temp: float) -> int:
        """날씨 악천후 등급을 0-3 스케일로 계산합니다."""
        severity = 0
        # 강수량 기준 (mm/h)
        if precipitation >= 15: severity = max(severity, 3) # 호우
        elif precipitation >= 3: severity = max(severity, 2) # 보통 비
        elif precipitation > 0: severity = max(severity, 1) # 약한 비

        # 풍속 기준 (m/s)
        if wind_speed >= 14: severity = max(severity, 2) # 강풍
        elif wind_speed >= 9: severity = max(severity, 1) # 다소 강한 바람

        # 기온 기준 (°C)
        if temp <= -5 or temp >= 33: severity = max(severity, 2) # 한파/폭염
        
        return severity

    def fetch_current_weather(self) -> dict | None:
        """현재 위치의 날씨 데이터를 가져와 정제된 딕셔셔너리로 반환합니다."""
        now = datetime.now()
        # API는 매시간 30분에 데이터를 생성하므로, 가장 최신 데이터를 얻기 위해 현재 시간을 기준으로 base_time 설정
        # 만약 현재 40분 미만이면, 이전 시간대 데이터를 요청해야 함
        if now.minute < 40:
            now -= timedelta(hours=1)
        
        base_date = now.strftime('%Y%m%d')
        base_time = now.strftime('%H00')

        params = {
            'serviceKey': self.api_key,
            'pageNo': '1',
            'numOfRows': '10', # 한번에 여러 항목(기온, 습도 등)을 모두 받기 위해 넉넉히 설정
            'dataType': 'JSON',
            'base_date': base_date,
            'base_time': base_time,
            'nx': str(self.nx),
            'ny': str(self.ny)
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()

            result_code = data.get("response", {}).get("header", {}).get("resultCode")
            if result_code != '00':
                error_msg = data.get("response", {}).get("header", {}).get("resultMsg", "알 수 없는 오류")
                logging.error(f"API 에러: {error_msg} (코드: {result_code})")
                return None
            
            items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
            if not items:
                logging.warning("API에서 날씨 데이터를 찾을 수 없습니다.")
                return None
            
            # API 응답은 {'category': 'T1H', 'obsrValue': '15'} 형태의 리스트이므로 딕셔너리로 변환
            weather_data = {item['category']: item['obsrValue'] for item in items}
            
            temp = float(weather_data.get("T1H", 0)) # 기온
            humidity = float(weather_data.get("REH", 0)) # 습도
            wind_speed = float(weather_data.get("WSD", 0)) # 풍속
            
            # 강수량(RN1)은 '강수 없음'일 경우 "0" 또는 아예 항목이 없을 수 있음
            precipitation = float(weather_data.get("RN1", "0"))

            weather_info = {
                "temperature": temp,
                "humidity": humidity,
                "precipitation": precipitation,
                "wind_speed": wind_speed,
                "is_raining": 1 if precipitation > 0 else 0,
                "weather_severity": self._calculate_severity(precipitation, wind_speed, temp),
                "timestamp": datetime.now(),
                "weather_source": "KMA_UltraSrtNcst" # API 변경에 따라 source도 변경
            }
            logging.info(f"날씨 데이터 수집 성공: 기온 {temp}°C, 강수량 {precipitation}mm")
            
            # 캐시 업데이트
            _weather_cache['data'] = weather_info
            _weather_cache['timestamp'] = datetime.now()
            
            return weather_info

        except requests.exceptions.RequestException as e:
            logging.error(f"기상청 API 요청 중 에러 발생: {e}", exc_info=True)
            # 캐시 확인 및 폴백
            if _weather_cache['data'] and (datetime.now() - _weather_cache['timestamp']) < _cache_duration:
                logging.warning(f"API 호출 실패, {round((datetime.now() - _weather_cache['timestamp']).total_seconds()/60)}분 전 캐시된 데이터를 사용합니다.")
                return _weather_cache['data']
            else:
                logging.error("API 호출 실패 및 유효한 캐시 데이터 없음.")
                return None
        except Exception as e:
            logging.error(f"날씨 데이터 처리 중 예기치 않은 에러 발생: {e}")
            # 캐시 확인 및 폴백
            if _weather_cache['data'] and (datetime.now() - _weather_cache['timestamp']) < _cache_duration:
                logging.warning(f"데이터 처리 중 오류 발생, {round((datetime.now() - _weather_cache['timestamp']).total_seconds()/60)}분 전 캐시된 데이터를 사용합니다.")
                return _weather_cache['data']
            else:
                logging.error("데이터 처리 중 오류 발생 및 유효한 캐시 데이터 없음.")
                return None

if __name__ == '__main__':
    # .env 파일에 WEATHER_API_KEY가 설정되어 있는지 확인하세요.
    
    logging.info("--- 날씨 수집기 테스트 시작 (위치: 서울시청) ---")
    
    # 클래스 생성 시 위도, 경도를 넣어 원하는 지역의 날씨를 조회할 수 있습니다.
    # 예: 평택시청 날씨 조회 -> weather_collector = RealtimeWeatherCollector(lat=36.9912, lon=127.0901)
    weather_collector = RealtimeWeatherCollector()
    current_weather = weather_collector.fetch_current_weather()

    if current_weather:
        print("\n[수집된 현재 날씨 정보]")
        for key, value in current_weather.items():
            print(f"- {key}: {value}")
    else:
        print("\n날씨 정보를 가져오는 데 실패했습니다.")