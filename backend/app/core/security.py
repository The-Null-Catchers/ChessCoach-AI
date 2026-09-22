from datetime import datetime, timedelta, timezone
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.core.config import settings

_hasher = PasswordHasher()

def hash_password(password: str) -> str:
    return _hasher.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except VerifyMismatchError:
        return False

def make_token(user_id: str, token_type: str, expires: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {'sub': user_id, 'type': token_type, 'iat': now, 'exp': now + expires}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def token_pair(user_id: str) -> tuple[str, str]:
    access = make_token(user_id, 'access', timedelta(minutes=settings.access_token_minutes))
    refresh = make_token(user_id, 'refresh', timedelta(days=settings.refresh_token_days))
    return access, refresh
