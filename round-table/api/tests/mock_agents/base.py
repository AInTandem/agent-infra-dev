# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Mock Agent Base Class

Provides a base class for creating deterministic mock agents for testing.
"""

import asyncio
import logging
from typing import Any, AsyncIterator, Callable, Optional

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AgentMessage(BaseModel):
    """Message sent between agents"""
    from_agent: str
    to_agent: str
    content: dict[str, Any] | None = None
    message_type: str = "request"
    timestamp: Optional[str] = None


class MockAgent:
    """
    Deterministic mock agent for testing Round Table interactions.

    The MockAgent can be configured with specific behaviors for different
    message types, allowing for deterministic testing of agent interactions.
    """

    def __init__(
        self,
        agent_id: str,
        behavior: dict[str, dict[str, Any]] | None = None,
        name: str | None = None,
        description: str = "",
    ):
        """
        Initialize a mock agent.

        Args:
            agent_id: Unique identifier for this agent
            behavior: Dictionary mapping message types to responses
                     Example: {"request": {"status": "acknowledged"}}
            name: Human-readable name (defaults to agent_id)
            description: Agent description
        """
        self.agent_id = agent_id
        self.name = name or agent_id
        self.description = description
        self.behavior = behavior or {}
        self.message_history: list[AgentMessage] = []
        self.http_client: httpx.AsyncClient | None = None
        self.api_base_url: str | None = None
        self.access_token: str | None = None
        self.workspace_id: str | None = None
        self.sandbox_id: str | None = None
        self._running = False
        self._message_handlers: dict[str, Callable[[AgentMessage], dict[str, Any] | None]] = {}

    async def connect(
        self,
        api_base_url: str,
        access_token: str,
        workspace_id: str | None = None,
    ) -> None:
        """
        Connect the agent to Round Table.

        Args:
            api_base_url: Base URL of the Round Table API
            access_token: JWT access token for authentication
            workspace_id: Optional workspace ID to join
        """
        self.api_base_url = api_base_url.rstrip("/")
        self.access_token = access_token
        self.workspace_id = workspace_id

        # Create HTTP client
        self.http_client = httpx.AsyncClient(
            base_url=self.api_base_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        logger.info(f"Agent {self.agent_id} connected to {self.api_base_url}")

        # Register/create sandbox if workspace provided
        if workspace_id:
            await self._register_sandbox()

    async def _register_sandbox(self) -> None:
        """Register this agent as a sandbox in the workspace."""
        if not self.workspace_id:
            return

        response = await self.http_client.post(
            f"/api/v1/sandboxes/{self.workspace_id}/sandboxes",
            json={
                "name": self.name,
                "agent_config": {
                    "primary_agent": "mock",
                    "model": "mock",
                },
            },
        )

        if response.status_code == 201:
            data = response.json()
            self.sandbox_id = data["data"]["sandbox_id"]
            logger.info(f"Agent {self.agent_id} registered as sandbox {self.sandbox_id}")
        else:
            logger.warning(f"Failed to register sandbox: {response.status_code}")

    async def disconnect(self) -> None:
        """Disconnect from Round Table."""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None

        self._running = False
        logger.info(f"Agent {self.agent_id} disconnected")

    async def send_to(
        self,
        to_agent_id: str,
        content: dict[str, Any],
        message_type: str = "request",
    ) -> dict[str, Any] | None:
        """
        Send a message to another agent.

        Args:
            to_agent_id: ID of the recipient agent
            content: Message content
            message_type: Type of message (request, response, notification, etc.)

        Returns:
            Response data if successful, None otherwise
        """
        if not self.http_client:
            raise RuntimeError("Agent not connected. Call connect() first.")

        if not self.sandbox_id:
            raise RuntimeError("Agent not registered as a sandbox")

        message = AgentMessage(
            from_agent=self.agent_id,
            to_agent=to_agent_id,
            content=content,
            message_type=message_type,
        )

        response = await self.http_client.post(
            f"/api/v1/messages/sandboxes/{self.sandbox_id}/messages",
            json={
                "to_sandbox_id": to_agent_id,
                "content": content,
                "message_type": message_type,
            },
        )

        if response.status_code == 202:
            data = response.json()
            logger.info(f"Agent {self.agent_id} sent message to {to_agent_id}")
            return data["data"]
        else:
            logger.error(f"Failed to send message: {response.status_code}")
            return None

    async def broadcast(
        self,
        workspace_id: str,
        content: dict[str, Any],
        message_type: str = "notification",
    ) -> dict[str, Any] | None:
        """
        Broadcast a message to all agents in a workspace.

        Args:
            workspace_id: ID of the workspace
            content: Message content
            message_type: Type of message

        Returns:
            Response data if successful, None otherwise
        """
        if not self.http_client:
            raise RuntimeError("Agent not connected. Call connect() first.")

        response = await self.http_client.post(
            f"/api/v1/messages/workspaces/{workspace_id}/broadcast",
            json={
                "content": content,
                "message_type": message_type,
            },
        )

        if response.status_code == 202:
            data = response.json()
            logger.info(f"Agent {self.agent_id} broadcast to workspace {workspace_id}")
            return data["data"]
        else:
            logger.error(f"Failed to broadcast: {response.status_code}")
            return None

    async def get_messages(self) -> list[dict[str, Any]]:
        """
        Get messages sent to this agent.

        Returns:
            List of messages
        """
        if not self.http_client or not self.sandbox_id:
            return []

        response = await self.http_client.get(
            f"/api/v1/messages/sandboxes/{self.sandbox_id}/messages"
        )

        if response.status_code == 200:
            data = response.json()
            return data["data"]["messages"]
        return []

    def handle_message(self, message: AgentMessage) -> dict[str, Any] | None:
        """
        Handle an incoming message and return a response.

        This method looks up the behavior for the message type and returns
        the configured response. Subclasses can override this for custom logic.

        Args:
            message: The incoming message

        Returns:
            Response dictionary or None
        """
        # Store message in history
        self.message_history.append(message)

        # Check for custom handler
        msg_type = message.content.get("type") if message.content else None
        if not msg_type:
            msg_type = message.message_type

        if msg_type in self._message_handlers:
            return self._message_handlers[msg_type](message)

        # Use configured behavior
        if msg_type in self.behavior:
            response = self.behavior[msg_type].copy()
            # Add context
            response["from_agent"] = message.from_agent
            response["original_content"] = message.content
            return response

        # Default response
        return {
            "status": "received",
            "from_agent": message.from_agent,
            "content": message.content,
        }

    def on_message(
        self, message_type: str, handler: Callable[[AgentMessage], dict[str, Any] | None]
    ) -> None:
        """
        Register a custom message handler.

        Args:
            message_type: Type of message to handle
            handler: Async handler function
        """
        self._message_handlers[message_type] = handler

    async def start(self) -> None:
        """Start the agent (placeholder for future implementation)."""
        self._running = True
        logger.info(f"Agent {self.agent_id} started")

    async def stop(self) -> None:
        """Stop the agent."""
        self._running = False
        logger.info(f"Agent {self.agent_id} stopped")

    def get_message_count(self) -> int:
        """Get the number of messages received."""
        return len(self.message_history)

    def get_messages_by_type(self, message_type: str) -> list[AgentMessage]:
        """Get all messages of a specific type."""
        return [
            msg
            for msg in self.message_history
            if msg.content.get("type") == message_type or msg.message_type == message_type
        ]

    def clear_history(self) -> None:
        """Clear message history."""
        self.message_history.clear()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    def __repr__(self) -> str:
        return f"MockAgent(id={self.agent_id}, name={self.name})"
