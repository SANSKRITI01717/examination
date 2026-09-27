"""
Authentication service layer.
Handles login authentication and token issuance.
"""
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import create_access_token, verify_password
from app.models.user import User


def authenticate_user(
    db: Session, email: str, password: str
) -> tuple[str, int, User]:
    """
    Authenticate user with email and password.
    Returns (access_token, expires_in, user).
    Raises AppError('INVALID_CREDENTIALS', 401) or AppError('USER_INACTIVE', 403).
    """
    normalized_email = email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()

    if not user or not verify_password(password, user.password_hash):
        raise AppError(
            code="INVALID_CREDENTIALS",
            message="Invalid email or password",
            status_code=401,
        )

    if not user.is_active:
        raise AppError(
            code="USER_INACTIVE",
            message="Account is inactive",
            status_code=403,
        )

    token, expires_in = create_access_token(subject=user.id, role=user.role)
    return token, expires_in, user
