# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Integration tests for Sandbox API endpoints
"""

import pytest
import time


class TestSandboxCreate:
    """Test sandbox creation endpoint"""

    @pytest.mark.asyncio
    async def test_create_sandbox_success(self, test_client):
        """Test successful sandbox creation"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        # Create workspace
        workspace_response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": "Test Workspace"},
            headers={"Authorization": f"Bearer {token}"}
        )
        workspace_id = workspace_response.json()["data"]["workspace_id"]

        # Create sandbox
        response = await test_client.post(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            json={
                "name": "Test Agent",
                "agent_config": {
                    "primary_agent": "researcher",
                    "model": "gpt-4",
                    "max_tokens": 4096,
                }
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Test Agent"
        assert data["data"]["status"] == "provisioning"
        assert data["data"]["agent_config"]["primary_agent"] == "researcher"
        assert "sandbox_id" in data["data"]

    @pytest.mark.asyncio
    async def test_create_sandbox_workspace_not_found(self, test_client):
        """Test creating sandbox in non-existent workspace"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        response = await test_client.post(
            "/api/v1/sandboxes/ws_nonexistent/sandboxes",
            json={
                "name": "Test Agent",
                "agent_config": {"primary_agent": "researcher", "model": "gpt-4"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_sandbox_invalid_config(self, test_client):
        """Test creating sandbox with invalid agent config"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        # Create workspace
        workspace_response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": "Test Workspace"},
            headers={"Authorization": f"Bearer {token}"}
        )
        workspace_id = workspace_response.json()["data"]["workspace_id"]

        # Create sandbox with invalid model (empty string)
        response = await test_client.post(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            json={
                "name": "Test Agent",
                "agent_config": {"primary_agent": "", "model": "gpt-4"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 422  # Validation error


class TestSandboxList:
    """Test sandbox listing endpoint"""

    @pytest.mark.asyncio
    async def test_list_sandboxes_empty(self, test_client):
        """Test listing sandboxes in empty workspace"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        # Create workspace
        workspace_response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": "Test Workspace"},
            headers={"Authorization": f"Bearer {token}"}
        )
        workspace_id = workspace_response.json()["data"]["workspace_id"]

        # List sandboxes
        response = await test_client.get(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["sandboxes"] == []
        assert data["data"]["count"] == 0

    @pytest.mark.asyncio
    async def test_list_sandboxes_with_data(self, test_client):
        """Test listing sandboxes with existing sandboxes"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        # Create workspace
        workspace_response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": "Test Workspace"},
            headers={"Authorization": f"Bearer {token}"}
        )
        workspace_id = workspace_response.json()["data"]["workspace_id"]

        # Create sandbox
        await test_client.post(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            json={
                "name": "Agent 1",
                "agent_config": {"primary_agent": "researcher", "model": "gpt-4"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        # List sandboxes
        response = await test_client.get(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["count"] == 1
        assert data["data"]["sandboxes"][0]["name"] == "Agent 1"


class TestSandboxGet:
    """Test getting sandbox details"""

    @pytest.mark.asyncio
    async def test_get_sandbox_success(self, test_client):
        """Test getting sandbox details"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        # Create workspace and sandbox
        workspace_response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": "Test Workspace"},
            headers={"Authorization": f"Bearer {token}"}
        )
        workspace_id = workspace_response.json()["data"]["workspace_id"]

        sandbox_response = await test_client.post(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            json={
                "name": "Test Agent",
                "agent_config": {"primary_agent": "researcher", "model": "gpt-4"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        sandbox_id = sandbox_response.json()["data"]["sandbox_id"]

        # Get sandbox
        response = await test_client.get(
            f"/api/v1/sandboxes/{sandbox_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["sandbox_id"] == sandbox_id
        assert data["data"]["name"] == "Test Agent"

    @pytest.mark.asyncio
    async def test_get_sandbox_not_found(self, test_client):
        """Test getting non-existent sandbox"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        response = await test_client.get(
            "/api/v1/sandboxes/sb_nonexistent",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404


class TestSandboxLifecycle:
    """Test sandbox lifecycle management"""

    @pytest.mark.asyncio
    async def test_start_sandbox(self, test_client):
        """Test starting a sandbox"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        # Create workspace and sandbox
        workspace_response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": "Test Workspace"},
            headers={"Authorization": f"Bearer {token}"}
        )
        workspace_id = workspace_response.json()["data"]["workspace_id"]

        sandbox_response = await test_client.post(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            json={
                "name": "Test Agent",
                "agent_config": {"primary_agent": "researcher", "model": "gpt-4"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        sandbox_id = sandbox_response.json()["data"]["sandbox_id"]

        # Start sandbox
        response = await test_client.post(
            f"/api/v1/sandboxes/{sandbox_id}/start",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "running"

    @pytest.mark.asyncio
    async def test_stop_sandbox(self, test_client):
        """Test stopping a sandbox"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        # Create workspace and sandbox
        workspace_response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": "Test Workspace"},
            headers={"Authorization": f"Bearer {token}"}
        )
        workspace_id = workspace_response.json()["data"]["workspace_id"]

        sandbox_response = await test_client.post(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            json={
                "name": "Test Agent",
                "agent_config": {"primary_agent": "researcher", "model": "gpt-4"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        sandbox_id = sandbox_response.json()["data"]["sandbox_id"]

        # Stop sandbox
        response = await test_client.post(
            f"/api/v1/sandboxes/{sandbox_id}/stop",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "stopped"

    @pytest.mark.asyncio
    async def test_delete_sandbox(self, test_client):
        """Test deleting a sandbox"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        # Create workspace and sandbox
        workspace_response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": "Test Workspace"},
            headers={"Authorization": f"Bearer {token}"}
        )
        workspace_id = workspace_response.json()["data"]["workspace_id"]

        sandbox_response = await test_client.post(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            json={
                "name": "To Delete",
                "agent_config": {"primary_agent": "researcher", "model": "gpt-4"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        sandbox_id = sandbox_response.json()["data"]["sandbox_id"]

        # Delete sandbox
        response = await test_client.delete(
            f"/api/v1/sandboxes/{sandbox_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 204

        # Verify it's deleted
        get_response = await test_client.get(
            f"/api/v1/sandboxes/{sandbox_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert get_response.status_code == 404


class TestSandboxStatus:
    """Test sandbox status endpoint"""

    @pytest.mark.asyncio
    async def test_get_sandbox_status(self, test_client):
        """Test getting sandbox status"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        # Create workspace and sandbox
        workspace_response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": "Test Workspace"},
            headers={"Authorization": f"Bearer {token}"}
        )
        workspace_id = workspace_response.json()["data"]["workspace_id"]

        sandbox_response = await test_client.post(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            json={
                "name": "Test Agent",
                "agent_config": {"primary_agent": "researcher", "model": "gpt-4"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        sandbox_id = sandbox_response.json()["data"]["sandbox_id"]

        # Get status
        response = await test_client.get(
            f"/api/v1/sandboxes/{sandbox_id}/status",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "status" in data["data"]
        assert "sandbox_id" in data["data"]


class TestSandboxLogs:
    """Test sandbox logs endpoint"""

    @pytest.mark.asyncio
    async def test_get_sandbox_logs(self, test_client):
        """Test getting sandbox logs (placeholder)"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        # Create workspace and sandbox
        workspace_response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": "Test Workspace"},
            headers={"Authorization": f"Bearer {token}"}
        )
        workspace_id = workspace_response.json()["data"]["workspace_id"]

        sandbox_response = await test_client.post(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            json={
                "name": "Test Agent",
                "agent_config": {"primary_agent": "researcher", "model": "gpt-4"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        sandbox_id = sandbox_response.json()["data"]["sandbox_id"]

        # Get logs
        response = await test_client.get(
            f"/api/v1/sandboxes/{sandbox_id}/logs",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Placeholder returns empty logs
        assert data["data"]["logs"] == []


class TestSandboxMetrics:
    """Test sandbox metrics endpoint"""

    @pytest.mark.asyncio
    async def test_get_sandbox_metrics(self, test_client):
        """Test getting sandbox metrics (placeholder)"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        # Create workspace and sandbox
        workspace_response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": "Test Workspace"},
            headers={"Authorization": f"Bearer {token}"}
        )
        workspace_id = workspace_response.json()["data"]["workspace_id"]

        sandbox_response = await test_client.post(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            json={
                "name": "Test Agent",
                "agent_config": {"primary_agent": "researcher", "model": "gpt-4"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        sandbox_id = sandbox_response.json()["data"]["sandbox_id"]

        # Get metrics
        response = await test_client.get(
            f"/api/v1/sandboxes/{sandbox_id}/metrics",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Placeholder returns zero metrics
        assert "metrics" in data["data"]
        assert data["data"]["sandbox_id"] == sandbox_id
