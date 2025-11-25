# check_env.py
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# MASTER_API_KEY 값 가져오기
master_api_key = os.getenv("MASTER_API_KEY")

# 결과 출력
if master_api_key:
    print(f"✅ MASTER_API_KEY를 성공적으로 찾았습니다.")
    # 보안을 위해 키의 일부만 출력
    print(f"   - 값(일부): {master_api_key[:4]}...{master_api_key[-4:]}")
else:
    print(f"❌ MASTER_API_KEY를 .env 파일에서 찾을 수 없습니다.")
    print(f"   - .env 파일에 'MASTER_API_KEY=your_key_value' 형식으로 저장되어 있는지 확인해주세요.")

# 다른 키들도 확인
db_user = os.getenv("DB_USER")
if db_user:
    print(f"✅ DB_USER 키는 찾았습니다: {db_user}")
else:
    print(f"❌ DB_USER 키는 찾을 수 없습니다.")
