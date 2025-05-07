"""
과목(Subject) 관련 API 엔드포인트 모듈
사용자의 과목을 생성, 조회, 업데이트 및 삭제하는 API 엔드포인트가 정의되어 있습니다.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import asyncio

from route.auth.google import get_current_user_from_backend_token
from db.subject import (
    get_subjects_by_user_id,
    get_subject_by_id,
    create_subject,
    update_subject,
    delete_subject
)

# 라우터 정의
router = APIRouter(
    prefix="/subjects",
    tags=["subjects"],
    responses={404: {"description": "Not found"}},
)

# 요청 및 응답 모델 정의
class EvaluationRatio(BaseModel):
    mid_term_ratio: int = 0
    final_term_ratio: int = 0
    quiz_ratio: int = 0
    assignment_ratio: int = 0
    attendance_ratio: int = 0

class TargetStudyTime(BaseModel):
    daily_target_study_time: int = 0
    weekly_target_study_time: int = 0
    monthly_target_study_time: int = 0

class SubjectCreate(BaseModel):
    name: str
    type: int  # 0: 전필, 1: 전선, 2: 교양
    credit: int
    difficulty: Optional[int] = None
    mid_term_schedule: Optional[str] = None
    final_term_schedule: Optional[str] = None
    evaluation_ratio: Optional[EvaluationRatio] = None
    target_study_time: Optional[TargetStudyTime] = None
    color: Optional[str] = None

class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[int] = None
    credit: Optional[int] = None
    difficulty: Optional[int] = None
    mid_term_schedule: Optional[str] = None
    final_term_schedule: Optional[str] = None
    evaluation_ratio: Optional[EvaluationRatio] = None
    target_study_time: Optional[TargetStudyTime] = None
    color: Optional[str] = None

class SubjectResponse(BaseModel):
    id: str
    user_id: str
    name: str
    type: int
    credit: int
    difficulty: Optional[int] = None
    mid_term_schedule: Optional[str] = None
    final_term_schedule: Optional[str] = None
    evaluation_ratio: Optional[Dict[str, int]] = None
    target_study_time: Optional[Dict[str, int]] = None
    color: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class SubjectListResponse(BaseModel):
    subjects: List[SubjectResponse]
    message: str

@router.get("/", response_model=SubjectListResponse)
async def get_all_subjects(
    current_user = Depends(get_current_user_from_backend_token)
):
    """
    현재 인증된 사용자의 모든 과목을 조회합니다.
    
    - Authorization 헤더에 "Bearer <access_token>" 형태로 토큰이 필요합니다.
    """
    try:
        user_id = current_user["id"]
        subjects = await get_subjects_by_user_id(user_id)
        
        return {
            "subjects": subjects,
            "message": "과목 조회 성공"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"과목 조회 실패: {str(e)}"
        )

@router.get("/{subject_id}", response_model=SubjectResponse)
async def get_subject(
    subject_id: str,
    current_user = Depends(get_current_user_from_backend_token)
):
    """
    특정 ID의 과목을 조회합니다.
    
    - Authorization 헤더에 "Bearer <access_token>" 형태로 토큰이 필요합니다.
    - subject_id: 조회할 과목 ID
    """
    try:
        subject = await get_subject_by_id(subject_id)
        
        if not subject:
            raise HTTPException(
                status_code=404,
                detail=f"ID가 {subject_id}인 과목을 찾을 수 없습니다."
            )
        
        # 권한 확인: 자신의 과목만 조회 가능
        if subject.get("user_id") != current_user["id"]:
            raise HTTPException(
                status_code=403,
                detail="다른 사용자의 과목을 조회할 권한이 없습니다."
            )
        
        return subject
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"과목 조회 실패: {str(e)}"
        )

@router.post("/", response_model=SubjectResponse)
async def create_new_subject(
    subject_data: SubjectCreate,
    current_user = Depends(get_current_user_from_backend_token)
):
    """
    새 과목을 생성합니다.
    
    - Authorization 헤더에 "Bearer <access_token>" 형태로 토큰이 필요합니다.
    - 요청 바디에 과목 데이터를 JSON 형식으로 제공해야 합니다.
    """
    try:
        user_id = current_user["id"]
        
        evaluation_ratio = None
        if subject_data.evaluation_ratio:
            evaluation_ratio = subject_data.evaluation_ratio.dict()
            
        target_study_time = None
        if subject_data.target_study_time:
            target_study_time = subject_data.target_study_time.dict()
        
        new_subject = await create_subject(
            user_id=user_id,
            name=subject_data.name,
            subject_type=subject_data.type,
            credit=subject_data.credit,
            difficulty=subject_data.difficulty,
            mid_term_schedule=subject_data.mid_term_schedule,
            final_term_schedule=subject_data.final_term_schedule,
            evaluation_ratio=evaluation_ratio,
            target_study_time=target_study_time,
            color=subject_data.color
        )
        
        return new_subject
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"과목 생성 실패: {str(e)}"
        )

@router.patch("/{subject_id}", response_model=SubjectResponse)
async def update_existing_subject(
    subject_id: str,
    update_data: SubjectUpdate,
    current_user = Depends(get_current_user_from_backend_token)
):
    """
    기존 과목을 업데이트합니다.
    
    - Authorization 헤더에 "Bearer <access_token>" 형태로 토큰이 필요합니다.
    - subject_id: 업데이트할 과목 ID
    - 요청 바디에 업데이트할 과목 데이터를 JSON 형식으로 제공해야 합니다.
    """
    try:
        # 대상 과목 조회
        subject = await get_subject_by_id(subject_id)
        
        if not subject:
            raise HTTPException(
                status_code=404,
                detail=f"ID가 {subject_id}인 과목을 찾을 수 없습니다."
            )
        
        # 권한 확인: 자신의 과목만 업데이트 가능
        if subject.get("user_id") != current_user["id"]:
            raise HTTPException(
                status_code=403,
                detail="다른 사용자의 과목을 업데이트할 권한이 없습니다."
            )
        
        # 업데이트할 데이터 준비
        update_dict = update_data.dict(exclude_unset=True)
        
        # 중첩된 객체 처리
        if 'evaluation_ratio' in update_dict and update_dict['evaluation_ratio']:
            update_dict['evaluation_ratio'] = update_dict['evaluation_ratio'].dict()
            
        if 'target_study_time' in update_dict and update_dict['target_study_time']:
            update_dict['target_study_time'] = update_dict['target_study_time'].dict()
        
        # 업데이트 수행
        updated_subject = await update_subject(subject_id, update_dict)
        
        return updated_subject
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"과목 업데이트 실패: {str(e)}"
        )

@router.delete("/{subject_id}")
async def delete_existing_subject(
    subject_id: str,
    current_user = Depends(get_current_user_from_backend_token)
):
    """
    과목을 삭제합니다.
    
    - Authorization 헤더에 "Bearer <access_token>" 형태로 토큰이 필요합니다.
    - subject_id: 삭제할 과목 ID
    """
    try:
        # 대상 과목 조회
        subject = await get_subject_by_id(subject_id)
        
        if not subject:
            raise HTTPException(
                status_code=404,
                detail=f"ID가 {subject_id}인 과목을 찾을 수 없습니다."
            )
        
        # 권한 확인: 자신의 과목만 삭제 가능
        if subject.get("user_id") != current_user["id"]:
            raise HTTPException(
                status_code=403,
                detail="다른 사용자의 과목을 삭제할 권한이 없습니다."
            )
        
        # 삭제 수행
        success = await delete_subject(subject_id)
        
        if success:
            return {"message": "과목이 성공적으로 삭제되었습니다."}
        else:
            raise HTTPException(
                status_code=500,
                detail="과목 삭제 실패"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"과목 삭제 실패: {str(e)}"
        )