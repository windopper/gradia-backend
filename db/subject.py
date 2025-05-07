import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore_async
from typing import Optional, Dict, Any, List
from datetime import datetime

# 데이터베이스 클라이언트 가져오기
db = firestore_async.client()

# 과목 컬렉션 상수
SUBJECT_COLLECTION = 'subjects'

async def get_subjects_by_user_id(user_id: str) -> List[Dict[str, Any]]:
    """
    사용자 ID를 사용하여 해당 사용자의 모든 과목을 조회합니다.
    
    Args:
        user_id: 사용자 고유 ID
        
    Returns:
        과목 목록
    """
    query = db.collection(SUBJECT_COLLECTION).where('user_id', '==', user_id)
    results = await query.get()
    
    subjects = []
    for doc in results:
        subject_data = doc.to_dict()
        subject_data['id'] = doc.id
        subjects.append(subject_data)
    
    return subjects

async def get_subject_by_id(subject_id: str) -> Optional[Dict[str, Any]]:
    """
    과목 ID로 특정 과목을 조회합니다.
    
    Args:
        subject_id: 과목 ID
        
    Returns:
        과목 정보 또는 없는 경우 None
    """
    doc_ref = db.collection(SUBJECT_COLLECTION).document(subject_id)
    doc = await doc_ref.get()
    
    if doc.exists:
        subject_data = doc.to_dict()
        subject_data['id'] = doc.id
        return subject_data
    
    return None

async def create_subject(user_id: str, name: str, subject_type: int, credit: int, 
                        difficulty: Optional[int] = None, mid_term_schedule: Optional[str] = None, 
                        final_term_schedule: Optional[str] = None, 
                        evaluation_ratio: Optional[Dict[str, int]] = None,
                        target_study_time: Optional[Dict[str, int]] = None,
                        color: Optional[str] = None) -> Dict[str, Any]:
    """
    새 과목을 생성합니다.
    
    Args:
        user_id: 사용자 고유 ID
        name: 과목명
        subject_type: 과목 구분 (0: 전필, 1: 전선, 2: 교양)
        credit: 학점
        difficulty: 난이도 (선택)
        mid_term_schedule: 중간고사 일정 (선택)
        final_term_schedule: 기말고사 일정 (선택)
        evaluation_ratio: 평가 비율 (선택)
        target_study_time: 목표 공부 시간 (선택)
        color: UI 색상 태그 (선택)
        
    Returns:
        생성된 과목 정보
    """
    subject_data = {
        'user_id': user_id,
        'name': name,
        'type': subject_type,
        'credit': credit,
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    
    if difficulty is not None:
        subject_data['difficulty'] = difficulty
    
    if mid_term_schedule:
        subject_data['mid_term_schedule'] = mid_term_schedule
    
    if final_term_schedule:
        subject_data['final_term_schedule'] = final_term_schedule
    
    if evaluation_ratio:
        subject_data['evaluation_ratio'] = evaluation_ratio
    
    if target_study_time:
        subject_data['target_study_time'] = target_study_time
    
    if color:
        subject_data['color'] = color
    
    # 과목 추가
    doc_ref = db.collection(SUBJECT_COLLECTION).document()
    await doc_ref.set(subject_data)
    
    # 생성된 문서 반환
    subject_data['id'] = doc_ref.id
    return subject_data

async def update_subject(subject_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    과목 정보를 업데이트합니다.
    
    Args:
        subject_id: 과목 ID
        update_data: 업데이트할 데이터
        
    Returns:
        업데이트된 과목 정보
    """
    # 항상 업데이트 시간 갱신
    update_data['updated_at'] = datetime.now()
    
    doc_ref = db.collection(SUBJECT_COLLECTION).document(subject_id)
    await doc_ref.update(update_data)
    
    # 업데이트된 문서 조회
    doc = await doc_ref.get()
    subject_data = doc.to_dict()
    subject_data['id'] = doc.id
    
    return subject_data

async def delete_subject(subject_id: str) -> bool:
    """
    과목을 삭제합니다.
    
    Args:
        subject_id: 과목 ID
        
    Returns:
        삭제 성공 여부
    """
    doc_ref = db.collection(SUBJECT_COLLECTION).document(subject_id)
    doc = await doc_ref.get()
    
    if not doc.exists:
        return False
    
    await doc_ref.delete()
    return True