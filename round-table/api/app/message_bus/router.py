# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Message router for topic-based routing and direct messaging

Integrates Pub/Sub and Queue operations to provide unified messaging
with support for topics, direct messages, and broadcast.
"""

import logging
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from redis.asyncio import Redis

from .pubsub import PubSubManager, Message
from .queue import QueueManager

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Message type enumeration"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    COMMAND = "command"


class DeliveryMode(Enum):
    """Message delivery mode"""
    PUBSUB = "pubsub"  # Real-time pub/sub
    QUEUE = "queue"  # Reliable queue delivery
    BOTH = "both"  # Both pub/sub and queue


@dataclass
class AgentMessage:
    """
    Message structure for agent communication

    Attributes:
        from_agent: Sender agent ID
        to_agent: Recipient agent ID (None for broadcast/topic)
        workspace_id: Workspace ID
        content: Message content (dict)
        message_type: Type of message
        message_id: Unique message ID
        timestamp: Message timestamp
        delivery_mode: Delivery mode
        priority: Message priority (for queue)
        metadata: Additional metadata
    """
    from_agent: str
    content: dict
    to_agent: Optional[str] = None
    workspace_id: Optional[str] = None
    message_type: MessageType = field(default_factory=lambda: MessageType.NOTIFICATION)
    message_id: str = field(default_factory=lambda: f"msg_{secrets.token_hex(8)}")
    timestamp: float = field(default_factory=time.time)
    delivery_mode: DeliveryMode = field(default_factory=lambda: DeliveryMode.PUBSUB)
    priority: int = 0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "workspace_id": self.workspace_id,
            "content": self.content,
            "message_type": self.message_type.value if isinstance(self.message_type, MessageType) else self.message_type,
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "priority": self.priority,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AgentMessage":
        """Create from dictionary"""
        # Handle message_type conversion
        msg_type = data.get("message_type", "notification")
        if isinstance(msg_type, str):
            try:
                msg_type = MessageType(msg_type)
            except ValueError:
                msg_type = MessageType.NOTIFICATION

        return cls(
            from_agent=data["from_agent"],
            to_agent=data.get("to_agent"),
            workspace_id=data.get("workspace_id"),
            content=data["content"],
            message_type=msg_type,
            message_id=data.get("message_id", f"msg_{secrets.token_hex(8)}"),
            timestamp=data.get("timestamp", time.time()),
            priority=data.get("priority", 0),
            metadata=data.get("metadata", {}),
        )


class MessageRouter:
    """
    Message router for agent communication

    Features:
    - Topic-based publish/subscribe
    - Direct messaging (agent to agent)
    - Broadcast messaging (workspace-wide)
    - Reliable queue delivery
    - Real-time pub/sub delivery
    - Message acknowledgment tracking

    Usage:
        router = MessageRouter(redis_client)

        # Subscribe agent to topics
        await router.subscribe("agent_123", ["research", "development"])

        # Send direct message
        await router.send_direct(
            from_agent="agent_123",
            to_agent="agent_456",
            content={"type": "request", "data": "..."}
        )

        # Publish to topic
        await router.publish("research", AgentMessage(...))

        # Get pending messages
        messages = await router.get_pending("agent_123")
    """

    # Topic prefixes
    AGENT_TOPIC_PREFIX = "agent:"
    WORKSPACE_TOPIC_PREFIX = "workspace:"
    BROADCAST_TOPIC = "broadcast"

    def __init__(self, redis_client: Redis):
        """
        Initialize message router

        Args:
            redis_client: Redis client instance
        """
        self._redis = redis_client
        self._pubsub = PubSubManager(redis_client)
        self._queue = QueueManager(redis_client)
        self._subscriptions: dict[str, set[str]] = {}

    async def subscribe(
        self,
        agent_id: str,
        topics: list[str] | tuple[str, ...],
    ) -> None:
        """
        Subscribe an agent to topics

        Args:
            agent_id: Agent ID
            topics: List of topic names

        Example:
            await router.subscribe("agent_123", ["research", "development"])
        """
        # Build full topic names
        full_topics = [f"{self.AGENT_TOPIC_PREFIX}{topic}" for topic in topics]

        # Subscribe via pub/sub
        await self._pubsub.subscribe(agent_id, full_topics)

        # Track subscriptions
        if agent_id not in self._subscriptions:
            self._subscriptions[agent_id] = set()
        self._subscriptions[agent_id].update(topics)

        logger.info(f"Agent {agent_id} subscribed to topics: {topics}")

    async def unsubscribe(
        self,
        agent_id: str,
        topics: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        """
        Unsubscribe an agent from topics

        Args:
            agent_id: Agent ID
            topics: List of topics (None = unsubscribe from all)

        Example:
            await router.unsubscribe("agent_123", ["research"])
        """
        if agent_id not in self._subscriptions:
            return

        if topics is None:
            # Unsubscribe from all
            all_topics = list(self._subscriptions[agent_id])
            full_topics = [f"{self.AGENT_TOPIC_PREFIX}{t}" for t in all_topics]
            await self._pubsub.unsubscribe(agent_id, full_topics)
            del self._subscriptions[agent_id]
        else:
            # Unsubscribe from specific topics
            full_topics = [f"{self.AGENT_TOPIC_PREFIX}{t}" for t in topics]
            await self._pubsub.unsubscribe(agent_id, full_topics)
            self._subscriptions[agent_id].difference_update(topics)

            if not self._subscriptions[agent_id]:
                del self._subscriptions[agent_id]

        logger.info(f"Agent {agent_id} unsubscribed from topics: {topics}")

    async def publish(
        self,
        topic: str,
        message: AgentMessage,
    ) -> int:
        """
        Publish a message to a topic

        Args:
            topic: Topic name (without prefix)
            message: AgentMessage to publish

        Returns:
            Number of subscribers who received the message

        Example:
            msg = AgentMessage(
                from_agent="agent_123",
                content={"type": "update", "data": "..."}
            )
            count = await router.publish("research", msg)
        """
        full_topic = f"{self.AGENT_TOPIC_PREFIX}{topic}"

        if message.delivery_mode in (DeliveryMode.PUBSUB, DeliveryMode.BOTH):
            # Publish via pub/sub
            count = await self._pubsub.publish(
                full_topic,
                message.to_dict(),
                message_id=message.message_id,
            )
            logger.debug(f"Published {message.message_id} to {topic} ({count} subscribers)")
            return count
        else:
            # Queue only - count subscribers
            subscribers = self._pubsub.get_subscribers(full_topic)
            return len(subscribers)

    async def send_direct(
        self,
        from_agent: str,
        to_agent: str,
        content: dict,
        message_type: MessageType = MessageType.REQUEST,
        delivery_mode: DeliveryMode = DeliveryMode.BOTH,
        priority: int = 0,
    ) -> str:
        """
        Send a direct message from one agent to another

        Args:
            from_agent: Sender agent ID
            to_agent: Recipient agent ID
            content: Message content
            message_type: Type of message
            delivery_mode: Delivery mode
            priority: Message priority (for queue)

        Returns:
            Message ID

        Example:
            msg_id = await router.send_direct(
                from_agent="agent_123",
                to_agent="agent_456",
                content={"type": "request", "task": "..."}
            )
        """
        message = AgentMessage(
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            message_type=message_type,
            delivery_mode=delivery_mode,
            priority=priority,
        )

        recipient_queue = f"{self.AGENT_TOPIC_PREFIX}{to_agent}:inbox"

        if delivery_mode in (DeliveryMode.QUEUE, DeliveryMode.BOTH):
            # Queue for reliable delivery
            await self._queue.enqueue(
                recipient_queue,
                message.to_dict(),
                message_id=message.message_id,
                priority=priority,
            )

        if delivery_mode in (DeliveryMode.PUBSUB, DeliveryMode.BOTH):
            # Also publish via pub/sub for real-time delivery
            await self._pubsub.publish(
                recipient_queue,
                message.to_dict(),
                message_id=message.message_id,
            )

        logger.info(f"Direct message {message.message_id}: {from_agent} -> {to_agent}")
        return message.message_id

    async def broadcast(
        self,
        from_agent: str,
        workspace_id: str,
        content: dict,
        message_type: MessageType = MessageType.NOTIFICATION,
        exclude_agent: str | None = None,
    ) -> int:
        """
        Broadcast a message to all agents in a workspace

        Args:
            from_agent: Sender agent ID
            workspace_id: Workspace ID
            content: Message content
            message_type: Type of message
            exclude_agent: Optional agent ID to exclude from broadcast

        Returns:
            Number of agents that received the message

        Example:
            count = await router.broadcast(
                from_agent="agent_123",
                workspace_id="ws_abc",
                content={"type": "announcement", "message": "..."}
            )
        """
        message = AgentMessage(
            from_agent=from_agent,
            workspace_id=workspace_id,
            content=content,
            message_type=message_type,
            delivery_mode=DeliveryMode.PUBSUB,
        )

        topic = f"{self.WORKSPACE_TOPIC_PREFIX}{workspace_id}"

        # Publish to workspace topic
        count = await self._pubsub.publish(
            topic,
            message.to_dict(),
            message_id=message.message_id,
        )

        logger.info(f"Broadcast {message.message_id} to workspace {workspace_id} ({count} agents)")
        return count

    async def get_pending(self, agent_id: str, limit: int = 100) -> list[AgentMessage]:
        """
        Get pending messages for an agent

        Args:
            agent_id: Agent ID
            limit: Maximum number of messages to retrieve

        Returns:
            List of pending AgentMessage objects

        Example:
            messages = await router.get_pending("agent_123")
            for msg in messages:
                print(f"From: {msg.from_agent}, Content: {msg.content}")
        """
        queue_name = f"{self.AGENT_TOPIC_PREFIX}{agent_id}:inbox"

        pending = await self._queue.get_pending(queue_name)

        # Convert to AgentMessage objects
        messages = []
        for queued_msg in pending[:limit]:
            agent_msg = AgentMessage.from_dict(queued_msg.payload)
            messages.append(agent_msg)

        return messages

    async def acknowledge(
        self,
        agent_id: str,
        message_id: str,
    ) -> bool:
        """
        Acknowledge a message (remove from queue)

        Args:
            agent_id: Agent ID
            message_id: Message ID to acknowledge

        Returns:
            True if acknowledged successfully

        Example:
            success = await router.acknowledge("agent_123", msg.message_id)
        """
        queue_name = f"{self.AGENT_TOPIC_PREFIX}{agent_id}:inbox"
        return await self._queue.acknowledge(queue_name, message_id)

    async def reject(
        self,
        agent_id: str,
        message_id: str,
        requeue: bool = False,
    ) -> bool:
        """
        Reject a message (move to dead letter or requeue)

        Args:
            agent_id: Agent ID
            message_id: Message ID to reject
            requeue: If True, requeue the message

        Returns:
            True if rejected successfully

        Example:
            await router.reject("agent_123", msg.message_id, requeue=True)
        """
        queue_name = f"{self.AGENT_TOPIC_PREFIX}{agent_id}:inbox"
        return await self._queue.reject(queue_name, message_id, requeue=requeue)

    def on_message(self, callback):
        """
        Register a callback for pub/sub messages

        Args:
            callback: Function to call when message received

        Example:
            def handle_message(msg: Message):
                agent_msg = AgentMessage.from_dict(msg.payload)
                print(f"Received: {agent_msg.content}")

            router.on_message(handle_message)
        """
        def wrapper(message: Message):
            agent_msg = AgentMessage.from_dict(message.payload)
            callback(agent_msg)

        self._pubsub.on_message(wrapper)

    async def start_listening(self) -> None:
        """Start listening for pub/sub messages"""
        await self._pubsub.start_listening()

    async def stop_listening(self) -> None:
        """Stop listening for pub/sub messages"""
        await self._pubsub.stop_listening()

    def get_subscribers(self, topic: str) -> set[str]:
        """
        Get subscribers for a topic

        Args:
            topic: Topic name (without prefix)

        Returns:
            Set of agent IDs
        """
        full_topic = f"{self.AGENT_TOPIC_PREFIX}{topic}"
        return self._pubsub.get_subscribers(full_topic)

    def get_subscriptions(self, agent_id: str) -> set[str]:
        """
        Get topics an agent is subscribed to

        Args:
            agent_id: Agent ID

        Returns:
            Set of topic names
        """
        return self._subscriptions.get(agent_id, set()).copy()

    async def get_queue_stats(self, agent_id: str) -> dict:
        """
        Get queue statistics for an agent

        Args:
            agent_id: Agent ID

        Returns:
            Dictionary with queue statistics

        Example:
            stats = await router.get_queue_stats("agent_123")
            print(f"Pending: {stats['pending']}")
        """
        queue_name = f"{self.AGENT_TOPIC_PREFIX}{agent_id}:inbox"
        return await self._queue.get_queue_size(queue_name)

    async def cleanup_stale_messages(
        self,
        agent_id: str,
        max_age: float = 3600,
    ) -> int:
        """
        Clean up stale messages for an agent

        Args:
            agent_id: Agent ID
            max_age: Maximum age in seconds

        Returns:
            Number of messages cleaned up
        """
        queue_name = f"{self.AGENT_TOPIC_PREFIX}{agent_id}:inbox"
        return await self._queue.cleanup_stale_messages(queue_name, max_age)

    async def close(self) -> None:
        """Close the message router and cleanup resources"""
        await self._pubsub.close()
