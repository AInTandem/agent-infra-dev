# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Integration tests for Authentication API

Tests user registration, login, token refresh, and protected endpoints.
"""

import pytest
import time


class TestUserRegistration:
    """Test user registration endpoint"""

    @pytest.mark.asyncio
    async def test_register_user_success(self, test_client):
        """Test successful user registration"""
        # Use unique email to avoid conflicts
        unique_email = f"test_{int(time.time())}@example.com"

        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email,
                "password": "securepass123",
                "full_name": "Test User",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(self, test_client):
        """Test registration with duplicate email"""
        email = f"test_{int(time.time())}@example.com"

        # First registration
        await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "securepass123",
            }
        )

        # Duplicate registration
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "anotherpass123",
            }
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_user_invalid_email(self, test_client):
        """Test registration with invalid email"""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "securepass123",
            }
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_register_user_short_password(self, test_client):
        """Test registration with short password"""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "short",
            }
        )

        assert response.status_code == 422  # Validation error


class TestUserLogin:
    """Test user login endpoint"""

    @pytest.mark.asyncio
    async def test_login_success(self, test_client):
        """Test successful login"""
        email = f"test_{int(time.time())}@example.com"

        # First register
        await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "loginpass123",
            }
        )

        # Then login
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": "loginpass123",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]

    @pytest.mark.asyncio
    async def test_login_wrong_email(self, test_client):
        """Test login with wrong email"""
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "anypassword",
            }
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, test_client):
        """Test login with wrong password"""
        email = f"test_{int(time.time())}@example.com"

        # First register
        await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "correctpass",
            }
        )

        # Then login with wrong password
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": "wrongpass",
            }
        )

        assert response.status_code == 401


class TestTokenRefresh:
    """Test token refresh endpoint"""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, test_client):
        """Test successful token refresh"""
        email = f"test_{int(time.time())}@example.com"

        # Register to get tokens
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "refreshpass123",
            }
        )
        refresh_token = register_response.json()["data"]["refresh_token"]

        # Refresh access token
        response = await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, test_client):
        """Test refresh with invalid token"""
        response = await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"}
        )

        assert response.status_code == 401


class TestProtectedEndpoints:
    """Test protected endpoints with authentication"""

    @pytest.mark.asyncio
    async def test_get_current_user_info(self, test_client):
        """Test getting current user info"""
        email = f"test_{int(time.time())}@example.com"

        # Register to get token
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "testpass123",
                "full_name": "Test User",
            }
        )
        token = register_response.json()["data"]["access_token"]

        # Access protected endpoint
        response = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["email"] == email
        assert data["data"]["full_name"] == "Test User"

    @pytest.mark.asyncio
    async def test_protected_endpoint_no_token(self, test_client):
        """Test accessing protected endpoint without token"""
        response = await test_client.get("/api/v1/auth/me")

        # When no bearer token is provided, HTTPBearer returns 401
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_endpoint_invalid_token(self, test_client):
        """Test accessing protected endpoint with invalid token"""
        response = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token"}
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout(self, test_client):
        """Test logout endpoint"""
        email = f"test_{int(time.time())}@example.com"

        # Register to get token
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "logoutpass123",
            }
        )
        token = register_response.json()["data"]["access_token"]

        # Logout
        response = await test_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestOAuth2TokenEndpoint:
    """Test OAuth2 compatible token endpoint"""

    @pytest.mark.asyncio
    async def test_oauth2_token_flow(self, test_client):
        """Test OAuth2 password flow"""
        email = f"test_{int(time.time())}@example.com"

        # First register
        await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "oauth2pass123",
            }
        )

        # Get token via OAuth2 endpoint
        response = await test_client.post(
            "/api/v1/auth/token",
            data={
                "username": email,
                "password": "oauth2pass123",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
