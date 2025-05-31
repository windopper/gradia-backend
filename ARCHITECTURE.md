# Gradia Backend API 아키텍처

## 개요

Gradia Backend는 학습 관리 및 성적 예측 서비스를 제공하는 RESTful API 서버입니다. 마이크로서비스 아키텍처 패턴을 기반으로 하며, Google Cloud Platform(GCP)의 서비스들을 활용하여 확장 가능하고 안정적인 서비스를 제공합니다.

## 전체 시스템 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GitHub Repo   │───▶│  Cloud Build    │───▶│ Artifact Registry│
│   (master)      │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Secret Manager  │───▶│   Cloud Run     │◀───│  Docker Image   │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Firebase      │◀───│  FastAPI App    │───▶│ Google Gen AI   │
│   Firestore     │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## CI/CD 파이프라인

### 1. 소스 코드 관리
- **Repository**: GitHub
- **Branch Strategy**: master 브랜치 기반 배포
- **Trigger**: master 브랜치에 커밋 시 자동 빌드 트리거

### 2. 빌드 프로세스
- **Build Service**: Google Cloud Build
- **Build Trigger**: GitHub master 브랜치 커밋
- **Build Process**:
  1. 소스 코드 체크아웃
  2. Docker 이미지 빌드 (`Dockerfile` 기반)
  3. 의존성 설치 (`requirements.txt`)
  4. Playwright 브라우저 설치
  5. 이미지 태깅 및 푸시

### 3. 이미지 저장소
- **Registry**: Google Artifact Registry
- **Image Naming**: 프로젝트별 네이밍 컨벤션 적용
- **Versioning**: 커밋 해시 또는 태그 기반 버전 관리

### 4. 배포
- **Platform**: Google Cloud Run
- **Deployment Strategy**: 최신 이미지 자동 배포
- **Scaling**: 자동 스케일링 (0 to N instances)
- **Traffic**: 100% 트래픽을 최신 버전으로 라우팅

## 애플리케이션 아키텍처

### 기술 스택

#### 백엔드 프레임워크
- **FastAPI**: 고성능 비동기 웹 프레임워크
- **Python 3.13**: 최신 Python 런타임
- **Uvicorn**: ASGI 서버

#### 데이터베이스
- **Firebase Firestore**: NoSQL 문서 데이터베이스
- **실시간 동기화**: 클라이언트와 실시간 데이터 동기화 지원

#### 웹 스크래핑
- **Playwright**: 모던 브라우저 자동화 도구
- **Chromium**: 헤드리스 브라우저 엔진
- **BeautifulSoup4**: HTML 파싱 라이브러리

#### AI/ML 서비스
- **Google Generative AI**: LLM 서비스 (Gemini)
- **Langchain**: LLM 관리 및 체인 구성
- **Jinja2**: 프롬프트 템플릿 엔진

#### 보안 및 인증
- **Google Secret Manager**: 비밀 정보 관리
- **Firebase Authentication**: 사용자 인증
- **OAuth 2.0**: Google, Kakao 소셜 로그인

### 애플리케이션 구조

```
gradia-backend/
├── main.py                 # FastAPI 애플리케이션 진입점
├── dependencies.py         # 의존성 주입 설정
├── route/                  # API 라우터 모듈
│   ├── __init__.py        # 통합 라우터 설정
│   ├── auth/              # 인증 관련 라우터
│   ├── timetable.py       # 시간표 API
│   ├── subject.py         # 과목 관리 API
│   ├── study_session.py   # 학습 세션 API
│   └── grade_prediction.py # 성적 예측 API
├── db/                     # 데이터베이스 계층
│   ├── __init__.py        # Firebase 초기화
│   ├── user.py            # 사용자 데이터 액세스
│   ├── subject.py         # 과목 데이터 액세스
│   └── study_session.py   # 학습 세션 데이터 액세스
├── entity/                 # 데이터 모델 정의
│   ├── UserEntity.java
│   ├── SubjectEntity.java
│   └── StudySessionEntity.java
├── utils/                  # 유틸리티 모듈
│   ├── chromium_everytime.py      # 에브리타임 스크래핑
│   ├── sync_playwright_everytime.py # Playwright 스크래핑
│   └── learning_pattern_analyser.py # 학습 패턴 분석
├── templates/              # Jinja2 템플릿
├── secret/                 # 로컬 비밀 정보 (개발용)
├── Dockerfile             # 컨테이너 이미지 정의
└── requirements.txt       # Python 의존성
```

## 데이터 아키텍처

### Firebase Firestore 컬렉션 구조

```
firestore/
├── users/                  # 사용자 정보
│   └── {user_id}/
│       ├── profile         # 사용자 프로필
│       ├── subjects/       # 사용자별 과목
│       └── study_sessions/ # 학습 세션
├── subjects/               # 과목 정보
│   └── {subject_id}/
└── study_sessions/         # 학습 세션
    └── {session_id}/
```

### 데이터 모델

#### User Entity
```java
public class UserEntity {
    private String userId;
    private String email;
    private String name;
    private String googleId;
    private String picture;
    private Timestamp createdAt;
    private Timestamp updatedAt;
}
```

#### Subject Entity
```java
public class SubjectEntity {
    private String subjectId;
    private String userId;
    private String name;
    private int type;           // 0: 전공필수, 1: 전공선택, 2: 교양
    private int credit;
    private int difficulty;
    private Timestamp midTermSchedule;
    private Timestamp finalTermSchedule;
    private EvaluationRatio evaluationRatio;
    private TargetStudyTime targetStudyTime;
    private String color;
}
```

#### Study Session Entity
```java
public class StudySessionEntity {
    private String sessionId;
    private String userId;
    private String subjectId;
    private LocalDate date;
    private int studyTime;      // 분 단위
    private Timestamp startTime;
    private Timestamp endTime;
    private int restTime;       // 분 단위
    private int focusLevel;     // 1-5 집중도
    private String memo;
}
```

