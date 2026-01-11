# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Sandbox API endpoints

Provides sandbox lifecycle management operations.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.auth.models import UserInDB
from app.db import get_db
from app.models.common import SuccessResponse
from app.models.sandbox import (
    AgentConfig,
    HealthStatus,
    ResourceLimits,
    Sandbox,
    SandboxCreateRequest,
    SandboxSummary,
)
from app.repositories import SandboxRepository, WorkspaceRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sandboxes", tags=["sandboxes"])


@router.get("/{sandbox_id}", response_model=SuccessResponse)
async def get_sandbox(
    sandbox_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get sandbox details

    Args:
        sandbox_id: Sandbox ID
        current_user: Current authenticated user
        db_session: Database session

    Returns:
        SuccessResponse with sandbox details

    Raises:
        HTTPException: 404 if sandbox not found
    """
    sandbox_repo = SandboxRepository(db_session)
    workspace_repo = WorkspaceRepository(db_session)

    sandbox = await sandbox_repo.get(sandbox_id)
    if not sandbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sandbox {sandbox_id} not found"
        )

    # Check workspace ownership
    workspace = await workspace_repo.get_by_field("workspace_id", sandbox.workspace_id)
    if not workspace or workspace.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this sandbox"
        )

    # Convert to response model
    import json

    agent_config = AgentConfig(**json.loads(sandbox.agent_config_json)) if sandbox.agent_config_json else AgentConfig()

    health = HealthStatus(
        status=sandbox.status,
        last_check=None,
        container_status=sandbox.status,
        resource_usage={},
    )

    response_sandbox = Sandbox(
        sandbox_id=sandbox.sandbox_id,
        workspace_id=sandbox.workspace_id,
        name=sandbox.name,
        status=sandbox.status,
        agent_config=agent_config,
        resource_limits=ResourceLimits(),
        health=health,
        connection=None,
        created_at=sandbox.created_at.isoformat() if sandbox.created_at else None,
        updated_at=sandbox.updated_at.isoformat() if sandbox.updated_at else None,
    )

    return SuccessResponse(data=response_sandbox.model_dump())


@router.post("/{sandbox_id}/start", response_model=SuccessResponse)
async def start_sandbox(
    sandbox_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Start a sandbox

    Args:
        sandbox_id: Sandbox ID
        current_user: Current authenticated user
        db_session: Database session

    Returns:
        SuccessResponse with updated sandbox

    Raises:
        HTTPException: 404 if sandbox not found
    """
    sandbox_repo = SandboxRepository(db_session)
    workspace_repo = WorkspaceRepository(db_session)

    sandbox = await sandbox_repo.get(sandbox_id)
    if not sandbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sandbox {sandbox_id} not found"
        )

    # Check workspace ownership
    workspace = await workspace_repo.get_by_field("workspace_id", sandbox.workspace_id)
    if not workspace or workspace.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to start this sandbox"
        )

    # Update status to running
    updated_sandbox = await sandbox_repo.update_status(sandbox_id, "running")

    logger.info(f"Started sandbox {sandbox_id}")

    # Convert to response model
    import json

    agent_config = AgentConfig(**json.loads(updated_sandbox.agent_config_json)) if updated_sandbox.agent_config_json else AgentConfig()

    health = HealthStatus(
        status=updated_sandbox.status,
        last_check=None,
        container_status=updated_sandbox.status,
        resource_usage={},
    )

    response_sandbox = Sandbox(
        sandbox_id=updated_sandbox.sandbox_id,
        workspace_id=updated_sandbox.workspace_id,
        name=updated_sandbox.name,
        status=updated_sandbox.status,
        agent_config=agent_config,
        resource_limits=ResourceLimits(),
        health=health,
        connection=None,
        created_at=updated_sandbox.created_at.isoformat() if updated_sandbox.created_at else None,
        updated_at=updated_sandbox.updated_at.isoformat() if updated_sandbox.updated_at else None,
    )

    return SuccessResponse(data=response_sandbox.model_dump())


