# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Workspace API endpoints

Provides CRUD operations for workspace management.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.auth.models import UserInDB
from app.db import get_db
from app.models.common import SuccessResponse
from app.models.workspace import (
    Workspace,
    WorkspaceCreateRequest,
    WorkspaceSummary,
    WorkspaceUpdateRequest,
)
from app.repositories import WorkspaceRepository, SandboxRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=SuccessResponse)
async def list_workspaces(
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    """
    List all workspaces for the current user

    Args:
        current_user: Current authenticated user
        db_session: Database session
        offset: Pagination offset
        limit: Maximum number of workspaces to return

    Returns:
        SuccessResponse with list of workspace summaries
    """
    workspace_repo = WorkspaceRepository(db_session)
    sandbox_repo = SandboxRepository(db_session)

    # Get workspaces for user
    workspaces = await workspace_repo.get_by_user(current_user.user_id)

    # Get sandbox counts for each workspace
    workspace_summaries = []
    for workspace in workspaces[offset:offset + limit]:
        sandbox_count = await sandbox_repo.count(workspace_id=workspace.workspace_id)

        summary = WorkspaceSummary(
            workspace_id=workspace.workspace_id,
            name=workspace.name,
            description=workspace.description,
            sandbox_count=sandbox_count,
            created_at=workspace.created_at.isoformat() if workspace.created_at else None,
        )
        workspace_summaries.append(summary)

    logger.info(f"Listed {len(workspace_summaries)} workspaces for user {current_user.user_id}")

    return SuccessResponse(
        data={
            "workspaces": [ws.model_dump() for ws in workspace_summaries],
            "count": len(workspace_summaries),
            "offset": offset,
            "limit": limit,
        }
    )


@router.post("", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    workspace_in: WorkspaceCreateRequest,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a new workspace

    Args:
        workspace_in: Workspace creation data
        current_user: Current authenticated user
        db_session: Database session

    Returns:
        SuccessResponse with created workspace
    """
    workspace_repo = WorkspaceRepository(db_session)

    # Create workspace
    workspace = await workspace_repo.create_workspace(workspace_in, current_user.user_id)

    logger.info(f"Created workspace {workspace.workspace_id} for user {current_user.user_id}")

    # Convert to response model
    from app.models.workspace import WorkspaceSettings
    import json

    settings = WorkspaceSettings(**json.loads(workspace.settings_json)) if workspace.settings_json else WorkspaceSettings()

    response_workspace = Workspace(
        workspace_id=workspace.workspace_id,
        user_id=workspace.user_id,
        name=workspace.name,
        description=workspace.description,
        settings=settings,
        is_active=workspace.is_active,
        created_at=workspace.created_at.isoformat() if workspace.created_at else None,
        updated_at=workspace.updated_at.isoformat() if workspace.updated_at else None,
    )

    return SuccessResponse(
        data=response_workspace.model_dump(),
        status_code=201,
    )


@router.get("/{workspace_id}", response_model=SuccessResponse)
async def get_workspace(
    workspace_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get workspace details

    Args:
        workspace_id: Workspace ID
        current_user: Current authenticated user
        db_session: Database session

    Returns:
        SuccessResponse with workspace details

    Raises:
        HTTPException: 404 if workspace not found
    """
    workspace_repo = WorkspaceRepository(db_session)

    workspace = await workspace_repo.get_by_field("workspace_id", workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {workspace_id} not found"
        )

    # Check ownership
    if workspace.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this workspace"
        )

    # Convert to response model
    from app.models.workspace import WorkspaceSettings
    import json

    settings = WorkspaceSettings(**json.loads(workspace.settings_json)) if workspace.settings_json else WorkspaceSettings()

    response_workspace = Workspace(
        workspace_id=workspace.workspace_id,
        user_id=workspace.user_id,
        name=workspace.name,
        description=workspace.description,
        settings=settings,
        is_active=workspace.is_active,
        created_at=workspace.created_at.isoformat() if workspace.created_at else None,
        updated_at=workspace.updated_at.isoformat() if workspace.updated_at else None,
    )

    return SuccessResponse(data=response_workspace.model_dump())


@router.put("/{workspace_id}", response_model=SuccessResponse)
async def update_workspace(
    workspace_id: str,
    workspace_in: WorkspaceUpdateRequest,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update workspace

    Args:
        workspace_id: Workspace ID
        workspace_in: Workspace update data
        current_user: Current authenticated user
        db_session: Database session

    Returns:
        SuccessResponse with updated workspace

    Raises:
        HTTPException: 404 if workspace not found
    """
    workspace_repo = WorkspaceRepository(db_session)

    # Check ownership first
    workspace = await workspace_repo.get_by_field("workspace_id", workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {workspace_id} not found"
        )

    if workspace.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this workspace"
        )

    # Update workspace
    updated_workspace = await workspace_repo.update_workspace(workspace_id, workspace_in)
    if not updated_workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {workspace_id} not found"
        )

    logger.info(f"Updated workspace {workspace_id}")

    # Convert to response model
    from app.models.workspace import WorkspaceSettings
    import json

    settings = WorkspaceSettings(**json.loads(updated_workspace.settings_json)) if updated_workspace.settings_json else WorkspaceSettings()

    response_workspace = Workspace(
        workspace_id=updated_workspace.workspace_id,
        user_id=updated_workspace.user_id,
        name=updated_workspace.name,
        description=updated_workspace.description,
        settings=settings,
        is_active=updated_workspace.is_active,
        created_at=updated_workspace.created_at.isoformat() if updated_workspace.created_at else None,
        updated_at=updated_workspace.updated_at.isoformat() if updated_workspace.updated_at else None,
    )

    return SuccessResponse(data=response_workspace.model_dump())


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Delete workspace

    Args:
        workspace_id: Workspace ID
        current_user: Current authenticated user
        db_session: Database session

    Returns:
        204 No Content on success

    Raises:
        HTTPException: 404 if workspace not found
    """
    workspace_repo = WorkspaceRepository(db_session)

    # Check ownership first
    workspace = await workspace_repo.get_by_field("workspace_id", workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {workspace_id} not found"
        )

    if workspace.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this workspace"
        )

    # Delete workspace
    deleted = await workspace_repo.delete(workspace_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {workspace_id} not found"
        )

    logger.info(f"Deleted workspace {workspace_id}")

    from fastapi import Response
    return Response(status_code=204)


@router.get("/{workspace_id}/config", response_model=SuccessResponse)
async def get_workspace_config(
    workspace_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get workspace configuration

    Args:
        workspace_id: Workspace ID
        current_user: Current authenticated user
        db_session: Database session

    Returns:
        SuccessResponse with workspace configuration
    """
    workspace_repo = WorkspaceRepository(db_session)

    workspace = await workspace_repo.get_by_field("workspace_id", workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {workspace_id} not found"
        )

    if workspace.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this workspace"
        )

    # Parse settings
    from app.models.workspace import WorkspaceSettings
    import json

    settings = WorkspaceSettings(**json.loads(workspace.settings_json)) if workspace.settings_json else WorkspaceSettings()

    return SuccessResponse(data=settings.model_dump())


@router.put("/{workspace_id}/config", response_model=SuccessResponse)
async def update_workspace_config(
    workspace_id: str,
    settings: dict,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Update workspace configuration

    Args:
        workspace_id: Workspace ID
        settings: New workspace settings
        current_user: Current authenticated user
        db_session: Database session

    Returns:
        SuccessResponse with updated configuration
    """
    workspace_repo = WorkspaceRepository(db_session)

    workspace = await workspace_repo.get_by_field("workspace_id", workspace_id)
    if not workspace:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {workspace_id} not found"
        )

    if workspace.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this workspace"
        )

    # Update settings
    from app.models.workspace import WorkspaceSettings
    from app.models.workspace import WorkspaceUpdateRequest

    new_settings = WorkspaceSettings(**settings)
    update_request = WorkspaceUpdateRequest(settings=new_settings)

    updated_workspace = await workspace_repo.update_workspace(workspace_id, update_request)

    logger.info(f"Updated config for workspace {workspace_id}")

    return SuccessResponse(data=new_settings.model_dump())
