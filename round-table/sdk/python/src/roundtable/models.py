# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Pydantic models for Round Table SDK.

Defines data models for workspaces, sandboxes, messages, and collaborations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class WorkspaceSettings(BaseModel):
    """Workspace configuration settings."""

    max_sandboxes: int = Field(default=10, ge=1, le=100)
    auto_cleanup: bool = True
    retention_days: int = Field(default=30, ge=1, le=365)
    collaboration_policy: dict[str, Any] = Field(default_factory=dict)


class Workspace(BaseModel):
    """Workspace model."""

    workspace_id: str
    user_id: str
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    settings: WorkspaceSettings
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class WorkspaceSummary(BaseModel):
    """Lightweight workspace reference."""

    workspace_id: str
    name: str
    description: Optional[str] = None
    sandbox_count: int = 0
    created_at: Optional[str] = None


class WorkspaceCreateRequest(BaseModel):
    """Workspace creation request."""

    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    settings: Optional[WorkspaceSettings] = None


class WorkspaceUpdateRequest(BaseModel):
    """Workspace update request."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    settings: Optional[WorkspaceSettings] = None
    is_active: Optional[bool] = None


class AgentConfig(BaseModel):
    """Agent configuration."""

    primary_agent: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)
    max_tokens: Optional[int] = Field(None, ge=1, le=128000)
    temperature: Optional[float] = Field(None, ge=0, le=1)
    system_prompt: Optional[str] = None
    tools: list[str] = Field(default_factory=list)
    extra_config: dict[str, Any] = Field(default_factory=dict)


class ResourceLimits(BaseModel):
    """Resource limits for sandbox."""

    max_memory_mb: Optional[int] = Field(None, ge=128, le=32768)
    max_cpu_cores: Optional[float] = Field(None, ge=0.1, le=16.0)
    max_disk_gb: Optional[int] = Field(None, ge=1, le=1000)
    max_execution_time_seconds: Optional[int] = Field(None, ge=1, le=86400)


class Sandbox(BaseModel):
    """Sandbox model."""

    sandbox_id: str
    workspace_id: str
    name: str = Field(min_length=1, max_length=100)
    status: str = Field(default="provisioning")
    agent_config: AgentConfig
    connection_details: Optional[dict[str, Any]] = None
    container_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SandboxCreateRequest(BaseModel):
    """Sandbox creation request."""

    name: str = Field(min_length=1, max_length=100)
    agent_config: AgentConfig
    description: Optional[str] = None


class SandboxUpdateRequest(BaseModel):
    """Sandbox update request."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    agent_config: Optional[AgentConfig] = None


class AgentMessage(BaseModel):
    """Message sent between agents."""

    message_id: str
    from_sandbox_id: str
    to_sandbox_id: str
    workspace_id: str
    content: dict[str, Any]
    message_type: str = Field(default="request")
    status: str = Field(default="pending")
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class MessageCreateRequest(BaseModel):
    """Message creation request."""

    to_sandbox_id: str
    content: dict[str, Any]
    message_type: str = Field(default="request")


class BroadcastRequest(BaseModel):
    """Broadcast message request."""

    content: dict[str, Any]
    message_type: str = Field(default="notification")


class CollaborationMode(BaseModel):
    """Collaboration mode configuration."""

    mode: str = Field(pattern=r"^(orchestrated|peer_to_peer|broadcast)$")
    max_duration_seconds: Optional[int] = Field(None, ge=1, le=3600)
    allow_parallel_tasks: bool = False
    require_consensus: bool = False


class CollaborationConfig(BaseModel):
    """Collaboration configuration."""

    timeout: int = Field(default=300, ge=10, le=3600)
    max_iterations: int = Field(default=10, ge=1, le=100)
    terminate_on_completion: bool = True
    save_history: bool = True
    extra_params: dict[str, Any] = Field(default_factory=dict)


class Collaboration(BaseModel):
    """Collaboration model."""

    collaboration_id: str
    workspace_id: str
    task: str
    mode: str
    participants: list[str]
    status: str = Field(default="running")
    config: CollaborationConfig
    result: Optional[dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class OrchestrateCollaborationRequest(BaseModel):
    """Collaboration orchestration request."""

    task: str = Field(min_length=1, max_length=1000)
    mode: str = Field(default="orchestrated")
    participants: list[str] = Field(min_length=1)
    config: Optional[CollaborationConfig] = None


class AgentInfo(BaseModel):
    """Agent information for discovery."""

    sandbox_id: str
    name: str
    primary_agent: str
    model: str
    status: str
    capabilities: list[str] = Field(default_factory=list)


class SystemHealth(BaseModel):
    """System health status."""

    status: str = Field(pattern=r"^(healthy|degraded|unhealthy)$")
    version: str
    database: str = Field(pattern=r"^(connected|disconnected)$")
    message_bus: str = Field(pattern=r"^(connected|disconnected)$")
    timestamp: str


class SystemInfo(BaseModel):
    """System information."""

    name: str
    version: str
    description: str
    environment: str
    python_version: str
    platform: str
    authenticated: bool = False
    user_id: Optional[str] = None
    email: Optional[str] = None


class AggregateMetrics(BaseModel):
    """Aggregate metrics for workspace."""

    workspace_id: str
    sandboxes: dict[str, Any]
    messages: dict[str, Any]
    collaborations: dict[str, Any]
    timestamp: str


class SandboxStatus(BaseModel):
    """Sandbox status information."""

    sandbox_id: str
    status: str
    container_status: Optional[str] = None
    last_heartbeat: Optional[str] = None
    uptime_seconds: Optional[int] = None


class SandboxMetrics(BaseModel):
    """Sandbox metrics."""

    sandbox_id: str
    metrics: dict[str, Any]
    timestamp: str


class WorkspaceListResponse(BaseModel):
    """Response from listing workspaces."""

    workspaces: list[WorkspaceSummary]
    count: int
    offset: int = 0
    limit: int = 100


class SandboxListResponse(BaseModel):
    """Response from listing sandboxes."""

    sandboxes: list[Sandbox]
    count: int
    offset: int = 0
    limit: int = 100


class MessageListResponse(BaseModel):
    """Response from listing messages."""

    messages: list[AgentMessage]
    count: int
    offset: int = 0
    limit: int = 100


class AgentListResponse(BaseModel):
    """Response from discovering agents."""

    workspace_id: str
    count: int
    agents: list[AgentInfo]
