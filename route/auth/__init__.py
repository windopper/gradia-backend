__all__ = ["google"]

from fastapi import APIRouter
from .google import router as google_router
from .common import common_router

# 인증 관련 모든 라우팅을 결합하는 메인 라우터
router = APIRouter()

# google.py의 라우터와 common.py의 라우터를 포함
router.include_router(google_router)
router.include_router(common_router)
