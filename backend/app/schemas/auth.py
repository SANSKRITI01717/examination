"""
Pydantic schemas for Authentication endpoints.
Mirrors api-spec.md §2 and frontend/src/api/types.ts.
"""
from pydantic import BaseModel, Field
from app.schemas.user import EMAIL_REGEX, UserResponse


class LoginRequest(BaseModel):
    email: str = Field(..., pattern=EMAIL_REGEX)
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
