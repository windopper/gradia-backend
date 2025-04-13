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
- ReDoc: `http://localhost:8000/redoc`

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

## 파서 선택 (내부 구현)

프로젝트는 두 가지 웹 파싱 방식을 지원합니다:

1. Selenium/ChromeDriver 기반 파서 (기존)
2. Playwright 기반 파서 (신규 추가)

각 파서는 다음과 같은 특징이 있습니다:

- **Selenium 파서**: 안정적이지만 ChromeDriver 설치 필요
- **Playwright 파서**: 브라우저 자동 설치 및 관리 지원, 더 빠른 성능

## 주의사항

- 에브리타임 웹사이트 구조가 변경되면 파싱 로직이 작동하지 않을 수 있습니다.
- ChromeDriver는 사용하는 Chrome 브라우저 버전과 일치해야 합니다.
- Docker 환경에서는 Playwright를 사용하여 브라우저 의존성 문제를 해결합니다.

## 부하 테스트

프로젝트에는 Locust를 사용한 부하 테스트 스크립트가 포함되어 있습니다. 이를 통해 시간표 API의 성능을 테스트할 수 있습니다.

### 사용 방법

1. `locustfile.py` 파일의 `EVERYTIME_SAMPLE_URLS` 리스트에 테스트에 사용할 에브리타임 URL 샘플들을 추가합니다.
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
- 1~3초 간격으로 무작위 요청 생성
- 응답 상태 코드 및 JSON 포맷 검증
- 테스트 결과 시각화 및 통계 제공