# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""Workspace-related Pydantic models"""

from typing import Any

from pydantic import BaseModel, Field


class WorkspaceSettings(BaseModel):
    """Workspace configuration settings"""
    max_sandboxes: int = Field(default=10, ge=1, le=100)
    auto_cleanup: bool = True
    retention_days: int = Field(default=30, ge=1, le=365)
    collaboration_policy: dict[str, Any] = Field(default_factory=dict)


class Workspace(BaseModel):
    """Full workspace entity"""
    workspace_id: str
    user_id: str
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    settings: WorkspaceSettings
    is_active: bool = True
    created_at: str | None = None
    updated_at: str | None = None


class WorkspaceSummary(BaseModel):
    """Lightweight workspace reference"""
    workspace_id: str
    name: str
    description: str | None = None
    sandbox_count: int = 0
    created_at: str | None = None


class WorkspaceCreateRequest(BaseModel):
    """Workspace creation request"""
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(None, max_length=1000)
    settings: WorkspaceSettings | None = None


class WorkspaceUpdateRequest(BaseModel):
    """Workspace update request"""
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=1000)
    settings: WorkspaceSettings | None = None
    is_active: bool | None = None
