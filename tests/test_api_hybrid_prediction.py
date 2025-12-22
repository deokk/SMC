# tests/test_api_hybrid_prediction.py

import requests
import pytest

BASE_URL = "http://127.0.0.1:8000"

# LSTM 모델로 학습된 것으로 알려진 유효한 station_id를 사용합니다.
# 이전에 ST-178, ST-239 등이 언급되었습니다.
VALID_STATION_ID = "ST-974" 
INVALID_STATION_ID = "ST-99999" # 존재하지 않는 대여소 ID
VALID_N_MINUTES = 60 # 허용 범위 내 (0 <= n_minutes <= 5760)
TOO_LARGE_N_MINUTES = 6000 # 허용 범위 초과
NEGATIVE_N_MINUTES = -1 # 유효하지 않은 음수

def test_get_hybrid_prediction_success():
    """
    /predict/hybrid/{station_id} 엔드포인트가 예측 결과를 성공적으로 반환하는지 테스트합니다.
    """
    params = {"n_minutes": VALID_N_MINUTES}
    response = requests.get(f"{BASE_URL}/predict/hybrid/{VALID_STATION_ID}", params=params)

    # 1. 상태 코드 검증 (200 OK)
    assert response.status_code == 200, f"예상 상태 코드 200, 실제: {response.status_code}. 응답: {response.text}"

    # 2. 응답 본문이 JSON 형식인지 검증
    try:
        response_data = response.json()
    except ValueError:
        pytest.fail("응답이 유효한 JSON 형식이 아닙니다.")

    # 3. 응답 데이터 구조 검증
    required_keys = ["station_id", "prediction_in_minutes", "predicted_bike_count", "model_loaded"]
    for key in required_keys:
        assert key in response_data, f"필수 키 '{key}'가 응답에 없습니다."

    assert response_data["station_id"] == VALID_STATION_ID, \
        f"예상 station_id '{VALID_STATION_ID}', 실제: {response_data['station_id']}"
    assert response_data["prediction_in_minutes"] == VALID_N_MINUTES, \
        f"예상 prediction_in_minutes '{VALID_N_MINUTES}', 실제: {response_data['prediction_in_minutes']}"
    assert isinstance(response_data["predicted_bike_count"], int), \
        f"'predicted_bike_count'는 정수여야 합니다 (실제: {type(response_data['predicted_bike_count'])})."
    assert isinstance(response_data["model_loaded"], bool), \
        f"'model_loaded'는 boolean이어야 합니다 (실제: {type(response_data['model_loaded'])})."
    
    print(f"\n✅ 테스트 성공: {VALID_STATION_ID}에 대한 예측 결과를 성공적으로 불러왔습니다.")

def test_get_hybrid_prediction_invalid_station_id():
    """
    유효하지 않은 station_id로 요청했을 때 404 에러를 반환하는지 테스트합니다.
    """
    params = {"n_minutes": VALID_N_MINUTES}
    response = requests.get(f"{BASE_URL}/predict/hybrid/{INVALID_STATION_ID}", params=params)

    assert response.status_code == 404, \
        f"예상 상태 코드 404, 실제: {response.status_code}. 응답: {response.text}"
    assert "not found in XGBoost historical data" in response.json().get("detail", ""), \
        "유효하지 않은 station_id에 대한 에러 메시지가 예상과 다릅니다."
        
    print(f"\n✅ 테스트 성공: 유효하지 않은 station_id({INVALID_STATION_ID})에 대해 404 에러를 올바르게 처리합니다.")

def test_get_hybrid_prediction_n_minutes_too_large():
    """
    n_minutes가 너무 클 때 422 에러를 반환하는지 테스트합니다.
    """
    params = {"n_minutes": TOO_LARGE_N_MINUTES}
    response = requests.get(f"{BASE_URL}/predict/hybrid/{VALID_STATION_ID}", params=params)

    assert response.status_code == 422, \
        f"예상 상태 코드 422, 실제: {response.status_code}. 응답: {response.text}"
    assert "Input should be less than or equal to 5760" in response.json().get("detail", "")[0].get("msg", ""), \
        "n_minutes가 너무 클 때의 에러 메시지가 예상과 다릅니다."
        
    print(f"\n✅ 테스트 성공: n_minutes가 너무 클 때 422 에러를 올바르게 처리합니다.")

def test_get_hybrid_prediction_n_minutes_negative():
    """
    n_minutes가 음수일 때 422 에러를 반환하는지 테스트합니다.
    """
    params = {"n_minutes": NEGATIVE_N_MINUTES}
    response = requests.get(f"{BASE_URL}/predict/hybrid/{VALID_STATION_ID}", params=params)

    assert response.status_code == 422, \
        f"예상 상태 코드 422, 실제: {response.status_code}. 응답: {response.text}"
    assert "Input should be greater than or equal to 0" in response.json().get("detail", "")[0].get("msg", ""), \
        "n_minutes가 음수일 때의 에러 메시지가 예상과 다릅니다."
        
    print(f"\n✅ 테스트 성공: n_minutes가 음수일 때 422 에러를 올바르게 처리합니다.")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