@router.post("/{sandbox_id}/stop", response_model=SuccessResponse)
async def stop_sandbox(
    sandbox_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Stop a sandbox

    Args:
        sandbox_id: Sandbox ID
        current_user: Current authenticated user
        db_session: Database session

    Returns:
        SuccessResponse with updated sandbox

    Raises:
        HTTPException: 404 if sandbox not found
    """
    sandbox_repo = SandboxRepository(db_session)
    workspace_repo = WorkspaceRepository(db_session)

    sandbox = await sandbox_repo.get(sandbox_id)
    if not sandbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sandbox {sandbox_id} not found"
        )

    # Check workspace ownership
    workspace = await workspace_repo.get_by_field("workspace_id", sandbox.workspace_id)
    if not workspace or workspace.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to stop this sandbox"
        )

    # Update status to stopped
    updated_sandbox = await sandbox_repo.update_status(sandbox_id, "stopped")

    logger.info(f"Stopped sandbox {sandbox_id}")

    # Convert to response model
    import json

    agent_config = AgentConfig(**json.loads(updated_sandbox.agent_config_json)) if updated_sandbox.agent_config_json else AgentConfig()

    health = HealthStatus(
        status=updated_sandbox.status,
        last_check=None,
        container_status=updated_sandbox.status,
        resource_usage={},
    )

    response_sandbox = Sandbox(
        sandbox_id=updated_sandbox.sandbox_id,
        workspace_id=updated_sandbox.workspace_id,
        name=updated_sandbox.name,
        status=updated_sandbox.status,
        agent_config=agent_config,
        resource_limits=ResourceLimits(),
        health=health,
        connection=None,
        created_at=updated_sandbox.created_at.isoformat() if updated_sandbox.created_at else None,
        updated_at=updated_sandbox.updated_at.isoformat() if updated_sandbox.updated_at else None,
    )

    return SuccessResponse(data=response_sandbox.model_dump())


@router.delete("/{sandbox_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sandbox(
    sandbox_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete a sandbox

    Args:
        sandbox_id: Sandbox ID
        current_user: Current authenticated user
        db_session: Database session

    Returns:
        204 No Content on success

    Raises:
        HTTPException: 404 if sandbox not found
    """
    sandbox_repo = SandboxRepository(db_session)
    workspace_repo = WorkspaceRepository(db_session)

    sandbox = await sandbox_repo.get(sandbox_id)
    if not sandbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sandbox {sandbox_id} not found"
        )

    # Check workspace ownership
    workspace = await workspace_repo.get_by_field("workspace_id", sandbox.workspace_id)
    if not workspace or workspace.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this sandbox"
        )

    # Delete sandbox
    deleted = await sandbox_repo.delete(sandbox_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sandbox {sandbox_id} not found"
        )

    logger.info(f"Deleted sandbox {sandbox_id}")

    from fastapi import Response
    return Response(status_code=204)


@router.get("/{sandbox_id}/status", response_model=SuccessResponse)
async def get_sandbox_status(
    sandbox_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get sandbox status

    Args:
        sandbox_id: Sandbox ID
        current_user: Current authenticated user
        db_session: Database session

    Returns:
        SuccessResponse with sandbox status

    Raises:
        HTTPException: 404 if sandbox not found
    """
    sandbox_repo = SandboxRepository(db_session)
    workspace_repo = WorkspaceRepository(db_session)

    sandbox = await sandbox_repo.get(sandbox_id)
    if not sandbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sandbox {sandbox_id} not found"
        )

    # Check workspace ownership
    workspace = await workspace_repo.get_by_field("workspace_id", sandbox.workspace_id)
    if not workspace or workspace.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this sandbox"
        )

    return SuccessResponse(
        data={
            "sandbox_id": sandbox.sandbox_id,
            "status": sandbox.status,
            "created_at": sandbox.created_at.isoformat() if sandbox.created_at else None,
            "updated_at": sandbox.updated_at.isoformat() if sandbox.updated_at else None,
        }
    )


@router.get("/{sandbox_id}/logs", response_model=SuccessResponse)
async def get_sandbox_logs(
    sandbox_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
):
    """
    Get sandbox logs

    Args:
        sandbox_id: Sandbox ID
        current_user: Current authenticated user
        db_session: Database session
        offset: Log offset
        limit: Maximum number of log lines

    Returns:
        SuccessResponse with sandbox logs

    Raises:
        HTTPException: 404 if sandbox not found

    Note:
        This is a placeholder implementation. In production, logs would be
        retrieved from a logging system or file storage.
    """
    sandbox_repo = SandboxRepository(db_session)
    workspace_repo = WorkspaceRepository(db_session)

    sandbox = await sandbox_repo.get(sandbox_id)
    if not sandbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sandbox {sandbox_id} not found"
        )

    # Check workspace ownership
    workspace = await workspace_repo.get_by_field("workspace_id", sandbox.workspace_id)
    if not workspace or workspace.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this sandbox"
        )

    # Placeholder: return empty logs
    return SuccessResponse(
        data={
            "sandbox_id": sandbox_id,
            "logs": [],
            "count": 0,
            "offset": offset,
            "limit": limit,
        }
    )


@router.get("/{workspace_id}/sandboxes", response_model=SuccessResponse)
async def list_workspace_sandboxes(
    workspace_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    """
    List all sandboxes in a workspace

    Args:
        workspace_id: Workspace ID
        current_user: Current authenticated user
        db_session: Database session
        offset: Pagination offset
        limit: Maximum number of sandboxes to return

    Returns:
        SuccessResponse with list of sandboxes

    Raises:
        HTTPException: 404 if workspace not found
    """
    workspace_repo = WorkspaceRepository(db_session)
    sandbox_repo = SandboxRepository(db_session)

    # Check workspace ownership
    workspace = await workspace_repo.get_by_field("workspace_id", workspace_id)
    if not workspace or workspace.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {workspace_id} not found"
        )

    # Get sandboxes for workspace
    sandboxes = await sandbox_repo.get_by_workspace(workspace_id)

    # Convert to summaries
    sandbox_summaries = []
    for sandbox in sandboxes[offset:offset + limit]:
        import json

        agent_config = AgentConfig(**json.loads(sandbox.agent_config_json)) if sandbox.agent_config_json else AgentConfig()

        summary = SandboxSummary(
            sandbox_id=sandbox.sandbox_id,
            workspace_id=sandbox.workspace_id,
            name=sandbox.name,
            status=sandbox.status,
            agent_config=agent_config,
            created_at=sandbox.created_at.isoformat() if sandbox.created_at else None,
        )
        sandbox_summaries.append(summary)

    logger.info(f"Listed {len(sandbox_summaries)} sandboxes for workspace {workspace_id}")

    return SuccessResponse(
        data={
            "sandboxes": [sb.model_dump() for sb in sandbox_summaries],
            "count": len(sandbox_summaries),
            "offset": offset,
            "limit": limit,
        }
    )


@router.post("/{workspace_id}/sandboxes", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_sandbox(
    workspace_id: str,
    sandbox_in: SandboxCreateRequest,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new sandbox in a workspace

    Args:
        workspace_id: Workspace ID
        sandbox_in: Sandbox creation data
        current_user: Current authenticated user
        db_session: Database session

    Returns:
        SuccessResponse with created sandbox

    Raises:
        HTTPException: 404 if workspace not found
    """
    workspace_repo = WorkspaceRepository(db_session)
    sandbox_repo = SandboxRepository(db_session)

    # Check workspace ownership
    workspace = await workspace_repo.get_by_field("workspace_id", workspace_id)
    if not workspace or workspace.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {workspace_id} not found"
        )

    # Create sandbox
    sandbox = await sandbox_repo.create_sandbox(sandbox_in, workspace_id)

    logger.info(f"Created sandbox {sandbox.sandbox_id} in workspace {workspace_id}")

    # Convert to response model
    import json

    agent_config = AgentConfig(**json.loads(sandbox.agent_config_json)) if sandbox.agent_config_json else AgentConfig()

    health = HealthStatus(
        status=sandbox.status,
        last_check=None,
        container_status=sandbox.status,
        resource_usage={},
    )

    response_sandbox = Sandbox(
        sandbox_id=sandbox.sandbox_id,
        workspace_id=sandbox.workspace_id,
        name=sandbox.name,
        status=sandbox.status,
        agent_config=agent_config,
        resource_limits=ResourceLimits(),
        health=health,
        connection=None,
        created_at=sandbox.created_at.isoformat() if sandbox.created_at else None,
        updated_at=sandbox.updated_at.isoformat() if sandbox.updated_at else None,
    )

    return SuccessResponse(
        data=response_sandbox.model_dump(),
        status_code=201,
    )


