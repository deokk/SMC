# SMC 프로젝트 프론트엔드 연동 가이드

이 가이드는 프론트엔드 개발자가 SMC 백엔드 API와 연동하는 방법을 안내합니다.

## 1. 기본 URL

- **로컬 개발:** `http://127.0.0.1:8000`

## 2. API 엔드포인트

### 2.1. 사용자 관리

#### **사용자 등록**

- **엔드포인트:** `POST /users/register`
- **설명:** 새로운 사용자를 등록합니다.
- **요청 본문 (Request Body):**
  ```json
  {
    "username": "newuser",
    "email": "user@example.com",
    "password": "securepassword123"
  }
  ```
- **응답 (성공):**
  ```json
  {
    "id": 1,
    "username": "newuser",
    "email": "user@example.com",
    "created_at": "2025-12-02T10:00:00.000Z"
  }
  ```
- **응답 (오류):**
  ```json
  {
    "detail": "이미 등록된 사용자 이름입니다."
  }
  ```

#### **사용자 로그인 (토큰 발급)**

- **엔드포인트:** `POST /token`
- **설명:** 사용자를 인증하고 JWT 액세스 토큰을 반환합니다. 요청은 `application/x-www-form-urlencoded` 형식으로 전송되어야 합니다.
- **요청 본문 (form-data):**
  - `username`: `testuser`
  - `password`: `password`
- **응답 (성공):**
  ```json
  {
    "access_token": "your_jwt_token_here",
    "token_type": "bearer"
  }
  ```
- **참고:** 보호된 모든 엔드포인트에는 `Authorization` 헤더에 `access_token`을 포함해야 합니다: `Authorization: Bearer your_jwt_token_here`.

### 2.2. 실시간 스테이션 정보

#### **실시간 스테이션 상태 조회**

- **엔드포인트:** `GET /stations/realtime`
- **설명:** 따릉이 스테이션의 실시간 가용 정보를 조회합니다. `station_id`, `station_number`, 또는 `station_display_name`으로 필터링할 수 있습니다.
- **쿼리 파라미터:**
  - `station_id` (선택 사항, 문자열): 예: `ST-123`
  - `station_number` (선택 사항, 문자열): 예: `1501`
  - `station_display_name` (선택 사항, 문자열): 예: `건국대학교 정문 앞`
- **사용 예시:**
  - `/stations/realtime?station_display_name=건국대학교`
- **응답 (성공):** 스테이션 객체 배열
  ```json
  [
    {
      "station_id": "ST-509",
      "station_number": 1501,
      "station_display_name": "건국대학교 정문 앞",
      "timestamp": "2025-12-02T10:30:00Z",
      "latitude": 37.5407,
      "longitude": 127.079,
      "available_bikes": 15,
      "station_capacity": 20,
      "available_racks": 5,
      // ... 기타 날씨/대기질 데이터
    }
  ]
  ```

### 2.3. 이력 데이터

#### **스테이션 이력 데이터 조회**

- **엔드포인트:** `GET /stations/{station_id}/historical`
- **설명:** 특정 스테이션의 과거 따릉이 가용 데이터를 지정된 기간 동안 조회합니다.
- **경로 파라미터 (Path Parameter):**
  - `station_id`: 스테이션 ID (예: `ST-509`).
- **쿼리 파라미터:**
  - `period`: `yesterday`, `2days`, 또는 `week`.
- **사용 예시:** `/stations/ST-509/historical?period=week`
- **응답 (성공):** 데이터 포인트 배열
  ```json
  [
    {
      "timestamp": "2025-11-25T11:00:00Z",
      "avg_available_bikes": 12.5
    },
    {
      "timestamp": "2025-11-25T12:00:00Z",
      "avg_available_bikes": 14.0
    }
  ]
  ```

#### **시간별 비교 데이터 조회**

- **엔드포인트:** `GET /stations/{station_id}/hourly_comparison`
- **설명:** 특정 스테이션의 시간별 평균 따릉이 가용 데이터를 오늘, 어제, 이틀 전, 지난주와 비교합니다.
- **경로 파라미터 (Path Parameter):**
  - `station_id`: 스테이션 ID (예: `ST-509`).
