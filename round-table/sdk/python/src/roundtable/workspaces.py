# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Workspace client for Round Table SDK.

Provides methods for managing workspaces.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from roundtable.models import (
    Workspace,
    WorkspaceCreateRequest,
    WorkspaceListResponse,
    WorkspaceSettings,
    WorkspaceSummary,
    WorkspaceUpdateRequest,
)

logger = logging.getLogger(__name__)


class WorkspaceClient:
    """
    Client for workspace operations.

    Provides methods for creating, listing, getting, updating, and deleting workspaces.
    """

    def __init__(self, http_client: Any):
        """
        Initialize the workspace client.

        Args:
            http_client: HTTP client instance
        """
        self._client = http_client

    async def list(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> WorkspaceListResponse:
        """
        List all workspaces for the authenticated user.

        Args:
            offset: Pagination offset
            limit: Maximum number of workspaces to return

        Returns:
            WorkspaceListResponse with list of workspaces

        Raises:
            RoundTableError: If the request fails
        """
        response = await self._request(
            "GET",
            "/workspaces",
            params={"offset": offset, "limit": limit},
        )
        data = response["data"]

        workspaces = [WorkspaceSummary(**ws) for ws in data["workspaces"]]

        return WorkspaceListResponse(
            workspaces=workspaces,
            count=data["count"],
            offset=data.get("offset", offset),
            limit=data.get("limit", limit),
        )

    async def create(
        self,
        name: str,
        description: str | None = None,
        settings: WorkspaceSettings | dict[str, Any] | None = None,
    ) -> Workspace:
        """
        Create a new workspace.

        Args:
            name: Workspace name
            description: Optional description
            settings: Optional workspace settings

        Returns:
            Created Workspace

        Raises:
            RoundTableError: If the request fails
        """
        request_data = {"name": name}

        if description is not None:
            request_data["description"] = description

        if settings is not None:
            if isinstance(settings, dict):
                settings = WorkspaceSettings(**settings)
            request_data["settings"] = settings.model_dump()

        response = await self._request(
            "POST",
            "/workspaces",
            json=request_data,
        )
        data = response["data"]

        # Parse settings
        if "settings" in data:
            if isinstance(data["settings"], dict):
                data["settings"] = WorkspaceSettings(**data["settings"])
            else:
                data["settings"] = WorkspaceSettings.model_validate(data["settings"])

        return Workspace(**data)

    async def get(self, workspace_id: str) -> Workspace:
        """
        Get workspace details.

        Args:
            workspace_id: Workspace ID

        Returns:
            Workspace details

        Raises:
            NotFoundError: If workspace doesn't exist
            RoundTableError: If the request fails
        """
        response = await self._request(
            "GET",
            f"/workspaces/{workspace_id}",
        )
        data = response["data"]

        # Parse settings
        if "settings" in data:
            if isinstance(data["settings"], dict):
                data["settings"] = WorkspaceSettings(**data["settings"])
            else:
                data["settings"] = WorkspaceSettings.model_validate(data["settings"])

        return Workspace(**data)

    async def update(
        self,
        workspace_id: str,
        name: str | None = None,
        description: str | None = None,
        settings: WorkspaceSettings | dict[str, Any] | None = None,
        is_active: bool | None = None,
    ) -> Workspace:
        """
        Update a workspace.

        Args:
            workspace_id: Workspace ID
            name: New name
            description: New description
            settings: New settings
            is_active: New active status

        Returns:
            Updated Workspace

        Raises:
            NotFoundError: If workspace doesn't exist
            RoundTableError: If the request fails
        """
        request_data: dict[str, Any] = {}

        if name is not None:
            request_data["name"] = name
        if description is not None:
            request_data["description"] = description
        if settings is not None:
            if isinstance(settings, dict):
                settings = WorkspaceSettings(**settings)
            request_data["settings"] = settings.model_dump()
        if is_active is not None:
            request_data["is_active"] = is_active

        response = await self._request(
            "PUT",
            f"/workspaces/{workspace_id}",
            json=request_data,
        )
        data = response["data"]

        # Parse settings
        if "settings" in data:
            if isinstance(data["settings"], dict):
                data["settings"] = WorkspaceSettings(**data["settings"])
            else:
                data["settings"] = WorkspaceSettings.model_validate(data["settings"])

        return Workspace(**data)

    async def delete(self, workspace_id: str) -> bool:
        """
        Delete a workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            True if deleted successfully

        Raises:
            NotFoundError: If workspace doesn't exist
            RoundTableError: If the request fails
        """
        await self._request(
            "DELETE",
            f"/workspaces/{workspace_id}",
        )
        return True

    async def get_config(self, workspace_id: str) -> WorkspaceSettings:
        """
        Get workspace configuration.

        Args:
            workspace_id: Workspace ID

        Returns:
            WorkspaceSettings

        Raises:
            NotFoundError: If workspace doesn't exist
            RoundTableError: If the request fails
        """
        response = await self._request(
            "GET",
            f"/workspaces/{workspace_id}/config",
        )
        data = response["data"]

        return WorkspaceSettings(**data)

    async def update_config(
        self,
        workspace_id: str,
        settings: WorkspaceSettings | dict[str, Any],
    ) -> WorkspaceSettings:
        """
        Update workspace configuration.

        Args:
            workspace_id: Workspace ID
            settings: New settings

        Returns:
            Updated WorkspaceSettings

        Raises:
            NotFoundError: If workspace doesn't exist
            RoundTableError: If the request fails
        """
        if isinstance(settings, WorkspaceSettings):
            settings_data = settings.model_dump()
        else:
            settings_data = settings

        response = await self._request(
            "PUT",
            f"/workspaces/{workspace_id}/config",
            json=settings_data,
        )
        data = response["data"]

        return WorkspaceSettings(**data)

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
        # This method wraps the main client's _request method
        # In a real implementation, this would call the main client
        # For now, we'll call the client directly
        url = path if path.startswith("http") else path

        response = await self._client.request(method, url, **kwargs)
        data = response.json()

        if not data.get("success") and response.status_code < 400:
            raise Exception(f"Request failed: {data.get('message')}")

        return data
