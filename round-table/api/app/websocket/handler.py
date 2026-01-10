# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
WebSocket message handler for routing messages between clients and message bus

Handles incoming WebSocket messages and routes them through the message bus
to other connected clients and agents.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from .manager import ConnectionManager, WebSocketConnection
from ..message_bus import MessageRouter, AgentMessage, MessageType, DeliveryMode

logger = logging.getLogger(__name__)


class MessageHandler:
    """
    WebSocket message handler

    Routes messages between WebSocket clients and the message bus (Redis).

    Features:
    - Handle client subscriptions
    - Route messages to Redis pub/sub
    - Deliver messages from Redis to WebSocket clients
    - Handle acknowledgments
    - Manage message queue for offline clients

    Usage:
        handler = MessageHandler(connection_manager, message_router)

        # Handle incoming WebSocket message
        await handler.handle_message(connection, {"type": "subscribe", "topics": [...]})

        # Start listening for Redis messages
        await handler.start_listening()
    """

    def __init__(
        self,
        connection_manager: ConnectionManager,
        message_router: MessageRouter,
    ):
        """
        Initialize message handler

        Args:
            connection_manager: WebSocket connection manager
            message_router: Redis message router
        """
        self._connection_manager = connection_manager
        self._message_router = message_router
        self._listening = False

    async def handle_message(
        self,
        connection: WebSocketConnection,
        message: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Handle incoming WebSocket message from a client

        Args:
            connection: WebSocket connection that sent the message
            message: Message data

        Returns:
            Optional response message to send back

        Message types:
        - subscribe: Subscribe to topics
        - unsubscribe: Unsubscribe from topics
        - send: Send message to agent or topic
        - broadcast: Broadcast to workspace
        - ping: Ping response
        - pong: Pong response
        """
        msg_type = message.get("type")

        try:
            if msg_type == "subscribe":
                return await self._handle_subscribe(connection, message)

            elif msg_type == "unsubscribe":
                return await self._handle_unsubscribe(connection, message)

            elif msg_type == "send":
                return await self._handle_send(connection, message)

            elif msg_type == "broadcast":
                return await self._handle_broadcast(connection, message)

            elif msg_type == "pong":
                self._handle_pong(connection)
                return None

            else:
                logger.warning(f"Unknown message type: {msg_type}")
                return {
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                }

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return {
                "type": "error",
                "message": str(e),
            }

    async def _handle_subscribe(
        self,
        connection: WebSocketConnection,
        message: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle subscription request"""
        topics = message.get("topics", [])

        if not topics:
            return {
                "type": "error",
                "message": "No topics specified",
            }

        # Subscribe to Redis topics (if agent_id is set)
        if connection.agent_id:
            await self._message_router.subscribe(connection.agent_id, topics)

        # Subscribe WebSocket connection to topics
        await self._connection_manager.subscribe(connection.connection_id, topics)

        logger.info(f"Subscribed {connection.connection_id} to topics: {topics}")

        return {
            "type": "subscribed",
            "topics": topics,
        }

    async def _handle_unsubscribe(
        self,
        connection: WebSocketConnection,
        message: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle unsubscribe request"""
        topics = message.get("topics")

        # Unsubscribe from Redis
        if connection.agent_id:
            await self._message_router.unsubscribe(connection.agent_id, topics)

        # Unsubscribe WebSocket connection
        await self._connection_manager.unsubscribe(connection.connection_id, topics)

        logger.info(f"Unsubscribed {connection.connection_id} from topics: {topics}")

        return {
            "type": "unsubscribed",
            "topics": topics if topics else "all",
        }

    async def _handle_send(
        self,
        connection: WebSocketConnection,
        message: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle send message request"""
        to_agent = message.get("to_agent")
        content = message.get("content", {})
        msg_type = MessageType(message.get("message_type", "request"))
        priority = message.get("priority", 0)

        if not to_agent:
            return {
                "type": "error",
                "message": "Missing to_agent",
            }

        if not connection.agent_id:
            return {
                "type": "error",
                "message": "Not authenticated as an agent",
            }

        # Send via message router
        msg_id = await self._message_router.send_direct(
            from_agent=connection.agent_id,
            to_agent=to_agent,
            content=content,
            message_type=msg_type,
            delivery_mode=DeliveryMode.BOTH,
            priority=priority,
        )

        logger.info(f"Sent message {msg_id}: {connection.agent_id} -> {to_agent}")

        return {
            "type": "sent",
            "message_id": msg_id,
        }

    async def _handle_broadcast(
        self,
        connection: WebSocketConnection,
        message: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle broadcast request"""
        workspace_id = message.get("workspace_id") or connection.workspace_id
        content = message.get("content", {})
        exclude_agent = message.get("exclude_agent")

        if not workspace_id:
            return {
                "type": "error",
                "message": "Missing workspace_id",
            }

        if not connection.agent_id:
            return {
                "type": "error",
                "message": "Not authenticated as an agent",
            }

        # Broadcast via message router
        count = await self._message_router.broadcast(
            from_agent=connection.agent_id,
            workspace_id=workspace_id,
            content=content,
            message_type=MessageType.NOTIFICATION,
            exclude_agent=exclude_agent,
        )

        logger.info(f"Broadcast from {connection.agent_id} to workspace {workspace_id}: {count} recipients")

        return {
            "type": "broadcast",
            "workspace_id": workspace_id,
            "recipient_count": count,
        }

    def _handle_pong(self, connection: WebSocketConnection) -> None:
        """Handle pong message"""
        self._connection_manager.handle_pong(connection.connection_id)

    async def start_listening(self) -> None:
        """
        Start listening for messages from Redis and forward to WebSocket clients

        This should be called once at application startup
        """
        if self._listening:
            return

        self._listening = True

        # Set up message callback from Redis
        async def on_redis_message(agent_message: AgentMessage):
            """Handle message from Redis pub/sub"""
            # Forward to WebSocket client for to_agent
            if agent_message.to_agent:
                conn_id = self._connection_manager.get_agent_connection(agent_message.to_agent)
                if conn_id:
                    await self._connection_manager.send_to_connection(
                        conn_id,
                        {
                            "type": "message",
                            "data": agent_message.to_dict(),
                        },
                    )

            # Forward to all subscribers of the topic
            # This is for topic-based subscriptions
            # (Implementation depends on how topics are mapped)

        self._message_router.on_message(on_redis_message)
        await self._message_router.start_listening()

        logger.info("Message handler started listening for Redis messages")

    async def stop_listening(self) -> None:
        """Stop listening for messages from Redis"""
        if not self._listening:
            return

        self._listening = False
        await self._message_router.stop_listening()

        logger.info("Message handler stopped listening")

    async def deliver_pending_messages(self, connection: WebSocketConnection) -> int:
        """
        Deliver pending messages from queue to a newly connected client

        Args:
            connection: WebSocket connection

        Returns:
            Number of messages delivered
        """
        if not connection.agent_id:
            return 0

        # Get pending messages from queue
        pending = await self._message_router.get_pending(connection.agent_id)

        delivered = 0
        for agent_message in pending:
            try:
                await connection.send_json({
                    "type": "message",
                    "data": agent_message.to_dict(),
                    "queued": True,
                })

                # Acknowledge the message
                await self._message_router.acknowledge(
                    connection.agent_id,
                    agent_message.message_id,
                )

                delivered += 1

            except Exception as e:
                logger.error(f"Failed to deliver pending message: {e}")
                break

        if delivered > 0:
            logger.info(f"Delivered {delivered} pending messages to {connection.connection_id}")

        return delivered
