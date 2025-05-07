FROM python:3.13-slim

WORKDIR /app

# shm 크기 관련 문제 해결을 위한 환경 변수 설정
# ENV PYTHONUNBUFFERED=1
# ENV DBUS_SESSION_BUS_ADDRESS=/dev/null
# ENV PYTHONTRACEMALLOC=1
# ENV PYTHONIOENCODING=UTF-8

# 필요한 시스템 패키지 설치
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y wget curl unzip

# 의존성 파일 복사
COPY requirements.txt .
# COPY uv.lock .

# uv를 통한 의존성 설치
RUN pip install -r requirements.txt

# Playwright 설치 및 브라우저 다운로드
RUN pip install playwright
RUN playwright install --with-deps chromium
RUN playwright install-deps

# 애플리케이션 코드 복사
COPY . .

# 포트 설정
EXPOSE 8000

# 애플리케이션 실행
CMD ["python", "main.py"]