# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Integration tests for Collaboration API endpoints
"""

import pytest
import time


class TestOrchestrateCollaboration:
    """Test collaboration orchestration endpoint"""

    @pytest.mark.asyncio
    async def test_orchestrate_collaboration_success(self, test_client):
        """Test successful collaboration orchestration"""
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

        # Create sandboxes
        sandbox1_response = await test_client.post(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            json={
                "name": "Researcher",
                "agent_config": {"primary_agent": "researcher", "model": "gpt-4"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        sandbox1_id = sandbox1_response.json()["data"]["sandbox_id"]

        sandbox2_response = await test_client.post(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            json={
                "name": "Analyst",
                "agent_config": {"primary_agent": "analyst", "model": "gpt-4"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        sandbox2_id = sandbox2_response.json()["data"]["sandbox_id"]

        # Orchestrate collaboration
        response = await test_client.post(
            f"/api/v1/collaborations/workspaces/{workspace_id}/collaboration/orchestrate",
            json={
                "task": "Analyze the latest research data",
                "mode": "orchestrated",
                "participants": [sandbox1_id, sandbox2_id],
                "config": {"timeout": 300}
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 202
        data = response.json()
        assert data["success"] is True
        assert data["data"]["task"] == "Analyze the latest research data"
        assert data["data"]["mode"] == "orchestrated"
        assert len(data["data"]["participants"]) == 2
        assert "collaboration_id" in data["data"]
        assert data["data"]["status"] == "running"

    @pytest.mark.asyncio
    async def test_orchestrate_collaboration_workspace_not_found(self, test_client):
        """Test orchestrating collaboration in non-existent workspace"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        response = await test_client.post(
            "/api/v1/collaborations/workspaces/ws_nonexistent/collaboration/orchestrate",
            json={
                "task": "Test task",
                "mode": "orchestrated",
                "participants": ["sb_test"]
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_orchestrate_collaboration_invalid_participant(self, test_client):
        """Test orchestrating collaboration with non-existent participant"""
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

        # Orchestrate with non-existent participant
        response = await test_client.post(
            f"/api/v1/collaborations/workspaces/{workspace_id}/collaboration/orchestrate",
            json={
                "task": "Test task",
                "mode": "orchestrated",
                "participants": ["sb_nonexistent"]
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_orchestrate_collaboration_different_workspace(self, test_client):
        """Test orchestrating with participant from different workspace"""
        email1 = f"user1_{int(time.time())}@example.com"
        email2 = f"user2_{int(time.time())}@example.com"

        # Create two users
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

        # Create workspaces for each user
        ws1_response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": "Workspace 1"},
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        workspace1_id = ws1_response.json()["data"]["workspace_id"]

        ws2_response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": "Workspace 2"},
            headers={"Authorization": f"Bearer {user2_token}"}
        )
        workspace2_id = ws2_response.json()["data"]["workspace_id"]

        # Create sandbox in workspace 2
        sb2_response = await test_client.post(
            f"/api/v1/sandboxes/{workspace2_id}/sandboxes",
            json={
                "name": "Other Agent",
                "agent_config": {"primary_agent": "analyst", "model": "gpt-4"}
            },
            headers={"Authorization": f"Bearer {user2_token}"}
        )
        sandbox2_id = sb2_response.json()["data"]["sandbox_id"]

        # Try to orchestrate in workspace 1 with sandbox from workspace 2
        response = await test_client.post(
            f"/api/v1/collaborations/workspaces/{workspace1_id}/collaboration/orchestrate",
            json={
                "task": "Test task",
                "mode": "orchestrated",
                "participants": [sandbox2_id]
            },
            headers={"Authorization": f"Bearer {user1_token}"}
        )

        assert response.status_code == 400  # Bad request


class TestGetCollaboration:
    """Test getting collaboration status"""

    @pytest.mark.asyncio
    async def test_get_collaboration_status(self, test_client):
        """Test getting collaboration status"""
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

        # Orchestrate collaboration
        orchestrate_response = await test_client.post(
            f"/api/v1/collaborations/workspaces/{workspace_id}/collaboration/orchestrate",
            json={
                "task": "Test task",
                "mode": "peer_to_peer",
                "participants": [sandbox_id]
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        collaboration_id = orchestrate_response.json()["data"]["collaboration_id"]

        # Get collaboration status
        response = await test_client.get(
            f"/api/v1/collaborations/collaborations/{collaboration_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["collaboration_id"] == collaboration_id
        assert data["data"]["status"] == "running"

    @pytest.mark.asyncio
    async def test_get_collaboration_not_found(self, test_client):
        """Test getting non-existent collaboration"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        response = await test_client.get(
            "/api/v1/collaborations/collaborations/col_nonexistent",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404


class TestDiscoverAgents:
    """Test agent discovery endpoint"""

    @pytest.mark.asyncio
    async def test_discover_agents_success(self, test_client):
        """Test discovering agents in workspace"""
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

        # Create multiple sandboxes
        await test_client.post(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            json={
                "name": "Research Agent",
                "agent_config": {"primary_agent": "researcher", "model": "gpt-4"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        await test_client.post(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            json={
                "name": "Analysis Agent",
                "agent_config": {"primary_agent": "analyst", "model": "gpt-4"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        # Discover agents
        response = await test_client.get(
            f"/api/v1/collaborations/workspaces/{workspace_id}/agents/discover",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["workspace_id"] == workspace_id
        assert data["data"]["count"] == 2
        assert len(data["data"]["agents"]) == 2
        assert data["data"]["agents"][0]["name"] in ["Research Agent", "Analysis Agent"]
        assert "primary_agent" in data["data"]["agents"][0]

    @pytest.mark.asyncio
    async def test_discover_agents_empty_workspace(self, test_client):
        """Test discovering agents in empty workspace"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        # Create workspace
        workspace_response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": "Empty Workspace"},
            headers={"Authorization": f"Bearer {token}"}
        )
        workspace_id = workspace_response.json()["data"]["workspace_id"]

        # Discover agents (should be empty)
        response = await test_client.get(
            f"/api/v1/collaborations/workspaces/{workspace_id}/agents/discover",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["count"] == 0
        assert data["data"]["agents"] == []

    @pytest.mark.asyncio
    async def test_discover_agents_workspace_not_found(self, test_client):
        """Test discovering agents in non-existent workspace"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        response = await test_client.get(
            "/api/v1/collaborations/workspaces/ws_nonexistent/agents/discover",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404
