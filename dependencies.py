# dependencies.py

from fastapi import Request, HTTPException
from db import get_firestore_client as db_get_firestore_client  # db 모듈 함수 import


async def get_db(request: Request):
    """FastAPI 의존성 함수: Firestore 클라이언트를 주입합니다 (app.state 우회)."""
    # print("DEBUG: get_db called. Directly calling db_get_firestore_client().") # 필요 시 디버그 로그
    try:
        # lifespan에서 사용하는 것과 동일한 함수를 호출하여 클라이언트를 가져옵니다.
        client = db_get_firestore_client()
        if client is None:
            print(
                "Error: db_get_firestore_client() returned None when called from get_db.")
            raise HTTPException(
                status_code=500, detail="Internal server error: Failed to get DB client via db module.")
        # print("DEBUG: Successfully obtained client via db_get_firestore_client() in get_db.")
        return client
    except Exception as e:
        print(f"Error directly calling db_get_firestore_client in get_db: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail="Internal server error: Failed getting DB client directly.")
