"""
학습 세션(Study Session) 관련 API 엔드포인트 모듈
사용자의 학습 세션을 생성, 조회, 업데이트 및 삭제하는 API 엔드포인트가 정의되어 있습니다.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Body, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date

from dependencies import get_db
from firebase_admin import firestore_async

from route.auth.google import get_current_user_from_backend_token

from db.study_session import (
    get_study_sessions_by_user_id,
    get_study_session_by_id,
    create_study_session,
    update_study_session,
    delete_study_session,
    get_study_sessions_by_subject_id
)

# 라우터 정의
router = APIRouter(
    prefix="/study-sessions",
    tags=["study-sessions"],
    responses={404: {"description": "Not found"}},
)

# 요청 및 응답 모델 정의


class StudySessionCreate(BaseModel):
    subject_id: str
    date: str
    study_time: int
    start_time: datetime
    end_time: datetime
    rest_time: int = 0


class StudySessionUpdate(BaseModel):
    subject_id: Optional[str] = None
    date: Optional[str] = None
    study_time: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    rest_time: Optional[int] = None


class StudySessionResponse(BaseModel):
    id: str
    user_id: str
    subject_id: str
    date: str
    study_time: int
    start_time: datetime
    end_time: datetime
    rest_time: int
    created_at: datetime
    updated_at: datetime


class StudySessionListResponse(BaseModel):
    sessions: List[StudySessionResponse]
    message: str


@router.get("/", response_model=StudySessionListResponse)
async def get_all_study_sessions_route(
    current_user: dict = Depends(get_current_user_from_backend_token),
    subject_id: Optional[str] = Query(
        None, description="특정 과목 ID에 대한 학습 세션만 조회"),
    db_client: firestore_async.AsyncClient = Depends(get_db)
):
    """
    현재 인증된 사용자의 모든 학습 세션을 조회합니다.

    - Authorization 헤더에 "Bearer <access_token>" 형태로 토큰이 필요합니다.
    - subject_id 매개변수를 사용하면 특정 과목에 대한 학습 세션만 조회할 수 있습니다.
    """
    try:
        user_id = current_user["id"]

        if subject_id:
            sessions = await get_study_sessions_by_subject_id(user_id, subject_id, db_client=db_client)
        else:
            sessions = await get_study_sessions_by_user_id(user_id, db_client=db_client)

        return {
            "sessions": sessions,
            "message": "학습 세션 조회 성공"
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"학습 세션 조회 실패: {str(e)}"
        )


@router.get("/{session_id}", response_model=StudySessionResponse)
async def get_study_session_route(
    session_id: str,
    current_user: dict = Depends(get_current_user_from_backend_token),
    db_client: firestore_async.AsyncClient = Depends(get_db)
):
    """
    특정 ID의 학습 세션을 조회합니다.

    - Authorization 헤더에 "Bearer <access_token>" 형태로 토큰이 필요합니다.
    - session_id: 조회할 학습 세션 ID
    """
    try:
        session = await get_study_session_by_id(session_id, db_client=db_client)

        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"ID가 {session_id}인 학습 세션을 찾을 수 없습니다."
            )

        # 권한 확인: 자신의 학습 세션만 조회 가능
        if session.get("user_id") != current_user["id"]:
            raise HTTPException(
                status_code=403,
                detail="다른 사용자의 학습 세션을 조회할 권한이 없습니다."
            )

        return session
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"학습 세션 조회 실패: {str(e)}"
        )


@router.post("/", response_model=StudySessionResponse, status_code=status.HTTP_201_CREATED)
async def create_new_study_session_route(
    session_data: StudySessionCreate,
    current_user: dict = Depends(get_current_user_from_backend_token),
    db_client: firestore_async.AsyncClient = Depends(get_db)
):
    """
    새 학습 세션을 생성합니다.

    - Authorization 헤더에 "Bearer <access_token>" 형태로 토큰이 필요합니다.
    - 요청 바디에 학습 세션 데이터를 JSON 형식으로 제공해야 합니다.
    """
    try:
        user_id = current_user["id"]

        new_session = await create_study_session(
            user_id=user_id,
            subject_id=session_data.subject_id,
            date=session_data.date,
            study_time=session_data.study_time,
            start_time=session_data.start_time,
            end_time=session_data.end_time,
            db_client=db_client,
            rest_time=session_data.rest_time
        )

        return new_session
    except Exception as e:
        print(
            f"Error in create_new_study_session_route: {type(e).__name__} - {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"학습 세션 생성 실패: {str(e)}"
        )


@router.patch("/{session_id}", response_model=StudySessionResponse)
async def update_existing_study_session_route(
    session_id: str,
    update_data: StudySessionUpdate,
    current_user: dict = Depends(get_current_user_from_backend_token),
    db_client: firestore_async.AsyncClient = Depends(get_db)
):
    """
    기존 학습 세션을 업데이트합니다.

    - Authorization 헤더에 "Bearer <access_token>" 형태로 토큰이 필요합니다.
    - session_id: 업데이트할 학습 세션 ID
    - 요청 바디에 업데이트할 학습 세션 데이터를 JSON 형식으로 제공해야 합니다.
    """
    try:
        # 대상 세션 조회
        session = await get_study_session_by_id(session_id, db_client=db_client)

        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"ID가 {session_id}인 학습 세션을 찾을 수 없습니다."
            )

        # 권한 확인: 자신의 학습 세션만 업데이트 가능
        if session.get("user_id") != current_user["id"]:
            raise HTTPException(
                status_code=403,
                detail="다른 사용자의 학습 세션을 업데이트할 권한이 없습니다."
            )

        # 업데이트할 데이터 필터링
        update_dict = update_data.dict(exclude_unset=True)

        # 업데이트 수행
        updated_session = await update_study_session(session_id, update_dict, db_client=db_client)

        return updated_session
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"학습 세션 업데이트 실패: {str(e)}"
        )


@router.delete("/{session_id}")
async def delete_existing_study_session_route(
    session_id: str,
    current_user: dict = Depends(get_current_user_from_backend_token),
    db_client: firestore_async.AsyncClient = Depends(get_db)
):
    """
    학습 세션을 삭제합니다.

    - Authorization 헤더에 "Bearer <access_token>" 형태로 토큰이 필요합니다.
    - session_id: 삭제할 학습 세션 ID
    """
    try:
        # 대상 세션 조회
        session = await get_study_session_by_id(session_id, db_client=db_client)

        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"ID가 {session_id}인 학습 세션을 찾을 수 없습니다."
            )

        # 권한 확인: 자신의 학습 세션만 삭제 가능
        if session.get("user_id") != current_user["id"]:
            raise HTTPException(
                status_code=403,
                detail="다른 사용자의 학습 세션을 삭제할 권한이 없습니다."
            )

        # 삭제 수행
        success = await delete_study_session(session_id, db_client=db_client)

        if success:
            return {"message": "학습 세션이 성공적으로 삭제되었습니다."}
        else:
            raise HTTPException(
                status_code=500,
                detail="학습 세션 삭제 실패"
            )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"학습 세션 삭제 실패: {str(e)}"
        )
