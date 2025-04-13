from locust import HttpUser, task, between
import urllib.parse
import random
import logging

# 테스트에 사용할 에브리타임 URL 샘플들
# 이 URL을 실제 테스트할 에브리타임 URL로 변경하세요
EVERYTIME_SAMPLE_URLS = [
    'https://everytime.kr/@Gpm4hmWAGNlbWwIKAaGa'
]

class TimeTableApiUser(HttpUser):
    """에브리타임 시간표 API에 부하 테스트를 수행하는 가상 사용자 클래스"""
    
    # 요청 사이의 대기 시간 (1초~3초 사이)
    wait_time = between(1, 3)
    
    def on_start(self):
        """사용자 세션 시작 시 호출되는 메서드"""
        logging.info("New user started")
    
    @task(1)
    def test_timetable_endpoint(self):
        """
        /timetable 엔드포인트 테스트
        샘플 URL 중 하나를 무작위로 선택하여 요청
        """
        # 샘플 URL 중 하나를 무작위로 선택
        url = random.choice(EVERYTIME_SAMPLE_URLS)
        
        # URL 인코딩
        encoded_url = urllib.parse.quote(url, safe='')
        
        # 요청 보내기
        with self.client.get(
            f"/timetable?url={encoded_url}", 
            name="/timetable",
            catch_response=True
        ) as response:
            # 응답 검증
            if response.status_code != 200:
                response.failure(f"Failed with status code: {response.status_code}, Response: {response.text}")
            else:
                try:
                    # JSON 응답 확인
                    json_data = response.json()
                    if "timetable" not in json_data or "message" not in json_data:
                        response.failure("잘못된 응답 형식입니다.")
                except Exception as e:
                    response.failure(f"JSON 파싱 오류: {str(e)}")

# 사용법:
# 1. 터미널에서 FastAPI 서버 실행: uvicorn main:app --host 0.0.0.0 --port 8000
# 2. 다른 터미널에서 Locust 실행: locust -f locustfile.py --host=http://localhost:8000
# 3. 웹 브라우저에서 http://localhost:8089 접속하여 테스트 구성 및 시작