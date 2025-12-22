# tests/test_api_route_optimization.py

import requests
import pytest

BASE_URL = "http://127.0.0.1:8000"

def test_post_route_optimized_success():
    """
    /route/optimized 엔드포인트가 경로 최적화 결과를 성공적으로 반환하는지 테스트합니다.
    ODsay API 키가 설정되어 있어야 합니다.
    """
    # 광진구 내 임의의 시작점과 끝점 좌표 (예: 건국대학교 -> 어린이대공원)
    # 실제 ODsay API 호출 시에는 좀 더 정확한 좌표를 사용해야 합니다.
    start_lat = 37.5408
    start_lon = 127.0793
    end_lat = 37.5471
    end_lon = 127.0734

    payload = {
        "start_lat": start_lat,
        "start_lon": start_lon,
        "end_lat": end_lat,
        "end_lon": end_lon
    }

    # API 요청
    response = requests.post(f"{BASE_URL}/route/optimized", json=payload)

    # 1. 상태 코드 검증 (200 OK)
    assert response.status_code == 200, f"예상 상태 코드 200, 실제: {response.status_code}. 응답: {response.text}"

    # 2. 응답 본문이 JSON 형식인지 검증
    try:
        response_data = response.json()
    except ValueError:
        pytest.fail("응답이 유효한 JSON 형식이 아닙니다.")

    # 3. 응답이 리스트 형태인지, 비어있지 않은지 검증
    assert isinstance(response_data, list), f"응답의 타입이 리스트가 아닙니다 (실제: {type(response_data)})."
    assert len(response_data) > 0, "경로 최적화 정보가 비어 있습니다."
    
    print(f"✅ 테스트 성공: {len(response_data)}개의 경로 옵션을 성공적으로 불러왔습니다.")

def test_route_option_data_structure():
    """
    반환된 개별 경로 옵션의 데이터 구조와 타입을 검증합니다.
    """
    start_lat = 37.5408
    start_lon = 127.0793
    end_lat = 37.5471
    end_lon = 127.0734

    payload = {
        "start_lat": start_lat,
        "start_lon": start_lon,
        "end_lat": end_lat,
        "end_lon": end_lon
    }
    
    response = requests.post(f"{BASE_URL}/route/optimized", json=payload)
    assert response.status_code == 200
    
    response_data = response.json()
    assert isinstance(response_data, list) and len(response_data) > 0

    # 첫 번째 경로 옵션을 샘플로 사용
    route_option = response_data[0]
    print(f"✅ 첫 번째 경로 옵션 샘플 데이터: {route_option}")

    # 4. 필수 키(Key) 존재 여부 검증
    required_keys = [
        "mode", "duration", "distance", "fare", "steps"
    ]
    for key in required_keys:
        assert key in route_option, f"필수 키 '{key}'가 응답에 없습니다."

    # 5. 각 키의 데이터 타입 검증
    assert isinstance(route_option["mode"], str), f"'mode'는 문자열이어야 합니다 (실제: {type(route_option['mode'])})."
    assert isinstance(route_option["duration"], int), f"'duration'은 정수여야 합니다 (실제: {type(route_option['duration'])})."
    assert isinstance(route_option["distance"], int), f"'distance'는 정수여야 합니다 (실제: {type(route_option['distance'])})."
    assert isinstance(route_option["fare"], int), f"'fare'는 정수여야 합니다 (실제: {type(route_option['fare'])})."
    assert isinstance(route_option["steps"], list), f"'steps'는 리스트여야 합니다 (실제: {type(route_option['steps'])})."
    
    # steps 리스트가 비어있지 않다면 첫 번째 step의 구조도 검증
    if route_option["steps"]:
        step = route_option["steps"][0]
        step_required_keys = ["type", "distance", "duration"]
        for key in step_required_keys:
            assert key in step, f"경로 스텝의 필수 키 '{key}'가 없습니다."
        assert isinstance(step["type"], str), f"스텝의 'type'은 문자열이어야 합니다."
        assert isinstance(step["distance"], int), f"스텝의 'distance'는 정수여야 합니다."
        assert isinstance(step["duration"], int), f"스텝의 'duration'은 정수여야 합니다."
    
    print("✅ 테스트 성공: 경로 옵션의 데이터 구조와 타입이 올바릅니다.")

def test_post_route_optimized_invalid_coords():
    """
    유효하지 않은 좌표로 요청했을 때 적절한 에러 응답을 반환하는지 테스트합니다.
    (예: 매우 먼 거리, 잘못된 형식 등 - 현재 ODsay API의 에러 처리 방식에 따라 달라질 수 있음)
    """
    # 매우 먼 거리에 있는 좌표 (ODsay API는 일정 거리 이상이면 경로를 찾지 못할 수 있음)
    start_lat = 0.0
    start_lon = 0.0
    end_lat = 1.0
    end_lon = 1.0

    payload = {
        "start_lat": start_lat,
        "start_lon": start_lon,
        "end_lat": end_lat,
        "end_lon": end_lon
    }

    response = requests.post(f"{BASE_URL}/route/optimized", json=payload)
    
    # ODsay API의 응답 정책에 따라 200 OK에 빈 리스트를 반환할 수도 있고,
    # 503 Service Unavailable을 반환할 수도 있습니다.
    # 현재 `app.py`에서는 `transit_routes`가 `None`일 때 503을 반환하도록 되어 있습니다.
    assert response.status_code in [200, 503], f"예상 상태 코드 200 또는 503, 실제: {response.status_code}. 응답: {response.text}"
    
    if response.status_code == 200:
        response_data = response.json()
        assert isinstance(response_data, list), "응답의 타입이 리스트가 아닙니다."
        # 이 경우 빈 리스트가 올 것으로 예상합니다.
        print(f"\n✅ 테스트 성공: 유효하지 않은 좌표로 요청 시 {len(response_data)}개의 경로를 반환했습니다. (200 OK)")
    elif response.status_code == 503:
        print(f"\n✅ 테스트 성공: 유효하지 않은 좌표로 요청 시 503 Service Unavailable을 반환했습니다.")
    
    # API 키 에러가 발생하면 503을 반환하는 경우가 많습니다.
    if response.status_code == 503 and "ODsay API 키가 설정되지 않았습니다." in response.text:
        print("💡 ODsay API 키 설정이 필요할 수 있습니다. `.env` 파일의 `ODSAY_API_KEY`를 확인하세요.")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
