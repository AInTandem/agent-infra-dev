# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Integration tests for System API endpoints
"""

import pytest


class TestHealthCheck:
    """Test health check endpoint"""

    @pytest.mark.asyncio
    async def test_health_check(self, test_client):
        """Test health check endpoint"""
        response = await test_client.get("/api/v1/system/health")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "status" in data["data"]
        assert data["data"]["status"] in ["healthy", "degraded", "unhealthy"]
        assert "version" in data["data"]
        assert "database" in data["data"]
        assert "message_bus" in data["data"]


class TestSystemInfo:
    """Test system information endpoint"""

    @pytest.mark.asyncio
    async def test_system_info_unauthenticated(self, test_client):
        """Test system info without authentication"""
        response = await test_client.get("/api/v1/system/info")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "name" in data["data"]
        assert "version" in data["data"]
        assert data["data"]["authenticated"] is False

    @pytest.mark.asyncio
    async def test_system_info_authenticated(self, test_client):
        """Test system info with authentication"""
        import time

        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        response = await test_client.get(
            "/api/v1/system/info",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["authenticated"] is True
        assert "user_id" in data["data"]
        assert data["data"]["email"] == email


class TestAggregateMetrics:
    """Test aggregate metrics endpoint"""

    @pytest.mark.asyncio
    async def test_get_aggregate_metrics(self, test_client):
        """Test getting aggregate metrics for workspace"""
        import time

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

        # Create a sandbox
        await test_client.post(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            json={
                "name": "Test Agent",
                "agent_config": {"primary_agent": "researcher", "model": "gpt-4"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        # Get aggregate metrics
        response = await test_client.get(
            f"/api/v1/system/workspaces/{workspace_id}/metrics/aggregate",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["workspace_id"] == workspace_id
        assert "sandboxes" in data["data"]
        assert data["data"]["sandboxes"]["total"] >= 1
        assert "messages" in data["data"]
        assert "timestamp" in data["data"]

    @pytest.mark.asyncio
    async def test_get_aggregate_metrics_workspace_not_found(self, test_client):
        """Test getting metrics for non-existent workspace"""
        import time

        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        response = await test_client.get(
            "/api/v1/system/workspaces/ws_nonexistent/metrics/aggregate",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_aggregate_metrics_unauthorized(self, test_client):
        """Test getting metrics without authentication"""
        response = await test_client.get(
            "/api/v1/system/workspaces/ws_test/metrics/aggregate"
        )

        assert response.status_code == 401
