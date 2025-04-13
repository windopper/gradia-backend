"""
에브리타임 시간표 파싱 기본 모듈

에브리타임 파서들의 공통 기능을 정의한 베이스 클래스입니다.
"""

from typing import Dict, List, Tuple, Optional
from bs4 import Tag
from fastapi import HTTPException


class EverytimeTimetableParserBase:
    """에브리타임 시간표 파서 베이스 클래스"""
    
    def __init__(self, url: str = None, timeout: int = 30):
        self.url = url
        self.day_enum = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        self.timeout = timeout
    
    def _validate_url(self, url: str) -> None:
        """URL이 유효한지 확인"""
        if not url.startswith(('http://', 'https://')):
            raise ValueError("유효하지 않은 URL 형식입니다.")
            
        # 에브리타임 URL인지 확인
        if not 'everytime.kr' in url:
            raise ValueError("에브리타임 URL이 아닙니다.")
    
    def _extract_time_of_subject(self, subject: Tag) -> Tuple[int, int, int, int]:
        """과목의 시작 및 종료 시간을 추출"""
        PART = 60
        
        try:
            style = subject['style']
            height = int(style.split(';')[0].split(':')[1].replace('px', ''))
            top = int(style.split(';')[1].split(':')[1].replace('px', ''))
            # 0px부터 오전 0시부터 시작
            # 50px당 1시간
            start_hour = top // PART
            start_minute = (top % PART) * 60 // PART
            end_hour = (top + height - 1) // PART
            end_minute = ((top + height - 1) % PART) * 60 // PART
            
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