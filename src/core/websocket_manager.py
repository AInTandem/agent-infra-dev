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
WebSocket Manager for real-time communication.

Manages WebSocket connections and message distribution for streaming reasoning.
"""

import asyncio
import json
import time
from typing import Any, Awaitable, Callable, Dict, Optional, Set
from fastapi import WebSocket

from loguru import logger


class WebSocketManager:
    """
    Manages WebSocket connections and message broadcasting.

    Features:
    - Connection lifecycle management
    - Message queuing for offline clients
    - Broadcast and targeted messaging
    - Heartbeat monitoring
    """

    def __init__(
        self,
        heartbeat_interval: float = 30.0,
        connection_timeout: float = 120.0,
    ):
        """
        Initialize the WebSocket Manager.

        Args:
            heartbeat_interval: Seconds between heartbeat pings
            connection_timeout: Seconds before marking a connection as stale
        """
        # session_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}

        # session_id -> connection metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}

        # session_id -> message queue (for buffering)
        self.message_queues: Dict[str, asyncio.Queue] = {}

        # Heartbeat settings
        self.heartbeat_interval = heartbeat_interval
        self.connection_timeout = connection_timeout

        # Heartbeat task
        self._heartbeat_task: Optional[asyncio.Task] = None

        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: WebSocket connection instance
            session_id: Unique session identifier
            metadata: Optional metadata to store with the connection
        """
        await websocket.accept()

        async with self._lock:
            self.active_connections[session_id] = websocket
            self.message_queues[session_id] = asyncio.Queue(maxsize=100)
            self.connection_metadata[session_id] = {
                **(metadata or {}),
                "connected_at": time.time(),
                "last_heartbeat": time.time(),
            }

        logger.info(f"[WS] Client connected: session={session_id}")

    async def disconnect(self, session_id: str) -> bool:
        """
        Disconnect and clean up a WebSocket connection.

        Args:
            session_id: Session identifier to disconnect

        Returns:
            True if connection was removed, False if not found
        """
        async with self._lock:
            if session_id in self.active_connections:
                try:
                    websocket = self.active_connections[session_id]
                    await websocket.close()
                except Exception as e:
                    logger.debug(f"[WS] Error closing connection for {session_id}: {e}")

                del self.active_connections[session_id]

                if session_id in self.connection_metadata:
                    del self.connection_metadata[session_id]

                if session_id in self.message_queues:
                    # Clear the queue
                    queue = self.message_queues.pop(session_id)
                    while not queue.empty():
                        try:
                            queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break

                logger.info(f"[WS] Client disconnected: session={session_id}")
                return True

        return False

    async def send_message(
        self,
        session_id: str,
        message: Dict[str, Any]
    ) -> bool:
        """
        Send a message to a specific client.

        Args:
            session_id: Target session identifier
            message: Message dictionary to send

        Returns:
            True if message was sent, False otherwise
        """
        async with self._lock:
            if session_id in self.active_connections:
                websocket = self.active_connections[session_id]
                try:
                    await websocket.send_json(message)
                    return True
                except Exception as e:
                    logger.warning(f"[WS] Failed to send to {session_id}: {e}")
                    # Connection might be dead, try to disconnect
                    await self.disconnect(session_id)
                    return False
            else:
                # Connection not found, buffer in queue
                if session_id in self.message_queues:
                    try:
                        self.message_queues[session_id].put_nowait(message)
                        logger.debug(f"[WS] Buffered message for {session_id}")
                        return True
                    except asyncio.QueueFull:
                        logger.warning(f"[WS] Queue full for {session_id}, dropping message")
                        return False

        return False

    async def broadcast(
        self,
        message: Dict[str, Any],
        exclude: Optional[Set[str]] = None
    ) -> int:
        """
        Broadcast a message to all connected clients.

        Args:
            message: Message dictionary to broadcast
            exclude: Optional set of session IDs to exclude

        Returns:
            Number of clients the message was sent to
        """
        exclude = exclude or set()
        sent_count = 0

        async with self._lock:
            # Copy keys to avoid modification during iteration
            session_ids = list(self.active_connections.keys())

        for session_id in session_ids:
            if session_id in exclude:
                continue

            if await self.send_message(session_id, message):
                sent_count += 1

        logger.debug(f"[WS] Broadcast sent to {sent_count}/{len(session_ids)} clients")
        return sent_count

    async def send_to_sessions(
        self,
        session_ids: Set[str],
        message: Dict[str, Any]
    ) -> int:
        """
        Send a message to multiple specific sessions.

        Args:
            session_ids: Set of target session identifiers
            message: Message dictionary to send

        Returns:
            Number of clients the message was sent to
        """
        sent_count = 0
        for session_id in session_ids:
            if await self.send_message(session_id, message):
                sent_count += 1

        return sent_count

    async def receive_message(
        self,
        session_id: str,
        timeout: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """
        Receive a message from a specific session's queue.

        Args:
            session_id: Session identifier
            timeout: Seconds to wait for a message

        Returns:
            Message dict or None if timeout
        """
        if session_id in self.message_queues:
            try:
                return await asyncio.wait_for(
                    self.message_queues[session_id].get(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                return None

        return None

    def get_connection_count(self) -> int:
        """
        Get the number of active connections.

        Returns:
            Number of active WebSocket connections
        """
        return len(self.active_connections)

    def get_connection_ids(self) -> Set[str]:
        """
        Get all active session IDs.

        Returns:
            Set of active session identifiers
        """
        return set(self.active_connections.keys())

    def is_connected(self, session_id: str) -> bool:
        """
        Check if a session is connected.

        Args:
            session_id: Session identifier to check

        Returns:
            True if session is connected
        """
        return session_id in self.active_connections

    def get_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a session.

        Args:
            session_id: Session identifier

        Returns:
            Metadata dict or None if not found
        """
        return self.connection_metadata.get(session_id)

    def update_metadata(
        self,
        session_id: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Update metadata for a session.

        Args:
            session_id: Session identifier
            metadata: Metadata to update (merged with existing)

        Returns:
            True if updated, False if session not found
        """
        if session_id in self.connection_metadata:
            self.connection_metadata[session_id].update(metadata)
            return True
        return False

    async def heartbeat(self, session_id: str) -> bool:
        """
        Send a heartbeat ping to a session.

        Args:
            session_id: Session identifier

        Returns:
            True if ping was sent successfully
        """
        return await self.send_message(session_id, {"type": "ping"})

    async def start_heartbeat_monitor(self):
        """
        Start the heartbeat monitoring task.

        Periodically sends pings and cleans up stale connections.
        """
        if self._heartbeat_task is not None:
            logger.warning("[WS] Heartbeat monitor already running")
            return

        async def _heartbeat_loop():
            while True:
                await asyncio.sleep(self.heartbeat_interval)

                # Send pings and check for stale connections
                now = time.time()
                stale_sessions = []

                async with self._lock:
                    for session_id, metadata in list(self.connection_metadata.items()):
                        last_heartbeat = metadata.get("last_heartbeat", 0)

                        # Mark as stale if no heartbeat for too long
                        if now - last_heartbeat > self.connection_timeout:
                            stale_sessions.append(session_id)
                        else:
                            # Send ping
                            await self.send_message(session_id, {"type": "ping"})

                # Clean up stale connections
                for session_id in stale_sessions:
                    logger.info(f"[WS] Cleaning up stale connection: {session_id}")
                    await self.disconnect(session_id)

        self._heartbeat_task = asyncio.create_task(_heartbeat_loop())
        logger.info("[WS] Heartbeat monitor started")

    async def stop_heartbeat_monitor(self):
        """
        Stop the heartbeat monitoring task.
        """
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
            logger.info("[WS] Heartbeat monitor stopped")

    async def cleanup_all(self):
        """
        Clean up all connections and resources.
        """
        logger.info(f"[WS] Cleaning up {self.get_connection_count()} connections")

        # Stop heartbeat
        await self.stop_heartbeat_monitor()

        # Disconnect all clients
        session_ids = list(self.active_connections.keys())
        for session_id in session_ids:
            await self.disconnect(session_id)

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_heartbeat_monitor()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup_all()


# Global WebSocket manager instance
_ws_manager: Optional[WebSocketManager] = None


def get_websocket_manager(
    heartbeat_interval: float = 30.0,
    connection_timeout: float = 120.0,
) -> WebSocketManager:
    """
    Get or create the global WebSocket manager instance.

    Args:
        heartbeat_interval: Seconds between heartbeat pings
        connection_timeout: Seconds before marking connection as stale

    Returns:
        WebSocketManager instance
    """
    global _ws_manager

    if _ws_manager is None:
        _ws_manager = WebSocketManager(
            heartbeat_interval=heartbeat_interval,
            connection_timeout=connection_timeout,
        )
        logger.info("Created global WebSocket manager")

    return _ws_manager
