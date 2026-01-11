# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Authentication API routes

Provides user registration, login, token refresh, and logout endpoints.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from .jwt import create_access_token, create_refresh_token, verify_token, JWTError, Token
from .models import (
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
    UserInDB,
)
from .dependencies import get_current_active_user
from .security import hash_password, verify_password
from ..repositories import UserRepository
from ..models.common import SuccessResponse
from ..db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=SuccessResponse)
async def register(
    user_in: RegisterRequest,
    db_session: AsyncSession = Depends(get_db),
):
    """
    Register a new user

    Args:
        user_in: Registration data
        db_session: Database session

    Returns:
        SuccessResponse with access token

    Raises:
        HTTPException: 400 if email already registered
    """
    user_repo = UserRepository(db_session)

    # Check if user already exists
    existing_user = await user_repo.get_by_email(user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Hash password
    hashed_password = hash_password(user_in.password)

    # Create user
    user = await user_repo.create_user(
        user_in,
        hashed_password,
    )

    # Generate tokens
    access_token = create_access_token(user.user_id)
    refresh_token = create_refresh_token(user.user_id)

    logger.info(f"User registered: {user.user_id}")

    return SuccessResponse(
        data=Token(
            access_token=access_token,
            refresh_token=refresh_token,
        ).to_dict()
    )


@router.post("/login", response_model=SuccessResponse)
async def login(
    user_in: LoginRequest,
    db_session: AsyncSession = Depends(get_db),
):
    """
    User login

    Args:
        user_in: Login data (email, password)
        db_session: Database session

    Returns:
        SuccessResponse with access token

    Raises:
        HTTPException: 401 if credentials invalid
        HTTPException: 403 if user inactive
    """
    user_repo = UserRepository(db_session)

    # Get user by email
    user = await user_repo.get_by_email(user_in.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Verify password
    if not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    # Generate tokens
    access_token = create_access_token(user.user_id)
    refresh_token = create_refresh_token(user.user_id)

    logger.info(f"User logged in: {user.user_id}")

    return SuccessResponse(
        data=Token(
            access_token=access_token,
            refresh_token=refresh_token,
        ).to_dict()
    )


@router.post("/refresh", response_model=SuccessResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db_session: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token

    Args:
        request: Refresh token request
        db_session: Database session

    Returns:
        SuccessResponse with new access token

    Raises:
        HTTPException: 401 if refresh token invalid
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
    )

    try:
        # Verify refresh token
        payload = verify_token(request.refresh_token, token_type="refresh")
        user_id = payload.sub

        # Get user from database
        user_repo = UserRepository(db_session)
        user = await user_repo.get(user_id)

        if user is None:
            raise credentials_exception

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user"
            )

        # Generate new access token
        access_token = create_access_token(user.user_id)

        logger.info(f"Token refreshed: {user.user_id}")

        return SuccessResponse(
            data=Token(access_token=access_token).to_dict()
        )

    except JWTError:
        raise credentials_exception


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    current_user: UserInDB = Depends(get_current_active_user),
):
    """
    Logout user

    Note: In a stateless JWT system, logout is primarily client-side.
    This endpoint can be used for logging or to invalidate tokens in a
    token blacklist (future enhancement).

    Args:
        current_user: Current authenticated user

    Returns:
        SuccessResponse
    """
    logger.info(f"User logged out: {current_user.user_id}")

    return SuccessResponse(
        data={"message": "Successfully logged out"}
    )


@router.get("/me", response_model=SuccessResponse)
async def get_current_user_info(
    current_user: UserInDB = Depends(get_current_active_user),
):
    """
    Get current user information

    Args:
        current_user: Current authenticated user

    Returns:
        SuccessResponse with user data
    """
    return SuccessResponse(
        data={
            "user_id": current_user.user_id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "is_active": current_user.is_active,
        }
    )


# OAuth2 compatible endpoint for token generation (useful for testing)
@router.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db_session: AsyncSession = Depends(get_db),
):
    """
    OAuth2 compatible token endpoint

    Compatible with OAuth2PasswordBearer flow. Useful for testing
    and integration with OAuth2 clients.

    Args:
        form_data: OAuth2 form data (username=email, password)
        db_session: Database session

    Returns:
        Token with access and refresh tokens
    """
    user_repo = UserRepository(db_session)

    # Get user by email (username field is used for email)
    user = await user_repo.get_by_email(form_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    # Generate tokens
    access_token = create_access_token(user.user_id)
    refresh_token = create_refresh_token(user.user_id)

    logger.info(f"User logged in via OAuth2: {user.user_id}")

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
    )
