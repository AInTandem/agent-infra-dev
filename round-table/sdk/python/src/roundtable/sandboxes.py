# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Sandbox client for Round Table SDK.

Provides methods for managing sandboxes (agent containers).
"""

from __future__ import annotations

import logging
from typing import Any

from roundtable.models import (
    AgentConfig,
    Sandbox,
    SandboxListResponse,
    SandboxMetrics,
    SandboxStatus,
)

logger = logging.getLogger(__name__)


class SandboxClient:
    """
    Client for sandbox operations.

    Provides methods for creating, listing, getting, starting, stopping,
    and deleting sandboxes.
    """

    def __init__(self, http_client: Any):
        """
        Initialize the sandbox client.

        Args:
            http_client: HTTP client instance
        """
        self._client = http_client

    async def list(
        self,
        workspace_id: str,
        offset: int = 0,
        limit: int = 100,
    ) -> SandboxListResponse:
        """
        List all sandboxes in a workspace.

        Args:
            workspace_id: Workspace ID
            offset: Pagination offset
            limit: Maximum number of sandboxes to return

        Returns:
            SandboxListResponse with list of sandboxes

        Raises:
            RoundTableError: If the request fails
        """
        response = await self._request(
            "GET",
            f"/sandboxes/{workspace_id}/sandboxes",
            params={"offset": offset, "limit": limit},
        )
        data = response["data"]

        sandboxes = [Sandbox(**sb) for sb in data["sandboxes"]]

        return SandboxListResponse(
            sandboxes=sandboxes,
            count=data["count"],
            offset=data.get("offset", offset),
            limit=data.get("limit", limit),
        )

    async def create(
        self,
        workspace_id: str,
        name: str,
        agent_config: AgentConfig | dict[str, Any],
        description: str | None = None,
    ) -> Sandbox:
        """
        Create a new sandbox.

        Args:
            workspace_id: Workspace ID
            name: Sandbox name
            agent_config: Agent configuration
            description: Optional description

        Returns:
            Created Sandbox

        Raises:
            RoundTableError: If the request fails
        """
        request_data = {"name": name}

        if isinstance(agent_config, dict):
            agent_config = AgentConfig(**agent_config)
        request_data["agent_config"] = agent_config.model_dump()

        if description is not None:
            request_data["description"] = description

        response = await self._request(
            "POST",
            f"/sandboxes/{workspace_id}/sandboxes",
            json=request_data,
        )
        data = response["data"]

        # Parse agent config
        if "agent_config" in data and isinstance(data["agent_config"], dict):
            data["agent_config"] = AgentConfig(**data["agent_config"])

        return Sandbox(**data)

    async def get(self, sandbox_id: str) -> Sandbox:
        """
        Get sandbox details.

        Args:
            sandbox_id: Sandbox ID

        Returns:
            Sandbox details

        Raises:
            NotFoundError: If sandbox doesn't exist
            RoundTableError: If the request fails
        """
        response = await self._request(
            "GET",
            f"/sandboxes/{sandbox_id}",
        )
        data = response["data"]

        # Parse agent config
        if "agent_config" in data and isinstance(data["agent_config"], dict):
            data["agent_config"] = AgentConfig(**data["agent_config"])

        return Sandbox(**data)

    async def start(self, sandbox_id: str) -> Sandbox:
        """
        Start a sandbox.

        Args:
            sandbox_id: Sandbox ID

        Returns:
            Updated Sandbox with running status

        Raises:
            NotFoundError: If sandbox doesn't exist
            RoundTableError: If the request fails
        """
        response = await self._request(
            "POST",
            f"/sandboxes/{sandbox_id}/start",
        )
        data = response["data"]

        if "agent_config" in data and isinstance(data["agent_config"], dict):
            data["agent_config"] = AgentConfig(**data["agent_config"])

        return Sandbox(**data)

    async def stop(self, sandbox_id: str) -> Sandbox:
        """
        Stop a sandbox.

        Args:
            sandbox_id: Sandbox ID

        Returns:
            Updated Sandbox with stopped status

        Raises:
            NotFoundError: If sandbox doesn't exist
            RoundTableError: If the request fails
        """
        response = await self._request(
            "POST",
            f"/sandboxes/{sandbox_id}/stop",
        )
        data = response["data"]

        if "agent_config" in data and isinstance(data["agent_config"], dict):
            data["agent_config"] = AgentConfig(**data["agent_config"])

        return Sandbox(**data)

    async def delete(self, sandbox_id: str) -> bool:
        """
        Delete a sandbox.

        Args:
            sandbox_id: Sandbox ID

        Returns:
            True if deleted successfully

        Raises:
            NotFoundError: If sandbox doesn't exist
            RoundTableError: If the request fails
        """
        await self._request(
            "DELETE",
            f"/sandboxes/{sandbox_id}",
        )
        return True

    async def status(self, sandbox_id: str) -> SandboxStatus:
        """
        Get sandbox status.

        Args:
            sandbox_id: Sandbox ID

        Returns:
            SandboxStatus information

        Raises:
            NotFoundError: If sandbox doesn't exist
            RoundTableError: If the request fails
        """
        response = await self._request(
            "GET",
            f"/sandboxes/{sandbox_id}/status",
        )
        data = response["data"]

        return SandboxStatus(**data)

    async def logs(self, sandbox_id: str) -> list[str]:
        """
        Get sandbox logs.

        Args:
            sandbox_id: Sandbox ID

        Returns:
            List of log lines

        Raises:
            NotFoundError: If sandbox doesn't exist
            RoundTableError: If the request fails
        """
        response = await self._request(
            "GET",
            f"/sandboxes/{sandbox_id}/logs",
        )
        data = response["data"]

        return data.get("logs", [])

    async def metrics(self, sandbox_id: str) -> SandboxMetrics:
        """
        Get sandbox metrics.

        Args:
            sandbox_id: Sandbox ID

        Returns:
            SandboxMetrics data

        Raises:
            NotFoundError: If sandbox doesn't exist
            RoundTableError: If the request fails
        """
        response = await self._request(
            "GET",
            f"/sandboxes/{sandbox_id}/metrics",
        )
        data = response["data"]

        return SandboxMetrics(**data)

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
