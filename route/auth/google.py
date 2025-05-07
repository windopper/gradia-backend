from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel # 요청 본문을 위한 모델 추가
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from typing import Optional
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError, ExpiredSignatureError
from db.user import get_user_by_google_id, get_or_create_user, get_user_by_id  # 새로 추가한 사용자 관리 모듈 import

# 설정값은 외부 파일이나 환경 변수에서 불러오는 것이 좋습니다.
GOOGLE_CLIENT_ID = "637824960431-fo6ev723vd5u0pmqm4m17r79icm5ugc1.apps.googleusercontent.com"
SECRET_KEY="your_secret_key"  # JWT 서명에 사용할 비밀 키
ALGORITHM = "HS256"  # JWT 서명 알고리즘

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={404: {"description": "Not found"}},
)

# 요청 본문을 위한 Pydantic 모델 정의
class GoogleIdToken(BaseModel):
    id_token_str: str # 클라이언트에서 "id_token_str" 또는 Body(alias="id_token")에 맞춰 "id_token"으로 보낼 수 있음

class TokenData(BaseModel):
    user_id: str # JWT의 subject를 사용자의 고유 식별자로 사용한다고 가정
    
bearer_scheme = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user_from_backend_token(credentials: str = Depends(bearer_scheme)):
    token = credentials.credentials # HTTPBearer에서 가져온 토큰
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub") # JWT의 subject를 사용자의 고유 식별자로 사용했다고 가정
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise credentials_exception
    
    # DB에서 user_id로 사용자 정보 조회
    user = await get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    
    return user  # 실제 사용자 정보 반환

@router.post("/google") # GET에서 POST로 변경
async def login_with_google(token_data: GoogleIdToken): # 요청 본문을 모델로 받음
    """
    Google ID Token을 사용하여 사용자 인증을 수행합니다.

    - **id_token_str**: Google ID Token (필수, 요청 본문에 JSON 형태로 전달: {"id_token_str": "YOUR_TOKEN_HERE"})
    """
    try:
        id_info = id_token.verify_oauth2_token(
            token_data.id_token_str, google_requests.Request(), GOOGLE_CLIENT_ID
        )

        # 토큰 검증 후 추가 확인 (선택 사항이지만 권장)
        # 예: aud (대상) 클레임이 GOOGLE_CLIENT_ID와 일치하는지 확인
        if id_info['aud'] != GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token audience.",
            )

        # 예: iss (발급자) 클레임 확인
        if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token issuer.",
            )

        google_user_id = id_info.get("sub")
        email = id_info.get("email")
        name = id_info.get("name")
        picture = id_info.get("picture")  # 프로필 사진 URL
        
        # DB에 사용자 정보 저장 또는 업데이트
        user = await get_or_create_user(
            google_id=google_user_id,
            email=email,
            name=name,
            picture=picture
        )
        
        # JWT 토큰 생성 - Firestore 문서 ID를 subject로 사용
        access_token = create_access_token(data={"sub": user["id"]})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user["id"],
            "email": email,
            "name": name
        }

    except ValueError as e:
        # ID 토큰이 유효하지 않거나 만료된 경우 발생
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired Google ID Token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        # 기타 예상치 못한 오류
        # 실제 프로덕션에서는 로깅을 철저히 하고, 민감한 오류 메시지를 클라이언트에 그대로 노출하지 않도록 주의
        print(f"An unexpected error occurred: {e}") # 서버 로그용
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred during authentication.",
        )
        
@router.get("/users/me")
async def read_users_me(current_user = Depends(get_current_user_from_backend_token)):
    """
    현재 인증된 사용자의 정보를 반환합니다.
    Authorization 헤더에 "Bearer <access_token>" 형태로 토큰이 전달되어야 합니다.
    """
    # current_user는 이미 DB에서 조회된 사용자 정보입니다
    return {
        "user_id": current_user["id"],
        "email": current_user["email"],
        "name": current_user["name"],
        "google_id": current_user["google_id"],
        "created_at": current_user["created_at"],
        "updated_at": current_user["updated_at"]
    }