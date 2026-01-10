# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
WebSocket routes for the Round Table API

Provides WebSocket endpoint for real-time communication.
"""

import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from .manager import ConnectionManager, get_connection_manager
from .handler import MessageHandler
from ..message_bus import MessageRouter, get_redis_client

logger = logging.getLogger(__name__)

# Create router
websocket_router = APIRouter(prefix="/ws", tags=["websocket"])

# Global message handler (initialized on startup)
_message_handler: Optional[MessageHandler] = None


def get_message_handler() -> Optional[MessageHandler]:
    """Get the global message handler instance"""
    return _message_handler


async def initialize_websocket():
    """Initialize WebSocket components (call on app startup)"""
    global _message_handler

    redis_client = await get_redis_client()
    message_router = MessageRouter(redis_client)
    connection_manager = get_connection_manager()

    _message_handler = MessageHandler(connection_manager, message_router)
    await _message_handler.start_listening()

    logger.info("WebSocket components initialized")


async def cleanup_websocket():
    """Cleanup WebSocket components (call on app shutdown)"""
    global _message_handler

    if _message_handler:
        await _message_handler.stop_listening()
        _message_handler = None

    connection_manager = get_connection_manager()
    await connection_manager.close_all()

    logger.info("WebSocket components cleaned up")


@websocket_router.websocket("/connect")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: Optional[str] = Query(None, description="User ID for authentication"),
    workspace_id: Optional[str] = Query(None, description="Workspace ID"),
    agent_id: Optional[str] = Query(None, description="Agent ID (for agent connections)"),
):
    """
    WebSocket endpoint for real-time communication

    Query Parameters:
    - user_id: User ID (optional)
    - workspace_id: Workspace ID (optional)
    - agent_id: Agent ID (optional, for agent connections)

    Message Format (Client -> Server):
    ```json
    {
        "type": "subscribe|unsubscribe|send|broadcast|pong",
        "topics": ["topic1", "topic2"],  // for subscribe/unsubscribe
        "to_agent": "agent_id",          // for send
        "workspace_id": "ws_id",         // for broadcast
        "content": {...},                // message content
        "message_type": "request|response|notification|command",
        "priority": 0
    }
    ```

    Message Format (Server -> Client):
    ```json
    {
        "type": "subscribed|unsubscribed|sent|broadcast|message|ping|error",
        "data": {...},
        "topics": [...],
        "message_id": "...",
        "recipient_count": 3
    }
    ```
    """
    connection_manager = get_connection_manager()
    handler = get_message_handler()

    if not handler:
        await websocket.close(code=1011, reason="WebSocket not initialized")
        return

    # Accept connection
    connection = await connection_manager.connect(
        websocket,
        user_id=user_id,
        workspace_id=workspace_id,
        agent_id=agent_id,
    )

    logger.info(f"WebSocket connection established: {connection.connection_id}")

    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "connection_id": connection.connection_id,
            "timestamp": connection.connected_at,
        })

        # Deliver any pending messages
        if agent_id:
            await handler.deliver_pending_messages(connection)

        # Message loop
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            # Handle message
            response = await handler.handle_message(connection, data)

            # Send response if any
            if response:
                await websocket.send_json(response)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected normally: {connection.connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {connection.connection_id}: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e),
            })
        except Exception:
            pass
    finally:
        # Cleanup connection
        await connection_manager.disconnect(connection.connection_id)


@websocket_router.get("/connections")
async def list_connections():
    """
    List active WebSocket connections (admin endpoint)

    Returns information about all active connections.
    """
    connection_manager = get_connection_manager()

    connections = []
    for conn in connection_manager.get_all_connections().values():
        connections.append(conn.to_dict())

    return {
        "total_connections": connection_manager.get_connection_count(),
        "connections": connections,
    }


@websocket_router.get("/connections/{connection_id}")
async def get_connection_info(connection_id: str):
    """
    Get information about a specific connection

    Args:
        connection_id: Connection ID

    Returns detailed information about the connection.
    """
    connection_manager = get_connection_manager()
    conn = connection_manager.get_connection(connection_id)

    if not conn:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Connection not found")

    return conn.to_dict()


@websocket_router.get("/stats")
async def get_websocket_stats():
    """
    Get WebSocket statistics

    Returns statistics about WebSocket connections.
    """
    connection_manager = get_connection_manager()

    # Count connections by various attributes
    user_count = len(connection_manager._user_connections)
    workspace_count = len(connection_manager._workspace_connections)
    agent_count = len(connection_manager._agent_connections)
    topic_count = len(connection_manager._topic_subscribers)

    return {
        "total_connections": connection_manager.get_connection_count(),
        "unique_users": user_count,
        "unique_workspaces": workspace_count,
        "unique_agents": agent_count,
        "active_topics": topic_count,
    }


# Lifespan event handlers for FastAPI app
async def on_websocket_startup():
    """Called on application startup"""
    await initialize_websocket()


async def on_websocket_shutdown():
    """Called on application shutdown"""
    await cleanup_websocket()
