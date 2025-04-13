"""
에브리타임 시간표 파싱 모듈 (동기식 Playwright 버전)

에브리타임 웹사이트에서 시간표 정보를 가져와 구조화된 데이터로 변환합니다.
동기식 Playwright API를 사용하여 Windows 환경 호환성 문제를 해결합니다.
"""

import os
import json
import time
from typing import Dict, List, Tuple, Optional
import threading
from concurrent.futures import ThreadPoolExecutor
import atexit
from bs4 import BeautifulSoup
from fastapi import HTTPException

# 동기식 Playwright 임포트
from playwright.sync_api import sync_playwright, Error

# 베이스 클래스 임포트
from utils.everytime_base import EverytimeTimetableParserBase

# 전역 스레드 풀 설정
_thread_executor = ThreadPoolExecutor(max_workers=10)

class SyncPlaywrightTimetableParser(EverytimeTimetableParserBase):
    def __init__(self, url: str = None, timeout: int = 30):
        super().__init__(url, timeout)
        self._lock = threading.Lock()
        
    @classmethod
    def parse_timetable_async(cls, url: str, timeout: int = 30):
        """비동기적으로 시간표 파싱 작업을 제출하고 결과를 반환하는 함수
        ThreadPool을 사용하여 논블로킹 방식으로 실행
        """
        parser = cls(url, timeout)
        return _thread_executor.submit(parser.parse_timetable, url)
    
    def parse_timetable(self, url: Optional[str] = None, max_retries: int = 2) -> List[Dict]:
        """에브리타임 URL에서 시간표를 동기적으로 파싱하여 구조화된 데이터로 반환"""
        target_url = url or self.url
        if not target_url:
            raise ValueError("URL이 제공되지 않았습니다.")
        
        # URL 유효성 확인
        self._validate_url(target_url)

        retries = 0
        last_error = None
        
        # 최대 재시도 횟수만큼 반복
        while retries <= max_retries:
            try:
                with sync_playwright() as playwright:
                    # 브라우저 실행
                    browser = playwright.chromium.launch(
                        headless=True,
                        args=[
                            '--no-sandbox',
                            '--disable-dev-shm-usage',
                            '--disable-gpu',
                            '--disable-extensions',
                        ]
                    )
                    
                    # 컨텍스트 및 페이지 생성
                    context = browser.new_context(
                        viewport={'width': 1920, 'height': 1080},
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
                    )
                    
                    # 페이지 생성 및 설정
                    page = context.new_page()
                    page.set_default_timeout(self.timeout * 1000)  # 밀리초 단위
                    
                    # 페이지 로딩
                    page.goto(target_url, wait_until='networkidle')
                    
                    # HTML 가져오기
                    html = page.content()
                    
                    # 자원 정리
                    page.close()
                    context.close()
                    browser.close()
                    
                    # HTML 파싱
                    return self._parse_html(html)
                    
            except Exception as e:
                print(f"파싱 오류: {type(e).__name__}: {str(e)}")
                last_error = e
                
                retries += 1
                if retries <= max_retries:
                    print(f"재시도 중... {retries}/{max_retries}")
                    time.sleep(1)  # 잠시 대기 후 재시도
                    continue
            
        # 최대 재시도 후에도 실패한 경우 적절한 예외 발생
        if isinstance(last_error, Error) and "timeout" in str(last_error).lower():
            raise HTTPException(status_code=504, detail="에브리타임 서버 응답 시간 초과. 나중에 다시 시도해주세요.")
        elif isinstance(last_error, Error):
            raise HTTPException(status_code=503, detail=f"브라우저 오류: {str(last_error)}")
        elif isinstance(last_error, ValueError):
            raise HTTPException(status_code=400, detail=str(last_error))
        else:
            raise HTTPException(status_code=500, detail=f"시간표 파싱 중 오류 발생: {str(last_error)}")
    
    def _parse_html(self, html: str) -> List[Dict]:
        """HTML 문서를 파싱하여 시간표 데이터 추출"""
        # BeautifulSoup으로 HTML 파싱
        soup = BeautifulSoup(html, 'html.parser')
        
        # 시간표 요소 선택
        days = soup.select('.wrap .tablebody .tablebody td')
        
        # 시간표 요소가 없는 경우 확인
        if not days or len(days) == 0:
            raise ValueError("시간표 데이터를 찾을 수 없습니다. URL이 올바른지 확인하세요.")
        
        # 시간표 데이터 추출
        timetable_data = []
        day_index = 0
        
        for day in days:
            subjects = day.select('.subject')
            if len(subjects) == 0:
                continue
                
            for subject in subjects:
                if day_index < len(self.day_enum):
                    start_hour, start_minute, end_hour, end_minute = self._extract_time_of_subject(subject)
                    name = self._extract_name_of_subject(subject)
                    place = self._extract_place_of_subject(subject)
                    professor = self._extract_professor_of_subject(subject)
                    
                    subject_data = {
                        "day": self.day_enum[day_index],
                        "name": name,
                        "start_time": f"{start_hour:02}:{start_minute:02}",
                        "end_time": f"{end_hour:02}:{end_minute:02}",
                        "place": place,
                        "professor": professor
                    }
                    timetable_data.append(subject_data)
            
            day_index += 1
            
        if not timetable_data:
            raise ValueError("시간표에서 과목 정보를 추출할 수 없습니다.")
        
        return timetable_data

# 프로그램 종료 시 정리 함수
def cleanup_resources():
    """사용한 자원 정리"""
    try:
        if _thread_executor:
            _thread_executor.shutdown(wait=False)
            print("ThreadExecutor 종료 완료")
    except Exception as e:
        print(f"ThreadExecutor 종료 중 오류: {str(e)}")

# 종료 시 리소스 정리 함수 등록
atexit.register(cleanup_resources)

# 모듈로 실행될 때의 테스트 코드
if __name__ == "__main__":
    url = input("에브리타임 시간표 URL을 입력하세요: ")
    parser = SyncPlaywrightTimetableParser(url)
    result = parser.parse_timetable()
    
    # 결과 출력
    print(json.dumps(result, indent=2, ensure_ascii=False))