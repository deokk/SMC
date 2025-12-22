import requests
import os
import json
from dotenv import load_dotenv

def get_air_korea_station_names(service_key):
    """
    한국환경공단 에어코리아 API에서 측정소 목록을 조회합니다.
    """
    base_url = "http://openapi.airkorea.or.kr/openapi/services/rest/MsrstnInfoInqireSvc/"
    operation = "getMsrstnList"
    
    params = {
        "serviceKey": service_key,
        "returnType": "json",
        "numOfRows": "1000",
        "pageNo": "1",
        "addr": "서울" # 서울 지역만 조회
    }

    try:
        response = requests.get(f"{base_url}{operation}", params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("response") and data["response"].get("header") and data["response"]["header"].get("resultCode") != "00":
            print(f"API Error: {data['response']['header'].get('resultMsg')}")
            return []

        items = data.get("response", {}).get("body", {}).get("items", [])
        station_names = [item.get("stationName") for item in items if item.get("stationName")]
        return station_names
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON response: {e}")
        print(f"Response content: {response.text}")
        return []

if __name__ == "__main__":
    load_dotenv()
    air_korea_service_key = os.getenv("AIR_QUALITY_API_KEY")

    if not air_korea_service_key:
        print("Error: AIR_QUALITY_API_KEY environment variable not set.")
    else:
        print("Fetching Air Korea station names for Seoul...")
        station_list = get_air_korea_station_names(air_korea_service_key)
        
        if station_list:
            print(f"Found {len(station_list)} stations:")
            # '종로'가 포함된 측정소만 필터링하여 출력
            jongro_stations = [name for name in station_list if '종로' in name]
            if jongro_stations:
                print("\n--- Stations in Jongno-gu ---")
                for name in jongro_stations:
                    print(f"- {name}")
            else:
                print("\n--- No stations found in Jongno-gu ---")
                print("\n--- All stations in Seoul ---")
                for name in station_list:
                    print(f"- {name}")
        else:
            print("No station names found or an error occurred.")