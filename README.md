# Gradia Backend

Gradia 백엔드

## 기능

- 에브리타임 URL에서 시간표 정보 파싱 (Selenium 및 Playwright 지원)
- RESTful API로 시간표 데이터 제공
- Docker 지원으로 간편한 배포 환경 구성

## 기술 스택

- Python 3.12+
- FastAPI
- Selenium
- Playwright
- BeautifulSoup4
- Docker

## 설치 방법

### 요구 사항

- Python 3.12 이상
- Chrome 웹 브라우저
- ChromeDriver (Chrome 버전과 일치하는 버전 필요) 또는 Playwright

### 패키지 설치

```bash
# 의존성 패키지 설치
uv sync
```

### Playwright 설치 (선택사항)

```bash
# Playwright 브라우저 설치
python -m playwright install
```

## 실행 방법

### 로컬 실행

```bash
# 개발 서버 실행
python main.py
```

또는

```bash
uvicorn main:app --reload
```

서버는 기본적으로 `http://localhost:8000`에서 실행됩니다.

### Docker 실행

```bash
# Docker 이미지 빌드
docker build -t gradia-backend .

# Docker 컨테이너 실행
docker run -p 8000:8000 gradia-backend
```

## API 문서

FastAPI는 자동으로 API 문서를 생성합니다:

- Swagger UI: `http://localhost:8000/docs`

## API 엔드포인트

### 시간표 가져오기

```
GET /timetable?url={에브리타임_URL}
```

#### 응답 예시

```json
{
  "timetable": [
    {
      "day": "Monday",
      "name": "데이터베이스",
      "start_time": "09:00",
      "end_time": "10:30",
      "place": "공학관 204",
      "professor": "김교수"
    },
    // ... 다른 시간표 항목들
  ],
  "message": "시간표 파싱 성공"
}
```

### 인증 (Authentication)

#### Google 계정으로 로그인

```
POST /auth/google
```

- Google ID 토큰을 사용하여 사용자를 인증하고, Gradia 서비스의 액세스 토큰을 발급합니다.
- **요청 본문**:
  ```json
  {
    "id_token_str": "YOUR_GOOGLE_ID_TOKEN"
  }
  ```
- **성공 응답 예시**:
  ```json
  {
    "access_token": "string (Gradia Access Token)",
    "token_type": "bearer",
    "user_id": "string",
    "email": "user@example.com",
    "name": "User Name"
  }
  ```

#### 현재 사용자 정보 조회

```
GET /auth/users/me
```

- 현재 Gradia 서비스에 로그인된 사용자의 정보를 반환합니다.
- `Authorization` 헤더에 `Bearer <Gradia_Access_Token>` 형태로 토큰이 필요합니다.
- **성공 응답 예시**:
  ```json
  {
    "user_id": "string",
    "email": "user@example.com",
    "name": "User Name",
    "google_id": "string (Google User ID)",
    "created_at": "YYYY-MM-DDTHH:MM:SS.ffffffZ",
    "updated_at": "YYYY-MM-DDTHH:MM:SS.ffffffZ",
    "picture": "URL_to_profile_picture_or_null"
  }
  ```

### 학습 세션 (Study Sessions)

모든 학습 세션 관련 API는 `Authorization` 헤더에 `Bearer <access_token>` 형태의 토큰이 필요합니다.

#### 학습 세션 목록 조회

```
GET /study-sessions/
```

- 현재 인증된 사용자의 모든 학습 세션을 조회합니다.
- 선택적으로 `subject_id` 쿼리 파라미터를 사용하여 특정 과목의 학습 세션만 필터링할 수 있습니다.

#### 특정 학습 세션 조회

```
GET /study-sessions/{session_id}
```

- `{session_id}`에 해당하는 특정 학습 세션의 상세 정보를 조회합니다.

#### 새 학습 세션 생성

```
POST /study-sessions/
```

