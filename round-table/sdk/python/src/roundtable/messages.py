# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Message client for Round Table SDK.

Provides methods for sending and managing messages between agents.
"""

from __future__ import annotations

import logging
from typing import Any

from roundtable.models import (
    AgentMessage,
    MessageListResponse,
)

logger = logging.getLogger(__name__)


class MessageClient:
    """
    Client for message operations.

    Provides methods for sending messages, getting messages,
    and broadcasting to workspaces.
    """

    def __init__(self, http_client: Any):
        """
        Initialize the message client.

        Args:
            http_client: HTTP client instance
        """
        self._client = http_client

    async def send(
        self,
        from_sandbox_id: str,
        to_sandbox_id: str,
        content: dict[str, Any],
        message_type: str = "request",
    ) -> AgentMessage:
        """
        Send a message from one sandbox to another.

        Args:
            from_sandbox_id: Sender sandbox ID
            to_sandbox_id: Recipient sandbox ID
            content: Message content
            message_type: Type of message (request, response, notification, etc.)

        Returns:
            Sent AgentMessage

        Raises:
            NotFoundError: If sandbox doesn't exist
            RoundTableError: If the request fails
        """
        request_data = {
            "to_sandbox_id": to_sandbox_id,
            "content": content,
            "message_type": message_type,
        }

        response = await self._request(
            "POST",
            f"/messages/sandboxes/{from_sandbox_id}/messages",
            json=request_data,
        )
        data = response["data"]

        return AgentMessage(**data)

    async def get_messages(
        self,
        sandbox_id: str,
        offset: int = 0,
        limit: int = 100,
    ) -> MessageListResponse:
        """
        Get messages for a sandbox.

        Args:
            sandbox_id: Sandbox ID
            offset: Pagination offset
            limit: Maximum number of messages to return

        Returns:
            MessageListResponse with list of messages

        Raises:
            NotFoundError: If sandbox doesn't exist
            RoundTableError: If the request fails
        """
        response = await self._request(
            "GET",
            f"/messages/sandboxes/{sandbox_id}/messages",
            params={"offset": offset, "limit": limit},
        )
        data = response["data"]

        messages = [AgentMessage(**msg) for msg in data["messages"]]

        return MessageListResponse(
            messages=messages,
            count=data["count"],
            offset=data.get("offset", offset),
            limit=data.get("limit", limit),
        )

    async def get_message(self, message_id: str) -> AgentMessage:
        """
        Get message details by ID.

        Args:
            message_id: Message ID

        Returns:
            AgentMessage details

        Raises:
            NotFoundError: If message doesn't exist
            RoundTableError: If the request fails
        """
        response = await self._request(
            "GET",
            f"/messages/messages/{message_id}",
        )
        data = response["data"]

        return AgentMessage(**data)

    async def broadcast(
        self,
        workspace_id: str,
        content: dict[str, Any],
        message_type: str = "notification",
    ) -> dict[str, Any]:
        """
        Broadcast a message to all sandboxes in a workspace.

        Args:
            workspace_id: Workspace ID
            content: Message content
            message_type: Type of message

        Returns:
            Broadcast response data

        Raises:
            NotFoundError: If workspace doesn't exist
            RoundTableError: If the request fails
        """
        request_data = {
            "content": content,
            "message_type": message_type,
        }

        response = await self._request(
            "POST",
            f"/messages/workspaces/{workspace_id}/broadcast",
            json=request_data,
        )

        return response["data"]

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Make an HTTP request.

        Args:
            method: HTTP method
            path: Request path
            **kwargs: Additional arguments

        Returns:
            Response data
        """
        url = path if path.startswith("http") else path

        response = await self._client.request(method, url, **kwargs)
        data = response.json()

        if not data.get("success") and response.status_code < 400:
            raise Exception(f"Request failed: {data.get('message')}")

        return data
