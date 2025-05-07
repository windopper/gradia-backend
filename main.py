from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psutil
from datetime import datetime
import asyncio
import platform

# Windows 환경에서는 이벤트 루프 정책 변경
# if platform.system() == 'Windows':
#     asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
#     print("Windows 환경 감지: SelectorEventLoop 정책으로 변경됨")

# 라우터 모듈 임포트
from route import timetable, study_session, subject
from route.auth import google

app = FastAPI(title="Gradia Backend", description="Gradia Backend API")

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 환경에서는 허용할 도메인만 지정하세요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(timetable.router)
app.include_router(google.router)
app.include_router(study_session.router)
app.include_router(subject.router)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/system/memory", tags=["System"])
async def get_memory_info():
    """현재 시스템과 애플리케이션의 메모리 사용량 정보를 반환합니다."""
    process = psutil.Process()
    process_memory = process.memory_info()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "application": {
            "rss_mb": process_memory.rss / 1024 / 1024,
            "vms_mb": process_memory.vms / 1024 / 1024,
            "percent": process.memory_percent()
        },
        "system": {
            "total_gb": psutil.virtual_memory().total / 1024 / 1024 / 1024,
            "available_gb": psutil.virtual_memory().available / 1024 / 1024 / 1024,
            "used_percent": psutil.virtual_memory().percent
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)