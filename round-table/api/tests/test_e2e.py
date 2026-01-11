# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
End-to-End tests for Round Table API.

These tests cover complete workflows across multiple components.
"""

from __future__ import annotations

import asyncio
import pytest
from httpx import AsyncClient, ASGITransport

from api.app.main import app


@pytest.mark.e2e
class TestCompleteCollaborationWorkflow:
    """
    Test complete collaboration workflow:
    Workspace creation -> Sandbox creation -> Orchestration -> Cleanup
    """

    async def test_researcher_developer_tester_workflow(self, async_client: AsyncClient):
        """
        E2E Test: Researcher -> Developer -> Tester workflow

        This test simulates a complete multi-agent collaboration scenario
        where a task flows through different agent roles.
        """
        # Step 1: Create workspace
        workspace_response = await async_client.post(
            "/api/v1/workspaces",
            json={
                "name": "project-x",
                "description": "Test project for e2e",
            },
        )
        assert workspace_response.status_code == 201
        workspace_data = workspace_response.json()["data"]
        workspace_id = workspace_data["workspace_id"]
        assert workspace_id.startswith("ws_")

        # Step 2: Create researcher sandbox
        researcher_response = await async_client.post(
            f"/api/v1/workspaces/{workspace_id}/sandboxes",
            json={
                "name": "researcher-agent",
                "description": "Research specialist",
                "agent_config": {
                    "primary_agent": "researcher",
                    "model": "gpt-4",
                    "temperature": 0.7,
                },
            },
        )
        assert researcher_response.status_code == 201
        researcher_data = researcher_response.json()["data"]
        researcher_sandbox_id = researcher_data["sandbox_id"]
        assert researcher_data["status"] in ["provisioning", "stopped"]

        # Step 3: Create developer sandbox
        developer_response = await async_client.post(
            f"/api/v1/workspaces/{workspace_id}/sandboxes",
            json={
                "name": "developer-agent",
                "description": "Development specialist",
                "agent_config": {
                    "primary_agent": "developer",
                    "model": "gpt-4",
                    "temperature": 0.5,
                },
            },
        )
        assert developer_response.status_code == 201
        developer_data = developer_response.json()["data"]
        developer_sandbox_id = developer_data["status"]

        # Step 4: Start the researcher sandbox
        start_response = await async_client.post(
            f"/api/v1/sandboxes/{researcher_sandbox_id}/start"
        )
        assert start_response.status_code in [200, 202]

        # Step 5: Discover agents in workspace
        discover_response = await async_client.get(
            f"/api/v1/workspaces/{workspace_id}/agents/discover"
        )
        assert discover_response.status_code == 200
        agents_data = discover_response.json()["data"]
        assert agents_data["count"] >= 1
        assert len(agents_data["agents"]) >= 1

        # Step 6: Orchestrate collaboration
        collab_response = await async_client.post(
            f"/api/v1/workspaces/{workspace_id}/collaboration/orchestrate",
            json={
                "task": "Build a REST API for user management",
                "mode": "orchestrated",
                "participants": [researcher_sandbox_id],
                "config": {
                    "max_duration": 300,
                    "timeout": 30,
                },
            },
        )
        assert collab_response.status_code in [201, 202]
        collab_data = collab_response.json()["data"]
        collaboration_id = collab_data["collaboration_id"]
        assert collab_data["status"] in ["pending", "in_progress"]

        # Step 7: Get collaboration status
        status_response = await async_client.get(
            f"/api/v1/collaborations/{collaboration_id}"
        )
        assert status_response.status_code == 200
        status_data = status_response.json()["data"]
        assert status_data["collaboration_id"] == collaboration_id
        assert status_data["task"] == "Build a REST API for user management"

        # Step 8: Cleanup - Stop sandbox
        stop_response = await async_client.post(
            f"/api/v1/sandboxes/{researcher_sandbox_id}/stop"
        )
        assert stop_response.status_code in [200, 202]

        # Step 9: Delete sandbox
        delete_response = await async_client.delete(
            f"/api/v1/sandboxes/{researcher_sandbox_id}"
        )
        assert delete_response.status_code in [200, 204]

        # Step 10: Delete workspace
        delete_ws_response = await async_client.delete(
            f"/api/v1/workspaces/{workspace_id}"
        )
        assert delete_ws_response.status_code in [200, 204]


@pytest.mark.e2e
class TestMessageFlowWorkflow:
    """
    Test complete message flow workflow.
    """

    async def test_message_send_receive_flow(self, async_client: AsyncClient):
        """
        E2E Test: Message send and receive flow
        """
        # Create workspace
        workspace_response = await async_client.post(
            "/api/v1/workspaces",
            json={"name": "message-test-workspace"},
        )
        workspace_id = workspace_response.json()["data"]["workspace_id"]

        # Create two sandboxes
        sandbox1_response = await async_client.post(
            f"/api/v1/workspaces/{workspace_id}/sandboxes",
            json={
                "name": "sender-agent",
                "agent_config": {"primary_agent": "agent1", "model": "gpt-4"},
            },
        )
        sandbox1_id = sandbox1_response.json()["data"]["sandbox_id"]

        sandbox2_response = await async_client.post(
            f"/api/v1/workspaces/{workspace_id}/sandboxes",
            json={
                "name": "receiver-agent",
                "agent_config": {"primary_agent": "agent2", "model": "gpt-4"},
            },
        )
        sandbox2_id = sandbox2_response.json()["data"]["sandbox_id"]

        # Send message from sandbox1 to sandbox2
        message_response = await async_client.post(
            f"/api/v1/sandboxes/{sandbox1_id}/messages",
            json={
                "to_sandbox_id": sandbox2_id,
                "content": {
                    "type": "greeting",
                    "text": "Hello from agent1!",
                },
            },
        )
        assert message_response.status_code in [201, 202]
        message_data = message_response.json()["data"]
        assert message_data["from_sandbox_id"] == sandbox1_id
        assert message_data["to_sandbox_id"] == sandbox2_id

        # Get messages for sandbox2
        messages_response = await async_client.get(
            f"/api/v1/sandboxes/{sandbox2_id}/messages"
        )
        assert messages_response.status_code == 200
        messages_data = messages_response.json()["data"]
        assert len(messages_data["messages"]) >= 1

        # Get specific message details
        message_id = message_data["message_id"]
        detail_response = await async_client.get(f"/api/v1/messages/{message_id}")
        assert detail_response.status_code == 200
        detail_data = detail_response.json()["data"]
        assert detail_data["message_id"] == message_id


@pytest.mark.e2e
class TestErrorScenarios:
    """
    Test error handling scenarios.
    """

    async def test_not_found_errors(self, async_client: AsyncClient):
        """
        E2E Test: 404 Not Found errors
        """
        # Non-existent workspace
        response = await async_client.get("/api/v1/workspaces/ws_nonexistent")
        assert response.status_code == 404

        # Non-existent sandbox
        response = await async_client.get("/api/v1/sandboxes/sb_nonexistent")
        assert response.status_code == 404

        # Non-existent collaboration
        response = await async_client.get("/api/v1/collaborations/coll_nonexistent")
        assert response.status_code == 404

    async def test_validation_errors(self, async_client: AsyncClient):
        """
        E2E Test: Validation errors
        """
        # Invalid workspace creation (missing name)
        response = await async_client.post(
            "/api/v1/workspaces",
            json={"description": "No name provided"},
        )
        assert response.status_code == 422

        # Invalid sandbox creation (missing agent_config)
        workspace_response = await async_client.post(
            "/api/v1/workspaces",
            json={"name": "test-workspace"},
        )
        workspace_id = workspace_response.json()["data"]["workspace_id"]

        response = await async_client.post(
            f"/api/v1/workspaces/{workspace_id}/sandboxes",
            json={"name": "test-sandbox"},
        )
        assert response.status_code == 422


@pytest.mark.e2e
class TestSystemHealthWorkflow:
    """
    Test system health and monitoring workflow.
    """

    async def test_health_check_flow(self, async_client: AsyncClient):
        """
        E2E Test: System health check flow
        """
        # Check system health
        health_response = await async_client.get("/api/v1/system/health")
        assert health_response.status_code == 200
        health_data = health_response.json()["data"]
        assert "status" in health_data
        assert health_data["status"] in ["healthy", "degraded"]

        # Get system info
        info_response = await async_client.get("/api/v1/system/info")
        assert info_response.status_code == 200
        info_data = info_response.json()["data"]
        assert "version" in info_data

        # Create workspace and check its metrics
        workspace_response = await async_client.post(
            "/api/v1/workspaces",
            json={"name": "metrics-test"},
        )
        workspace_id = workspace_response.json()["data"]["workspace_id"]

        # Get aggregate metrics
        metrics_response = await async_client.get(
            f"/api/v1/workspaces/{workspace_id}/metrics/aggregate"
        )
        assert metrics_response.status_code == 200
        metrics_data = metrics_response.json()["data"]
        assert "total_sandboxes" in metrics_data
        assert "total_messages" in metrics_data


@pytest.mark.e2e
class TestConfigurationWorkflow:
    """
    Test configuration management workflow.
    """

    async def test_workspace_configuration_flow(self, async_client: AsyncClient):
        """
        E2E Test: Workspace configuration management
        """
        # Create workspace
        workspace_response = await async_client.post(
            "/api/v1/workspaces",
            json={"name": "config-test"},
        )
        workspace_id = workspace_response.json()["data"]["workspace_id"]

        # Get initial configuration
        get_response = await async_client.get(
            f"/api/v1/workspaces/{workspace_id}/config"
        )
        assert get_response.status_code == 200
        config_data = get_response.json()["data"]
        assert "config" in config_data

        # Update configuration
        update_response = await async_client.put(
            f"/api/v1/workspaces/{workspace_id}/config",
            json={
                "config": {
                    "max_sandboxes": 10,
                    "max_agents_per_sandbox": 5,
                }
            },
        )
        assert update_response.status_code == 200

        # Verify configuration was updated
        verify_response = await async_client.get(
            f"/api/v1/workspaces/{workspace_id}/config"
        )
        assert verify_response.status_code == 200
        verify_data = verify_response.json()["data"]
        assert verify_data["config"]["max_sandboxes"] == 10


@pytest.fixture
async def async_client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client
