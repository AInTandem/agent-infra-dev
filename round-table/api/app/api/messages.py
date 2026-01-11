# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Message API endpoints

Provides message sending, retrieval, and broadcasting operations.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_active_user
from app.auth.models import UserInDB
from app.db import get_db
from app.models.common import SuccessResponse
from app.models.message import (
    AgentMessage,
    BroadcastMessageRequest,
    MessageStatus,
    SendMessageRequest,
)
from app.repositories import MessageRepository, SandboxRepository, WorkspaceRepository
from app.message_bus.client import get_redis_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("/sandboxes/{sandbox_id}/messages", response_model=SuccessResponse, status_code=status.HTTP_202_ACCEPTED)
async def send_message(
    sandbox_id: str,
    message_in: SendMessageRequest,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Send a message from one sandbox to another

    Args:
        sandbox_id: Sender sandbox ID
        message_in: Message data
        current_user: Current authenticated user
        db_session: Database session

    Returns:
        SuccessResponse with sent message

    Raises:
        HTTPException: 404 if sandbox not found
    """
    sandbox_repo = SandboxRepository(db_session)
    workspace_repo = WorkspaceRepository(db_session)
    message_repo = MessageRepository(db_session)

    # Verify sender sandbox exists and user has access
    sender_sandbox = await sandbox_repo.get(sandbox_id)
    if not sender_sandbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sender sandbox {sandbox_id} not found"
        )

    # Check workspace ownership
    workspace = await workspace_repo.get_by_field("workspace_id", sender_sandbox.workspace_id)
    if not workspace or workspace.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to send messages from this sandbox"
        )

    # Verify recipient sandbox exists
    recipient_sandbox = await sandbox_repo.get(message_in.to_sandbox_id)
    if not recipient_sandbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipient sandbox {message_in.to_sandbox_id} not found"
        )

    # Verify recipient is in same workspace
    if recipient_sandbox.workspace_id != sender_sandbox.workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipient sandbox must be in the same workspace"
        )

    # Create message in audit log
    message = await message_repo.create_message(
        from_sandbox_id=sandbox_id,
        to_sandbox_id=message_in.to_sandbox_id,
        workspace_id=sender_sandbox.workspace_id,
        content=message_in.content,
        message_type=message_in.message_type,
    )

    # Publish message to message bus
    try:
        redis_client = get_redis_client()
        import json

        # Publish direct message
        await redis_client.publish(
            f"direct:{message_in.to_sandbox_id}",
            json.dumps({
                "from": sandbox_id,
                "to": message_in.to_sandbox_id,
                "content": message_in.content,
                "type": message_in.message_type,
            })
        )
        logger.info(f"Published message from {sandbox_id} to {message_in.to_sandbox_id}")
    except Exception as e:
        logger.error(f"Failed to publish message: {e}")
        # Don't fail the request if message bus fails

    # Convert to response model
    import json

    message_status = MessageStatus(
        status=message.status,
        sent_at=message.created_at,
        delivered_at=None,
        failed_at=None,
        error_message=None,
    )

    response_message = AgentMessage(
        message_id=message.message_id,
        from_sandbox_id=message.from_sandbox_id,
        to_sandbox_id=message.to_sandbox_id,
        workspace_id=message.workspace_id,
        content=json.loads(message.content_json) if message.content_json else message_in.content,
        message_type=message.message_type,
        status=message_status,
        created_at=message.created_at.isoformat() if message.created_at else None,
        updated_at=message.updated_at.isoformat() if message.updated_at else None,
    )

    return SuccessResponse(
        data=response_message.model_dump(),
        status_code=202,
    )


@router.get("/sandboxes/{sandbox_id}/messages", response_model=SuccessResponse)
async def get_sandbox_messages(
    sandbox_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    """
    Get messages for a sandbox

    Args:
        sandbox_id: Sandbox ID
        current_user: Current authenticated user
        db_session: Database session
        offset: Pagination offset
        limit: Maximum number of messages to return

    Returns:
        SuccessResponse with list of messages

    Raises:
        HTTPException: 404 if sandbox not found
    """
    sandbox_repo = SandboxRepository(db_session)
    workspace_repo = WorkspaceRepository(db_session)
    message_repo = MessageRepository(db_session)

    # Verify sandbox exists and user has access
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
            detail="Not authorized to access messages from this sandbox"
        )

    # Get messages for sandbox
    messages = await message_repo.get_by_sandbox(sandbox_id, limit=limit)

    # Convert to response models
    import json

    message_list = []
    for message in messages[offset:offset + limit]:
        message_status = MessageStatus(
            status=message.status,
            sent_at=message.created_at,
            delivered_at=None,
            failed_at=None,
            error_message=None,
        )

        response_message = AgentMessage(
            message_id=message.message_id,
            from_sandbox_id=message.from_sandbox_id,
            to_sandbox_id=message.to_sandbox_id,
            workspace_id=message.workspace_id,
            content=json.loads(message.content_json) if message.content_json else {},
            message_type=message.message_type,
            status=message_status,
            created_at=message.created_at.isoformat() if message.created_at else None,
            updated_at=message.updated_at.isoformat() if message.updated_at else None,
        )
        message_list.append(response_message)

    logger.info(f"Retrieved {len(message_list)} messages for sandbox {sandbox_id}")

    return SuccessResponse(
        data={
            "messages": [msg.model_dump() for msg in message_list],
            "count": len(message_list),
            "offset": offset,
            "limit": limit,
        }
    )


@router.post("/workspaces/{workspace_id}/broadcast", response_model=SuccessResponse, status_code=status.HTTP_202_ACCEPTED)
async def broadcast_message(
    workspace_id: str,
    broadcast_in: BroadcastMessageRequest,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Broadcast a message to all sandboxes in a workspace

    Args:
        workspace_id: Workspace ID
        broadcast_in: Broadcast message data
        current_user: Current authenticated user
        db_session: Database session

    Returns:
        SuccessResponse with broadcast result

    Raises:
        HTTPException: 404 if workspace not found
    """
    workspace_repo = WorkspaceRepository(db_session)
    sandbox_repo = SandboxRepository(db_session)
    message_repo = MessageRepository(db_session)

    # Check workspace ownership
    workspace = await workspace_repo.get_by_field("workspace_id", workspace_id)
    if not workspace or workspace.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {workspace_id} not found"
        )

    # Get all sandboxes in workspace
    sandboxes = await sandbox_repo.get_by_workspace(workspace_id)

    if not sandboxes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No sandboxes in workspace to broadcast to"
        )

    # Publish broadcast message to message bus
    try:
        redis_client = get_redis_client()
        import json

        # Publish broadcast message to workspace
        await redis_client.publish(
            f"workspace:{workspace_id}",
            json.dumps({
                "workspace_id": workspace_id,
                "content": broadcast_in.content,
                "type": broadcast_in.message_type,
                "exclude_sender": broadcast_in.exclude_sender,
            })
        )
        logger.info(f"Broadcast message to workspace {workspace_id}")
    except Exception as e:
        logger.error(f"Failed to broadcast message: {e}")
        # Don't fail the request if message bus fails

    return SuccessResponse(
        data={
            "workspace_id": workspace_id,
            "broadcast_to": len(sandboxes),
            "message_type": broadcast_in.message_type,
        },
        status_code=202,
    )


