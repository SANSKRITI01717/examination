"""
Security utilities: password hashing and JWT token management.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
import bcrypt
import jwt

from app.core.config import settings
from app.core.errors import AppError

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def create_access_token(
    subject: Union[str, int],
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, int]:
    """
    Generate a signed JWT access token.
    Returns (token_string, expires_in_seconds).
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
        expires_in = int(expires_delta.total_seconds())
    else:
        expires_in = settings.JWT_EXPIRE_MINUTES * 60
        expire = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    encoded_jwt = jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt, expires_in


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT access token.
    Raises AppError('UNAUTHENTICATED') on expired or invalid signature.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise AppError(
                code="UNAUTHENTICATED",
                message="Invalid token type",
                status_code=401,
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise AppError(
            code="UNAUTHENTICATED",
            message="Token has expired",
            status_code=401,
        )
    except (jwt.InvalidTokenError, Exception) as exc:
        raise AppError(
            code="UNAUTHENTICATED",
            message="Could not validate credentials",
            status_code=401,
        )
