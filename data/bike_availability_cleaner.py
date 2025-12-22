"""
SMC 프로젝트를 위한 데이터 클리너 및 특성 생성기
"""
import pandas as pd
import numpy as np

class BikeDataCleaner:
    """수집된 실시간 따릉이 데이터프레임을 정제하고, 모델 학습에 필요한 특성을 추가합니다."""

    def clean_and_enrich(self, df: pd.DataFrame) -> pd.DataFrame:
        """데이터프레임을 입력받아 정제 및 특성 추가 후, 새로운 데이터프레임을 반환합니다.

        Args:
            df (pd.DataFrame): RealtimeBikeCollector로부터 수집된 원본 데이터프레임

        Returns:
            pd.DataFrame: 정제되고 새로운 특성이 추가된 데이터프레임
        """
        if df.empty:
            return pd.DataFrame()

        # 원본 데이터프레임 복사
        processed_df = df.copy()

        # 1. 데이터 유효성 검사 및 정제
        # - station_capacity가 0보다 큰 대여소만 사용 (분모가 0이 되는 것 방지)
        processed_df = processed_df[processed_df['station_capacity'] > 0].copy()

        # - available_bikes가 음수인 경우 0으로 보정
        processed_df['available_bikes'] = processed_df['available_bikes'].clip(lower=0)

        # 2. 기본 파생 특성 추가
        # - 이용 가능한 거치대 수
        processed_df['available_racks'] = processed_df['station_capacity'] - processed_df['available_bikes']
        
        # - 이용률 (0 ~ 1)
        # processed_df['utilization_rate'] = (processed_df['available_bikes'] / processed_df['station_capacity']).round(3)

        # 3. 재고 상태 관련 특성 추가 (분류 모델의 Target이 될 수 있음)
        # - 재고 없음 (자전거 2대 이하)
        processed_df['is_stockout'] = (processed_df['available_bikes'] <= 2).astype(int)
        
        # - 거의 비어감 (자전거 5대 이하)
        # processed_df['is_nearly_empty'] = (processed_df['available_bikes'] <= 5).astype(int)
        
        # - 거의 가득 참 (빈 거치대 5개 이하)
        # processed_df['is_nearly_full'] = (processed_df['available_racks'] <= 5).astype(int)

        # 4. 시간 관련 특성 추가
        processed_df['hour'] = processed_df['timestamp'].dt.hour
        processed_df['day_of_week'] = processed_df['timestamp'].dt.dayofweek  # 0:월요일, 6:일요일
        processed_df['is_weekend'] = (processed_df['day_of_week'] >= 5).astype(int) # 토,일

        # 5. station_name을 station_number와 station_display_name으로 분리
        # '대여소번호. 대여소이름' 형식이라고 가정
        # 오류 방지를 위해 apply 사용
        def split_station_name(name):
            if isinstance(name, str) and '.' in name:
                parts = name.split('.', 1)
                try:
                    num = int(parts[0].strip())
                    display_name = parts[1].strip()
                    return num, display_name
                except ValueError:
                    # 숫자로 변환할 수 없는 경우
                    return None, name
            return None, name # 형식이 맞지 않는 경우

        processed_df[['station_number', 'station_display_name']] = processed_df['station_name'].apply(lambda x: pd.Series(split_station_name(x)))

        # 필요한 컬럼만 선택하여 최종 데이터프레임 생성
        final_columns = [
            'station_id', 'station_number', 'station_display_name', 'timestamp', 'latitude', 'longitude',
            'available_bikes', 'station_capacity', 'available_racks',
            'is_stockout',
            'hour', 'day_of_week', 'is_weekend'
        ]
        
        return processed_df[final_columns]


if __name__ == '__main__':
    # 이 스크립트가 잘 작동하는지 테스트하기 위한 예시 코드
    
    # 1. 가상의 데이터프레임 생성 (RealtimeBikeCollector의 출력과 유사한 형태)
    print("[테스트] 가상 데이터 생성 중...")
    sample_data = {
        'station_id': [f'ST-{i:03d}' for i in range(1, 6)],
        'station_name': ['테스트 대여소 1', '테스트 대여소 2', '테스트 대여소 3', '테스트 대여소 4', '테스트 대여소 5'],
        'available_bikes': [0, 3, 15, 20, -1], # 일부러 이상치(-1) 포함
        'station_capacity': [10, 15, 15, 18, 10], # 일부러 용량 초과(20) 포함
        'latitude': [37.5665, 37.5665, 37.5665, 37.5665, 37.5665],
        'longitude': [126.9780, 126.9780, 126.9780, 126.9780, 126.9780],
        'timestamp': pd.to_datetime(['2025-10-26 15:30:00'] * 5)
    }
    sample_df = pd.DataFrame(sample_data)
    print("\n[원본 데이터프레임]")
    print(sample_df.head())

    # 2. 클리너 객체 생성 및 데이터 처리
    print("\n[클리너] 데이터 정제 및 특성 추가 작업 수행 중...")
    cleaner = BikeDataCleaner()
    enriched_df = cleaner.clean_and_enrich(sample_df)

    # 3. 결과 확인
    print("\n[결과 데이터프레임]")
    print(enriched_df.head())
    print("\n[추가된 특성 확인]")
    print(enriched_df.columns)