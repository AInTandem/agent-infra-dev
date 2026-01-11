# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Agent Registry

Provides helper functions for registering and managing mock agents
in test scenarios.
"""

import asyncio
import logging
from typing import Any

import httpx

from .base import AgentMessage, MockAgent
from .behaviors import (
    create_calculator_agent,
    create_developer_agent,
    create_echo_agent,
    create_researcher_agent,
)

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Registry for managing multiple mock agents.

    Provides convenient methods for creating, connecting, and managing
    groups of mock agents in test scenarios.
    """

    def __init__(self, api_base_url: str, access_token: str, workspace_id: str):
        """
        Initialize the agent registry.

        Args:
            api_base_url: Base URL of the Round Table API
            access_token: JWT access token for authentication
            workspace_id: Workspace ID for all agents
        """
        self.api_base_url = api_base_url.rstrip("/")
        self.access_token = access_token
        self.workspace_id = workspace_id
        self.agents: dict[str, MockAgent] = {}

    async def create_agent(
        self,
        agent_id: str,
        agent_type: str = "echo",
        name: str | None = None,
    ) -> MockAgent:
        """
        Create and register a new mock agent.

        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type of agent (echo, calculator, researcher, developer)
            name: Optional display name

        Returns:
            Created and connected MockAgent
        """
        # Create agent based on type
        if agent_type == "echo":
            agent = create_echo_agent(agent_id, name)
        elif agent_type == "calculator":
            agent = create_calculator_agent(agent_id, name)
        elif agent_type == "researcher":
            agent = create_researcher_agent(agent_id, name)
        elif agent_type == "developer":
            agent = create_developer_agent(agent_id, name)
        else:
            # Default to echo with custom behavior
            agent = MockAgent(agent_id, name=name or agent_id)

        # Connect to Round Table
        await agent.connect(self.api_base_url, self.access_token, self.workspace_id)

        # Register
        self.agents[agent_id] = agent

        logger.info(f"Created and registered agent {agent_id} of type {agent_type}")
        return agent

    async def create_agents(
        self,
        agent_configs: list[dict[str, Any]],
    ) -> list[MockAgent]:
        """
        Create multiple agents from configuration.

        Args:
            agent_configs: List of agent configuration dictionaries
                          Each dict should have: agent_id, agent_type, name (optional)

        Returns:
            List of created agents
        """
        agents = []
        for config in agent_configs:
            agent = await self.create_agent(
                agent_id=config["agent_id"],
                agent_type=config.get("agent_type", "echo"),
                name=config.get("name"),
            )
            agents.append(agent)

        logger.info(f"Created {len(agents)} agents")
        return agents

    def get_agent(self, agent_id: str) -> MockAgent | None:
        """Get an agent by ID."""
        return self.agents.get(agent_id)

    def list_agents(self) -> list[MockAgent]:
        """Get all registered agents."""
        return list(self.agents.values())

    async def disconnect_all(self) -> None:
        """Disconnect all agents."""
        for agent in self.agents.values():
            await agent.disconnect()

        self.agents.clear()
        logger.info("Disconnected all agents")

    async def send_message(
        self,
        from_agent_id: str,
        to_agent_id: str,
        content: dict[str, Any],
        message_type: str = "request",
    ) -> dict[str, Any] | None:
        """
        Send a message from one agent to another.

        Args:
            from_agent_id: Sender agent ID
            to_agent_id: Recipient agent ID
            content: Message content
            message_type: Type of message

        Returns:
            Response data or None
        """
        from_agent = self.get_agent(from_agent_id)
        if not from_agent:
            logger.error(f"Sender agent {from_agent_id} not found")
            return None

        return await from_agent.send_to(to_agent_id, content, message_type)

    async def broadcast(
        self,
        from_agent_id: str,
        content: dict[str, Any],
        message_type: str = "notification",
    ) -> dict[str, Any] | None:
        """
        Broadcast a message from an agent to the workspace.

        Args:
            from_agent_id: Sender agent ID
            content: Message content
            message_type: Type of message

        Returns:
            Response data or None
        """
        from_agent = self.get_agent(from_agent_id)
        if not from_agent:
            logger.error(f"Sender agent {from_agent_id} not found")
            return None

        return await from_agent.broadcast(self.workspace_id, content, message_type)

    def get_all_message_counts(self) -> dict[str, int]:
        """Get message count for all agents."""
        return {agent_id: agent.get_message_count() for agent_id, agent in self.agents.items()}

    def clear_all_histories(self) -> None:
        """Clear message history for all agents."""
        for agent in self.agents.values():
            agent.clear_history()

        logger.info("Cleared all agent message histories")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect_all()


class TestClient:
    """
    Test client for Round Table API.

    Provides helper methods for common test operations.
    """

    def __init__(self, api_base_url: str = "http://localhost:8000/api/v1"):
        """
        Initialize test client.

        Args:
            api_base_url: Base URL of the Round Table API
        """
        self.api_base_url = api_base_url.rstrip("/")
        self.http_client: httpx.AsyncClient | None = None
        self.access_token: str | None = None

    async def register_user(self, email: str, password: str) -> dict[str, Any]:
        """
        Register a new user.

        Args:
            email: User email
            password: User password

        Returns:
            Registration response data
        """
        if not self.http_client:
            self.http_client = httpx.AsyncClient(base_url=self.api_base_url)

        response = await self.http_client.post(
            "/auth/register",
            json={"email": email, "password": password},
        )

        if response.status_code == 201:
            data = response.json()
            self.access_token = data["data"]["access_token"]
            return data["data"]

        raise RuntimeError(f"Registration failed: {response.status_code}")

    async def create_workspace(self, name: str) -> dict[str, Any]:
        """
        Create a workspace.

        Args:
            name: Workspace name

        Returns:
            Workspace data
        """
        if not self.http_client or not self.access_token:
            raise RuntimeError("Not authenticated")

        response = await self.http_client.post(
            "/workspaces",
            json={"name": name},
            headers={"Authorization": f"Bearer {self.access_token}"},
        )

        if response.status_code == 201:
            return response.json()["data"]

        raise RuntimeError(f"Workspace creation failed: {response.status_code}")

    async def create_agent_registry(self, workspace_id: str) -> AgentRegistry:
        """
        Create an agent registry for the workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            AgentRegistry instance
        """
        return AgentRegistry(self.api_base_url, self.access_token, workspace_id)

    async def close(self) -> None:
        """Close the test client."""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.http_client = httpx.AsyncClient(base_url=self.api_base_url)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


async def setup_test_environment(
    api_base_url: str = "http://localhost:8000/api/v1",
) -> tuple[TestClient, AgentRegistry, dict[str, Any]]:
    """
    Set up a complete test environment with user, workspace, and agent registry.

    Args:
        api_base_url: Base URL of the Round Table API

    Returns:
        Tuple of (test_client, agent_registry, workspace_data)
    """
    import time

    async with TestClient(api_base_url) as client:
        # Register user
        email = f"test_{int(time.time())}@example.com"
        await client.register_user(email, "testpass123")

        # Create workspace
        workspace = await client.create_workspace("Test Workspace")

        # Create agent registry
        registry = await client.create_agent_registry(workspace["workspace_id"])

        return client, registry, workspace
