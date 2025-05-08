from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel  # 요청 본문을 위한 모델 추가
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from jose import jwt, JWTError, ExpiredSignatureError
# 공용 모듈 import
from .common import SECRET_KEY, ALGORITHM, TokenData, create_access_token, get_current_user_from_token, bearer_scheme
# 새로 추가한 사용자 관리 모듈 import
from db.user import get_user_by_google_id, get_or_create_user, get_user_by_id
from dependencies import get_db  # get_db 의존성 함수 import
from firebase_admin import firestore_async  # db_client 타입 힌트용

# 설정값은 외부 파일이나 환경 변수에서 불러오는 것이 좋습니다.
GOOGLE_CLIENT_ID = "637824960431-fo6ev723vd5u0pmqm4m17r79icm5ugc1.apps.googleusercontent.com"

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={404: {"description": "Not found"}},
)


class GoogleIdToken(BaseModel):
    id_token_str: str


@router.post("/google")
async def login_with_google_route(
    token_data: GoogleIdToken,
    db_client: firestore_async.AsyncClient = Depends(get_db)
):
    """
    Google ID Token을 사용하여 사용자 인증을 수행합니다.

    - **id_token_str**: Google ID Token (필수, 요청 본문에 JSON 형태로 전달: {"id_token_str": "YOUR_TOKEN_HERE"})
    """
    try:
        id_info = id_token.verify_oauth2_token(
            token_data.id_token_str, google_requests.Request(), GOOGLE_CLIENT_ID
        )

        if id_info['aud'] != GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token audience.",
            )

        if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token issuer.",
            )

        google_user_id = id_info.get("sub")
        email = id_info.get("email")
        name = id_info.get("name")
        picture = id_info.get("picture")

        user = await get_or_create_user(
            google_id=google_user_id,
            email=email,
            name=name,
            db_client=db_client,
            picture=picture
        )

        access_token = create_access_token(data={"sub": user["id"]})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user["id"],
            "email": user['email'],
            "name": user['name']
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired Google ID Token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        print(
            f"An unexpected error occurred in login_with_google_route: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred during authentication.",
        )


@router.get("/users/me")
async def read_users_me_route(
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    현재 인증된 사용자의 정보를 반환합니다.
    Authorization 헤더에 "Bearer <access_token>" 형태로 토큰이 전달되어야 합니다.
    """
    return {
        "user_id": current_user["id"],
        "email": current_user["email"],
        "name": current_user["name"],
        "google_id": current_user["google_id"],
        "created_at": current_user["created_at"],
        "updated_at": current_user["updated_at"],
        "picture": current_user.get("picture")
    }
