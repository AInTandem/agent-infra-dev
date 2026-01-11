# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Unit tests for Authentication module

Tests JWT operations, password hashing, and auth dependencies.
"""

import pytest

from app.auth.jwt import JWTManager, create_access_token, create_refresh_token, verify_token, JWTError
from app.auth.security import hash_password, verify_password


class TestPasswordHashing:
    """Test password hashing and verification"""

    def test_hash_password(self):
        """Test password hashing"""
        password = "abc123"
        hashed = hash_password(password)

        assert hashed != password
        assert len(hashed) > 20  # bcrypt hashes are long
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "abc123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "abc123"
        wrong_password = "xyz789"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_hash_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes (salt)"""
        password1 = "abc123"
        password2 = "xyz789"

        hash1 = hash_password(password1)
        hash2 = hash_password(password2)

        assert hash1 != hash2

    def test_hash_same_password_different_hashes(self):
        """Test that same password produces different hashes (random salt)"""
        password = "abc123"

        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2  # Different due to random salt


class TestJWTOperations:
    """Test JWT token operations"""

    def test_create_access_token(self):
        """Test access token creation"""
        user_id = "usr_test123"
        token = create_access_token(user_id)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long

    def test_create_refresh_token(self):
        """Test refresh token creation"""
        user_id = "usr_test123"
        token = create_refresh_token(user_id)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50

    def test_verify_access_token(self):
        """Test access token verification"""
        user_id = "usr_test123"
        token = create_access_token(user_id)

        payload = verify_token(token, token_type="access")

        assert payload.sub == user_id
        assert payload.type == "access"

    def test_verify_refresh_token(self):
        """Test refresh token verification"""
        user_id = "usr_test123"
        token = create_refresh_token(user_id)

        payload = verify_token(token, token_type="refresh")

        assert payload.sub == user_id
        assert payload.type == "refresh"

    def test_verify_token_wrong_type(self):
        """Test token verification with wrong type"""
        user_id = "usr_test123"
        refresh_token = create_refresh_token(user_id)

        with pytest.raises(JWTError):
            verify_token(refresh_token, token_type="access")

    def test_verify_invalid_token(self):
        """Test token verification with invalid token"""
        invalid_token = "invalid.token.here"

        with pytest.raises(JWTError):
            verify_token(invalid_token)

    def test_jwt_manager_custom_settings(self):
        """Test JWT manager with custom settings"""
        manager = JWTManager(
            secret_key="custom-secret",
            access_expire_minutes=60,
            refresh_expire_days=30,
        )

        token = manager.create_access_token("usr_test")
        payload = manager.decode_token(token)

        assert payload.sub == "usr_test"
        assert payload.type == "access"


class TestJWTManager:
    """Test JWT Manager class"""

    def test_create_access_token_with_claims(self):
        """Test access token with additional claims"""
        manager = JWTManager()
        user_id = "usr_test123"
        claims = {"role": "admin", "scopes": ["read", "write"]}

        token = manager.create_access_token(user_id, additional_claims=claims)
        payload = manager.decode_token(token)

        assert payload.sub == user_id
        assert payload.type == "access"

    def test_token_expiration(self):
        """Test token expiration"""
        from app.config import settings

        manager = JWTManager(access_expire_minutes=1)
        user_id = "usr_test123"

        token = manager.create_access_token(user_id)
        payload = manager.decode_token(token)

        # Check expiration is set
        assert payload.exp is not None
        assert payload.iat is not None
