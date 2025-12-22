import os
import httpx
import asyncio
import json
from dotenv import load_dotenv

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

# 환경 변수에서 ODsay API 키를 가져옵니다.
ODSAY_API_KEY = os.getenv("ODSAY_API_KEY")

async def test_odsay_api():
    """ODsay 대중교통 길찾기 API를 직접 호출하여 응답을 테스트합니다."""

    if not ODSAY_API_KEY:
        print("❌ 에러: .env 파일에 ODSAY_API_KEY가 설정되지 않았습니다.")
        return

    print(f"🔑 사용 중인 API 키: ...{ODSAY_API_KEY[-4:]}") # 키의 마지막 4자리만 표시

    # 테스트용 출발지/도착지 좌표 (건국대학교 -> 화양동 주민센터)
    params = {
        "apiKey": ODSAY_API_KEY,
        "SX": "127.0793",
        "SY": "37.5408",
        "EX": "127.0713",
        "EY": "37.5453",    
    }
    
    url = "https://api.odsay.com/v1/api/searchPubTransPathR"

    print(f"\n🚀 ODsay API에 GET 요청을 보냅니다...")
    print(f"URL: {url}")
    print(f"파라미터: { {k: (v if k != 'apiKey' else '...') for k, v in params.items()} }")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)

            print(f"\n✅ API 응답 상태 코드: {response.status_code}")
            
            # 응답 받은 JSON 데이터를 예쁘게 출력합니다.
            response_data = response.json()
            print("\n📋 ODsay API 원본 응답:")
            print(json.dumps(response_data, indent=2, ensure_ascii=False))

    except httpx.HTTPError as e:
        print(f"\n❌ HTTP 요청 중 에러 발생: {e}")
    except Exception as e:
        print(f"\n❌ 예상치 못한 에러 발생: {e}")

if __name__ == "__main__":
    asyncio.run(test_odsay_api())