@router.get("/{sandbox_id}/metrics", response_model=SuccessResponse)
async def get_sandbox_metrics(
    sandbox_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get sandbox metrics

    Args:
        sandbox_id: Sandbox ID
        current_user: Current authenticated user
        db_session: Database session

    Returns:
        SuccessResponse with sandbox metrics

    Raises:
        HTTPException: 404 if sandbox not found

    Note:
        This is a placeholder implementation. In production, metrics would be
        retrieved from a monitoring system.
    """
    sandbox_repo = SandboxRepository(db_session)
    workspace_repo = WorkspaceRepository(db_session)

    sandbox = await sandbox_repo.get(sandbox_id)
    if not sandbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sandbox {sandbox_id} not found"
        )

    # Check workspace ownership
    workspace = await workspace_repo.get_by_field("workspace_id", sandbox.workspace_id)
    if not workspace or workspace.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this sandbox"
        )

    # Placeholder: return empty metrics
    return SuccessResponse(
        data={
            "sandbox_id": sandbox_id,
            "metrics": {
                "cpu_usage": 0.0,
                "memory_usage_mb": 0,
                "disk_usage_gb": 0.0,
                "network_io": {"bytes_sent": 0, "bytes_received": 0},
                "uptime_seconds": 0,
            },
        }
    )


@router.put("/{sandbox_id}/config", response_model=SuccessResponse)
async def update_sandbox_config(
    sandbox_id: str,
    config: dict,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update sandbox configuration

    Args:
        sandbox_id: Sandbox ID
        config: New sandbox configuration
        current_user: Current authenticated user
        db_session: Database session

    Returns:
        SuccessResponse with updated configuration

    Raises:
        HTTPException: 404 if sandbox not found

    Note:
        This is a placeholder implementation. In production, this would update
        the sandbox's configuration in the container orchestration system.
    """
    sandbox_repo = SandboxRepository(db_session)
    workspace_repo = WorkspaceRepository(db_session)

    sandbox = await sandbox_repo.get(sandbox_id)
    if not sandbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sandbox {sandbox_id} not found"
        )

    # Check workspace ownership
    workspace = await workspace_repo.get_by_field("workspace_id", sandbox.workspace_id)
    if not workspace or workspace.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this sandbox"
        )

    logger.info(f"Updated config for sandbox {sandbox_id}")

    # Placeholder: return the config that was sent
    return SuccessResponse(data=config)
