import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore_async
from firebase_admin import firestore
from typing import Optional, Dict, Any, List
from datetime import datetime

# 학습 세션 컬렉션 상수
STUDY_SESSION_COLLECTION = 'study_sessions'


async def get_study_sessions_by_user_id(user_id: str, db_client: firestore_async.AsyncClient) -> List[Dict[str, Any]]:
    """
    사용자 ID를 사용하여 해당 사용자의 모든 학습 세션을 조회합니다.

    Args:
        user_id: 사용자 고유 ID
        db_client: Firestore 클라이언트

    Returns:
        학습 세션 목록
    """
    query = db_client.collection(
        STUDY_SESSION_COLLECTION).where('user_id', '==', user_id)
    results = await query.get()

    sessions = []
    for doc in results:
        session_data = doc.to_dict()
        session_data['id'] = doc.id
        sessions.append(session_data)

    return sessions


async def get_study_session_by_id(session_id: str, db_client: firestore_async.AsyncClient) -> Optional[Dict[str, Any]]:
    """
    세션 ID로 특정 학습 세션을 조회합니다.

    Args:
        session_id: 학습 세션 ID
        db_client: Firestore 클라이언트

    Returns:
        학습 세션 정보 또는 없는 경우 None
    """
    doc_ref = db_client.collection(
        STUDY_SESSION_COLLECTION).document(session_id)
    doc = await doc_ref.get()

    if doc.exists:
        session_data = doc.to_dict()
        session_data['id'] = doc.id
        return session_data

    return None


async def create_study_session(user_id: str, subject_id: str, date: str, study_time: int,
                               start_time: datetime, end_time: datetime,
                               db_client: firestore_async.AsyncClient,
                               focus_level: int = 0,
                               rest_time: int = 0,
                               memo: str = "") -> Dict[str, Any]:
    """
    새 학습 세션을 생성합니다.

    Args:
        user_id: 사용자 고유 ID
        subject_id: 과목 ID
        date: 공부한 날짜 (YYYY-MM-DD 형식)
        study_time: 공부 시간 (초 단위)
        start_time: 시작 시각
        end_time: 종료 시각
        db_client: Firestore 클라이언트
        rest_time: 휴식/중지 시간 (초 단위)

    Returns:
        생성된 학습 세션 정보
    """
    session_data = {
        'user_id': user_id,
        'subject_id': subject_id,
        'date': date,
        'study_time': study_time,
        'start_time': start_time,
        'end_time': end_time,
        'rest_time': rest_time,
        'focus_level': focus_level,
        'memo': memo,
        'created_at': firestore.SERVER_TIMESTAMP,
        'updated_at': firestore.SERVER_TIMESTAMP
    }

    doc_ref = db_client.collection(STUDY_SESSION_COLLECTION).document()
    await doc_ref.set(session_data)

    created_doc = await doc_ref.get()
    new_session_data = created_doc.to_dict()
    new_session_data['id'] = created_doc.id
    return new_session_data


async def update_study_session(session_id: str, update_data: Dict[str, Any], db_client: firestore_async.AsyncClient) -> Dict[str, Any]:
    """
    학습 세션 정보를 업데이트합니다.

    Args:
        session_id: 학습 세션 ID
        update_data: 업데이트할 데이터
        db_client: Firestore 클라이언트

    Returns:
        업데이트된 학습 세션 정보
    """
    update_data['updated_at'] = firestore.SERVER_TIMESTAMP

    doc_ref = db_client.collection(
        STUDY_SESSION_COLLECTION).document(session_id)
    await doc_ref.update(update_data)

    updated_doc = await doc_ref.get()
    updated_session_data = updated_doc.to_dict()
    updated_session_data['id'] = updated_doc.id
    return updated_session_data


async def delete_study_session(session_id: str, db_client: firestore_async.AsyncClient) -> bool:
    """
    학습 세션을 삭제합니다.

    Args:
        session_id: 학습 세션 ID
        db_client: Firestore 클라이언트

    Returns:
        삭제 성공 여부
    """
    doc_ref = db_client.collection(
        STUDY_SESSION_COLLECTION).document(session_id)
    doc = await doc_ref.get()

    if not doc.exists:
        return False

    await doc_ref.delete()
    return True


async def get_study_sessions_by_subject_id(user_id: str, subject_id: str, db_client: firestore_async.AsyncClient) -> List[Dict[str, Any]]:
    """
    특정 과목 ID에 해당하는 모든 학습 세션을 조회합니다.

    Args:
        user_id: 사용자 고유 ID
        subject_id: 과목 ID
        db_client: Firestore 클라이언트

    Returns:
        학습 세션 목록
    """
    query = db_client.collection(STUDY_SESSION_COLLECTION).where(
        'user_id', '==', user_id).where('subject_id', '==', subject_id)
    results = await query.get()

    sessions = []
    for doc in results:
        session_data = doc.to_dict()
        session_data['id'] = doc.id
        sessions.append(session_data)

    return sessions


async def delete_study_sessions_by_subject_id(user_id: str, subject_id: str, db_client: firestore_async.AsyncClient) -> int:
    """
    특정 과목 ID에 해당하는 모든 학습 세션을 삭제합니다.

    Args:
        user_id: 사용자 고유 ID
        subject_id: 과목 ID
        db_client: Firestore 클라이언트

    Returns:
        삭제된 학습 세션 개수
    """
    # 먼저 해당 과목의 모든 학습 세션을 조회
    query = db_client.collection(STUDY_SESSION_COLLECTION).where(
        'user_id', '==', user_id).where('subject_id', '==', subject_id)
    results = await query.get()

    deleted_count = 0

    # 각 학습 세션을 삭제
    for doc in results:
        await doc.reference.delete()
        deleted_count += 1

    return deleted_count
