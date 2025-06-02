from fastapi import APIRouter, HTTPException, Depends, Query
from firebase_admin import firestore_async
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import uuid

from dependencies import get_db
from db.user import USER_COLLECTION
from db.subject import create_subject, SUBJECT_COLLECTION
from db.study_session import create_study_session, STUDY_SESSION_COLLECTION

router = APIRouter()

# 실제 있을 만한 과목 데이터
SAMPLE_SUBJECTS = [
    {"name": "데이터구조와 알고리즘", "type": 0, "credit": 3,
        "difficulty": 4, "color": "#FF6B6B"},
    {"name": "운영체제", "type": 0, "credit": 3, "difficulty": 5, "color": "#4ECDC4"},
    {"name": "데이터베이스 시스템", "type": 0, "credit": 3,
        "difficulty": 4, "color": "#45B7D1"},
    {"name": "소프트웨어공학", "type": 1, "credit": 3,
        "difficulty": 3, "color": "#96CEB4"},
    {"name": "인공지능", "type": 1, "credit": 3, "difficulty": 5, "color": "#FFEAA7"},
    {"name": "컴퓨터네트워크", "type": 0, "credit": 3,
        "difficulty": 4, "color": "#DDA0DD"},
    {"name": "웹프로그래밍", "type": 1, "credit": 3,
        "difficulty": 3, "color": "#98D8C8"},
]

# 실제 있을 만한 메모 데이터
SAMPLE_MEMOS = [
    "오늘은 집중이 잘 되었다. 개념 이해가 수월했음",
    "중간에 졸려서 휴식을 많이 취했다",
    "어려운 부분이 있어서 시간이 오래 걸렸다",
    "복습 위주로 진행했다",
    "새로운 개념을 배웠는데 흥미로웠다",
    "과제 준비로 바빴다",
    "시험 준비로 집중해서 공부했다",
    "친구와 함께 스터디했다",
    "온라인 강의를 들었다",
    "실습 위주로 진행했다",
    "이론 정리를 했다",
    "문제 풀이 중심으로 공부했다",
    "",  # 빈 메모도 포함
]


async def get_user_by_email(email: str, db_client: firestore_async.AsyncClient) -> Dict[str, Any]:
    """이메일로 사용자를 찾는 함수"""
    query = db_client.collection(USER_COLLECTION).where('email', '==', email)
    results = await query.get()

    if len(results) == 0:
        raise HTTPException(status_code=404, detail="해당 이메일의 사용자를 찾을 수 없습니다")

    user_doc = results[0]
    user_data = user_doc.to_dict()
    user_data['id'] = user_doc.id
    return user_data


async def delete_existing_data(user_id: str, db_client: firestore_async.AsyncClient):
    """기존 과목과 세션 데이터를 삭제하는 함수"""
    # 기존 과목 삭제
    subjects_query = db_client.collection(
        SUBJECT_COLLECTION).where('user_id', '==', user_id)
    subjects = await subjects_query.get()

    for subject_doc in subjects:
        await subject_doc.reference.delete()

    # 기존 세션 삭제
    sessions_query = db_client.collection(
        STUDY_SESSION_COLLECTION).where('user_id', '==', user_id)
    sessions = await sessions_query.get()

    for session_doc in sessions:
        await session_doc.reference.delete()


