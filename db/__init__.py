import firebase_admin
from firebase_admin import credentials

cred = credentials.Certificate('./secret/gradia-68f97-firebase-adminsdk-fbsvc-4c8e24ca75.json')
app = firebase_admin.initialize_app(cred)

__all__ = ["db"]