# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
FastAPI dependencies for authentication

Provides dependency functions for protecting API endpoints with JWT authentication.
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .jwt import verify_token, JWTError
from .models import UserInDB
from ..repositories import UserRepository
from ..db import get_db

logger = logging.getLogger(__name__)

# Security scheme for HTTP Bearer tokens
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db_session = Depends(get_db),
) -> UserInDB:
    """
    Get current authenticated user from JWT token

    Args:
        credentials: HTTP Bearer credentials
        db_session: Database session

    Returns:
        UserInDB

    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Verify token
        payload = verify_token(credentials.credentials, token_type="access")
        user_id = payload.sub

    except JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        raise credentials_exception

    # Get user from database
    user_repo = UserRepository(db_session)
    user = await user_repo.get(user_id)

    if user is None:
        raise credentials_exception

    return UserInDB(
        user_id=user.user_id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
    )


async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user),
) -> UserInDB:
    """
    Get current active user

    Args:
        current_user: Current authenticated user

    Returns:
        UserInDB

    Raises:
        HTTPException: 403 if user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


# Optional authentication (doesn't raise if no token)
async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db_session = Depends(get_db),
) -> Optional[UserInDB]:
    """
    Get current user if authenticated, otherwise None

    Args:
        credentials: HTTP Bearer credentials (optional)
        db_session: Database session

    Returns:
        UserInDB or None
    """
    if credentials is None:
        return None

    try:
        payload = verify_token(credentials.credentials, token_type="access")
        user_id = payload.sub

        user_repo = UserRepository(db_session)
        user = await user_repo.get(user_id)

        if user:
            return UserInDB(
                user_id=user.user_id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
            )
    except Exception:
        pass

    return None