def generate_random_sessions(user_id: str, subject_ids: List[str], count: int = 75) -> List[Dict[str, Any]]:
    """랜덤 세션 데이터를 생성하는 함수 (시간 겹침 방지, 하루 3-4개 세션)"""
    sessions = []
    current_date = datetime.now()

    def check_time_overlap(new_start: datetime, new_end: datetime, existing_sessions: List[Dict[str, Any]]) -> bool:
        """새로운 세션이 기존 세션과 시간이 겹치는지 확인"""
        for session in existing_sessions:
            existing_start = session['start_time']
            existing_end = session['end_time']

            # 시간 겹침 확인: 새 세션의 시작이 기존 세션 범위 내에 있거나,
            # 새 세션의 끝이 기존 세션 범위 내에 있거나,
            # 새 세션이 기존 세션을 완전히 포함하는 경우
            if (new_start < existing_end and new_end > existing_start):
                return True
        return False

    def get_sessions_for_date(target_date: datetime, existing_sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """특정 날짜의 기존 세션들을 반환"""
        date_str = target_date.strftime('%Y-%m-%d')
        return [session for session in existing_sessions if session['date'] == date_str]

    # 과거 25일 동안 각 날짜별로 3-4개의 세션 생성
    for days_ago in range(1, 26):
        session_date = current_date - timedelta(days=days_ago)
        daily_sessions_count = random.randint(3, 4)
        daily_sessions = []
        max_daily_attempts = 50  # 하루당 최대 시도 횟수
        daily_attempts = 0

        while len(daily_sessions) < daily_sessions_count and daily_attempts < max_daily_attempts:
            daily_attempts += 1

            # 랜덤한 시작 시간 (오전 6시 ~ 오후 11시)
            start_hour = random.randint(6, 23)
            start_minute = random.randint(0, 59)
            start_time = session_date.replace(
                hour=start_hour, minute=start_minute, second=0, microsecond=0)

            # 공부 시간 (30분 ~ 3시간, 하루에 여러 세션이므로 조금 줄임)
            study_time_minutes = random.randint(30, 180)

            # 휴식 시간 (공부 시간의 5% ~ 20%)
            rest_time_minutes = random.randint(
                int(study_time_minutes * 0.05),
                int(study_time_minutes * 0.20)
            )

            # 종료 시간 계산 (분을 초로 변환하여 계산)
            total_seconds = (study_time_minutes + rest_time_minutes) * 60
            end_time = start_time + timedelta(seconds=total_seconds)

            # 하루를 넘어가지 않도록 제한 (다음날 새벽 2시까지만 허용)
            max_end_time = session_date.replace(
                hour=23, minute=59, second=59) + timedelta(hours=2)
            if end_time > max_end_time:
                continue

            # 같은 날짜의 기존 세션들과 시간 겹침 확인
            all_existing_sessions = sessions + daily_sessions
            if not check_time_overlap(start_time, end_time, all_existing_sessions):
                # 집중도 (1~5)
                focus_level = random.randint(1, 5)

                # 랜덤 과목 선택
                subject_id = random.choice(subject_ids)

                # 랜덤 메모 선택
                memo = random.choice(SAMPLE_MEMOS)

                session_data = {
                    'user_id': user_id,
                    'subject_id': subject_id,
                    'date': session_date.strftime('%Y-%m-%d'),
                    'study_time': study_time_minutes,
                    'start_time': start_time,
                    'end_time': end_time,
                    'rest_time': rest_time_minutes,
                    'focus_level': focus_level,
                    'memo': memo
                }

                daily_sessions.append(session_data)

        # 하루 세션들을 전체 세션 리스트에 추가
        sessions.extend(daily_sessions)

    # 시간순으로 정렬
    sessions.sort(key=lambda x: x['start_time'])

    return sessions


@router.get("/v1")
async def create_temp_data(
    email: str = Query(..., description="사용자 이메일"),
    db_client: firestore_async.AsyncClient = Depends(get_db)
):
    """
    사용자 이메일을 받아서 해당 사용자에게 임의의 과목과 세션 데이터를 생성합니다.

    - **email**: 대상 사용자의 이메일 주소
    """
    try:
        # 1. 이메일로 사용자 찾기
        user = await get_user_by_email(email, db_client)
        user_id = user['id']

        # 2. 기존 데이터 삭제
        await delete_existing_data(user_id, db_client)

        # 3. 랜덤하게 5-6개의 과목 생성
        num_subjects = random.randint(5, 6)
        selected_subjects = random.sample(SAMPLE_SUBJECTS, num_subjects)

        created_subjects = []
        subject_ids = []

        for subject_data in selected_subjects:
            # 평가 비율 생성 (중간고사, 기말고사, 과제, 출석)
            evaluation_ratio = {
                "midterm": random.randint(20, 35),
                "final": random.randint(25, 40),
                "assignment": random.randint(15, 30),
                "attendance": random.randint(5, 15)
            }

            # 목표 공부 시간 생성 (주당 시간)
            target_study_time = {
                "weekly_hours": random.randint(3, 8)
            }

            # 시험 일정 생성 (현재로부터 미래 날짜)
            mid_term_date = datetime.now() + timedelta(days=random.randint(30, 60))
            final_term_date = datetime.now() + timedelta(days=random.randint(90, 120))

            subject = await create_subject(
                user_id=user_id,
                name=subject_data["name"],
                subject_type=subject_data["type"],
                credit=subject_data["credit"],
                difficulty=subject_data["difficulty"],
                mid_term_schedule=mid_term_date.strftime('%Y-%m-%d'),
                final_term_schedule=final_term_date.strftime('%Y-%m-%d'),
                evaluation_ratio=evaluation_ratio,
                target_study_time=target_study_time,
                color=subject_data["color"],
                db_client=db_client
            )

            created_subjects.append(subject)
            subject_ids.append(subject['id'])

        # 4. 70개 이상의 랜덤 세션 생성 (25일 × 3-4개 = 75-100개)
        session_data_list = generate_random_sessions(
            user_id, subject_ids)

        created_sessions = []
        for session_data in session_data_list:
            session = await create_study_session(
                user_id=session_data['user_id'],
                subject_id=session_data['subject_id'],
                date=session_data['date'],
                study_time=session_data['study_time'],
                start_time=session_data['start_time'],
                end_time=session_data['end_time'],
                focus_level=session_data['focus_level'],
                rest_time=session_data['rest_time'],
                memo=session_data['memo'],
                db_client=db_client
            )
            created_sessions.append(session)

        return {
            "message": "임시 데이터가 성공적으로 생성되었습니다",
            "user_email": email,
            "user_id": user_id,
            "created_subjects_count": len(created_subjects),
            "created_sessions_count": len(created_sessions),
            "subjects": created_subjects,
            "sessions_summary": {
                "total_sessions": len(created_sessions),
                "date_range": {
                    "earliest": min(session['date'] for session in created_sessions),
                    "latest": max(session['date'] for session in created_sessions)
                },
                "total_study_time_hours": sum(session['study_time'] for session in created_sessions) / 60
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"데이터 생성 중 오류가 발생했습니다: {str(e)}")