- **응답 (성공):**
  ```json
  {
    "today": {
      "date": "2025-12-02",
      "hourly_data": [{ "hour": 10, "timestamp": "...", "avg_available_bikes": 18.0 }]
    },
    "yesterday": {
      "date": "2025-12-01",
      "hourly_data": [{ "hour": 10, "timestamp": "...", "avg_available_bikes": 15.5 }]
    },
    "two_days_ago": null, // 데이터가 없는 경우
    "last_week": {
      "date": "2025-11-25",
      "hourly_data": [{ "hour": 10, "timestamp": "...", "avg_available_bikes": 12.0 }]
    }
  }
  ```

### 2.4. 경로 최적화

#### **최적화된 경로 조회**

- **엔드포인트:** `POST /route/optimized`
- **설명:** 도보, 따릉이, 대중교통을 결합한 최적화된 경로를 추천합니다. "퍼스트 마일" (출발지에서 대중교통 승차 지점까지) 및 "라스트 마일" (대중교통 하차 지점에서 최종 목적지까지)에 대해 가장 가까운 이용 가능한 따릉이 대여소를 식별합니다.
- **요청 본문 (Request Body):**
  ```json
  {
    "start_lat": 37.5519,
    "start_lon": 126.9918,
    "end_lat": 37.5407,
    "end_lon": 127.0790
  }
  ```
- **응답 (성공):**
  ```json
  {
    "message": "대중교통 경로의 퍼스트 마일 및 라스트 마일 대여소를 성공적으로 찾았습니다.",
    "path": [ /* 카카오 API에서 제공하는 경로 섹션 배열 */ ],
    "first_mile": {
      "start_station": { "station_id": "ST-XXX", "station_display_name": "...", "distance_m": 250 },
      "end_station": { "station_id": "ST-YYY", "station_display_name": "...", "distance_m": 300 }
    },
    "last_mile": {
      "start_station": { "station_id": "ST-ZZZ", "station_display_name": "...", "distance_m": 150 },
      "end_station": { "station_id": "ST-AAA", "station_display_name": "...", "distance_m": 400 }
    }
  }
  ```

### 2.5. 라이더 추적 (실시간 위치)

이 기능은 주기적인 업데이트를 위한 표준 HTTP 엔드포인트와 실시간 추적을 위한 WebSocket을 모두 사용합니다.

#### **라이더 위치 업데이트 (HTTP)**

- **엔드포인트:** `POST /riders/{rider_id}/location`
- **설명:** 라이더의 기기에서 주기적으로 서버에 위치를 전송하는 데 사용됩니다.
- **경로 파라미터 (Path Parameter):**
  - `rider_id`: 라이더의 고유 식별자 (예: `user123`).
- **요청 본문 (Request Body):**
  ```json
  {
    "latitude": 37.541,
    "longitude": 127.079
  }
  ```

#### **라이더 위치 추적 (WebSocket)**

- **엔드포인트:** `ws://127.0.0.1:8000/ws/track/{rider_id}`
- **설명:** 라이더의 실시간 위치 업데이트를 수신하기 위한 WebSocket 연결을 설정합니다.
- **경로 파라미터 (Path Parameter):**
  - `rider_id`: 추적할 라이더의 ID.
- **이벤트 (서버에서):** 서버는 라이더의 위치가 업데이트될 때마다 JSON 메시지를 푸시합니다.
  ```json
  {
    "latitude": 37.541,
    "longitude": 127.079,
    "timestamp": "2025-12-02T12:00:00Z"
  }
  ```
- **클라이언트 측 예시 (JavaScript):**
  ```javascript
  const riderId = 'user123';
  const ws = new WebSocket(`ws://127.0.0.1:8000/ws/track/${riderId}`);

  ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('라이더 위치 업데이트:', data);
    // data.latitude 및 data.longitude로 지도 마커 업데이트
  };

  ws.onopen = function(event) {
    console.log('WebSocket 연결이 설정되었습니다.');
  };

  ws.onclose = function(event) {
    console.log('WebSocket 연결이 종료되었습니다.');
  };
  ```

### 2.6. 개인화된 패턴 (준비 중)

- **엔드포인트:** `GET /users/{user_id}/patterns`
- **설명:** 사용자의 개인화된 따릉이 이용 패턴을 조회합니다. **(현재 준비 중입니다).**
- **경로 파라미터 (Path Parameter):**
  - `user_id`: 사용자 ID.
- **응답:**
  ```json
  {
    "message": "개인화된 패턴 분석 기능은 개발 중입니다.",
    "favorite_station_id": "ST-509",
    "avg_duration_minutes": 15.5,
    "total_trips": 42
  }
  ```