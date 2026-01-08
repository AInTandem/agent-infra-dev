# Copyright (c) 2025 AInTandem
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
WebSocket API endpoints for real-time streaming reasoning.

Provides WebSocket connections for agent chat with streaming reasoning steps.
"""

import asyncio
from typing import Any, Dict, Optional, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from loguru import logger

from core.websocket_manager import WebSocketManager, get_websocket_manager
from core.agent_manager import AgentManager


# Global agent manager (will be injected during app initialization)
_agent_manager: Optional[AgentManager] = None


def set_agent_manager(agent_manager: AgentManager):
    """Set the global agent manager instance."""
    global _agent_manager
    _agent_manager = agent_manager


def get_agent_manager() -> AgentManager:
    """Get the global agent manager instance."""
    if _agent_manager is None:
        raise RuntimeError("AgentManager not initialized. Call set_agent_manager() first.")
    return _agent_manager


# Create router
router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/chat/{session_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    session_id: str,
    agent_name: Optional[str] = "researcher"
):
    """
    WebSocket endpoint for real-time agent chat with streaming reasoning.

    Connect to this endpoint to:
    1. Send chat messages to the agent
    2. Receive reasoning steps in real-time
    3. Get notified when reasoning completes

    Message Format (Client → Server):
    ```json
    {
        "type": "chat",
        "payload": {
            "message": "Your question here",
            "agent_name": "researcher",
            "enable_reasoning": true
        }
    }
    ```

    Message Format (Server → Client):
    ```json
    {
        "type": "reasoning_step",
        "data": {
            "type": "thought",
            "content": "Thinking content...",
            "iteration": 1,
            "timestamp": 1641234567.123
        }
    }
    ```

    Args:
        websocket: WebSocket connection
        session_id: Unique session identifier (auto-generated or provided)
        agent_name: Default agent to use (can be overridden in messages)
    """
    # Get WebSocket manager
    ws_manager = get_websocket_manager()

    # Accept connection
    await ws_manager.connect(
        websocket,
        session_id,
        metadata={"agent_name": agent_name}
    )

    # Send welcome message
    await ws_manager.send_message(session_id, {
        "type": "connected",
        "data": {
            "session_id": session_id,
            "agent_name": agent_name,
            "message": "Connected to agent chat"
        }
    })

    logger.info(f"[WS] Chat connection established: session={session_id}, agent={agent_name}")

    try:
        while True:
            # Receive message from client
            try:
                data = await websocket.receive_json()
            except Exception as e:
                logger.warning(f"[WS] Invalid JSON from {session_id}: {e}")
                await ws_manager.send_message(session_id, {
                    "type": "error",
                    "data": {"message": f"Invalid message format: {str(e)}"}
                })
                continue

            message_type = data.get("type")
            payload = data.get("payload", {})

            # Handle different message types
            if message_type == "chat":
                # Handle chat request
                user_message = payload.get("message")
                requested_agent = payload.get("agent_name", agent_name)
                enable_reasoning = payload.get("enable_reasoning", True)

                if not user_message:
                    await ws_manager.send_message(session_id, {
                        "type": "error",
                        "data": {"message": "Message content is required"}
                    })
                    continue

                # Start reasoning in background task
                asyncio.create_task(
                    handle_reasoning_request(
                        ws_manager,
                        session_id,
                        requested_agent,
                        user_message,
                        enable_reasoning
                    )
                )

            elif message_type == "ping":
                # Heartbeat response
                await ws_manager.send_message(session_id, {
                    "type": "pong",
                    "data": {"timestamp": data.get("timestamp")}
                })

                # Update last heartbeat
                ws_manager.update_metadata(session_id, {"last_heartbeat": data.get("timestamp")})

            elif message_type == "interrupt":
                # Handle interruption request
                await ws_manager.send_message(session_id, {
                    "type": "interrupted",
                    "data": {"message": "Reasoning interrupted"}
                })

            else:
                logger.warning(f"[WS] Unknown message type: {message_type}")
                await ws_manager.send_message(session_id, {
                    "type": "error",
                    "data": {"message": f"Unknown message type: {message_type}"}
                })

    except WebSocketDisconnect:
        logger.info(f"[WS] Client disconnected normally: session={session_id}")
    except Exception as e:
        logger.exception(f"[WS] Error in chat endpoint for {session_id}: {e}")
        await ws_manager.send_message(session_id, {
            "type": "error",
            "data": {"message": f"Internal error: {str(e)}"}
        })
    finally:
        await ws_manager.disconnect(session_id)


async def handle_reasoning_request(
    ws_manager: WebSocketManager,
    session_id: str,
    agent_name: str,
    message: str,
    enable_reasoning: bool
):
    """
    Handle a reasoning request and push steps to client via WebSocket.

    Args:
        ws_manager: WebSocket manager instance
        session_id: Session identifier
        agent_name: Agent to use
        message: User's message
        enable_reasoning: Whether to use continuous reasoning
    """
    agent_manager = get_agent_manager()

    try:
        # Send start notification
        await ws_manager.send_message(session_id, {
            "type": "reasoning_start",
            "data": {
                "agent": agent_name,
                "message": message,
                "enable_reasoning": enable_reasoning
            }
        })

        # Get agent
        agent = agent_manager.get_agent(agent_name)
        if not agent:
            await ws_manager.send_message(session_id, {
                "type": "error",
                "data": {"message": f"Agent '{agent_name}' not found"}
            })
            return

        if enable_reasoning:
            # Check if agent has streaming method
            if hasattr(agent, 'run_with_reasoning_stream'):
                # Use streaming reasoning
                async for step in agent.run_with_reasoning_stream(message):
                    # Push each step to client
                    await ws_manager.send_message(session_id, {
                        "type": "reasoning_step",
                        "data": step
                    })
            else:
                # Fallback to non-streaming
                logger.warning(f"[WS] Agent {agent_name} does not support streaming, using non-streaming mode")
                steps = await agent.run_with_reasoning(message)

                # Send all steps at once
                for step in steps:
                    await ws_manager.send_message(session_id, {
                        "type": "reasoning_step",
                        "data": step
                    })

        else:
            # Non-streaming mode
            response = await agent.run_async(message)

            # Extract content
            content = ""
            for msg in response:
                if hasattr(msg, 'content') and msg.content:
                    content += msg.content
                elif isinstance(msg, dict):
                    content += msg.get('content', '')

            await ws_manager.send_message(session_id, {
                "type": "response",
                "data": {"content": content}
            })

        # Send completion notification
        await ws_manager.send_message(session_id, {
            "type": "reasoning_complete",
            "data": {}
        })

    except Exception as e:
        logger.exception(f"[WS] Error handling reasoning for {session_id}: {e}")
        await ws_manager.send_message(session_id, {
            "type": "error",
            "data": {"message": str(e)}
        })


@router.get("/connections")
async def get_connections(ws_manager: WebSocketManager = Depends(get_websocket_manager)):
    """
    Get information about active WebSocket connections.

    Returns:
        Dictionary with connection statistics
    """
    return {
        "active_connections": ws_manager.get_connection_count(),
        "session_ids": list(ws_manager.get_connection_ids()),
        "timestamp": ws_manager.get_metadata("system") or {}
    }


@router.post("/broadcast")
async def broadcast_message(
    message: Dict[str, Any],
    ws_manager: WebSocketManager = Depends(get_websocket_manager)
):
    """
    Broadcast a message to all connected WebSocket clients.

    Args:
        message: Message to broadcast

    Returns:
        Dictionary with broadcast results
    """
    sent_count = await ws_manager.broadcast(message)

    return {
        "success": True,
        "sent_to": sent_count,
        "message": message
    }
