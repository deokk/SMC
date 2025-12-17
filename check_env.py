import os
from dotenv import load_dotenv

# .env 파일 로드
# 이 스크립트가 프로젝트 루트에 있다고 가정합니다.
# 만약 다른 위치에 있다면, dotenv_path를 명시해야 합니다.
# 예: load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv()

# ORS_API_KEY 환경 변수 가져오기
api_key = os.getenv("ORS_API_KEY")

# 결과 출력
if api_key:
    print(f"✅ ORS_API_KEY를 성공적으로 로드했습니다.")
    print(f"   - 일부만 표시: {api_key[:5]}...{api_key[-5:]}")
else:
    print(f"❌ ORS_API_KEY를 로드하지 못했습니다.")
    print("   - .env 파일이 프로젝트 루트 디렉터리에 있는지 확인하세요.")
    print("   - .env 파일에 'ORS_API_KEY=Your_Key' 형식으로 키가 저장되었는지 확인하세요.")
    print("   - `python-dotenv` 라이브러리가 설치되었는지 확인하세요. (pip install python-dotenv)")

print("\n--- 모든 로드된 환경 변수 (일부) ---")
# 디버깅을 위해 로드된 모든 환경 변수를 출력해볼 수 있습니다.
# 민감한 정보가 있을 수 있으니 주의하세요.
for key, value in os.environ.items():
    if "KEY" in key.upper() or "SECRET" in key.upper():
        print(f"{key}: ...")
    elif "ORS" in key.upper():
         print(f"{key}: {value[:5]}...")