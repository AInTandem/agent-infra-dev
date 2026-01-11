# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
System API endpoints

Provides health checks, system information, and metrics.
"""

import logging
import platform
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.auth.dependencies import get_optional_user
from app.auth.models import UserInDB
from app.config import settings
from app.db import get_db
from app.models.common import SuccessResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health", response_model=SuccessResponse)
async def health_check(
    db_session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Health check endpoint

    Args:
        db_session: Database session

    Returns:
        SuccessResponse with health status
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.1.0-alpha",
    }

    # Check database connection
    try:
        await db_session.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["database"] = "disconnected"
        health_status["status"] = "unhealthy"

    # Check message bus connection (placeholder)
    try:
        from app.message_bus.client import get_redis_client
        redis_client = get_redis_client()
        await redis_client.ping()
        health_status["message_bus"] = "connected"
    except Exception as e:
        logger.error(f"Message bus health check failed: {e}")
        health_status["message_bus"] = "disconnected"
        health_status["status"] = "degraded"

    return SuccessResponse(data=health_status)


@router.get("/info", response_model=SuccessResponse)
async def system_info(
    current_user: Annotated[UserInDB | None, Depends(get_optional_user)] = None,
):
    """
    Get system information

    Args:
        current_user: Current authenticated user (optional)

    Returns:
        SuccessResponse with system information
    """
    info = {
        "name": "Round Table Collaboration Bus",
        "version": "0.1.0-alpha",
        "description": "Cross-container AI agent collaboration infrastructure",
        "environment": settings.environment,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "authenticated": current_user is not None,
    }

    if current_user:
        info["user_id"] = current_user.user_id
        info["email"] = current_user.email

    return SuccessResponse(data=info)


@router.get("/workspaces/{workspace_id}/metrics/aggregate", response_model=SuccessResponse)
async def get_aggregate_metrics(
    workspace_id: str,
    current_user: Annotated[UserInDB | None, Depends(get_optional_user)] = None,
    db_session: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """
    Get aggregate metrics for a workspace

    Args:
        workspace_id: Workspace ID
        current_user: Current authenticated user (optional)
        db_session: Database session

    Returns:
        SuccessResponse with aggregate metrics

    Raises:
        HTTPException: 401 if not authenticated, 404 if workspace not found
    """
    from fastapi import HTTPException, status
    from app.repositories import WorkspaceRepository, SandboxRepository, MessageRepository

    # Check authentication
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )

    workspace_repo = WorkspaceRepository(db_session)
    sandbox_repo = SandboxRepository(db_session)
    message_repo = MessageRepository(db_session)

    # Check workspace ownership
    workspace = await workspace_repo.get_by_field("workspace_id", workspace_id)
    if not workspace or workspace.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail=f"Workspace {workspace_id} not found")

    # Get counts
    sandbox_count = await sandbox_repo.count(workspace_id=workspace_id)

    # Get recent messages
    recent_messages = await message_repo.get_by_workspace(workspace_id, limit=100)

    # Calculate metrics
    from collections import Counter

    message_types = Counter(msg.message_type for msg in recent_messages)
    message_statuses = Counter(msg.status for msg in recent_messages)

    metrics = {
        "workspace_id": workspace_id,
        "sandboxes": {
            "total": sandbox_count,
            "by_status": {
                "running": 0,
                "stopped": 0,
                "provisioning": 0,
                "error": 0,
            },
        },
        "messages": {
            "total": len(recent_messages),
            "by_type": dict(message_types),
            "by_status": dict(message_statuses),
        },
        "collaborations": {
            "active": 0,
            "completed": 0,
            "failed": 0,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Count sandboxes by status
    sandboxes = await sandbox_repo.get_by_workspace(workspace_id)
    for sandbox in sandboxes:
        if sandbox.status in metrics["sandboxes"]["by_status"]:
            metrics["sandboxes"]["by_status"][sandbox.status] += 1

    return SuccessResponse(data=metrics)
