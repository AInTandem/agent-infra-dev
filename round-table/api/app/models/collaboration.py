# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""Collaboration-related Pydantic models"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CollaborationProgress(BaseModel):
    """Progress tracking for collaboration"""
    current_step: int = 0
    total_steps: int = 1
    percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    status_message: str | None = None
    last_update: datetime | None = None


class Collaboration(BaseModel):
    """Collaboration entity"""
    collaboration_id: str
    workspace_id: str
    task: str = Field(min_length=1, max_length=1000)
    mode: str = Field(pattern="^(orchestrated|peer_to_peer|swarm)$")
    status: str = "initializing"
    participants: list[str]
    progress: CollaborationProgress
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class OrchestrateCollaborationRequest(BaseModel):
    """Orchestrate collaboration request"""
    task: str = Field(min_length=1, max_length=1000)
    mode: str = Field(default="orchestrated", pattern="^(orchestrated|peer_to_peer|swarm)$")
    participants: list[str] = Field(min_length=1)
    config: dict[str, Any] = Field(default_factory=dict)
