from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError, ExpiredSignatureError

# 사용자 관리 모듈 및 의존성 함수 import
# get_user_by_id는 google.py에서만 사용
from db.user import get_or_create_user, get_user_by_google_id, get_user_by_id
from dependencies import get_db
from firebase_admin import firestore_async

SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"

common_router = APIRouter(
    tags=["auth"],
    responses={404: {"description": "Not found"}},
)


class TokenData(BaseModel):
    user_id: str


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # 기본 만료 시간을 2주로 설정 (google.py와 동일하게 유지)
        expire = datetime.now(timezone.utc) + timedelta(weeks=2)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


bearer_scheme = HTTPBearer()


async def get_current_user_from_token(
    credentials: str = Depends(bearer_scheme),
    db_client: firestore_async.AsyncClient = Depends(get_db)
):
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
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

    user = await get_user_by_id(user_id, db_client=db_client)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user


@common_router.post("/temp_user_for_test")
async def create_temp_user_and_get_token_route(
    db_client: firestore_async.AsyncClient = Depends(get_db)
):
    """
    테스트용 임시 사용자를 생성하고 액세스 토큰을 발급합니다.
    """
    try:
        timestamp_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        temp_google_id = f"temp_user_{timestamp_ms}"
        temp_email = f"{temp_google_id}@example.com"
        temp_name = "Temp User"
        temp_picture = f"https://robohash.org/{temp_google_id}.png?set=set4"

        user = await get_or_create_user(
            google_id=temp_google_id,
            email=temp_email,
            name=temp_name,
            db_client=db_client,
            picture=temp_picture
        )

        access_token = create_access_token(data={"sub": user["id"]})

        return {
            "message": "Temporary user created and token issued for testing.",
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user["id"],
            "email": user['email'],
            "name": user['name'],
            "google_id": user['google_id'],
            "picture": user.get('picture')
        }
    except Exception as e:
        print(
            f"Error in create_temp_user_and_get_token_route: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred while creating a temporary user.",
        )


@common_router.post("/refresh_token")
async def refresh_access_token_route(
    current_user: dict = Depends(get_current_user_from_token),
    db_client: firestore_async.AsyncClient = Depends(get_db)
):
    """
    현재 유효한 액세스 토큰을 새로운 토큰으로 연장합니다.
    """
    try:
        user_id = current_user["id"]

        # 새로운 액세스 토큰 생성 (2주 만료)
        new_access_token = create_access_token(data={"sub": user_id})

        return {
            "message": "Access token refreshed successfully.",
            "access_token": new_access_token,
            "token_type": "bearer",
            "user_id": user_id,
            "email": current_user.get('email'),
            "name": current_user.get('name'),
            "google_id": current_user.get('google_id'),
            "picture": current_user.get('picture')
        }
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Error in refresh_access_token_route: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred while refreshing the access token.",
        )


@common_router.delete("/temp_user_for_test")
async def delete_temp_user_route(
    current_user: dict = Depends(get_current_user_from_token),
    db_client: firestore_async.AsyncClient = Depends(get_db)
):
    """
    현재 인증된 테스트용 임시 사용자를 삭제합니다. (액세스 토큰 필요)
    """
    try:
        user_doc_id = current_user["id"]
        google_id_for_message = current_user.get("google_id", "N/A")

        await db_client.collection("users").document(user_doc_id).delete()

        return {
            "message": f"User with ID '{user_doc_id}' (Google ID: '{google_id_for_message}') deleted successfully via token."
        }
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(
            f"Error in delete_temp_user_route: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal server error occurred while deleting user '{current_user.get('id', 'Unknown')}'.",
        )
