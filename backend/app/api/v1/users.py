"""
User management API endpoints.
Mirrors api-spec.md §3 (U1, U2, U3).
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import require_role
from app.models.user import User
from app.schemas.user import UserCreate, UserListResponse, UserResponse, UserUpdate
from app.services.user_service import create_user, list_users, update_user

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account (U1)",
)
def create_new_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
) -> UserResponse:
    """
    Admin only: Create a new user account (admin, examiner, or moderator).
    """
    user = create_user(db=db, user_in=payload)
    return UserResponse.model_validate(user)


@router.get(
    "",
    response_model=UserListResponse,
    summary="List users with filters and pagination (U2)",
)
def get_users(
    role: Optional[str] = Query(None, description="Filter by user role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
) -> UserListResponse:
    """
    Admin only: List users with optional role and status filters and pagination.
    """
    items, total = list_users(
        db=db,
        role=role,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )
    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/{id}",
    response_model=UserResponse,
    summary="Edit or deactivate user (U3)",
)
def update_user_by_id(
    id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_role("admin")),
) -> UserResponse:
    """
    Admin only: Edit user attributes or deactivate account.
    Self-deactivation is rejected.
    """
    user = update_user(
        db=db,
        user_id=id,
        current_user_id=admin.id,
        user_in=payload,
    )
    return UserResponse.model_validate(user)