- 새로운 학습 세션을 생성합니다.
- 요청 바디 예시:
  ```json
  {
    "subject_id": "string",
    "date": "YYYY-MM-DD",
    "study_time": 0, // 분 단위
    "start_time": "YYYY-MM-DDTHH:MM:SSZ",
    "end_time": "YYYY-MM-DDTHH:MM:SSZ",
    "rest_time": 0 // 분 단위 (선택 사항)
  }
  ```

#### 학습 세션 업데이트

```
PATCH /study-sessions/{session_id}
```

- `{session_id}`에 해당하는 기존 학습 세션의 정보를 업데이트합니다.
- 업데이트할 필드만 요청 바디에 포함합니다.

#### 학습 세션 삭제

```
DELETE /study-sessions/{session_id}
```

- `{session_id}`에 해당하는 학습 세션을 삭제합니다.

### 과목 (Subjects)

모든 과목 관련 API는 `Authorization` 헤더에 `Bearer <access_token>` 형태의 토큰이 필요합니다.

#### 과목 목록 조회

```
GET /subjects/
```

- 현재 인증된 사용자의 모든 과목을 조회합니다.

#### 특정 과목 조회

```
GET /subjects/{subject_id}
```

- `{subject_id}`에 해당하는 특정 과목의 상세 정보를 조회합니다.

#### 새 과목 생성

```
POST /subjects/
```

- 새로운 과목을 생성합니다.
- 요청 바디 예시:
  ```json
  {
    "name": "string",
    "type": 0, // 0: 전공필수, 1: 전공선택, 2: 교양
    "credit": 0,
    "difficulty": 0, // 선택 사항
    "mid_term_schedule": "YYYY-MM-DDTHH:MM", // 선택 사항
    "final_term_schedule": "YYYY-MM-DDTHH:MM", // 선택 사항
    "evaluation_ratio": { // 선택 사항
      "mid_term_ratio": 0,
      "final_term_ratio": 0,
      "quiz_ratio": 0,
      "assignment_ratio": 0,
      "attendance_ratio": 0
    },
    "target_study_time": { // 선택 사항
      "daily_target_study_time": 0, // 분 단위
      "weekly_target_study_time": 0, // 분 단위
      "monthly_target_study_time": 0 // 분 단위
    },
    "color": "#FFFFFF" // 선택 사항, HEX 코드
  }
  ```

#### 과목 정보 업데이트

```
PATCH /subjects/{subject_id}
```

- `{subject_id}`에 해당하는 기존 과목의 정보를 업데이트합니다.
- 업데이트할 필드만 요청 바디에 포함합니다.

#### 과목 삭제

```
DELETE /subjects/{subject_id}
```

- `{subject_id}`에 해당하는 과목을 삭제합니다.

### 성적 예측

```
POST /grade-prediction/
```

- 입력한 과목명, 이해 수준, 학습 시간, 과제/퀴즈 평균 점수를 바탕으로 예상 점수, 등급, 예측 근거, 구체적 조언을 반환합니다.
- **요청 바디 예시**:
  ```json
  {
    "subject_name": "데이터베이스",
    "understanding_level": 3,
    "study_time_hours": 4,
    "assignment_quiz_avg_score": 80 // 이 필드는 optional 입니다
  }
  ```
