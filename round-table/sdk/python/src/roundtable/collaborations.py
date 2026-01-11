# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Collaboration client for Round Table SDK.

Provides methods for orchestrating and managing multi-agent collaborations.
"""

from __future__ import annotations

import logging
from typing import Any

from roundtable.models import (
    AgentInfo,
    AgentListResponse,
    Collaboration,
    CollaborationConfig,
    OrchestrateCollaborationRequest,
)

logger = logging.getLogger(__name__)


class CollaborationClient:
    """
    Client for collaboration operations.

    Provides methods for orchestrating collaborations, getting status,
    and discovering agents.
    """

    def __init__(self, http_client: Any):
        """
        Initialize the collaboration client.

        Args:
            http_client: HTTP client instance
        """
        self._client = http_client

    async def orchestrate(
        self,
        workspace_id: str,
        task: str,
        participants: list[str],
        mode: str = "orchestrated",
        config: CollaborationConfig | dict[str, Any] | None = None,
    ) -> Collaboration:
        """
        Orchestrate a collaboration task.

        Args:
            workspace_id: Workspace ID
            task: Task description
            participants: List of sandbox IDs to participate
            mode: Collaboration mode (orchestrated, peer_to_peer, broadcast)
            config: Optional collaboration configuration

        Returns:
            Created Collaboration

        Raises:
            NotFoundError: If workspace or participant doesn't exist
            RoundTableError: If the request fails
        """
        request_data = {
            "task": task,
            "mode": mode,
            "participants": participants,
        }

        if config is not None:
            if isinstance(config, dict):
                config = CollaborationConfig(**config)
            request_data["config"] = config.model_dump()

        response = await self._request(
            "POST",
            f"/collaborations/workspaces/{workspace_id}/collaboration/orchestrate",
            json=request_data,
        )
        data = response["data"]

        # Parse config
        if "config" in data and isinstance(data["config"], dict):
            data["config"] = CollaborationConfig(**data["config"])

        return Collaboration(**data)

    async def get_collaboration(self, collaboration_id: str) -> Collaboration:
        """
        Get collaboration status.

        Args:
            collaboration_id: Collaboration ID

        Returns:
            Collaboration details

        Raises:
            NotFoundError: If collaboration doesn't exist
            RoundTableError: If the request fails
        """
        response = await self._request(
            "GET",
            f"/collaborations/collaborations/{collaboration_id}",
        )
        data = response["data"]

        # Parse config
        if "config" in data and isinstance(data["config"], dict):
            data["config"] = CollaborationConfig(**data["config"])

        return Collaboration(**data)

    async def discover_agents(
        self,
        workspace_id: str,
    ) -> AgentListResponse:
        """
        Discover agents in a workspace.

        Args:
            workspace_id: Workspace ID

        Returns:
            AgentListResponse with list of agents

        Raises:
            NotFoundError: If workspace doesn't exist
            RoundTableError: If the request fails
        """
        response = await self._request(
            "GET",
            f"/collaborations/workspaces/{workspace_id}/agents/discover",
        )
        data = response["data"]

        agents = [AgentInfo(**agent) for agent in data["agents"]]

        return AgentListResponse(
            workspace_id=data["workspace_id"],
            count=data["count"],
            agents=agents,
        )

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
