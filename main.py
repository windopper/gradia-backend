from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Depends
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
# 개별 라우터 임포트 대신 route/__init__.py의 통합 라우터 사용
from route import router as route_router
from route.auth import google as auth_google_router_module, common as auth_common_router_module
from db import (
    initialize_firebase_app_if_not_yet as db_initialize_firebase_app,
    get_firestore_client as db_get_firestore_client,
    delete_firebase_app_if_exists as db_delete_firebase_app
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 애플리케이션 시작 시 실행될 코드
    print("FastAPI lifespan: Startup phase beginning...")
    try:
        db_initialize_firebase_app()
        app.state.firestore_client = db_get_firestore_client()
        if app.state.firestore_client:
            print(
                "Firestore client successfully obtained and set on app.state.firestore_client during lifespan startup.")
        else:
            print(
                "Critical Error: Firestore client could not be obtained during lifespan startup.")
    except Exception as e:
        print(
            f"Critical Error during FastAPI lifespan startup: Failed to initialize Firebase/Firestore: {e}")
        import traceback
        traceback.print_exc()

    yield  # 애플리케이션 실행 구간

    # 애플리케이션 종료 시 실행될 코드
    print("FastAPI lifespan: Shutdown phase beginning...")
    db_delete_firebase_app()
    if hasattr(app.state, "firestore_client"):
        delattr(app.state, "firestore_client")
        print("Firestore client removed from app.state during lifespan shutdown.")
    print("FastAPI lifespan: Shutdown phase complete.")


def create_app():
    app = FastAPI(title="Gradia Backend", version="0.1.0", lifespan=lifespan)

    # CORS 미들웨어 추가
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 실제 환경에서는 허용할 도메인만 지정하세요
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 라우터 등록
    # 개별 라우터 등록 대신 통합 라우터 사용
    app.include_router(route_router)

    @app.get("/")
    async def root():
        return {"message": "Welcome to Gradia Backend"}

    return app


app = create_app()


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
