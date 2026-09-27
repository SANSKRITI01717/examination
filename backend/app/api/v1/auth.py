"""
Authentication API endpoints.
Mirrors api-spec.md §2 (A1, A2).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.user import UserResponse
from app.services.auth_service import authenticate_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Log in and obtain JWT access token (A1)",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    """
    Authenticate user using email and password.
    Returns access_token, token_type, expires_in, and user profile.
    """
    token, expires_in, user = authenticate_user(
        db=db, email=payload.email, password=payload.password
    )
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile (A2)",
)
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """
    Return currently authenticated user's profile.
    """
    return UserResponse.model_validate(current_user)
