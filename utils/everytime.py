"""
에브리타임 시간표 파싱 모듈

에브리타임 웹사이트에서 시간표 정보를 가져와 구조화된 데이터로 변환합니다.
"""

from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from typing import Dict, List, Tuple, Optional
import json
from fastapi import HTTPException
from selenium.common.exceptions import WebDriverException, TimeoutException
import requests
import atexit
import threading
import queue
from concurrent.futures import ThreadPoolExecutor

# 드라이버 풀 클래스 구현
class WebDriverPool:
    def __init__(self, max_drivers=10, driver_options=None, timeout=10):
        self.max_drivers = max_drivers
        self.driver_options = driver_options
        self.timeout = timeout
        self.available_drivers = queue.Queue()
        self.active_drivers = 0
        self.lock = threading.Lock()
        self._shutdown = False
        
        # 프로그램 종료 시 모든 드라이버 정리
        atexit.register(self.shutdown)
        
    def get_driver(self):
        """풀에서 드라이버를 가져옴, 필요시 새로 생성"""
        with self.lock:
            # 풀이 이미 종료되었는지 확인
            if self._shutdown:
                raise RuntimeError("드라이버 풀이 이미 종료되었습니다.")
            
            try:
                # 사용 가능한 드라이버가 있는지 확인
                driver = self.available_drivers.get_nowait()
                
                # 드라이버 상태 확인
                try:
                    driver.title  # 간단한 명령으로 드라이버 상태 확인
                    return driver
                except Exception:
                    # 문제가 있는 드라이버는 종료하고 새로 생성
                    self._close_driver(driver)
                    # 이 경우 아래 코드로 이동하여 새 드라이버 생성
            except queue.Empty:
                # 사용 가능한 드라이버가 없음
                pass
            
            # 새 드라이버 생성 가능 여부 확인
            if self.active_drivers < self.max_drivers:
                driver = self._create_driver()
                self.active_drivers += 1
                return driver
            
            # 최대 드라이버 수에 도달한 경우 대기
            raise HTTPException(status_code=503, detail="사용 가능한 드라이버가 없습니다. 잠시 후 다시 시도해주세요.")
    
    def release_driver(self, driver):
        """사용 완료된 드라이버를 풀에 반환"""
        if self._shutdown:
            self._close_driver(driver)
            return
            
        with self.lock:
            try:
                # 드라이버 상태 확인
                driver.title
                # 정상 드라이버는 풀에 반환
                self.available_drivers.put(driver)
            except Exception:
                # 문제가 있는 드라이버는 종료하고 카운트 감소
                self._close_driver(driver)
                self.active_drivers -= 1
    
    def _create_driver(self):
        """새 웹드라이버 인스턴스 생성"""
        driver = webdriver.Chrome(options=self.driver_options)
        driver.set_page_load_timeout(self.timeout)
        return driver
    
    def _close_driver(self, driver):
        """드라이버 안전하게 종료"""
        try:
            driver.quit()
        except:
            pass
    
    def shutdown(self):
        """모든 드라이버 종료 및 풀 정리"""
        self._shutdown = True
        
        # 모든 대기 중인 드라이버 종료
        while not self.available_drivers.empty():
            driver = self.available_drivers.get()
            self._close_driver(driver)
        
        self.active_drivers = 0

# 전역 드라이버 풀 인스턴스
DRIVER_POOL = None
THREAD_POOL = ThreadPoolExecutor(max_workers=10)