## API 아키텍처

### 레이어드 아키텍처

```
┌─────────────────────────────────────────┐
│           Presentation Layer            │
│         (FastAPI Routes)                │
├─────────────────────────────────────────┤
│            Business Layer               │
│        (Service Logic)                  │
├─────────────────────────────────────────┤
│           Data Access Layer             │
│         (Firebase Firestore)           │
├─────────────────────────────────────────┤
│           External Services             │
│  (Google AI, Playwright, OAuth)        │
└─────────────────────────────────────────┘
```

### API 엔드포인트 구조

#### 인증 API (`/auth`)
- `POST /auth/google` - Google OAuth 로그인
- `POST /auth/kakao` - Kakao OAuth 로그인
- `GET /auth/users/me` - 현재 사용자 정보

#### 시간표 API (`/timetable`)
- `GET /timetable` - 에브리타임 URL에서 시간표 파싱

#### 과목 관리 API (`/subjects`)
- `GET /subjects/` - 과목 목록 조회
- `POST /subjects/` - 새 과목 생성
- `GET /subjects/{subject_id}` - 특정 과목 조회
- `PATCH /subjects/{subject_id}` - 과목 정보 수정
- `DELETE /subjects/{subject_id}` - 과목 삭제

#### 학습 세션 API (`/study-sessions`)
- `GET /study-sessions/` - 학습 세션 목록 조회
- `POST /study-sessions/` - 새 학습 세션 생성
- `GET /study-sessions/{session_id}` - 특정 세션 조회
- `PATCH /study-sessions/{session_id}` - 세션 정보 수정
- `DELETE /study-sessions/{session_id}` - 세션 삭제

#### 성적 예측 API (`/grade-prediction`)
- `POST /grade-prediction/` - 기본 성적 예측
- `POST /grade-prediction/v2` - 향상된 성적 예측 (학습 패턴 분석)

## 보안 아키텍처

### 인증 및 권한 관리

#### OAuth 2.0 플로우
```
Client App ──────▶ Google/Kakao OAuth
     │                    │
     ▼                    ▼
Gradia Backend ◀─── ID Token/Access Token
     │
     ▼
Firebase Auth ──────▶ Gradia Access Token
     │                    │
     ▼                    ▼
Protected APIs ◀─── Bearer Token
```

#### 비밀 정보 관리
- **Google Secret Manager**: 프로덕션 환경 비밀 정보
- **환경 변수**: 런타임 설정 주입
- **Firebase Service Account**: 서비스 간 인증

### 데이터 보안
- **HTTPS**: 모든 통신 암호화
- **CORS**: 허용된 도메인만 접근 가능
- **Input Validation**: 모든 입력 데이터 검증
- **Rate Limiting**: API 호출 제한 (Cloud Run 레벨)

## 성능 및 확장성

### 스케일링 전략

#### 수평 확장
- **Cloud Run**: 자동 스케일링 (0 to N instances)
- **Stateless Design**: 세션 상태 없는 설계
- **Database Scaling**: Firestore 자동 확장

#### 성능 최적화
- **비동기 처리**: FastAPI + asyncio
- **Connection Pooling**: Firebase 연결 풀링
- **Caching**: 메모리 기반 캐싱 (필요시)

### 모니터링 및 로깅

#### 시스템 모니터링
- **Cloud Run Metrics**: CPU, 메모리, 요청 수
- **Custom Metrics**: `/system/memory` 엔드포인트
- **Error Tracking**: 애플리케이션 오류 추적

#### 로깅
- **Structured Logging**: JSON 형태 로그
- **Cloud Logging**: GCP 통합 로깅
- **Request Tracing**: 요청별 추적 가능

## 외부 서비스 통합

### Google Generative AI
- **모델**: Gemini Flash 2.5
- **용도**: 성적 예측, 학습 조언 생성
- **Langchain**: LLM 체인 관리
- **Prompt Templates**: Jinja2 템플릿 엔진

### Playwright 웹 스크래핑
- **브라우저**: Chromium
- **용도**: 에브리타임 시간표 파싱
- **동적 콘텐츠**: JavaScript 렌더링 지원
- **안정성**: 재시도 로직 및 오류 처리

### Firebase 서비스
- **Firestore**: 메인 데이터베이스
- **Authentication**: 사용자 인증
- **Security Rules**: 데이터 접근 제어

## 배포 환경

### 컨테이너 설정
```dockerfile
FROM python:3.13-slim
WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y wget curl unzip

# Python 의존성 설치
COPY requirements.txt .
RUN pip install -r requirements.txt

# Playwright 설치
RUN pip install playwright
RUN playwright install --with-deps chromium
RUN playwright install-deps

# 애플리케이션 코드 복사
COPY . .

EXPOSE 8000
CMD ["python", "main.py"]
```

### Cloud Run 설정
- **CPU**: 1-2 vCPU
- **Memory**: 2-4 GB
- **Concurrency**: 80-100 requests per instance
- **Timeout**: 300 seconds (Playwright 작업 고려)
- **Min Instances**: 0 (비용 최적화)
- **Max Instances**: 100 (트래픽 대응)

## 개발 및 테스트

### 로컬 개발 환경
```bash
# 의존성 설치
uv sync

# Playwright 브라우저 설치
python -m playwright install

# 개발 서버 실행
python main.py
# 또는
uvicorn main:app --reload
```

### 부하 테스트
- **도구**: Locust
- **테스트 대상**: 모든 API 엔드포인트
- **시나리오**: CRUD 작업, 동시 사용자 시뮬레이션
- **메트릭**: 응답 시간, 처리량, 오류율