@router.get("/messages/{message_id}", response_model=SuccessResponse)
async def get_message(
    message_id: str,
    current_user: Annotated[UserInDB, Depends(get_current_active_user)],
    db_session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get message details

    Args:
        message_id: Message ID
        current_user: Current authenticated user
        db_session: Database session

    Returns:
        SuccessResponse with message details

    Raises:
        HTTPException: 404 if message not found
    """
    message_repo = MessageRepository(db_session)
    workspace_repo = WorkspaceRepository(db_session)

    message = await message_repo.get(message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message {message_id} not found"
        )

    # Check workspace ownership
    workspace = await workspace_repo.get_by_field("workspace_id", message.workspace_id)
    if not workspace or workspace.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this message"
        )

    # Convert to response model
    import json

    message_status = MessageStatus(
        status=message.status,
        sent_at=message.created_at,
        delivered_at=None,
        failed_at=None,
        error_message=None,
    )

    response_message = AgentMessage(
        message_id=message.message_id,
        from_sandbox_id=message.from_sandbox_id,
        to_sandbox_id=message.to_sandbox_id,
        workspace_id=message.workspace_id,
        content=json.loads(message.content_json) if message.content_json else {},
        message_type=message.message_type,
        status=message_status,
        created_at=message.created_at.isoformat() if message.created_at else None,
        updated_at=message.updated_at.isoformat() if message.updated_at else None,
    )

    return SuccessResponse(data=response_message.model_dump())
