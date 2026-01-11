# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Unit tests for Round Table Python SDK.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRoundTableClient:
    """Test main RoundTableClient."""

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test client initialization."""
        from roundtable import RoundTableClient

        client = RoundTableClient(api_key="test-key")

        assert client.config.api_key == "test-key"
        assert "localhost:8000" in client.config.base_url

        await client.close()

    @pytest.mark.asyncio
    async def test_client_from_config(self):
        """Test client initialization from config."""
        from roundtable import RoundTableClient, RoundTableConfig

        config = RoundTableConfig(
            api_key="test-key",
            base_url="http://example.com/api/v1",
        )
        client = RoundTableClient(config=config)

        assert client.config.api_key == "test-key"
        assert "example.com" in client.config.base_url

        await client.close()

    @pytest.mark.asyncio
    async def test_client_context_manager(self):
        """Test client as async context manager."""
        from roundtable import RoundTableClient

        async with RoundTableClient(api_key="test-key") as client:
            assert client is not None

    @pytest.mark.asyncio
    async def test_workspace_property(self):
        """Test workspaces property."""
        from roundtable import RoundTableClient

        client = RoundTableClient(api_key="test-key")

        assert client.workspaces is not None
        assert client.workspaces._client is not None

        await client.close()

    @pytest.mark.asyncio
    async def test_sandboxes_property(self):
        """Test sandboxes property."""
        from roundtable import RoundTableClient

        client = RoundTableClient(api_key="test-key")

        assert client.sandboxes is not None
        assert client.sandboxes._client is not None

        await client.close()

    @pytest.mark.asyncio
    async def test_messages_property(self):
        """Test messages property."""
        from roundtable import RoundTableClient

        client = RoundTableClient(api_key="test-key")

        assert client.messages is not None
        assert client.messages._client is not None

        await client.close()

    @pytest.mark.asyncio
    async def test_collaborations_property(self):
        """Test collaborations property."""
        from roundtable import RoundTableClient

        client = RoundTableClient(api_key="test-key")

        assert client.collaborations is not None
        assert client.collaborations._client is not None

        await client.close()


class TestWorkspaceClient:
    """Test workspace client operations."""

    @pytest.mark.asyncio
    async def test_list_workspaces(self):
        """Test listing workspaces."""
        from roundtable import RoundTableClient

        client = RoundTableClient(api_key="test-key")

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "workspaces": [
                    {
                        "workspace_id": "ws_123",
                        "user_id": "user_1",
                        "name": "Test Workspace",
                        "description": "Test description",
                        "settings": {
                            "max_sandboxes": 10,
                            "auto_cleanup": True,
                            "retention_days": 30,
                            "collaboration_policy": {},
                        },
                        "is_active": True,
                        "created_at": "2025-01-01T00:00:00Z",
                        "updated_at": "2025-01-01T00:00:00Z",
                    }
                ],
                "count": 1,
                "offset": 0,
                "limit": 100,
            }
        }

        with patch.object(client._client, "request", new=AsyncMock(return_value=mock_response)):
            workspaces = await client.workspaces.list()

            assert workspaces.count == 1
            assert len(workspaces.workspaces) == 1
            assert workspaces.workspaces[0].name == "Test Workspace"

        await client.close()

    @pytest.mark.asyncio
    async def test_create_workspace(self):
        """Test creating a workspace."""
        from roundtable import RoundTableClient

        client = RoundTableClient(api_key="test-key")

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "workspace_id": "ws_123",
                "user_id": "user_1",
                "name": "New Workspace",
                "description": "A new workspace",
                "settings": {
                    "max_sandboxes": 10,
                    "auto_cleanup": True,
                    "retention_days": 30,
                    "collaboration_policy": {},
                },
                "is_active": True,
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }
        }

        with patch.object(client._client, "request", new=AsyncMock(return_value=mock_response)):
            workspace = await client.workspaces.create(
                name="New Workspace",
                description="A new workspace"
            )

            assert workspace.workspace_id == "ws_123"
            assert workspace.name == "New Workspace"

        await client.close()

    @pytest.mark.asyncio
    async def test_get_workspace(self):
        """Test getting a workspace."""
        from roundtable import RoundTableClient

        client = RoundTableClient(api_key="test-key")

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "workspace_id": "ws_123",
                "user_id": "user_1",
                "name": "Test Workspace",
                "description": "Test description",
                "settings": {
                    "max_sandboxes": 10,
                    "auto_cleanup": True,
                    "retention_days": 30,
                    "collaboration_policy": {},
                },
                "is_active": True,
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }
        }

        with patch.object(client._client, "request", new=AsyncMock(return_value=mock_response)):
            workspace = await client.workspaces.get("ws_123")

            assert workspace.workspace_id == "ws_123"
            assert workspace.name == "Test Workspace"

        await client.close()


class TestSandboxClient:
    """Test sandbox client operations."""

    @pytest.mark.asyncio
    async def test_list_sandboxes(self):
        """Test listing sandboxes."""
        from roundtable import RoundTableClient

        client = RoundTableClient(api_key="test-key")

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "sandboxes": [
                    {
                        "sandbox_id": "sb_123",
                        "workspace_id": "ws_123",
                        "name": "Test Agent",
                        "status": "running",
                        "agent_config": {
                            "primary_agent": "researcher",
                            "model": "gpt-4",
                            "max_tokens": 4000,
                            "temperature": 0.7,
                            "tools": [],
                            "extra_config": {},
                        },
                        "connection_details": {},
                        "container_id": "container_123",
                        "created_at": "2025-01-01T00:00:00Z",
                        "updated_at": "2025-01-01T00:00:00Z",
                    }
                ],
                "count": 1,
                "offset": 0,
                "limit": 100,
            }
        }

        with patch.object(client._client, "request", new=AsyncMock(return_value=mock_response)):
            sandboxes = await client.sandboxes.list("ws_123")

            assert sandboxes.count == 1
            assert len(sandboxes.sandboxes) == 1
            assert sandboxes.sandboxes[0].name == "Test Agent"

        await client.close()

    @pytest.mark.asyncio
    async def test_create_sandbox(self):
        """Test creating a sandbox."""
        from roundtable import RoundTableClient

        client = RoundTableClient(api_key="test-key")

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "sandbox_id": "sb_123",
                "workspace_id": "ws_123",
                "name": "New Agent",
                "status": "provisioning",
                "agent_config": {
                    "primary_agent": "researcher",
                    "model": "gpt-4",
                    "max_tokens": 4000,
                    "temperature": 0.7,
                    "tools": [],
                    "extra_config": {},
                },
                "connection_details": {},
                "container_id": None,
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }
        }

        with patch.object(client._client, "request", new=AsyncMock(return_value=mock_response)):
            sandbox = await client.sandboxes.create(
                workspace_id="ws_123",
                name="New Agent",
                agent_config={
                    "primary_agent": "researcher",
                    "model": "gpt-4"
                }
            )

            assert sandbox.sandbox_id == "sb_123"
            assert sandbox.name == "New Agent"

        await client.close()


class TestMessageClient:
    """Test message client operations."""

    @pytest.mark.asyncio
    async def test_send_message(self):
        """Test sending a message."""
        from roundtable import RoundTableClient

        client = RoundTableClient(api_key="test-key")

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "message_id": "msg_123",
                "from_sandbox_id": "sb_1",
                "to_sandbox_id": "sb_2",
                "workspace_id": "ws_123",
                "content": {"type": "greeting", "text": "Hello"},
                "message_type": "request",
                "status": "pending",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }
        }

        with patch.object(client._client, "request", new=AsyncMock(return_value=mock_response)):
            message = await client.messages.send(
                from_sandbox_id="sb_1",
                to_sandbox_id="sb_2",
                content={"type": "greeting", "text": "Hello"}
            )

            assert message.message_id == "msg_123"
            assert message.from_sandbox_id == "sb_1"
            assert message.to_sandbox_id == "sb_2"

        await client.close()

    @pytest.mark.asyncio
    async def test_broadcast_message(self):
        """Test broadcasting a message."""
        from roundtable import RoundTableClient

        client = RoundTableClient(api_key="test-key")

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "broadcast_to": 3,
                "workspace_id": "ws_123",
            }
        }

        with patch.object(client._client, "request", new=AsyncMock(return_value=mock_response)):
            result = await client.messages.broadcast(
                workspace_id="ws_123",
                content={"type": "announcement", "message": "Hello all!"}
            )

            assert result["broadcast_to"] == 3

        await client.close()


class TestCollaborationClient:
    """Test collaboration client operations."""

    @pytest.mark.asyncio
    async def test_orchestrate_collaboration(self):
        """Test orchestrating a collaboration."""
        from roundtable import RoundTableClient

        client = RoundTableClient(api_key="test-key")

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "collaboration_id": "col_123",
                "workspace_id": "ws_123",
                "task": "Analyze data",
                "mode": "orchestrated",
                "participants": ["sb_1", "sb_2"],
                "status": "running",
                "config": {
                    "timeout": 300,
                    "max_iterations": 10,
                    "terminate_on_completion": True,
                    "save_history": True,
                    "extra_params": {},
                },
                "result": None,
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }
        }

        with patch.object(client._client, "request", new=AsyncMock(return_value=mock_response)):
            collab = await client.collaborations.orchestrate(
                workspace_id="ws_123",
                task="Analyze data",
                participants=["sb_1", "sb_2"]
            )

            assert collab.collaboration_id == "col_123"
            assert collab.task == "Analyze data"
            assert collab.status == "running"

        await client.close()

    @pytest.mark.asyncio
    async def test_discover_agents(self):
        """Test discovering agents."""
        from roundtable import RoundTableClient

        client = RoundTableClient(api_key="test-key")

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": True,
            "data": {
                "workspace_id": "ws_123",
                "count": 2,
                "agents": [
                    {
                        "sandbox_id": "sb_1",
                        "name": "Researcher",
                        "primary_agent": "researcher",
                        "model": "gpt-4",
                        "status": "running",
                        "capabilities": ["analysis", "research"],
                    },
                    {
                        "sandbox_id": "sb_2",
                        "name": "Analyst",
                        "primary_agent": "analyst",
                        "model": "gpt-4",
                        "status": "running",
                        "capabilities": ["analysis", "reporting"],
                    }
                ]
            }
        }

        with patch.object(client._client, "request", new=AsyncMock(return_value=mock_response)):
            agents = await client.collaborations.discover_agents("ws_123")

            assert agents.workspace_id == "ws_123"
            assert agents.count == 2
            assert len(agents.agents) == 2

        await client.close()
