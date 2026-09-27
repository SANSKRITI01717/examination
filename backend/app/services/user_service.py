"""
User management service layer.
Handles user creation, listing, updating, and deactivation rules.
"""
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


def create_user(db: Session, user_in: UserCreate) -> User:
    """
    Create a new user account.
    Raises AppError('EMAIL_EXISTS', 409) if email is already registered.
    """
    normalized_email = user_in.email.strip().lower()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        raise AppError(
            code="EMAIL_EXISTS",
            message="A user with this email already exists",
            status_code=409,
        )

    user = User(
        email=normalized_email,
        password_hash=hash_password(user_in.password),
        full_name=user_in.full_name.strip(),
        role=user_in.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(
    db: Session,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 25,
) -> Tuple[List[User], int]:
    """
    List users with optional role and status filters and pagination.
    """
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    total = query.count()
    offset = max(0, (page - 1) * page_size)
    items = query.order_by(User.id.asc()).offset(offset).limit(page_size).all()
    return items, total


def get_user_by_id(db: Session, user_id: int) -> User:
    """
    Retrieve user by ID.
    Raises AppError('NOT_FOUND', 404) if user does not exist.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppError(
            code="NOT_FOUND",
            message="User not found",
            status_code=404,
        )
    return user


def update_user(
    db: Session,
    user_id: int,
    current_user_id: int,
    user_in: UserUpdate,
) -> User:
    """
    Update user attributes.
    Raises AppError('CANNOT_DEACTIVATE_SELF', 409) if an admin attempts to deactivate themselves.
    """
    user = get_user_by_id(db, user_id)

    # Invariant: Cannot deactivate self
    if user_in.is_active is False and user_id == current_user_id:
        raise AppError(
            code="CANNOT_DEACTIVATE_SELF",
            message="You cannot deactivate your own account",
            status_code=409,
        )

    if user_in.full_name is not None:
        user.full_name = user_in.full_name.strip()
    if user_in.role is not None:
        user.role = user_in.role
    if user_in.is_active is not None:
        user.is_active = user_in.is_active
    if user_in.password is not None:
        user.password_hash = hash_password(user_in.password)

    db.commit()
    db.refresh(user)
    return user
