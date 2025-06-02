"""
Gradia Backend 라우트 모듈
모든 API 엔드포인트가 이 패키지 안에 구조화되어 있습니다.
"""

# 각 라우트 모듈을 import할 때 route.__all__로 사용할 수 있도록 설정
__all__ = ["timetable", "study_session", "subject", "grade_prediction"]

from fastapi import APIRouter

from . import auth, subject, study_session, timetable, grade_prediction, temp

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(subject.router, prefix="/subject", tags=["subject"])
router.include_router(study_session.router,
                      prefix="/study-session", tags=["study_session"])
router.include_router(
    timetable.router, prefix="/timetable", tags=["timetable"])
router.include_router(grade_prediction.router,
                      prefix="/grade-prediction", tags=["grade_prediction"])
router.include_router(temp.router, prefix="/temp", tags=["temp"])
