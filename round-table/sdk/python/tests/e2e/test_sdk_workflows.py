# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
End-to-End workflow tests using the Python SDK.

These tests demonstrate real-world usage patterns of the Round Table SDK.
"""

from __future__ import annotations

import asyncio
import os
import pytest

from roundtable import RoundTableClient
from roundtable.exceptions import NotFoundError, ValidationError


# Test API key - in production this would come from environment
TEST_API_KEY = os.getenv("ROUND_TABLE_API_KEY", "test-api-key")
TEST_BASE_URL = os.getenv(
    "ROUND_TABLE_BASE_URL", "http://localhost:8000/api/v1"
)


@pytest.mark.e2e
@pytest.mark.skipif(
    os.getenv("RUN_E2E_TESTS") != "1",
    reason="Set RUN_E2E_TESTS=1 to run E2E tests",
)
class TestSDKWorkflows:
    """
    Test complete workflows using the Python SDK.
    """

    async def test_complete_collaboration_workflow(self):
        """
        Complete workflow: Workspace -> Sandboxes -> Collaboration -> Cleanup

        This demonstrates a realistic multi-agent collaboration scenario.
        """
        async with RoundTableClient(
            api_key=TEST_API_KEY,
            base_url=TEST_BASE_URL,
        ) as client:
            # Step 1: Create workspace
            workspace = await client.workspaces.create(
                name="sdk-test-project",
                description="E2E test project",
            )
            assert workspace.workspace_id.startswith("ws_")
            assert workspace.name == "sdk-test-project"

            # Step 2: Create researcher sandbox
            researcher = await client.sandboxes.create(
                workspace_id=workspace.workspace_id,
                name="researcher",
                agent_config={
                    "primary_agent": "researcher",
                    "model": "gpt-4",
                    "temperature": 0.7,
                },
            )
            assert researcher.sandbox_id.startswith("sb_")
            assert researcher.name == "researcher"

            # Step 3: Create developer sandbox
            developer = await client.sandboxes.create(
                workspace_id=workspace.workspace_id,
                name="developer",
                agent_config={
                    "primary_agent": "developer",
                    "model": "gpt-4",
                    "temperature": 0.5,
                },
            )
            assert developer.sandbox_id.startswith("sb_")

            # Step 4: Start researcher sandbox
            started_researcher = await client.sandboxes.start(
                researcher.sandbox_id
            )
            assert started_researcher.status in ["running", "starting"]

            # Step 5: Discover agents
            agents = await client.collaborations.discover_agents(
                workspace.workspace_id
            )
            assert agents.count >= 1
            assert len(agents.agents) >= 1

            # Step 6: Orchestrate collaboration
            collaboration = await client.collaborations.orchestrate(
                workspace_id=workspace.workspace_id,
                task="Implement a user authentication system",
                participants=[researcher.sandbox_id, developer.sandbox_id],
                mode="orchestrated",
                config={
                    "max_duration": 300,
                    "timeout": 30,
                },
            )
            assert collaboration.collaboration_id.startswith("collab_")
            assert collaboration.status in ["pending", "in_progress"]

            # Step 7: Check collaboration status
            status = await client.collaborations.get_collaboration(
                collaboration.collaboration_id
            )
            assert status.collaboration_id == collaboration.collaboration_id

            # Step 8: Send message between sandboxes
            await client.messages.send(
                from_sandbox_id=researcher.sandbox_id,
                to_sandbox_id=developer.sandbox_id,
                content={
                    "type": "task_update",
                    "message": "Starting research phase",
                },
            )

            # Step 9: Get messages
            messages = await client.messages.list(developer.sandbox_id)
            assert len(messages.messages) >= 1

            # Step 10: Cleanup
            await client.sandboxes.stop(researcher.sandbox_id)
            await client.sandboxes.delete(researcher.sandbox_id)
            await client.workspaces.delete(workspace.workspace_id)

    async def test_workspace_lifecycle_workflow(self):
        """
        Test complete workspace lifecycle.
        """
        async with RoundTableClient(
            api_key=TEST_API_KEY,
            base_url=TEST_BASE_URL,
        ) as client:
            # Create
            workspace = await client.workspaces.create(
                name="lifecycle-test",
                description="Testing workspace lifecycle",
            )
            workspace_id = workspace.workspace_id

            # Read
            fetched = await client.workspaces.get(workspace_id)
            assert fetched.workspace_id == workspace_id
            assert fetched.name == "lifecycle-test"

            # Update
            updated = await client.workspaces.update(
                workspace_id,
                name="lifecycle-test-updated",
                description="Updated description",
            )
            assert updated.name == "lifecycle-test-updated"

            # List
            workspaces = await client.workspaces.list()
            assert len(workspaces.workspaces) >= 1

            # Delete
            await client.workspaces.delete(workspace_id)

            # Verify deletion
            with pytest.raises(NotFoundError):
                await client.workspaces.get(workspace_id)

    async def test_sandbox_lifecycle_workflow(self):
        """
        Test complete sandbox lifecycle.
        """
        async with RoundTableClient(
            api_key=TEST_API_KEY,
            base_url=TEST_BASE_URL,
        ) as client:
            # Create workspace first
            workspace = await client.workspaces.create(
                name="sandbox-lifecycle-test"
            )

            # Create sandbox
            sandbox = await client.sandboxes.create(
                workspace_id=workspace.workspace_id,
                name="test-agent",
                agent_config={
                    "primary_agent": "tester",
                    "model": "gpt-4",
                },
            )
            sandbox_id = sandbox.sandbox_id

            # Get sandbox details
            fetched = await client.sandboxes.get(sandbox_id)
            assert fetched.sandbox_id == sandbox_id

            # Start sandbox
            started = await client.sandboxes.start(sandbox_id)
            assert started.status in ["running", "starting"]

            # Get status
            status = await client.sandboxes.status(sandbox_id)
            assert status.status in ["running", "starting"]

            # Get metrics
            metrics = await client.sandboxes.metrics(sandbox_id)
            assert metrics.sandbox_id == sandbox_id

            # Stop sandbox
            stopped = await client.sandboxes.stop(sandbox_id)
            assert stopped.status == "stopped"

            # Delete sandbox
            await client.sandboxes.delete(sandbox_id)

            # Verify deletion
            with pytest.raises(NotFoundError):
                await client.sandboxes.get(sandbox_id)

            # Cleanup workspace
            await client.workspaces.delete(workspace.workspace_id)

    async def test_message_workflow(self):
        """
        Test message sending and receiving workflow.
        """
        async with RoundTableClient(
            api_key=TEST_API_KEY,
            base_url=TEST_BASE_URL,
        ) as client:
            # Setup workspace and sandboxes
            workspace = await client.workspaces.create(name="message-test")

            sender = await client.sandboxes.create(
                workspace_id=workspace.workspace_id,
                name="sender",
                agent_config={"primary_agent": "agent1", "model": "gpt-4"},
            )

            receiver = await client.sandboxes.create(
                workspace_id=workspace.workspace_id,
                name="receiver",
                agent_config={"primary_agent": "agent2", "model": "gpt-4"},
            )

            # Send message
            message = await client.messages.send(
                from_sandbox_id=sender.sandbox_id,
                to_sandbox_id=receiver.sandbox_id,
                content={
                    "type": "request",
                    "action": "process_data",
                    "data": {"key": "value"},
                },
            )
            assert message.message_id.startswith("msg_")

            # Get message details
            fetched = await client.messages.get(message.message_id)
            assert fetched.message_id == message.message_id

            # List messages for receiver
            messages = await client.messages.list(receiver.sandbox_id)
            assert len(messages.messages) >= 1

            # Broadcast message to workspace
            broadcast = await client.messages.broadcast(
                workspace_id=workspace.workspace_id,
                from_sandbox_id=sender.sandbox_id,
                content={
                    "type": "announcement",
                    "message": "Hello everyone!",
                },
            )
            assert broadcast.message_id.startswith("msg_")

            # Cleanup
            await client.sandboxes.delete(sender.sandbox_id)
            await client.sandboxes.delete(receiver.sandbox_id)
            await client.workspaces.delete(workspace.workspace_id)

    async def test_system_monitoring_workflow(self):
        """
        Test system monitoring and health checks.
        """
        async with RoundTableClient(
            api_key=TEST_API_KEY,
            base_url=TEST_BASE_URL,
        ) as client:
            # Health check
            health = await client.health_check()
            assert health.status in ["healthy", "degraded"]

            # System info
            info = await client.system_info()
            assert info.version is not None

            # Create workspace for metrics
            workspace = await client.workspaces.create(name="metrics-test")

            # Create sandbox to generate activity
            sandbox = await client.sandboxes.create(
                workspace_id=workspace.workspace_id,
                name="metrics-agent",
                agent_config={"primary_agent": "agent", "model": "gpt-4"},
            )

            # Get aggregate metrics
            metrics = await client.aggregate_metrics(workspace.workspace_id)
            assert metrics.workspace_id == workspace.workspace_id
            assert metrics.total_sandboxes >= 1

            # Cleanup
            await client.sandboxes.delete(sandbox.sandbox_id)
            await client.workspaces.delete(workspace.workspace_id)

    async def test_error_handling_workflow(self):
        """
        Test error handling patterns.
        """
        async with RoundTableClient(
            api_key=TEST_API_KEY,
            base_url=TEST_BASE_URL,
        ) as client:
            # Test not found error
            with pytest.raises(NotFoundError):
                await client.workspaces.get("ws_nonexistent")

            # Test validation error
            with pytest.raises(ValidationError):
                await client.workspaces.create(
                    name="",  # Empty name should fail validation
                )

            # Test with invalid sandbox ID
            workspace = await client.workspaces.create(name="error-test")
            with pytest.raises(NotFoundError):
                await client.sandboxes.get("sb_nonexistent")

            # Cleanup
            await client.workspaces.delete(workspace.workspace_id)


@pytest.mark.e2e
@pytest.mark.skipif(
    os.getenv("RUN_E2E_TESTS") != "1",
    reason="Set RUN_E2E_TESTS=1 to run E2E tests",
)
class TestSDKPatterns:
    """
    Test common usage patterns with the SDK.
    """

    async def test_context_manager_pattern(self):
        """
        Test using SDK with async context manager.
        """
        # This pattern ensures proper cleanup
        async with RoundTableClient(
            api_key=TEST_API_KEY,
            base_url=TEST_BASE_URL,
        ) as client:
            workspace = await client.workspaces.create(name="context-test")
            assert workspace.workspace_id.startswith("ws_")
        # Client is automatically closed here

    async def test_retry_pattern(self):
        """
        Test retry pattern for transient failures.
        """
        async with RoundTableClient(
            api_key=TEST_API_KEY,
            base_url=TEST_BASE_URL,
            timeout=60.0,  # Longer timeout for retries
        ) as client:
            # Create workspace
            workspace = await client.workspaces.create(name="retry-test")

            # Start sandbox (may need retry if not ready)
            sandbox = await client.sandboxes.create(
                workspace_id=workspace.workspace_id,
                name="retry-agent",
                agent_config={"primary_agent": "agent", "model": "gpt-4"},
            )

            # Retry logic for starting
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    started = await client.sandboxes.start(sandbox.sandbox_id)
                    if started.status in ["running", "starting"]:
                        break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(1)

            # Cleanup
            await client.sandboxes.delete(sandbox.sandbox_id)
            await client.workspaces.delete(workspace.workspace_id)

    async def test_batch_operations_pattern(self):
        """
        Test batch operations pattern.
        """
        async with RoundTableClient(
            api_key=TEST_API_KEY,
            base_url=TEST_BASE_URL,
        ) as client:
            # Create workspace
            workspace = await client.workspaces.create(name="batch-test")

            # Create multiple sandboxes concurrently
            sandbox_tasks = [
                client.sandboxes.create(
                    workspace_id=workspace.workspace_id,
                    name=f"agent-{i}",
                    agent_config={
                        "primary_agent": f"agent_{i}",
                        "model": "gpt-4",
                    },
                )
                for i in range(3)
            ]
            sandboxes = await asyncio.gather(*sandbox_tasks)

            assert len(sandboxes) == 3

            # Start all sandboxes concurrently
            start_tasks = [
                client.sandboxes.start(sb.sandbox_id) for sb in sandboxes
            ]
            await asyncio.gather(*start_tasks)

            # Cleanup all concurrently
            delete_tasks = [
                client.sandboxes.delete(sb.sandbox_id) for sb in sandboxes
            ]
            await asyncio.gather(*delete_tasks)

            await client.workspaces.delete(workspace.workspace_id)