- **성공 응답 예시**:
  ```json
  {
    "raw_prediction": "```xml\n<prediction>\n    <score>84</score>\n    <grade>B+</grade>\n    <factors>\n        <factor>과제/퀴즈 평균 점수 80.0점은 꾸준한 학습 참여와 기본적인 내용 이해를 보여주는 긍정적인 지표입니다.</factor>\n        <factor>자기 평가 이해 수준 3/5은 일부 개념에 대한 추가적인 학습이나 명확화가 필요할 수 있음을 시사합니다.</factor>\n        <factor>주간 학습 시간 4.0시간은 안정적인 학습량을 나타내지만, 깊이 있는 이해나 어려운 내용 정복을 위해 조절할 필요가 있을 수 있습니다.</factor>\n    </factors>\n    <advice>\n        <point>자기 평가에서 이해도가 낮다고 느낀 부분이나 과제/퀴즈에서 어려움을 겪었던 개념들을 집중적으로 복습하고, 필요시 교수님이나 조교에게 질문하여 명확히 이해하세요.</point>\n        <point>이미 받은 과제/퀴즈의 오답을 분석하여 자신의 약점을 파악하고, 관련된 내용을 보충 학습하는 것이 시험 대비에 큰 도움이 될 것입니다.</point>\n    </advice>\n</prediction>\n```",
    "structured_prediction": {
      "score": "84",
      "grade": "B+",
      "factors": [
        "과제/퀴즈 평균 점수 80.0점은 꾸준한 학습 참여와 기본적인 내용 이해를 보여주는 긍정적인 지표입니다.",
        "자기 평가 이해 수준 3/5은 일부 개념에 대한 추가적인 학습이나 명확화가 필요할 수 있음을 시사합니다.",
        "주간 학습 시간 4.0시간은 안정적인 학습량을 나타내지만, 깊이 있는 이해나 어려운 내용 정복을 위해 조절할 필요가 있을 수 있습니다."
      ],
      "advice": [
        "자기 평가에서 이해도가 낮다고 느낀 부분이나 과제/퀴즈에서 어려움을 겪었던 개념들을 집중적으로 복습하고, 필요시 교수님이나 조교에게 질문하여 명확히 이해하세요.",
        "이미 받은 과제/퀴즈의 오답을 분석하여 자신의 약점을 파악하고, 관련된 내용을 보충 학습하는 것이 시험 대비에 큰 도움이 될 것입니다."
      ]
    }
  }
  ```

## 부하 테스트

프로젝트에는 Locust를 사용한 부하 테스트 스크립트가 포함되어 있습니다. 이를 통해 시간표 API, 과목(Subject) API, 학습 세션(Study Session) API의 성능을 테스트할 수 있습니다.

### 사용 방법

1. `locustfile.py` 파일의 `EVERYTIME_SAMPLE_URLS` 리스트에 시간표 API 테스트에 사용할 에브리타임 URL 샘플들을 추가합니다. (과목 및 학습 세션 API 테스트는 내부적으로 임시 사용자를 생성하므로 별도 설정이 필요 없습니다.)
2. 먼저 FastAPI 서버를 실행합니다:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```
3. 다른 터미널에서 Locust를 실행합니다:
   ```bash
   locust -f locustfile.py --host=http://localhost:8000
   ```
4. 웹 브라우저에서 http://localhost:8089 에 접속하여 테스트를 구성하고 시작합니다.

### 테스트 기능

- `/timetable` 엔드포인트에 대한 부하 테스트
- 과목(Subject) 및 학습 세션(Study Session) API에 대한 CRUD 부하 테스트:
    - 테스트 시작 시 임시 사용자 계정을 동적으로 생성하고, 해당 사용자의 인증 토큰을 사용하여 API를 호출합니다.
    - **과목(Subject) API 테스트 대상**:
        - 과목 생성 (`POST /subjects/`)
        - 전체 과목 목록 조회 (`GET /subjects/`)
        - 특정 과목 상세 조회 (`GET /subjects/{subject_id}`)
        - 과목 정보 수정 (`PATCH /subjects/{subject_id}`)
        - 과목 삭제 (`DELETE /subjects/{subject_id}`)
    - **학습 세션(Study Session) API 테스트 대상**:
        - 학습 세션 생성 (`POST /study-sessions/`)
        - 전체 학습 세션 목록 또는 특정 과목의 세션 목록 조회 (`GET /study-sessions/`, `GET /study-sessions/?subject_id={subject_id}`)
        - 특정 학습 세션 상세 조회 (`GET /study-sessions/{session_id}`)
        - 학습 세션 정보 수정 (`PATCH /study-sessions/{session_id}`)
        - 학습 세션 삭제 (`DELETE /study-sessions/{session_id}`)
    - 테스트 종료 시 생성되었던 모든 과목, 학습 세션 및 임시 사용자 계정을 자동으로 삭제하여 환경을 정리합니다.
- 1~3초 간격으로 무작위 요청 생성
- 응답 상태 코드 및 JSON 포맷 검증
- 테스트 결과 시각화 및 통계 제공
