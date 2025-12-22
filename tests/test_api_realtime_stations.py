# tests/test_api_realtime_stations.py

import requests
import pytest

# FastAPI 애플리케이션이 실행 중인 기본 URL
# 사용자의 환경에 맞게 변경될 수 있습니다.
BASE_URL = "http://127.0.0.1:8000"

def test_get_all_realtime_stations_success():
    """
    /stations/realtime 엔드포인트가 모든 대여소 정보를 성공적으로 반환하는지 테스트합니다.
    """
    # API 요청
    response = requests.get(f"{BASE_URL}/stations/realtime")

    # 1. 상태 코드 검증 (200 OK)
    assert response.status_code == 200, f"예상 상태 코드 200, 실제: {response.status_code}"

    # 2. 응답 본문이 JSON 형식인지 검증
    try:
        response_data = response.json()
    except ValueError:
        pytest.fail("응답이 유효한 JSON 형식이 아닙니다.")

    # 3. 응답이 리스트 형태인지, 비어있지 않은지 검증
    assert isinstance(response_data, list), f"응답의 타입이 리스트가 아닙니다 (실제: {type(response_data)})."
    assert len(response_data) > 0, "실시간 대여소 정보가 비어 있습니다."
    
    print(f"\n✅ 테스트 성공: {len(response_data)}개의 실시간 대여소 정보를 성공적으로 불러왔습니다.")

def test_realtime_station_data_structure():
    """
    반환된 개별 대여소 정보의 데이터 구조와 타입을 검증합니다.
    """
    response = requests.get(f"{BASE_URL}/stations/realtime")
    assert response.status_code == 200
    
    response_data = response.json()
    assert isinstance(response_data, list) and len(response_data) > 0

    # 첫 번째 대여소 정보를 샘플로 사용
    station = response_data[0]
    print(f"✅ 첫 번째 대여소 샘플 데이터: {station}")

    # 4. 필수 키(Key) 존재 여부 검증
    required_keys = [
        "station_id", "station_display_name", "latitude", "longitude", 
        "available_bikes", "station_capacity", "timestamp"
    ]
    for key in required_keys:
        assert key in station, f"필수 키 '{key}'가 응답에 없습니다."

    # 5. 각 키의 데이터 타입 검증
    assert isinstance(station["station_id"], str), f"'station_id'는 문자열이어야 합니다 (실제: {type(station['station_id'])})."
    assert isinstance(station["latitude"], float), f"'latitude'는 float이어야 합니다 (실제: {type(station['latitude'])})."
    assert isinstance(station["longitude"], float), f"'longitude'는 float이어야 합니다 (실제: {type(station['longitude'])})."
    assert isinstance(station["available_bikes"], int), f"'available_bikes'는 정수여야 합니다 (실제: {type(station['available_bikes'])})."
    assert isinstance(station["station_capacity"], int), f"'station_capacity'는 정수여야 합니다 (실제: {type(station['station_capacity'])})."
    
    print("✅ 테스트 성공: 데이터 구조와 타입이 올바릅니다.")

def test_get_specific_realtime_station_by_name():
    """
    특정 대여소 이름으로 조회했을 때 정상적으로 필터링되는지 테스트합니다.
    '건국대학교'를 예시로 사용합니다.
    """
    # 테스트할 대여소 이름
    station_name_to_search = "건국대학교"
    params = {"station_display_name": station_name_to_search}

    response = requests.get(f"{BASE_URL}/stations/realtime", params=params)
    
    assert response.status_code == 200, f"예상 상태 코드 200, 실제: {response.status_code}"
    response_data = response.json()
    
    assert isinstance(response_data, list), "필터링된 응답이 리스트가 아닙니다."
    
    # "건국대학교"가 포함된 결과가 하나 이상 있어야 함
    assert len(response_data) > 0, f"'{station_name_to_search}' 이름으로 조회된 대여소가 없습니다."

    # 모든 결과의 이름에 '건국대학교'가 포함되어 있는지 확인
    for station in response_data:
        assert station_name_to_search in station.get("station_display_name", ""), \
            f"조회된 결과 '{station.get('station_display_name')}'에 '{station_name_to_search}'가 포함되어 있지 않습니다."
            
    print(f"\n✅ 테스트 성공: '{station_name_to_search}' 이름으로 {len(response_data)}개의 대여소를 성공적으로 조회했습니다.")

if __name__ == "__main__":
    # 이 스크립트를 직접 실행할 경우, pytest를 사용하여 테스트를 실행합니다.
    # 터미널에서 `pytest tests/test_api_realtime_stations.py -v` 명령으로도 실행할 수 있습니다.
    pytest.main([__file__, "-v"])
