
import os
import logging
from dotenv import load_dotenv
from data.air_quality_collector import AirQualityCollector

# 로깅 설정 강화: 모든 INFO 레벨 로그가 출력되도록 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger().setLevel(logging.INFO)

# .env 파일 로드
load_dotenv()

print("--- 대기질 데이터 단독 수집 테스트 시작 ---")

collector = AirQualityCollector()

try:
    air_quality_data = collector.fetch_air_quality()

    if air_quality_data:
        print("\n✅ 대기질 데이터 수집 성공:")
        for key, value in air_quality_data.items():
            print(f"  {key}: {value}")
    else:
        print("\n❌ 대기질 데이터 수집 실패: (API 키 문제 또는 응답 없음)")
except Exception as e:
    print(f"\n❌ 대기질 데이터 수집 중 예외 발생: {e}")

print("--- 대기질 데이터 단독 수집 테스트 종료 ---")
