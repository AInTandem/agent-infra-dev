# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
WebSocket connection manager for real-time client communication

Manages WebSocket connections, subscriptions, and message broadcasting.
"""

import asyncio
import json
import logging
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """WebSocket connection state"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"


@dataclass
class WebSocketConnection:
    """
    Represents a single WebSocket connection

    Attributes:
        connection_id: Unique connection ID
        websocket: FastAPI WebSocket instance
        user_id: User ID (optional)
        workspace_id: Workspace ID (optional)
        agent_id: Agent ID (optional)
        subscriptions: Set of topics this connection is subscribed to
        state: Current connection state
        connected_at: Timestamp when connection was established
        last_ping: Timestamp of last ping
        last_pong: Timestamp of last pong
    """
    connection_id: str
    websocket: WebSocket
    user_id: Optional[str] = None
    workspace_id: Optional[str] = None
    agent_id: Optional[str] = None
    subscriptions: Set[str] = field(default_factory=set)
    state: ConnectionState = ConnectionState.CONNECTING
    connected_at: float = field(default_factory=time.time)
    last_ping: float = 0
    last_pong: float = 0

    async def send_json(self, data: dict) -> bool:
        """
        Send JSON data to this connection

        Args:
            data: Dictionary to send as JSON

        Returns:
            True if sent successfully
        """
        try:
            await self.websocket.send_json(data)
            return True
        except Exception as e:
            logger.warning(f"Failed to send to {self.connection_id}: {e}")
            return False

    async def send_text(self, text: str) -> bool:
        """
        Send text to this connection

        Args:
            text: Text to send

        Returns:
            True if sent successfully
        """
        try:
            await self.websocket.send_text(text)
            return True
        except Exception as e:
            logger.warning(f"Failed to send to {self.connection_id}: {e}")
            return False

    def to_dict(self) -> dict:
        """Convert connection to dictionary representation"""
        return {
            "connection_id": self.connection_id,
            "user_id": self.user_id,
            "workspace_id": self.workspace_id,
            "agent_id": self.agent_id,
            "subscriptions": list(self.subscriptions),
            "state": self.state.value,
            "connected_at": self.connected_at,
            "duration_seconds": time.time() - self.connected_at,
        }


