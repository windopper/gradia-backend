import firebase_admin
from firebase_admin import credentials, firestore_async
import os

# Firestore 클라이언트를 저장할 변수 (단일 인스턴스 보장용)
_db_client = None


def initialize_firebase_app_if_not_yet():
    """Firebase 앱이 초기화되지 않았으면 초기화합니다."""
    if not firebase_admin._apps:
        try:
            # 환경 변수 또는 고정 경로 사용
            original_path = './secret/gradia-68f97-firebase-adminsdk-fbsvc-4c8e24ca75.json'
            # __file__은 현재 파일(db/__init__.py)의 경로입니다.
            # 프로젝트 루트를 기준으로 경로를 구성하려면 os.path.join(os.path.dirname(__file__), '..', 'secret', ...)와 같이 합니다.
            # 여기서는 현재 파일의 디렉토리(db)의 부모 디렉토리(프로젝트 루트) 아래 secret 폴더를 찾습니다.
            proj_root = os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))
            cred_path_from_proj_root = os.path.join(
                proj_root, 'secret', 'gradia-68f97-firebase-adminsdk-fbsvc-4c8e24ca75.json')

            cred_path = os.path.abspath(cred_path_from_proj_root)  # 기본 경로

            if not os.path.exists(cred_path):
                # GOOGLE_APPLICATION_CREDENTIALS 환경 변수 확인
                cred_path_env = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                if cred_path_env and os.path.exists(cred_path_env):
                    cred_path = cred_path_env
                    print(f"Using GOOGLE_APPLICATION_CREDENTIALS: {cred_path}")
                else:
                    # 원래 시도했던 original_path (상대 경로)도 마지막으로 확인
                    abs_original_path = os.path.abspath(original_path)
                    if os.path.exists(abs_original_path):
                        cred_path = abs_original_path
                        print(f"Using relative path resolved to: {cred_path}")
                    else:
                        # 모든 경로 탐색 실패
                        error_msg = (
                            f"Firebase service account key not found.\n"
                            f"Tried project root relative: {cred_path_from_proj_root}\n"
                            f"Tried environment variable GOOGLE_APPLICATION_CREDENTIALS.\n"
                            f"Tried original relative path: {original_path}"
                        )
                        raise FileNotFoundError(error_msg)

            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print(
                f"Firebase App initialized by db module using key: {cred_path}")
            return True
        except Exception as e:
            print(f"Failed to initialize Firebase App in db module: {e}")
            import traceback
            traceback.print_exc()
            raise RuntimeError(
                f"Firebase initialization failed in db module: {e}") from e
    return False


def get_firestore_client():
    """Firestore 비동기 클라이언트를 반환합니다 (필요시 Firebase 앱 초기화)."""
    global _db_client
    initialize_firebase_app_if_not_yet()
    if _db_client is None:
        _db_client = firestore_async.client()
        print("Firestore client created by db module.")
    return _db_client


def delete_firebase_app_if_exists():
    """Firebase 앱이 존재하면 삭제합니다 (주로 테스트 종료 시)."""
    try:
        app_instance = firebase_admin.get_app()
        firebase_admin.delete_app(app_instance)
        print("Firebase App deleted by db module.")
        global _db_client
        _db_client = None
        return True
    except ValueError:
        return False
    except Exception as e:
        print(f"Error deleting Firebase app in db module: {e}")
        return False


__all__ = ["get_firestore_client",
           "initialize_firebase_app_if_not_yet", "delete_firebase_app_if_exists"]
