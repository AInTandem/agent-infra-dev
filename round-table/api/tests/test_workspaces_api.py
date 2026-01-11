# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Integration tests for Workspace API endpoints
"""

import pytest
import time


class TestWorkspaceList:
    """Test workspace listing endpoint"""

    @pytest.mark.asyncio
    async def test_list_workspaces_empty(self, test_client):
        """Test listing workspaces when user has none"""
        # Register and login to get token
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "testpass123",
                "full_name": "Test User",
            }
        )
        token = register_response.json()["data"]["access_token"]

        # List workspaces
        response = await test_client.get(
            "/api/v1/workspaces",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["workspaces"] == []
        assert data["data"]["count"] == 0

    @pytest.mark.asyncio
    async def test_list_workspaces_with_data(self, test_client):
        """Test listing workspaces with existing workspaces"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "testpass123",
                "full_name": "Test User",
            }
        )
        token = register_response.json()["data"]["access_token"]

        # Create a workspace first
        await test_client.post(
            "/api/v1/workspaces",
            json={"name": "Test Workspace"},
            headers={"Authorization": f"Bearer {token}"}
        )

        # List workspaces
        response = await test_client.get(
            "/api/v1/workspaces",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["count"] == 1
        assert data["data"]["workspaces"][0]["name"] == "Test Workspace"

    @pytest.mark.asyncio
    async def test_list_workspaces_unauthorized(self, test_client):
        """Test listing workspaces without authentication"""
        response = await test_client.get("/api/v1/workspaces")

        assert response.status_code == 401


class TestWorkspaceCreate:
    """Test workspace creation endpoint"""

    @pytest.mark.asyncio
    async def test_create_workspace_success(self, test_client):
        """Test successful workspace creation"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "testpass123",
                "full_name": "Test User",
            }
        )
        token = register_response.json()["data"]["access_token"]

        response = await test_client.post(
            "/api/v1/workspaces",
            json={
                "name": "My Research Workspace",
                "description": "For AI research",
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "My Research Workspace"
        assert data["data"]["description"] == "For AI research"
        assert data["data"]["user_id"] is not None
        assert "workspace_id" in data["data"]

    @pytest.mark.asyncio
    async def test_create_workspace_with_settings(self, test_client):
        """Test workspace creation with custom settings"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "testpass123",
            }
        )
        token = register_response.json()["data"]["access_token"]

        response = await test_client.post(
            "/api/v1/workspaces",
            json={
                "name": "Custom Workspace",
                "settings": {
                    "max_sandboxes": 20,
                    "auto_cleanup": False,
                    "retention_days": 90,
                }
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["settings"]["max_sandboxes"] == 20
        assert data["data"]["settings"]["auto_cleanup"] is False

    @pytest.mark.asyncio
    async def test_create_workspace_invalid_name(self, test_client):
        """Test workspace creation with invalid name"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": ""},  # Empty name
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 422  # Validation error


class TestWorkspaceGet:
    """Test getting workspace details"""

    @pytest.mark.asyncio
    async def test_get_workspace_success(self, test_client):
        """Test getting workspace details"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        # Create workspace
        create_response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": "Test Workspace"},
            headers={"Authorization": f"Bearer {token}"}
        )
        workspace_id = create_response.json()["data"]["workspace_id"]

        # Get workspace
        response = await test_client.get(
            f"/api/v1/workspaces/{workspace_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["workspace_id"] == workspace_id
        assert data["data"]["name"] == "Test Workspace"

    @pytest.mark.asyncio
    async def test_get_workspace_not_found(self, test_client):
        """Test getting non-existent workspace"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        response = await test_client.get(
            "/api/v1/workspaces/ws_nonexistent",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_workspace_unauthorized_user(self, test_client):
        """Test getting workspace owned by another user"""
        # Create two users
        email1 = f"user1_{int(time.time())}@example.com"
        email2 = f"user2_{int(time.time())}@example.com"

        user1_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email1, "password": "testpass123"}
        )
        user1_token = user1_response.json()["data"]["access_token"]

        user2_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email2, "password": "testpass123"}
        )
        user2_token = user2_response.json()["data"]["access_token"]

        # Create workspace as user1
        create_response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": "User1 Workspace"},
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        workspace_id = create_response.json()["data"]["workspace_id"]

        # Try to get as user2
        response = await test_client.get(
            f"/api/v1/workspaces/{workspace_id}",
            headers={"Authorization": f"Bearer {user2_token}"}
        )

        assert response.status_code == 403  # Forbidden (user2 can't see user1's workspace)


class TestWorkspaceUpdate:
    """Test workspace update endpoint"""

    @pytest.mark.asyncio
    async def test_update_workspace_name(self, test_client):
        """Test updating workspace name"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        # Create workspace
        create_response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": "Original Name"},
            headers={"Authorization": f"Bearer {token}"}
        )
        workspace_id = create_response.json()["data"]["workspace_id"]

        # Update workspace
        response = await test_client.put(
            f"/api/v1/workspaces/{workspace_id}",
            json={"name": "Updated Name"},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_workspace_not_found(self, test_client):
        """Test updating non-existent workspace"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        response = await test_client.put(
            "/api/v1/workspaces/ws_nonexistent",
            json={"name": "New Name"},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404


class TestWorkspaceDelete:
    """Test workspace deletion endpoint"""

    @pytest.mark.asyncio
    async def test_delete_workspace_success(self, test_client):
        """Test successful workspace deletion"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        # Create workspace
        create_response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": "To Delete"},
            headers={"Authorization": f"Bearer {token}"}
        )
        workspace_id = create_response.json()["data"]["workspace_id"]

        # Delete workspace
        response = await test_client.delete(
            f"/api/v1/workspaces/{workspace_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 204

        # Verify it's deleted
        get_response = await test_client.get(
            f"/api/v1/workspaces/{workspace_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_workspace_not_found(self, test_client):
        """Test deleting non-existent workspace"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        response = await test_client.delete(
            "/api/v1/workspaces/ws_nonexistent",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404


class TestWorkspaceConfig:
    """Test workspace configuration endpoints"""

    @pytest.mark.asyncio
    async def test_get_workspace_config(self, test_client):
        """Test getting workspace configuration"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        # Create workspace with custom settings
        create_response = await test_client.post(
            "/api/v1/workspaces",
            json={
                "name": "Config Test",
                "settings": {"max_sandboxes": 15}
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        workspace_id = create_response.json()["data"]["workspace_id"]

        # Get config
        response = await test_client.get(
            f"/api/v1/workspaces/{workspace_id}/config",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["max_sandboxes"] == 15

    @pytest.mark.asyncio
    async def test_update_workspace_config(self, test_client):
        """Test updating workspace configuration"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        # Create workspace
        create_response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": "Config Update Test"},
            headers={"Authorization": f"Bearer {token}"}
        )
        workspace_id = create_response.json()["data"]["workspace_id"]

        # Update config
        response = await test_client.put(
            f"/api/v1/workspaces/{workspace_id}/config",
            json={"max_sandboxes": 25, "auto_cleanup": False},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["max_sandboxes"] == 25
        assert data["data"]["auto_cleanup"] is False
