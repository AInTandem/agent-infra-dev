# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Authentication models

Pydantic models for authentication requests and responses.
"""

import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    """Token response"""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    """JWT token payload"""

    sub: str  # user_id
    exp: datetime.datetime
    iat: datetime.datetime
    type: str = "access"


class UserInDB(BaseModel):
    """User from database (for auth purposes)"""

    user_id: str
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True


class LoginRequest(BaseModel):
    """User login request"""

    email: EmailStr
    password: str = Field(min_length=1, max_length=100)


class RegisterRequest(BaseModel):
    """User registration request"""

    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""

    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Change password request"""

    old_password: str
    new_password: str = Field(min_length=8, max_length=100)
