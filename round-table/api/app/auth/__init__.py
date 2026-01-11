# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Authentication and Authorization module

Provides JWT-based authentication with password hashing, token validation,
and refresh token support.
"""

from .jwt import JWTManager, create_access_token, create_refresh_token
from .security import hash_password, verify_password
from .dependencies import get_current_user, get_current_active_user
from .models import Token, TokenPayload, UserInDB

__all__ = [
    "JWTManager",
    "create_access_token",
    "create_refresh_token",
    "hash_password",
    "verify_password",
    "get_current_user",
    "get_current_active_user",
    "Token",
    "TokenPayload",
    "UserInDB",
]
