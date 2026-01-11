# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Integration tests for agent interactions using mock agents.

Tests the complete interaction patterns between multiple mock agents
through the Round Table collaboration bus.
"""

import asyncio
import time

import pytest

from tests.mock_agents import (
    AgentRegistry,
    MockAgent,
    create_calculator_agent,
    create_developer_agent,
    create_echo_agent,
    create_researcher_agent,
)
from tests.mock_agents.scenarios import (
    BroadcastScenario,
    CalculatorWorkflow,
    MultiAgentCollaboration,
    ResearchAnalysisWorkflow,
    TwoAgentCommunication,
    run_scenario,
)


class TestMockAgent:
    """Test basic MockAgent functionality."""

    @pytest.mark.asyncio
    async def test_mock_agent_creation(self):
        """Test creating a mock agent."""
        agent = MockAgent(
            agent_id="test_agent",
            behavior={"ping": {"type": "pong"}},
            name="Test Agent",
        )

        assert agent.agent_id == "test_agent"
        assert agent.name == "Test Agent"
        assert agent.behavior == {"ping": {"type": "pong"}}

    @pytest.mark.asyncio
    async def test_mock_agent_message_handling(self):
        """Test message handling."""
        from tests.mock_agents.base import AgentMessage

        agent = MockAgent(
            agent_id="test_agent",
            behavior={"greeting": {"response": "hello"}},
        )

        message = AgentMessage(
            from_agent="other_agent",
            to_agent="test_agent",
            content={"type": "greeting", "text": "hi"},
        )

        response = agent.handle_message(message)

        assert response is not None
        assert response["response"] == "hello"
        assert response["from_agent"] == "other_agent"

    @pytest.mark.asyncio
    async def test_mock_agent_message_history(self):
        """Test message history tracking."""
        from tests.mock_agents.base import AgentMessage

        agent = MockAgent(agent_id="test_agent")

        # Send some messages
        for i in range(3):
            message = AgentMessage(
                from_agent=f"sender_{i}",
                to_agent="test_agent",
                content={"type": "test", "index": i},
            )
            agent.handle_message(message)

        assert agent.get_message_count() == 3

        # Clear history
        agent.clear_history()
        assert agent.get_message_count() == 0

    @pytest.mark.asyncio
    async def test_mock_agent_custom_handler(self):
        """Test custom message handler."""
        from tests.mock_agents.base import AgentMessage

        agent = MockAgent(agent_id="test_agent")

        # Register custom handler
        def custom_handler(message):
            return {
                "custom": True,
                "received": message.content,
            }

        agent.on_message("custom", custom_handler)

        # Test the handler
        message = AgentMessage(
            from_agent="sender",
            to_agent="test_agent",
            content={"type": "custom", "data": "test"},
        )

        response = agent.handle_message(message)

        assert response["custom"] is True
        assert response["received"]["data"] == "test"


class TestPredefinedAgents:
    """Test predefined agent types."""

    @pytest.mark.asyncio
    async def test_echo_agent(self):
        """Test echo agent behavior."""
        from tests.mock_agents.base import AgentMessage

        agent = create_echo_agent("echo_agent")
        message = AgentMessage(
            from_agent="sender",
            to_agent="echo_agent",
            content={"type": "echo", "text": "test message"},
        )

        response = agent.handle_message(message)

        assert response is not None
        assert response["action"] == "echo"
        assert response["echoed_content"]["text"] == "test message"

    @pytest.mark.asyncio
    async def test_calculator_agent(self):
        """Test calculator agent behavior."""
        from tests.mock_agents.base import AgentMessage

        agent = create_calculator_agent("calc_agent")

        # Test addition
        message = AgentMessage(
            from_agent="sender",
            to_agent="calc_agent",
            content={"type": "calculate", "operation": "add", "a": 5, "b": 3},
        )

        response = agent.handle_message(message)

        assert response is not None
        assert response["operation"] == "add"
        assert response["result"] == 8

    @pytest.mark.asyncio
    async def test_researcher_agent(self):
        """Test researcher agent behavior."""
        from tests.mock_agents.base import AgentMessage

        agent = create_researcher_agent("researcher")

        message = AgentMessage(
            from_agent="sender",
            to_agent="researcher",
            content={"type": "research", "topic": "AI agents", "depth": "basic"},
        )

        response = agent.handle_message(message)

        assert response is not None
        assert response["status"] == "completed"
        assert response["topic"] == "AI agents"
        assert "findings" in response

    @pytest.mark.asyncio
    async def test_developer_agent(self):
        """Test developer agent behavior."""
        from tests.mock_agents.base import AgentMessage

        agent = create_developer_agent("developer")

        message = AgentMessage(
            from_agent="sender",
            to_agent="developer",
            content={"type": "develop", "task": "Build API", "language": "python"},
        )

        response = agent.handle_message(message)

        assert response is not None
        assert response["status"] == "completed"
        assert response["task"] == "Build API"


class TestAgentRegistry:
    """Test AgentRegistry functionality."""

    @pytest.mark.asyncio
    async def test_registry_create_agent(self, test_client):
        """Test creating an agent through registry."""
        # Register user and get token
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"},
        )
        token = register_response.json()["data"]["access_token"]

        # Create workspace
        workspace_response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": "Test Workspace"},
            headers={"Authorization": f"Bearer {token}"},
        )
        workspace_id = workspace_response.json()["data"]["workspace_id"]

        # Create registry
        registry = AgentRegistry(
            api_base_url="http://test/api/v1",
            access_token=token,
            workspace_id=workspace_id,
        )

        # Note: This will fail to connect since we're using a test URL
        # but we can test the creation logic
        agent = MockAgent("test_agent", name="Test Agent")
        registry.agents["test_agent"] = agent

        assert registry.get_agent("test_agent") == agent
        assert len(registry.list_agents()) == 1

    @pytest.mark.asyncio
    async def test_registry_disconnect_all(self, test_client):
        """Test disconnecting all agents."""
        # Register user
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"},
        )
        token = register_response.json()["data"]["access_token"]

        # Create workspace
        workspace_response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": "Test Workspace"},
            headers={"Authorization": f"Bearer {token}"},
        )
        workspace_id = workspace_response.json()["data"]["workspace_id"]

        registry = AgentRegistry(
            api_base_url="http://test/api/v1",
            access_token=token,
            workspace_id=workspace_id,
        )

        # Add mock agents
        for i in range(3):
            agent = MockAgent(f"agent_{i}", name=f"Agent {i}")
            registry.agents[f"agent_{i}"] = agent

        assert len(registry.agents) == 3

        # Disconnect all
        await registry.disconnect_all()

        assert len(registry.agents) == 0


class TestTwoAgentCommunication:
    """Test two-agent communication scenario."""

    @pytest.mark.asyncio
    async def test_two_agent_communication_scenario(self, test_client):
        """Test the two-agent communication scenario."""
        # Register user
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"},
        )
        token = register_response.json()["data"]["access_token"]

        # Create workspace
        workspace_response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": "Test Workspace"},
            headers={"Authorization": f"Bearer {token}"},
        )
        workspace_id = workspace_response.json()["data"]["workspace_id"]

        # Create registry
        registry = AgentRegistry(
            api_base_url="http://test/api/v1",
            access_token=token,
            workspace_id=workspace_id,
        )

        # Create scenario
        scenario = TwoAgentCommunication()

        # Setup mock agents (without actually connecting)
        agent_a = create_echo_agent("agent_a", "Agent A")
        agent_b = create_echo_agent("agent_b", "Agent B")
        agent_a.sandbox_id = "sb_agent_a"
        agent_b.sandbox_id = "sb_agent_b"

        registry.agents = {"agent_a": agent_a, "agent_b": agent_b}

        # Simulate message
        from tests.mock_agents.base import AgentMessage

        message = AgentMessage(
            from_agent="agent_a",
            to_agent="agent_b",
            content={"type": "echo", "text": "Hello!"},
        )

        response = agent_b.handle_message(message)

        assert response is not None
        assert response["action"] == "echo"
        assert agent_b.get_message_count() == 1


class TestMultiAgentCollaboration:
    """Test multi-agent collaboration scenario."""

    @pytest.mark.asyncio
    async def test_multi_agent_scenario(self):
        """Test multi-agent collaboration scenario setup."""
        scenario = MultiAgentCollaboration(num_agents=3)

        assert scenario.name == "Multi-Agent Collaboration"
        assert scenario.num_agents == 3

    @pytest.mark.asyncio
    async def test_multi_agent_agent_types(self):
        """Test creating agents with different types."""
        scenario = MultiAgentCollaboration(
            num_agents=4,
            agent_types=["echo", "calculator", "researcher", "developer"],
        )

        assert scenario.num_agents == 4
        assert len(scenario.agent_types) == 4


class TestBroadcastScenario:
    """Test broadcast messaging scenario."""

    @pytest.mark.asyncio
    async def test_broadcast_scenario(self):
        """Test broadcast scenario setup."""
        scenario = BroadcastScenario(num_agents=4)

        assert scenario.name == "Broadcast Messaging"
        assert scenario.num_agents == 4


class TestCalculatorWorkflow:
    """Test calculator workflow scenario."""

    @pytest.mark.asyncio
    async def test_calculator_workflow(self):
        """Test calculator workflow scenario."""
        from tests.mock_agents.base import AgentMessage

        scenario = CalculatorWorkflow()

        # Create agents
        calculator = create_calculator_agent("calculator", "Calculator")
        client = create_echo_agent("client", "Client")

        # Test calculation
        test_message = AgentMessage(
            from_agent="client",
            to_agent="calculator",
            content={"type": "calculate", "operation": "add", "a": 10, "b": 5},
        )

        response = calculator.handle_message(test_message)

        assert response is not None
        assert response["result"] == 15
        assert calculator.get_message_count() == 1


class TestResearchAnalysisWorkflow:
    """Test research-analysis workflow scenario."""

    @pytest.mark.asyncio
    async def test_research_analysis_workflow(self):
        """Test research-analysis workflow scenario."""
        from tests.mock_agents.base import AgentMessage

        scenario = ResearchAnalysisWorkflow()

        # Create agents
        researcher = create_researcher_agent("researcher", "Researcher")
        developer = create_developer_agent("developer", "Developer")

        # Test research
        research_message = AgentMessage(
            from_agent="client",
            to_agent="researcher",
            content={"type": "research", "topic": "Test topic", "depth": "basic"},
        )

        research_response = researcher.handle_message(research_message)

        assert research_response is not None
        assert research_response["status"] == "completed"

        # Test development
        dev_message = AgentMessage(
            from_agent="client",
            to_agent="developer",
            content={
                "type": "develop",
                "task": "Build feature",
                "language": "python",
            },
        )

        dev_response = developer.handle_message(dev_message)

        assert dev_response is not None
        assert dev_response["status"] == "completed"


class TestScenarioRunner:
    """Test scenario execution utilities."""

    @pytest.mark.asyncio
    async def test_run_scenario(self):
        """Test running a scenario through the scenario runner."""
        # Create a mock registry
        registry = AgentRegistry(
            api_base_url="http://test/api/v1",
            access_token="test_token",
            workspace_id="test_workspace",
        )

        # Add mock agents directly without connecting
        agent_a = create_echo_agent("agent_a", "Agent A")
        agent_b = create_echo_agent("agent_b", "Agent B")
        # Set mock sandbox IDs
        agent_a.sandbox_id = "sb_agent_a"
        agent_b.sandbox_id = "sb_agent_b"
        registry.agents = {"agent_a": agent_a, "agent_b": agent_b}

        # Run two-agent scenario (with mock setup)
        scenario = TwoAgentCommunication()
        scenario.registry = registry
        scenario.agents = registry.agents

        # Mock send_to to avoid HTTP calls
        async def mock_send(to_sandbox_id, content, message_type="request"):
            return {"success": True, "mock": True}

        agent_a.send_to = mock_send

        result = await scenario.run()

        assert result is not None
        assert "scenario" in result

    @pytest.mark.asyncio
    async def test_invalid_scenario(self):
        """Test running an invalid scenario."""
        registry = AgentRegistry(
            api_base_url="http://test/api/v1",
            access_token="test_token",
            workspace_id="test_workspace",
        )

        with pytest.raises(ValueError, match="Unknown scenario"):
            await run_scenario("invalid_scenario", registry)


class TestAgentIntegration:
    """Integration tests for agent interactions."""

    @pytest.mark.asyncio
    async def test_full_agent_lifecycle(self, test_client):
        """Test complete agent lifecycle with actual API."""
        # Register user
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"},
        )
        token = register_response.json()["data"]["access_token"]

        # Create workspace
        workspace_response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": "Test Workspace"},
            headers={"Authorization": f"Bearer {token}"},
        )
        workspace_id = workspace_response.json()["data"]["workspace_id"]

        # Create sandbox (representing an agent)
        sandbox_response = await test_client.post(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            json={
                "name": "Test Agent",
                "agent_config": {"primary_agent": "mock", "model": "mock"},
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert sandbox_response.status_code == 201
        sandbox_id = sandbox_response.json()["data"]["sandbox_id"]

        # Get sandbox status
        status_response = await test_client.get(
            f"/api/v1/sandboxes/{sandbox_id}/status",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert status_response.status_code == 200
        assert "data" in status_response.json()

    @pytest.mark.asyncio
    async def test_multi_sandbox_communication(self, test_client):
        """Test communication between multiple sandboxes."""
        # Register user
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"},
        )
        token = register_response.json()["data"]["access_token"]

        # Create workspace
        workspace_response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": "Test Workspace"},
            headers={"Authorization": f"Bearer {token}"},
        )
        workspace_id = workspace_response.json()["data"]["workspace_id"]

        # Create two sandboxes
        sb1_response = await test_client.post(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            json={
                "name": "Agent 1",
                "agent_config": {"primary_agent": "mock", "model": "mock"},
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        sandbox1_id = sb1_response.json()["data"]["sandbox_id"]

        sb2_response = await test_client.post(
            f"/api/v1/sandboxes/{workspace_id}/sandboxes",
            json={
                "name": "Agent 2",
                "agent_config": {"primary_agent": "mock", "model": "mock"},
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        sandbox2_id = sb2_response.json()["data"]["sandbox_id"]

        # Send message from agent 1 to agent 2
        message_response = await test_client.post(
            f"/api/v1/messages/sandboxes/{sandbox1_id}/messages",
            json={
                "to_sandbox_id": sandbox2_id,
                "content": {"type": "greeting", "text": "Hello from Agent 1"},
                "message_type": "request",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert message_response.status_code == 202
        data = message_response.json()
        assert data["success"] is True
        assert data["data"]["from_sandbox_id"] == sandbox1_id
        assert data["data"]["to_sandbox_id"] == sandbox2_id

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_sandboxes(self, test_client):
        """Test broadcasting to multiple sandboxes."""
        # Register user
        email = f"test_{int(time.time())}@example.com"
        register_response = await test_client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "testpass123"},
        )
        token = register_response.json()["data"]["access_token"]

        # Create workspace
        workspace_response = await test_client.post(
            "/api/v1/workspaces",
            json={"name": "Test Workspace"},
            headers={"Authorization": f"Bearer {token}"},
        )
        workspace_id = workspace_response.json()["data"]["workspace_id"]

        # Create three sandboxes
        for i in range(3):
            await test_client.post(
                f"/api/v1/sandboxes/{workspace_id}/sandboxes",
                json={
                    "name": f"Agent {i+1}",
                    "agent_config": {"primary_agent": "mock", "model": "mock"},
                },
                headers={"Authorization": f"Bearer {token}"},
            )

        # Broadcast message
        broadcast_response = await test_client.post(
            f"/api/v1/messages/workspaces/{workspace_id}/broadcast",
            json={
                "content": {
                    "type": "announcement",
                    "message": "Broadcast to all agents",
                },
                "message_type": "notification",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        assert broadcast_response.status_code == 202
        data = broadcast_response.json()
        assert data["data"]["broadcast_to"] == 3
