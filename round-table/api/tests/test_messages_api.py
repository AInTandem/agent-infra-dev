# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Integration tests for Message API endpoints
"""

import pytest
import time


class TestSendMessage:
    """Test sending messages between sandboxes"""

    @pytest.mark.asyncio
    async def test_send_message_success(self, test_client):
        """Test sending a message from one sandbox to another"""
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

        # Create two sandboxes
        sandbox1_response = await test_client.post(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            json={
                "name": "Agent 1",
                "agent_config": {"primary_agent": "researcher", "model": "gpt-4"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        sandbox1_id = sandbox1_response.json()["data"]["sandbox_id"]

        sandbox2_response = await test_client.post(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            json={
                "name": "Agent 2",
                "agent_config": {"primary_agent": "analyst", "model": "gpt-4"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        sandbox2_id = sandbox2_response.json()["data"]["sandbox_id"]

        # Send message
        response = await test_client.post(
            f"/api/v1/messages/sandboxes/{sandbox1_id}/messages",
            json={
                "to_sandbox_id": sandbox2_id,
                "content": {"type": "greeting", "text": "Hello from Agent 1"},
                "message_type": "request"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 202
        data = response.json()
        assert data["success"] is True
        assert data["data"]["from_sandbox_id"] == sandbox1_id
        assert data["data"]["to_sandbox_id"] == sandbox2_id
        assert data["data"]["content"]["text"] == "Hello from Agent 1"
        assert "message_id" in data["data"]

    @pytest.mark.asyncio
    async def test_send_message_sandbox_not_found(self, test_client):
        """Test sending message from non-existent sandbox"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        response = await test_client.post(
            "/api/v1/messages/sandboxes/sb_nonexistent/messages",
            json={
                "to_sandbox_id": "sb_other",
                "content": {"test": "data"},
                "message_type": "request"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_send_message_recipient_not_found(self, test_client):
        """Test sending message to non-existent sandbox"""
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
                "name": "Agent 1",
                "agent_config": {"primary_agent": "researcher", "model": "gpt-4"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        sandbox_id = sandbox_response.json()["data"]["sandbox_id"]

        # Send to non-existent recipient
        response = await test_client.post(
            f"/api/v1/messages/sandboxes/{sandbox_id}/messages",
            json={
                "to_sandbox_id": "sb_nonexistent",
                "content": {"test": "data"},
                "message_type": "request"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404


class TestGetMessages:
    """Test getting messages"""

    @pytest.mark.asyncio
    async def test_get_sandbox_messages(self, test_client):
        """Test getting messages for a sandbox"""
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
        sandbox_response = await test_client.post(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            json={
                "name": "Test Agent",
                "agent_config": {"primary_agent": "researcher", "model": "gpt-4"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        sandbox_id = sandbox_response.json()["data"]["sandbox_id"]

        # Get messages (should be empty initially)
        response = await test_client.get(
            f"/api/v1/messages/sandboxes/{sandbox_id}/messages",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["messages"] == []
        assert data["data"]["count"] == 0

    @pytest.mark.asyncio
    async def test_get_sandbox_messages_sandbox_not_found(self, test_client):
        """Test getting messages for non-existent sandbox"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        response = await test_client.get(
            "/api/v1/messages/sandboxes/sb_nonexistent/messages",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404


class TestBroadcastMessage:
    """Test broadcasting messages"""

    @pytest.mark.asyncio
    async def test_broadcast_message_success(self, test_client):
        """Test broadcasting a message to all sandboxes in workspace"""
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

        # Create two sandboxes
        await test_client.post(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            json={
                "name": "Agent 1",
                "agent_config": {"primary_agent": "researcher", "model": "gpt-4"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        await test_client.post(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            json={
                "name": "Agent 2",
                "agent_config": {"primary_agent": "analyst", "model": "gpt-4"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        # Broadcast message
        response = await test_client.post(
            f"/api/v1/messages/workspaces/{workspace_id}/broadcast",
            json={
                "content": {"type": "announcement", "message": "Hello everyone!"},
                "message_type": "notification"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 202
        data = response.json()
        assert data["success"] is True
        assert data["data"]["workspace_id"] == workspace_id
        assert data["data"]["broadcast_to"] == 2

    @pytest.mark.asyncio
    async def test_broadcast_message_empty_workspace(self, test_client):
        """Test broadcasting to workspace with no sandboxes"""
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

        # Broadcast to empty workspace
        response = await test_client.post(
            f"/api/v1/messages/workspaces/{workspace_id}/broadcast",
            json={
                "content": {"test": "data"},
                "message_type": "notification"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_broadcast_message_workspace_not_found(self, test_client):
        """Test broadcasting to non-existent workspace"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        response = await test_client.post(
            "/api/v1/messages/workspaces/ws_nonexistent/broadcast",
            json={
                "content": {"test": "data"},
                "message_type": "notification"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404


class TestGetMessage:
    """Test getting individual message details"""

    @pytest.mark.asyncio
    async def test_get_message_details(self, test_client):
        """Test getting message details by ID"""
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

        # Create two sandboxes
        sandbox1_response = await test_client.post(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            json={
                "name": "Agent 1",
                "agent_config": {"primary_agent": "researcher", "model": "gpt-4"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        sandbox1_id = sandbox1_response.json()["data"]["sandbox_id"]

        sandbox2_response = await test_client.post(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            json={
                "name": "Agent 2",
                "agent_config": {"primary_agent": "analyst", "model": "gpt-4"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        sandbox2_id = sandbox2_response.json()["data"]["sandbox_id"]

        # Send message
        send_response = await test_client.post(
            f"/api/v1/messages/sandboxes/{sandbox1_id}/messages",
            json={
                "to_sandbox_id": sandbox2_id,
                "content": {"type": "test", "data": "test data"},
                "message_type": "request"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        message_id = send_response.json()["data"]["message_id"]

        # Get message details
        response = await test_client.get(
            f"/api/v1/messages/messages/{message_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["message_id"] == message_id
        assert data["data"]["content"]["data"] == "test data"

    @pytest.mark.asyncio
    async def test_get_message_not_found(self, test_client):
        """Test getting non-existent message"""
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"}
        )
        token = register_response.json()["data"]["access_token"]

        response = await test_client.get(
            "/api/v1/messages/messages/msg_nonexistent",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404
