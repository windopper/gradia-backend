import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore_async
from typing import Optional, Dict, Any
from datetime import datetime

# Firebase 초기화는 이미 다른 곳에서 완료되었다고 가정 (test.py에서 초기화됨)
# 데이터베이스 클라이언트 가져오기
db = firestore_async.client()

# 사용자 컬렉션 상수
USER_COLLECTION = 'users'

async def get_user_by_google_id(google_id: str) -> Optional[Dict[str, Any]]:
    """
    Google ID를 사용하여 사용자 정보를 조회합니다.
    
    Args:
        google_id: Google 인증으로 얻은 사용자 고유 ID
        
    Returns:
        사용자 정보 딕셔너리 또는 사용자가 없는 경우 None
    """
    query = db.collection(USER_COLLECTION).where('google_id', '==', google_id)
    results = await query.get()
    
    if len(results) > 0:
        user_doc = results[0]
        user_data = user_doc.to_dict()
        user_data['id'] = user_doc.id  # Firestore 문서 ID 추가
        return user_data
    
    return None

async def create_user(google_id: str, email: str, name: str, picture: Optional[str] = None) -> Dict[str, Any]:
    """
    새 사용자를 생성합니다.
    
    Args:
        google_id: Google 인증으로 얻은 사용자 고유 ID
        email: 사용자 이메일 주소
        name: 사용자 이름
        picture: 프로필 사진 URL (선택 사항)
        
    Returns:
        생성된 사용자 정보
    """
    user_data = {
        'google_id': google_id,
        'email': email,
        'name': name,
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }
    
    if picture:
        user_data['picture'] = picture
    
    # 사용자 추가
    doc_ref = db.collection(USER_COLLECTION).document()
    await doc_ref.set(user_data)
    
    # 생성된 문서 반환
    user_data['id'] = doc_ref.id
    return user_data

async def update_user(user_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    사용자 정보를 업데이트합니다.
    
    Args:
        user_id: Firestore 문서 ID
        update_data: 업데이트할 데이터
        
    Returns:
        업데이트된 사용자 정보
    """
    # 항상 업데이트 시간 갱신
    update_data['updated_at'] = datetime.now()
    
    doc_ref = db.collection(USER_COLLECTION).document(user_id)
    await doc_ref.update(update_data)
    
    # 업데이트된 문서 조회
    doc = await doc_ref.get()
    user_data = doc.to_dict()
    user_data['id'] = doc.id
    
    return user_data

async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    문서 ID로 사용자 정보를 조회합니다.
    
    Args:
        user_id: Firestore 문서 ID
        
    Returns:
        사용자 정보 딕셔너리 또는 사용자가 없는 경우 None
    """
    doc_ref = db.collection(USER_COLLECTION).document(user_id)
    doc = await doc_ref.get()
    
    if doc.exists:
        user_data = doc.to_dict()
        user_data['id'] = doc.id
        return user_data
    
    return None

async def get_or_create_user(google_id: str, email: str, name: str, picture: Optional[str] = None) -> Dict[str, Any]:
    """
    Google ID로 사용자를 조회하고, 존재하지 않으면 새로 생성합니다.
    
    Args:
        google_id: Google 인증으로 얻은 사용자 고유 ID
        email: 사용자 이메일 주소
        name: 사용자 이름
        picture: 프로필 사진 URL (선택 사항)
        
    Returns:
        사용자 정보
    """
    user = await get_user_by_google_id(google_id)
    
    if user:
        # 선택적으로 기존 정보 업데이트
        update_needed = False
        update_data = {}
        
        if user.get('email') != email:
            update_data['email'] = email
            update_needed = True
            
        if user.get('name') != name:
            update_data['name'] = name
            update_needed = True
            
        if picture and user.get('picture') != picture:
            update_data['picture'] = picture
            update_needed = True
            
        if update_needed:
            user = await update_user(user['id'], update_data)
            
        return user
    else:
        # 새 사용자 생성
        return await create_user(google_id, email, name, picture)