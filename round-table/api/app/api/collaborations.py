# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Collaboration API endpoints

Provides collaboration orchestration and monitoring operations.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.auth.models import UserInDB
from app.db import get_db
from app.models.common import SuccessResponse, generate_id
from app.models.collaboration import (
    Collaboration,
    CollaborationProgress,
    OrchestrateCollaborationRequest,
)
from app.repositories import WorkspaceRepository, SandboxRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collaborations", tags=["collaborations"])

# In-memory storage for active collaborations (in production, use Redis or database)
active_collaborations: dict[str, Collaboration] = {}


@router.post("/workspaces/{workspace_id}/collaboration/orchestrate", response_model=SuccessResponse, status_code=status.HTTP_202_ACCEPTED)
async def orchestrate_collaboration(
    workspace_id: str,
    request: OrchestrateCollaborationRequest,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Orchestrate a collaboration task

    Args:
        workspace_id: Workspace ID
        request: Collaboration orchestration request
        current_user: Current authenticated user
        db_session: Database session

    Returns:
        SuccessResponse with collaboration details

    Raises:
        HTTPException: 404 if workspace not found
        HTTPException: 400 if participants not found
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

    # Verify all participant sandboxes exist and belong to the workspace
    participant_sandboxes = []
    for sandbox_id in request.participants:
        sandbox = await sandbox_repo.get(sandbox_id)
        if not sandbox:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Participant sandbox {sandbox_id} not found"
            )
        if sandbox.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Participant sandbox {sandbox_id} is not in workspace {workspace_id}"
            )
        participant_sandboxes.append(sandbox)

    # Create collaboration
    collaboration_id = generate_id("col")

    progress = CollaborationProgress(
        current_step=0,
        total_steps=len(request.participants) + 1,
        percentage=0.0,
        status_message="Initializing collaboration",
        last_update=None,
    )

    collaboration = Collaboration(
        collaboration_id=collaboration_id,
        workspace_id=workspace_id,
        task=request.task,
        mode=request.mode,
        status="initializing",
        participants=request.participants,
        progress=progress,
        result=None,
        error=None,
        created_at=None,
        updated_at=None,
    )

    # Store in active collaborations
    active_collaborations[collaboration_id] = collaboration

    logger.info(f"Orchestrated collaboration {collaboration_id} in workspace {workspace_id}")

    # In a real implementation, this would trigger the actual collaboration workflow
    # For now, we'll mark it as running
    collaboration.status = "running"
    collaboration.progress.current_step = 1
    collaboration.progress.percentage = 10.0
    collaboration.progress.status_message = "Collaboration started"

    return SuccessResponse(
        data=collaboration.model_dump(),
        status_code=202,
    )


@router.get("/collaborations/{collaboration_id}", response_model=SuccessResponse)
async def get_collaboration(
    collaboration_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get collaboration status

    Args:
        collaboration_id: Collaboration ID
        current_user: Current authenticated user
        db_session: Database session

    Returns:
        SuccessResponse with collaboration details

    Raises:
        HTTPException: 404 if collaboration not found
    """
    workspace_repo = WorkspaceRepository(db_session)

    # Get collaboration
    collaboration = active_collaborations.get(collaboration_id)
    if not collaboration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collaboration {collaboration_id} not found"
        )

    # Check workspace ownership
    workspace = await workspace_repo.get_by_field("workspace_id", collaboration.workspace_id)
    if not workspace or workspace.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this collaboration"
        )

    return SuccessResponse(data=collaboration.model_dump())


@router.get("/workspaces/{workspace_id}/agents/discover", response_model=SuccessResponse)
async def discover_agents(
    workspace_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Discover agents in a workspace

    Args:
        workspace_id: Workspace ID
        current_user: Current authenticated user
        db_session: Database session

    Returns:
        SuccessResponse with list of discovered agents

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

    # Get all sandboxes (agents) in workspace
    sandboxes = await sandbox_repo.get_by_workspace(workspace_id)

    # Convert to agent discovery format
    agents = []
    import json

    for sandbox in sandboxes:
        agent_config = {}
        if sandbox.agent_config_json:
            try:
                agent_config = json.loads(sandbox.agent_config_json)
            except:
                pass

        agent = {
            "sandbox_id": sandbox.sandbox_id,
            "name": sandbox.name,
            "status": sandbox.status,
            "primary_agent": agent_config.get("primary_agent", "unknown"),
            "model": agent_config.get("model", "unknown"),
            "capabilities": [],  # Would be populated from agent metadata
            "created_at": sandbox.created_at.isoformat() if sandbox.created_at else None,
        }
        agents.append(agent)

    logger.info(f"Discovered {len(agents)} agents in workspace {workspace_id}")

    return SuccessResponse(
        data={
            "workspace_id": workspace_id,
            "agents": agents,
            "count": len(agents),
        }
    )
