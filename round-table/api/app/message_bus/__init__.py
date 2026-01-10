# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Message Bus Layer - Redis-based pub/sub and messaging

This module provides Redis-based message bus functionality for the Round Table
collaboration bus, including:
- Connection pooling and management
- Pub/Sub operations
- Message queues
- Health checks
"""

from .client import RedisClient, get_redis_client, close_redis_client
from .pubsub import PubSubManager, Message
from .queue import QueueManager, QueuedMessage
from .health import HealthChecker, HealthStatus, HealthCheckResult
from .router import MessageRouter, AgentMessage, MessageType, DeliveryMode

__all__ = [
    "RedisClient",
    "get_redis_client",
    "close_redis_client",
    "PubSubManager",
    "Message",
    "QueueManager",
    "QueuedMessage",
    "HealthChecker",
    "HealthStatus",
    "HealthCheckResult",
    "MessageRouter",
    "AgentMessage",
    "MessageType",
    "DeliveryMode",
]
