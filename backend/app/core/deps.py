"""
FastAPI dependencies for authentication, database session, and role-based access control.
"""
from typing import Callable, Optional
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Extracts Bearer token from Authorization header, validates signature and expiration,
    and returns the authenticated active User model instance.
    Raises AppError('UNAUTHENTICATED', status_code=401) if token is missing or invalid.
    Raises AppError('USER_INACTIVE', status_code=403) if user is deactivated.
    """
    if auth is None or not auth.credentials:
        raise AppError(
            code="UNAUTHENTICATED",
            message="Authentication credentials were not provided",
            status_code=401,
        )

    payload = decode_access_token(auth.credentials)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise AppError(
            code="UNAUTHENTICATED",
            message="Invalid token payload",
            status_code=401,
        )

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise AppError(
            code="UNAUTHENTICATED",
            message="Invalid user identifier in token",
            status_code=401,
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppError(
            code="UNAUTHENTICATED",
            message="User associated with token no longer exists",
            status_code=401,
        )

    if not user.is_active:
        raise AppError(
            code="USER_INACTIVE",
            message="Account is inactive",
            status_code=403,
        )

    return user


def require_role(*allowed_roles: str) -> Callable[[User], User]:
    """
    Dependency factory that verifies current user has one of the allowed roles.
    Raises AppError('FORBIDDEN', status_code=403) if role is not allowed.
    """

    def role_dependency(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in allowed_roles:
            raise AppError(
                code="FORBIDDEN",
                message=f"Access denied for role '{current_user.role}'",
                status_code=403,
            )
        return current_user

    return role_dependency
