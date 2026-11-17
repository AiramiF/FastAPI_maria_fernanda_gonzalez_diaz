import uuid
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

settings = get_settings()


def normalizar_utc(fecha: datetime | None) -> datetime | None:
    if fecha is None:
        return None
    if fecha.tzinfo is None:
        return fecha.replace(tzinfo=timezone.utc)
    return fecha.astimezone(timezone.utc)


class SecurityService:
    _password_hasher = PasswordHash.recommended()

    @classmethod
    def hash_password(cls, password: str) -> str:
        return cls._password_hasher.hash(password)

    @classmethod
    def verify_password(cls, password: str, password_hash: str) -> bool:
        return cls._password_hasher.verify(password, password_hash)

    @classmethod
    def create_token(cls, user_id: int, role: str, token_type: str, jti: str | None = None) -> tuple[str, datetime, str]:
        now = datetime.now(timezone.utc)
        if token_type == "access":
            expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        elif token_type == "refresh":
            expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        else:
            raise ValueError("Tipo de token no soportado")

        token_jti = jti or str(uuid.uuid4())
        expires_at = now + expires_delta
        payload = {
            "sub": str(user_id),
            "rol": role,
            "type": token_type,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
            "jti": token_jti,
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return token, expires_at, token_jti

    @classmethod
    def decode_token(cls, token: str) -> dict:
        return jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"require": ["sub", "rol", "type", "iat", "exp", "jti"]},
        )