class TimetableParser:
    # 멀티스레딩 환경에서 스레드별 상태 저장
    _thread_local = threading.local()
    
    def __init__(self, url: str = None, headless: bool = True, timeout: int = 10):
        self.url = url
        self.day_enum = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        self.timeout = timeout
        self.headless = headless
        
        # Selenium 옵션 설정
        self.options = Options()
        if headless:
            self.options.add_argument('--headless')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3')
        self.options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        # 전역 드라이버 풀 초기화
        global DRIVER_POOL
        if DRIVER_POOL is None:
            DRIVER_POOL = WebDriverPool(max_drivers=10, driver_options=self.options, timeout=self.timeout)
    
    @classmethod
    def parse_timetable_async(cls, url: str, headless: bool = True, timeout: int = 10):
        """
        비동기적으로 시간표 파싱 작업을 제출하고 결과를 반환하는 함수
        
        Args:
            url: 에브리타임 시간표 URL
            headless: 헤드리스 모드 여부
            timeout: 페이지 로딩 타임아웃
            
        Returns:
            Future 객체 (결과를 얻으려면 result() 메서드 호출)
        """
        parser = cls(url, headless, timeout)
        return THREAD_POOL.submit(parser.parse_timetable, url)
        
    def parse_timetable(self, url: Optional[str] = None, max_retries: int = 2) -> List[Dict]:
        """
        에브리타임 URL에서 시간표를 파싱하여 구조화된 데이터로 반환
        
        Args:
            url: 에브리타임 시간표 URL (옵션)
            max_retries: 드라이버 문제 발생 시 최대 재시도 횟수
            
        Returns:
            List[Dict]: 파싱된 시간표 데이터 리스트
        """
        driver = None
        retries = 0
        last_exception = None
        
        while retries <= max_retries:
            try:
                target_url = url or self.url
                if not target_url:
                    raise ValueError("URL이 제공되지 않았습니다.")
                
                # URL 유효성 확인
                self._validate_url(target_url)
                    
                # 드라이버 풀에서 드라이버 획득
                driver = DRIVER_POOL.get_driver()
                
                # 페이지 로딩
                driver.get(target_url)
                time.sleep(2)  # 페이지 로딩 대기
                
                # HTML 파싱
                html = driver.page_source
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
                
                # 작업 완료 후 드라이버 반환
                if driver:
                    DRIVER_POOL.release_driver(driver)
                    driver = None
                    
                return timetable_data
                
            except (TimeoutException, WebDriverException) as e:
                # 드라이버 관련 오류 발생 시
                last_exception = e
                
                # 문제가 있는 드라이버 반환
                if driver:
                    DRIVER_POOL.release_driver(driver)
                    driver = None
                
                retries += 1
                # 마지막 시도가 아니면 잠시 대기 후 재시도
                if retries <= max_retries:
                    time.sleep(1)  # 재시도 전 대기
                    continue
                
                # 최대 재시도 횟수 초과 시 적절한 예외 발생
                if isinstance(e, TimeoutException):
                    raise HTTPException(status_code=504, detail="에브리타임 서버 응답 시간 초과. 나중에 다시 시도해주세요.")
                else:
                    raise HTTPException(status_code=503, detail=f"브라우저 드라이버 오류: {str(e)}")
            except requests.exceptions.RequestException as e:
                raise HTTPException(status_code=503, detail="에브리타임 서버에 접속할 수 없습니다. 인터넷 연결을 확인하세요.")
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                # 예상치 못한 오류 시 드라이버 반환
                last_exception = e
                if driver:
                    DRIVER_POOL.release_driver(driver)
                    driver = None
                    
                retries += 1
                # 마지막 시도가 아니면 재시도
                if retries <= max_retries and isinstance(e, (AttributeError, TypeError)):
                    time.sleep(1)
                    continue
                raise HTTPException(status_code=500, detail=f"시간표 파싱 중 오류 발생: {str(e)}")
            finally:
                # 예외 발생 여부와 관계없이 드라이버 반환 보장
                if driver:
                    DRIVER_POOL.release_driver(driver)
    
    def _validate_url(self, url: str) -> None:
        """URL이 유효한지 확인"""
        if not url.startswith(('http://', 'https://')):
            raise ValueError("유효하지 않은 URL 형식입니다.")
            
        # 에브리타임 URL인지 확인
        if not 'everytime.kr' in url:
            raise ValueError("에브리타임 URL이 아닙니다.")
    
    def _extract_time_of_subject(self, subject: Tag) -> Tuple[int, int, int, int]:
        """과목의 시작 및 종료 시간을 추출"""
        try:
            style = subject['style']
            height = int(style.split(';')[0].split(':')[1].replace('px', ''))
            top = int(style.split(';')[1].split(':')[1].replace('px', ''))
            # 0px부터 오전 0시부터 시작
            # 50px당 1시간
            start_hour = top // 50
            start_minute = (top % 50) * 60 // 50
            end_hour = (top + height - 1) // 50
            end_minute = ((top + height - 1) % 50) * 60 // 50
            
            return (start_hour, start_minute, end_hour, end_minute)
        except (KeyError, IndexError, ValueError) as e:
            raise ValueError(f"시간 정보 추출 실패: {str(e)}")
    
    def _extract_name_of_subject(self, subject: Tag) -> str:
        """과목명 추출"""
        name_element = subject.select_one('h3')
        return name_element.text.strip() if name_element else "알 수 없음"
    
    def _extract_place_of_subject(self, subject: Tag) -> str:
        """강의실 위치 추출"""
        place_element = subject.select_one('p span')
        return place_element.text.strip() if place_element else "장소 미정"
    
    def _extract_professor_of_subject(self, subject: Tag) -> str:
        """교수명 추출"""
        professor_element = subject.select_one('em')
        return professor_element.text.strip() if professor_element else "담당자 미정"

def cleanup_resources():
    """모듈 종료 시 모든 리소스 정리"""
    global DRIVER_POOL, THREAD_POOL
    
    if THREAD_POOL:
        THREAD_POOL.shutdown(wait=False)
        
    if DRIVER_POOL:
        DRIVER_POOL.shutdown()

# 프로그램 종료 시 정리 함수 등록
atexit.register(cleanup_resources)

# 모듈로 실행될 때의 테스트 코드
if __name__ == "__main__":
    url = input("에브리타임 시간표 URL을 입력하세요: ")
    parser = TimetableParser(url)
    result = parser.parse_timetable()
    
    # 결과 출력
    print(json.dumps(result, indent=2, ensure_ascii=False))