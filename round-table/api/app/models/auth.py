# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""Authentication-related Pydantic models"""

from email_validator import validate_email as _validate_email
from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    full_name: str | None = Field(None, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format"""
        emailinfo = _validate_email(v, check_deliverability=False)
        return emailinfo.normalized


class LoginRequest(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class User(BaseModel):
    """User entity"""
    user_id: str
    email: str
    full_name: str | None = None
    is_active: bool = True
    created_at: str | None = None


class AuthResponse(BaseModel):
    """Authentication response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: User


class UserResponse(BaseModel):
    """User response wrapper"""
    user: User
