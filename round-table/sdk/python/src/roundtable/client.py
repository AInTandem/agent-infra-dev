# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Main Round Table client.

Provides the main entry point for interacting with the Round Table API.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from roundtable.config import RoundTableConfig
from roundtable.exceptions import (
    AuthenticationError,
    BadRequestError,
    ConflictError,
    ConnectionError as SDKConnectionError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    RoundTableError,
    ServerError,
    ValidationError,
    raise_for_status,
)
from roundtable.models import (
    AggregateMetrics,
    Collaboration,
    OrchestrateCollaborationRequest,
    Sandbox,
    SandboxListResponse,
    SystemHealth,
    SystemInfo,
    Workspace,
    WorkspaceListResponse,
)

logger = logging.getLogger(__name__)


class RoundTableClient:
    """
    Main client for Round Table API.

    This is the main entry point for interacting with the Round Table
    Collaboration Bus. It provides access to all resource-specific clients.

    Example:
        ```python
        from roundtable import RoundTableClient

        async with RoundTableClient(api_key="your-api-key") as client:
            # Create workspace
            workspace = await client.workspaces.create(name="My Workspace")

            # Create sandbox
            sandbox = await client.sandboxes.create(
                workspace_id=workspace.workspace_id,
                name="My Agent",
                agent_config={"primary_agent": "researcher", "model": "gpt-4"},
            )
        ```
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "http://localhost:8000/api/v1",
        config: RoundTableConfig | None = None,
        timeout: float = 30.0,
        verify_ssl: bool = True,
    ):
        """
        Initialize the Round Table client.

        Args:
            api_key: API key for authentication
            base_url: Base URL of the Round Table API
            config: Optional configuration object (overrides other params)
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        if config:
            self.config = config
        else:
            if not api_key:
                raise ValueError("api_key is required if config is not provided")
            self.config = RoundTableConfig(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout,
                verify_ssl=verify_ssl,
            )

        # Create HTTP client
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                **self.config.extra_headers,
            },
            timeout=self.config.timeout,
            verify=self.config.verify_ssl,
        )

        # Lazy import of resource clients to avoid circular imports
        self._workspaces_client: Any | None = None
        self._sandboxes_client: Any | None = None
        self._messages_client: Any | None = None
        self._collaborations_client: Any | None = None

    @property
    def workspaces(self) -> "WorkspaceClient":
        """Get the workspaces client."""
        if self._workspaces_client is None:
            from roundtable.workspaces import WorkspaceClient

            self._workspaces_client = WorkspaceClient(self._client)
        return self._workspaces_client

    @property
    def sandboxes(self) -> "SandboxClient":
        """Get the sandboxes client."""
        if self._sandboxes_client is None:
            from roundtable.sandboxes import SandboxClient

            self._sandboxes_client = SandboxClient(self._client)
        return self._sandboxes_client

    @property
    def messages(self) -> "MessageClient":
        """Get the messages client."""
        if self._messages_client is None:
            from roundtable.messages import MessageClient

            self._messages_client = MessageClient(self._client)
        return self._messages_client

    @property
    def collaborations(self) -> "CollaborationClient":
        """Get the collaborations client."""
        if self._collaborations_client is None:
            from roundtable.collaborations import CollaborationClient

            self._collaborations_client = CollaborationClient(self._client)
        return self._collaborations_client

    async def health_check(self) -> SystemHealth:
        """
        Check the health of the Round Table system.

        Returns:
            SystemHealth status

        Raises:
            RoundTableError: If the request fails
        """
        response = await self._request("GET", "/system/health")
        data = response["data"]
        return SystemHealth(**data)

    async def system_info(self) -> SystemInfo:
        """
        Get system information.

        Returns:
            SystemInfo data

        Raises:
            RoundTableError: If the request fails
        """
        response = await self._request("GET", "/system/info")
        data = response["data"]
        return SystemInfo(**data)

    async def aggregate_metrics(self, workspace_id: str) -> AggregateMetrics:
        """
        Get aggregate metrics for a workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            AggregateMetrics data

        Raises:
            RoundTableError: If the request fails
        """
        response = await self._request(
            "GET",
            f"/system/workspaces/{workspace_id}/metrics/aggregate",
        )
        data = response["data"]
        return AggregateMetrics(**data)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Make an HTTP request to the API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: Request path
            **kwargs: Additional arguments for httpx

        Returns:
            Response data dictionary

        Raises:
            AuthenticationError: If authentication fails
            BadRequestError: If the request is malformed
            ForbiddenError: If access is forbidden
            NotFoundError: If resource is not found
            ValidationError: If validation fails
            RateLimitError: If rate limit is exceeded
            ServerError: If server error occurs
            RoundTableError: For other errors
        """
        url = path if path.startswith("http") else path

        try:
            response = await self._client.request(method, url, **kwargs)
        except httpx.ConnectError as e:
            raise SDKConnectionError(f"Connection error: {e}")
        except httpx.TimeoutException as e:
            raise SDKConnectionError(f"Request timeout: {e}")
        except httpx.HTTPError as e:
            raise RoundTableError(f"HTTP error: {e}")

        # Parse response
        try:
            data = response.json()
        except Exception:
            data = {"data": None, "message": response.text}

        # Check for errors
        if response.status_code >= 400:
            data["status_code"] = response.status_code
            raise_for_status(data)

        # Ensure success
        if not data.get("success"):
            raise RoundTableError(data.get("message", "Unknown error"))

        return data

    def __repr__(self) -> str:
        return f"RoundTableClient(base_url='{self.config.base_url}')"


# Import resource clients at the end to avoid circular imports
from roundtable.collaborations import CollaborationClient
from roundtable.messages import MessageClient
from roundtable.sandboxes import SandboxClient
from roundtable.workspaces import WorkspaceClient
