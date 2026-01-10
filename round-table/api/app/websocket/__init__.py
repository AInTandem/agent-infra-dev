# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
WebSocket connection management for real-time communication

Provides WebSocket connection management with topic subscription,
message streaming, and connection lifecycle management.
"""

from .manager import ConnectionManager, WebSocketConnection
from .handler import MessageHandler
from .routes import websocket_router, get_connection_manager

__all__ = [
    "ConnectionManager",
    "WebSocketConnection",
    "MessageHandler",
    "websocket_router",
    "get_connection_manager",
]
