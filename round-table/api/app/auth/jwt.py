# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
JWT token operations for authentication

Handles JWT token generation, validation, and refresh token support.
"""

import datetime
import logging
from typing import Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from ..config import settings

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenPayload:
    """
    JWT token payload

    Attributes:
        sub: User ID (subject)
        exp: Expiration time
        iat: Issued at time
        type: Token type (access or refresh)
    """

    def __init__(
        self,
        sub: str,
        exp: datetime.datetime,
        iat: datetime.datetime,
        type: str = "access",
    ):
        self.sub = sub
        self.exp = exp
        self.iat = iat
        self.type = type


class Token:
    """
    Token response wrapper

    Attributes:
        access_token: JWT access token
        refresh_token: JWT refresh token
        token_type: Token type (bearer)
        expires_in: Expiration time in seconds
    """

    def __init__(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        token_type: str = "bearer",
        expires_in: int = settings.jwt_access_token_expire_minutes * 60,
    ):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_type = token_type
        self.expires_in = expires_in

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        data = {
            "access_token": self.access_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
        }
        if self.refresh_token:
            data["refresh_token"] = self.refresh_token
        return data


class JWTManager:
    """
    JWT token manager for authentication

    Features:
    - Access token generation
    - Refresh token generation
    - Token validation
    - Token decoding
    """

    def __init__(
        self,
        secret_key: str | None = None,
        algorithm: str = "HS256",
        access_expire_minutes: int = 30,
        refresh_expire_days: int = 7,
    ):
        """
        Initialize JWT manager

        Args:
            secret_key: Secret key for signing (defaults to settings)
            algorithm: JWT algorithm
            access_expire_minutes: Access token expiration in minutes
            refresh_expire_days: Refresh token expiration in days
        """
        self.secret_key = secret_key or settings.jwt_secret_key
        self.algorithm = algorithm
        self.access_expire_minutes = access_expire_minutes
        self.refresh_expire_days = refresh_expire_days

    def create_access_token(
        self,
        user_id: str,
        additional_claims: dict | None = None,
    ) -> str:
        """
        Create JWT access token

        Args:
            user_id: User ID
            additional_claims: Optional additional claims to include

        Returns:
            JWT access token
        """
        now = datetime.datetime.utcnow()
        expire = now + datetime.timedelta(minutes=self.access_expire_minutes)

        to_encode = {
            "sub": user_id,
            "exp": expire,
            "iat": now.timestamp(),
            "type": "access",
            **(additional_claims or {}),
        }

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(self, user_id: str) -> str:
        """
        Create JWT refresh token

        Args:
            user_id: User ID

        Returns:
            JWT refresh token
        """
        now = datetime.datetime.utcnow()
        expire = now + datetime.timedelta(days=self.refresh_expire_days)

        to_encode = {
            "sub": user_id,
            "exp": expire,
            "iat": now.timestamp(),
            "type": "refresh",
        }

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def decode_token(self, token: str) -> TokenPayload:
        """
        Decode and validate JWT token

        Args:
            token: JWT token

        Returns:
            TokenPayload

        Raises:
            JWTError: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )
            return TokenPayload(
                sub=payload["sub"],
                exp=datetime.datetime.fromtimestamp(payload["exp"]),
                iat=datetime.datetime.fromtimestamp(payload["iat"]),
                type=payload.get("type", "access"),
            )
        except JWTError as e:
            logger.warning(f"Token decode failed: {e}")
            raise

    def verify_token(self, token: str, token_type: str = "access") -> TokenPayload:
        """
        Verify JWT token and return payload

        Args:
            token: JWT token
            token_type: Expected token type (access or refresh)

        Returns:
            TokenPayload

        Raises:
            JWTError: If token is invalid, expired, or wrong type
        """
        payload = self.decode_token(token)

        if payload.type != token_type:
            raise JWTError(f"Invalid token type: expected {token_type}, got {payload.type}")

        return payload


# Singleton instances
_jwt_manager: Optional[JWTManager] = None


def get_jwt_manager() -> JWTManager:
    """Get global JWT manager instance"""
    global _jwt_manager
    if _jwt_manager is None:
        _jwt_manager = JWTManager()
    return _jwt_manager


# Convenience functions
def create_access_token(user_id: str, additional_claims: dict | None = None) -> str:
    """Create access token"""
    return get_jwt_manager().create_access_token(user_id, additional_claims)


def create_refresh_token(user_id: str) -> str:
    """Create refresh token"""
    return get_jwt_manager().create_refresh_token(user_id)


def verify_token(token: str, token_type: str = "access") -> TokenPayload:
    """Verify token"""
    return get_jwt_manager().verify_token(token, token_type)
