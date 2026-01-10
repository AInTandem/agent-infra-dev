# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""Configuration-related Pydantic models"""

from typing import Any

from pydantic import BaseModel, Field


class LLMProviderConfig(BaseModel):
    """LLM provider settings"""
    provider: str = "openai"
    api_key: str = ""
    model: str = "gpt-4"
    base_url: str | None = None
    max_tokens: int = Field(default=4096, ge=256, le=128000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class MCPServerConfig(BaseModel):
    """MCP server settings"""
    server_name: str
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True


class CollaborationPolicy(BaseModel):
    """Collaboration rules"""
    auto_accept: bool = True
    timeout_seconds: int = Field(default=300, ge=10, le=3600)
    max_participants: int = Field(default=10, ge=1, le=100)
    allowed_modes: list[str] = Field(default_factory=lambda: ["orchestrated", "peer_to_peer"])


class AggregateMetrics(BaseModel):
    """Aggregated metrics data"""
    total_sandboxes: int = 0
    active_sandboxes: int = 0
    total_messages: int = 0
    total_collaborations: int = 0
    avg_resource_usage: dict[str, float] = Field(default_factory=dict)


class WorkspaceConfig(BaseModel):
    """Full workspace configuration"""
    llm_providers: list[LLMProviderConfig] = Field(default_factory=list)
    mcp_servers: list[MCPServerConfig] = Field(default_factory=list)
    collaboration_policy: CollaborationPolicy = Field(default_factory=CollaborationPolicy)


class WorkspaceSettings(BaseModel):
    """Workspace settings model (duplicate for compatibility)"""
    max_sandboxes: int = Field(default=10, ge=1, le=100)
    auto_cleanup: bool = True
    retention_days: int = Field(default=30, ge=1, le=365)
    config: WorkspaceConfig = Field(default_factory=WorkspaceConfig)
