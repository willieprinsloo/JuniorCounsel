"""
Pydantic schemas for authentication endpoints.
"""
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    """Schema for user registration request."""

    email: EmailStr
    password: str
    full_name: str

    model_config = {"str_strip_whitespace": True}


class UserLogin(BaseModel):
    """Schema for user login request."""

    email: EmailStr
    password: str


class Token(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for decoded JWT token data."""

    email: Optional[str] = None


class UserResponse(BaseModel):
    """Schema for user data in responses."""

    id: int
    email: str
    full_name: Optional[str] = None

    model_config = {"from_attributes": True}
