# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""Sandbox-related Pydantic models"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentDefinition(BaseModel):
    """Agent definition"""
    name: str
    type: str = "llm"
    version: str = "1.0.0"


class AgentConfig(BaseModel):
    """Agent configuration"""
    primary_agent: str = Field(min_length=1, max_length=100)
    model: str = Field(default="gpt-4")
    sub_agents: list[str] = Field(default_factory=list)
    max_tokens: int = Field(default=4096, ge=256, le=128000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class ResourceLimits(BaseModel):
    """Resource constraints"""
    max_memory_mb: int = Field(default=1024, ge=128, le=16384)
    max_cpu_cores: float = Field(default=1.0, ge=0.1, le=16.0)
    max_disk_gb: int = Field(default=10, ge=1, le=1000)
    timeout_seconds: int = Field(default=300, ge=10, le=86400)


class HealthStatus(BaseModel):
    """Health monitoring data"""
    status: str = "unknown"
    last_check: str | None = None
    container_status: str = "unknown"
    resource_usage: dict[str, Any] = Field(default_factory=dict)


class ConnectionDetails(BaseModel):
    """Connection information"""
    endpoint: str | None = None
    token: str | None = None
    websocket_url: str | None = None
    expires_at: datetime | None = None


class Sandbox(BaseModel):
    """Full sandbox entity"""
    sandbox_id: str
    workspace_id: str
    name: str = Field(min_length=1, max_length=100)
    status: str = "provisioning"
    agent_config: AgentConfig
    resource_limits: ResourceLimits
    health: HealthStatus
    connection: ConnectionDetails | None = None
    created_at: str | None = None
    updated_at: str | None = None


class SandboxSummary(BaseModel):
    """Lightweight sandbox reference"""
    sandbox_id: str
    workspace_id: str
    name: str
    status: str
    agent_config: AgentConfig
    created_at: str | None = None


class SandboxCreateRequest(BaseModel):
    """Sandbox creation request"""
    name: str = Field(min_length=1, max_length=100)
    agent_config: AgentConfig
    resource_limits: ResourceLimits | None = None
