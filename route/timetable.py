"""
Timetable 관련 API 엔드포인트 모듈
에브리타임 시간표 파싱과 관련된 모든 API 엔드포인트가 정의되어 있습니다.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from typing import List
import asyncio
import platform
from utils.chromium_everytime import ChromiumTimetableParser
from utils.sync_playwright_everytime import SyncPlaywrightTimetableParser

# 라우터 정의
router = APIRouter(
    prefix="/timetable",
    tags=["timetable"],
    responses={404: {"description": "Not found"}},
)

# 동시 처리 작업 수 제한을 위한 세마포어
MAX_CONCURRENT_JOBS = 10
processing_semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)

# 응답 모델 정의
class TimetableItem(BaseModel):
    day: str
    name: str
    start_time: str
    end_time: str
    place: str
    professor: str

class TimetableResponse(BaseModel):
    timetable: List[TimetableItem]
    message: str

@router.get("/", response_model=TimetableResponse)
async def get_timetable(url: HttpUrl = Query(..., description="에브리타임 시간표 URL")):
    """
    에브리타임 URL에서 시간표 정보를 파싱하여 반환합니다.
    
    - **url**: 에브리타임 시간표 URL (필수)
    """
    try:
        # 세마포어를 활용하여 동시 처리 작업 수 제한
        async with processing_semaphore:
            # 비동기 컨텍스트에서 스레드풀의 Future를 사용하여 처리
            
            if platform.system() == 'Windows':
                future = ChromiumTimetableParser.parse_timetable_async(str(url))
            else:
                # 호스팅 환경에서 스레드 환경에서 크로미움이 작동하지 않는 관계로
                # Playwright를 사용
                future = SyncPlaywrightTimetableParser.parse_timetable_async(str(url))
            
            # 이벤트 루프에서 Future 결과를 기다림
            loop = asyncio.get_event_loop()
            timetable_data = await loop.run_in_executor(None, future.result)
            
            return {
                "timetable": timetable_data,
                "message": "시간표 파싱 성공"
            }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"시간표 파싱 실패: {str(e)}")