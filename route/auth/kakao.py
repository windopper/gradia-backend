from fastapi import APIRouter, Depends, HTTPException, status
from firebase_admin import firestore_async
import httpx
from dependencies import get_db
from pydantic import BaseModel
from .common import create_access_token
from db.user import get_or_create_kakao_user

ACCESS_TOKEN_URL = "https://kapi.kakao.com/v1/user/access_token_info"
USER_INFO_URL = "https://kapi.kakao.com/v2/user/me"

router = APIRouter(
    tags=["auth"],
    responses={404: {"description": "Not found"}},
)


class KakaoAccessToken(BaseModel):
    access_token: str


@router.post("/kakao")
async def login_with_kakao_route(
    token_data: KakaoAccessToken,
    db_client: firestore_async.AsyncClient = Depends(get_db)
):
    """
    Kakao Access Token을 사용하여 사용자 인증을 수행합니다.     

    - **access_token**: Kakao Access Token (필수, 요청 본문에 JSON 형태로 전달: {"access_token": "YOUR_TOKEN_HERE"})
    """
    try:
        # 카카오 액세스 토큰 검증
        async with httpx.AsyncClient() as client:
            token_response = await client.get(
                ACCESS_TOKEN_URL,
                headers={"Authorization": f"Bearer {token_data.access_token}"}
            )

            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Kakao Access Token"
                )

            # 사용자 정보 가져오기
            user_response = await client.get(
                USER_INFO_URL,
                headers={"Authorization": f"Bearer {token_data.access_token}"}
            )

            if user_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Failed to get user information from Kakao"
                )

            user_info = user_response.json()

            print(user_info, "user_info")

            # 카카오 사용자 정보 추출
            kakao_user_id = str(user_info.get("id"))
            kakao_account = user_info.get("kakao_account", {})
            profile = kakao_account.get("profile", {})

            email = kakao_account.get("email")
            name = profile.get("nickname")
            picture = profile.get("profile_image_url")

            # 필수 정보 확인
            if not kakao_user_id or not name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Required user information not available from Kakao"
                )

            # 사용자 조회 또는 생성
            user = await get_or_create_kakao_user(
                kakao_id=kakao_user_id,
                email=email or "",  # 이메일이 없을 수 있으므로 빈 문자열로 처리
                name=name,
                db_client=db_client,
                picture=picture
            )

            # 액세스 토큰 생성
            access_token = create_access_token(data={"sub": user["id"]})

            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user_id": user["id"],
                "email": user.get('email', ''),
                "name": user['name']
            }

    except HTTPException:
        # HTTPException은 그대로 재발생
        raise
    except Exception as e:
        print(
            f"An unexpected error occurred in login_with_kakao_route: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred during authentication."
        )