class ConnectionManager:
    """
    WebSocket connection manager

    Features:
    - Connection lifecycle management
    - Topic-based subscriptions
    - Message broadcasting to subscribers
    - Connection health monitoring (ping/pong)
    - User/agent/workspace association

    Usage:
        manager = ConnectionManager()

        # Accept new connection
        conn = await manager.connect(websocket, user_id="user_123")

        # Subscribe to topics
        await manager.subscribe(conn.connection_id, ["topic1", "topic2"])

        # Broadcast to topic
        await manager.broadcast_to_topic("topic1", {"message": "hello"})

        # Send to specific connection
        await manager.send_to_connection(conn.connection_id, {"message": "hi"})

        # Disconnect
        await manager.disconnect(conn.connection_id)
    """

    def __init__(self, ping_interval: float = 30.0, ping_timeout: float = 60.0):
        """
        Initialize connection manager

        Args:
            ping_interval: Interval in seconds for sending pings
            ping_timeout: Timeout in seconds for pong response
        """
        self._connections: Dict[str, WebSocketConnection] = {}
        self._topic_subscribers: Dict[str, Set[str]] = {}  # topic -> connection IDs
        self._user_connections: Dict[str, Set[str]] = {}  # user_id -> connection IDs
        self._workspace_connections: Dict[str, Set[str]] = {}  # workspace_id -> connection IDs
        self._agent_connections: Dict[str, str] = {}  # agent_id -> connection ID
        self._lock = asyncio.Lock()

        # Ping/pong monitoring
        self._ping_interval = ping_interval
        self._ping_timeout = ping_timeout
        self._ping_task: Optional[asyncio.Task] = None

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str | None = None,
        workspace_id: str | None = None,
        agent_id: str | None = None,
    ) -> WebSocketConnection:
        """
        Accept and register a new WebSocket connection

        Args:
            websocket: FastAPI WebSocket instance
            user_id: Optional user ID
            workspace_id: Optional workspace ID
            agent_id: Optional agent ID

        Returns:
            WebSocketConnection object
        """
        # Accept the connection
        await websocket.accept()

        # Create connection object
        connection_id = f"conn_{secrets.token_hex(8)}"
        conn = WebSocketConnection(
            connection_id=connection_id,
            websocket=websocket,
            user_id=user_id,
            workspace_id=workspace_id,
            agent_id=agent_id,
            state=ConnectionState.CONNECTED,
        )

        async with self._lock:
            self._connections[connection_id] = conn

            if user_id:
                if user_id not in self._user_connections:
                    self._user_connections[user_id] = set()
                self._user_connections[user_id].add(connection_id)

            if workspace_id:
                if workspace_id not in self._workspace_connections:
                    self._workspace_connections[workspace_id] = set()
                self._workspace_connections[workspace_id].add(connection_id)

            if agent_id:
                self._agent_connections[agent_id] = connection_id

        logger.info(f"WebSocket connected: {connection_id} (user={user_id}, agent={agent_id})")

        # Start ping task if not running
        if self._ping_task is None:
            self._ping_task = asyncio.create_task(self._ping_loop())

        return conn

    async def disconnect(self, connection_id: str) -> None:
        """
        Disconnect and remove a WebSocket connection

        Args:
            connection_id: Connection ID to disconnect
        """
        async with self._lock:
            conn = self._connections.pop(connection_id, None)
            if not conn:
                return

            # Remove from user connections
            if conn.user_id and conn.user_id in self._user_connections:
                self._user_connections[conn.user_id].discard(connection_id)
                if not self._user_connections[conn.user_id]:
                    del self._user_connections[conn.user_id]

            # Remove from workspace connections
            if conn.workspace_id and conn.workspace_id in self._workspace_connections:
                self._workspace_connections[conn.workspace_id].discard(connection_id)
                if not self._workspace_connections[conn.workspace_id]:
                    del self._workspace_connections[conn.workspace_id]

            # Remove from agent connections
            if conn.agent_id and conn.agent_id in self._agent_connections:
                del self._agent_connections[conn.agent_id]

            # Remove subscriptions
            for topic in conn.subscriptions:
                if topic in self._topic_subscribers:
                    self._topic_subscribers[topic].discard(connection_id)
                    if not self._topic_subscribers[topic]:
                        del self._topic_subscribers[topic]

        logger.info(f"WebSocket disconnected: {connection_id}")

    async def subscribe(self, connection_id: str, topics: list[str] | tuple[str, ...]) -> bool:
        """
        Subscribe a connection to topics

        Args:
            connection_id: Connection ID
            topics: List of topics to subscribe to

        Returns:
            True if subscribed successfully
        """
        async with self._lock:
            conn = self._connections.get(connection_id)
            if not conn:
                return False

            for topic in topics:
                conn.subscriptions.add(topic)

                if topic not in self._topic_subscribers:
                    self._topic_subscribers[topic] = set()
                self._topic_subscribers[topic].add(connection_id)

            logger.debug(f"Connection {connection_id} subscribed to: {topics}")
            return True

    async def unsubscribe(self, connection_id: str, topics: list[str] | tuple[str, ...] | None = None) -> bool:
        """
        Unsubscribe a connection from topics

        Args:
            connection_id: Connection ID
            topics: List of topics (None = unsubscribe from all)

        Returns:
            True if unsubscribed successfully
        """
        async with self._lock:
            conn = self._connections.get(connection_id)
            if not conn:
                return False

            if topics is None:
                # Unsubscribe from all
                for topic in conn.subscriptions.copy():
                    if topic in self._topic_subscribers:
                        self._topic_subscribers[topic].discard(connection_id)
                        if not self._topic_subscribers[topic]:
                            del self._topic_subscribers[topic]
                conn.subscriptions.clear()
            else:
                # Unsubscribe from specific topics
                for topic in topics:
                    conn.subscriptions.discard(topic)
                    if topic in self._topic_subscribers:
                        self._topic_subscribers[topic].discard(connection_id)
                        if not self._topic_subscribers[topic]:
                            del self._topic_subscribers[topic]

            logger.debug(f"Connection {connection_id} unsubscribed from: {topics}")
            return True

    async def send_to_connection(self, connection_id: str, data: dict) -> bool:
        """
        Send data to a specific connection

        Args:
            connection_id: Connection ID
            data: Data to send

        Returns:
            True if sent successfully
        """
        conn = self._connections.get(connection_id)
        if not conn:
            return False

        return await conn.send_json(data)

    async def broadcast_to_topic(self, topic: str, data: dict) -> int:
        """
        Broadcast data to all subscribers of a topic

        Args:
            topic: Topic name
            data: Data to broadcast

        Returns:
            Number of connections that received the message
        """
        subscribers = self._topic_subscribers.get(topic, set()).copy()
        count = 0

        for connection_id in subscribers:
            if await self.send_to_connection(connection_id, data):
                count += 1

        return count

    async def broadcast_to_workspace(self, workspace_id: str, data: dict) -> int:
        """
        Broadcast data to all connections in a workspace

        Args:
            workspace_id: Workspace ID
            data: Data to broadcast

        Returns:
            Number of connections that received the message
        """
        connections = self._workspace_connections.get(workspace_id, set()).copy()
        count = 0

        for connection_id in connections:
            if await self.send_to_connection(connection_id, data):
                count += 1

        return count

    async def broadcast_to_all(self, data: dict) -> int:
        """
        Broadcast data to all connected clients

        Args:
            data: Data to broadcast

        Returns:
            Number of connections that received the message
        """
        connection_ids = list(self._connections.keys())
        count = 0

        for connection_id in connection_ids:
            if await self.send_to_connection(connection_id, data):
                count += 1

        return count

    def get_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        """Get connection by ID"""
        return self._connections.get(connection_id)

    def get_user_connections(self, user_id: str) -> Set[str]:
        """Get all connection IDs for a user"""
        return self._user_connections.get(user_id, set()).copy()

    def get_workspace_connections(self, workspace_id: str) -> Set[str]:
        """Get all connection IDs for a workspace"""
        return self._workspace_connections.get(workspace_id, set()).copy()

    def get_agent_connection(self, agent_id: str) -> Optional[str]:
        """Get connection ID for an agent"""
        return self._agent_connections.get(agent_id)

    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self._connections)

    def get_connections_by_topic(self, topic: str) -> Set[str]:
        """Get all connections subscribed to a topic"""
        return self._topic_subscribers.get(topic, set()).copy()

    def get_all_connections(self) -> Dict[str, WebSocketConnection]:
        """Get all connections"""
        return self._connections.copy()

    async def _ping_loop(self) -> None:
        """Background task for sending ping/pong to monitor connection health"""
        while True:
            try:
                await asyncio.sleep(self._ping_interval)

                # Send ping to all connections
                for conn_id, conn in list(self._connections.items()):
                    try:
                        # Check for stale connection
                        if conn.last_pong > 0 and time.time() - conn.last_pong > self._ping_timeout:
                            logger.warning(f"Connection {conn_id} timed out (no pong)")
                            await self.disconnect(conn_id)
                            continue

                        # Send ping
                        await conn.send_json({"type": "ping", "timestamp": time.time()})
                        conn.last_ping = time.time()

                    except Exception as e:
                        logger.debug(f"Failed to ping {conn_id}: {e}")
                        await self.disconnect(conn_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in ping loop: {e}")

    def handle_pong(self, connection_id: str) -> None:
        """
        Handle pong response from client

        Args:
            connection_id: Connection ID
        """
        conn = self._connections.get(connection_id)
        if conn:
            conn.last_pong = time.time()

    async def close_all(self) -> None:
        """Close all connections and cleanup"""
        # Cancel ping task
        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
            self._ping_task = None

        # Close all connections
        for conn_id in list(self._connections.keys()):
            await self.disconnect(conn_id)

        logger.info("All WebSocket connections closed")


# Global connection manager singleton
_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager
