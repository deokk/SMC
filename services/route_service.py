import os
import math
import logging
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 상수 정의
AVG_WALKING_SPEED_KMH = 5.0  # 평균 도보 속도 (km/h)
AVG_BIKE_SPEED_KMH = 15.0   # 평균 자전거 속도 (km/h)
EARTH_RADIUS_KM = 6371      # 지구 반지름

class RouteService:
    """
    경로 계산 관련 서비스를 제공합니다.
    초기 버전은 Haversine 공식을 이용한 직선 거리 기반으로 시간과 거리를 추정합니다.
    """
    def __init__(self):
        self.api_key = os.getenv("MAP_API_KEY")
        if not self.api_key:
            # API 키가 당장 사용되지는 않지만, 향후 확장을 위해 경고를 남깁니다.
            logging.warning("MAP_API_KEY가 .env 파일에 설정되지 않았습니다. 향후 API 연동 시 필요합니다.")

    def _haversine_distance(self, lon1: float, lat1: float, lon2: float, lat2: float) -> float:
        """
        두 지점의 경도, 위도를 받아 Haversine 공식으로 거리를 계산합니다.
        결과는 킬로미터(km) 단위로 반환합니다.
        """
        lon1_rad, lat1_rad, lon2_rad, lat2_rad = map(math.radians, [lon1, lat1, lon2, lat2])

        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad

        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance = EARTH_RADIUS_KM * c
        return distance

    def estimate_route(self, origin_lon: float, origin_lat: float, dest_lon: float, dest_lat: float, mode: str) -> dict:
        """
        출발지, 도착지, 이동 수단을 받아 예상 시간과 거리를 반환합니다.
        
        Args:
            origin_lon, origin_lat: 출발지 경도, 위도
            dest_lon, dest_lat: 도착지 경도, 위도
            mode (str): "walk" 또는 "bike"

        Returns:
            dict: {'duration': 초, 'distance': 미터}
        """
        if mode == 'walk':
            speed_kmh = AVG_WALKING_SPEED_KMH
        elif mode == 'bike':
            speed_kmh = AVG_BIKE_SPEED_KMH
        else:
            raise ValueError("지원하지 않는 이동 수단입니다. 'walk' 또는 'bike'를 사용하세요.")

        # 직선 거리 계산 (km)
        distance_km = self._haversine_distance(origin_lon, origin_lat, dest_lon, dest_lat)
        distance_meters = distance_km * 1000

        # 예상 소요 시간 계산 (시간)
        duration_hours = distance_km / speed_kmh
        duration_seconds = duration_hours * 3600
        
        # 실제 경로는 직선보다 길기 때문에, 보정계수 (e.g., 1.2)를 곱해줄 수 있습니다.
        # 여기서는 단순화를 위해 직선 거리 기준으로 계산합니다.

        return {
            "duration": int(duration_seconds),
            "distance": round(distance_meters, 2)
        }

    def get_public_transit_route(self, origin_lon: float, origin_lat: float, dest_lon: float, dest_lat: float) -> dict:
        """
        카카오내비 API를 호출하여 대중교통 경로 정보를 상세히 분석하여 반환합니다.
        
        Returns:
            dict: {'total_duration': 초, 'total_distance': 미터, 'path': 상세 경로 세그먼트 리스트}
            실패 시 None을 반환합니다.
        """
        if not self.api_key:
            logging.error("카카오 API 키가 없어 대중교통 경로를 조회할 수 없습니다.")
            return None

        url = "https://apis-navi.kakaomobility.com/v1/directions"
        
        headers = {"Authorization": f"KakaoAK {self.api_key}"}
        params = {"origin": f"{origin_lon},{origin_lat}", "destination": f"{dest_lon},{dest_lat}"}

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if not data.get('routes') or not data['routes'][0].get('sections'):
                logging.warning("카카오 API에서 경로 정보를 찾지 못했습니다.")
                return None

            route = data['routes'][0]
            path_segments = []

            for section in route['sections']:
                distance = section['distance']
                duration = section['duration']
                
                # 이동 수단 및 상세 설명 파싱
                if not section['guides']:
                    # 가이드 없는 구간(예: 단순 연결)은 건너뛰기
                    continue

                first_guide = section['guides'][0]
                transport_type = "walk" # 기본값은 도보
                description = f"도보 이동 ({distance}m)"

                if section.get('roads'): # 도로 정보가 있으면 이동수단이 있는 것
                    road_info = section['roads'][0]
                    if road_info.get('line_id', 0) != 0: # line_id가 있으면 버스 또는 지하철
                        transport_type = "bus" if road_info.get('bus_type', 0) != 0 else "subway"
                        line_name = road_info.get('name', '정보 없음')
                        
                        # 정류장 수 계산
                        stops_count = len(section.get('stops', []))
                        
                        description = f"{'버스' if transport_type == 'bus' else '지하철'} {line_name} ({stops_count} 정거장)"
                    else:
                        transport_type = "walk"
                        description = f"{road_info.get('name', '알수없는 도로')} 따라 도보 이동"
                
                path_segments.append({
                    "type": transport_type,
                    "description": description,
                    "duration": duration,
                    "distance": distance
                })

            if not path_segments:
                return None

            return {
                "total_duration": route['summary']['duration'],
                "total_distance": route['summary']['distance'],
                "path": path_segments
            }

        except requests.exceptions.RequestException as e:
            logging.error(f"카카오 API 요청 중 오류 발생: {e}")
            return None
        except Exception as e:
            logging.error(f"카카오 API 응답 처리 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return None

