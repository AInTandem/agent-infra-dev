# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Redis Pub/Sub operations for the message bus

Provides publish/subscribe functionality for real-time messaging
between agents and workspaces.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional, Set

from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Message wrapper for pub/sub"""

    topic: str
    payload: dict
    timestamp: float
    message_id: str

    def to_json(self) -> str:
        """Convert message to JSON string"""
        return json.dumps({
            "topic": self.topic,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "message_id": self.message_id,
        })

    @classmethod
    def from_json(cls, data: str) -> "Message":
        """Create message from JSON string"""
        parsed = json.loads(data)
        return cls(
            topic=parsed["topic"],
            payload=parsed["payload"],
            timestamp=parsed["timestamp"],
            message_id=parsed["message_id"],
        )


class PubSubManager:
    """
    Redis Pub/Sub manager for real-time messaging

    Features:
    - Topic-based publish/subscribe
    - Pattern-based subscription
    - Message callbacks
    - Automatic reconnection
    - Connection health monitoring

    Usage:
        pubsub = PubSubManager(redis_client)

        # Subscribe to topics
        await pubsub.subscribe("agent:123", ["topic1", "topic2"])

        # Register message handler
        pubsub.on_message(lambda msg: print(msg))

        # Publish message
        await pubsub.publish("topic1", {"data": "hello"})

        # Start listening
        await pubsub.start_listening()
    """

    def __init__(self, redis_client: Redis):
        """
        Initialize Pub/Sub manager

        Args:
            redis_client: Redis client instance
        """
        self._redis = redis_client
        self._pubsub = self._redis.pubsub()
        self._subscriptions: dict[str, Set[str]] = {}  # agent_id -> set of topics
        self._message_handlers: list[Callable[[Message], None]] = []
        self._listening = False
        self._listen_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def subscribe(
        self,
        subscriber_id: str,
        topics: list[str] | tuple[str, ...],
    ) -> None:
        """
        Subscribe a subscriber to one or more topics

        Args:
            subscriber_id: Unique identifier for the subscriber (agent_id, sandbox_id, etc.)
            topics: List of topic names to subscribe to

        Example:
            await pubsub.subscribe("agent_123", ["research", "development"])
        """
        async with self._lock:
            # Initialize subscriber if not exists
            if subscriber_id not in self._subscriptions:
                self._subscriptions[subscriber_id] = set()

            # Subscribe to new topics
            for topic in topics:
                if topic not in self._subscriptions[subscriber_id]:
                    await self._pubsub.subscribe(topic)
                    self._subscriptions[subscriber_id].add(topic)
                    logger.debug(f"Subscriber {subscriber_id} subscribed to {topic}")

    async def unsubscribe(
        self,
        subscriber_id: str,
        topics: list[str] | tuple[str, ...] | None = None,
    ) -> None:
        """
        Unsubscribe a subscriber from topics

        Args:
            subscriber_id: Unique identifier for the subscriber
            topics: List of topics to unsubscribe from (None = all topics)

        Example:
            # Unsubscribe from specific topics
            await pubsub.unsubscribe("agent_123", ["research"])

            # Unsubscribe from all topics
            await pubsub.unsubscribe("agent_123")
        """
        async with self._lock:
            if subscriber_id not in self._subscriptions:
                return

            if topics is None:
                # Unsubscribe from all topics
                for topic in self._subscriptions[subscriber_id]:
                    await self._pubsub.unsubscribe(topic)
                del self._subscriptions[subscriber_id]
                logger.debug(f"Subscriber {subscriber_id} unsubscribed from all topics")
            else:
                # Unsubscribe from specific topics
                for topic in topics:
                    if topic in self._subscriptions[subscriber_id]:
                        await self._pubsub.unsubscribe(topic)
                        self._subscriptions[subscriber_id].discard(topic)
                        logger.debug(f"Subscriber {subscriber_id} unsubscribed from {topic}")

                # Remove subscriber if no more subscriptions
                if not self._subscriptions[subscriber_id]:
                    del self._subscriptions[subscriber_id]

    async def publish(
        self,
        topic: str,
        payload: dict,
        message_id: str | None = None,
    ) -> int:
        """
        Publish a message to a topic

        Args:
            topic: Topic name to publish to
            payload: Message payload (dictionary)
            message_id: Optional message ID (auto-generated if not provided)

        Returns:
            Number of subscribers who received the message

        Example:
            count = await pubsub.publish(
                "research",
                {"type": "task", "data": "analyze this code"}
            )
        """
        import time
        import secrets

        msg = Message(
            topic=topic,
            payload=payload,
            timestamp=time.time(),
            message_id=message_id or f"msg_{secrets.token_hex(8)}",
        )

        try:
            # Publish to Redis
            result = await self._redis.publish(topic, msg.to_json())
            logger.debug(f"Published to {topic}: {msg.message_id} ({result} subscribers)")
            return result

        except RedisConnectionError as e:
            logger.error(f"Failed to publish to {topic}: {e}")
            raise

    async def psubscribe(
        self,
        subscriber_id: str,
        patterns: list[str] | tuple[str, ...],
    ) -> None:
        """
        Subscribe to topics matching a pattern

        Args:
            subscriber_id: Unique identifier for the subscriber
            patterns: List of glob patterns to match (e.g., "agent:*", "workspace:ws_*:*")

        Example:
            # Subscribe to all agent messages
            await pubsub.psubscribe("listener_1", ["agent:*"])

            # Subscribe to all topics in a workspace
            await pubsub.psubscribe("listener_2", ["workspace:ws_*:*"])
        """
        async with self._lock:
            if subscriber_id not in self._subscriptions:
                self._subscriptions[subscriber_id] = set()

            for pattern in patterns:
                await self._pubsub.psubscribe(pattern)
                self._subscriptions[subscriber_id].add(f"pattern:{pattern}")
                logger.debug(f"Subscriber {subscriber_id} subscribed to pattern {pattern}")

    def on_message(self, handler: Callable[[Message], None]) -> None:
        """
        Register a message handler callback

        Args:
            handler: Callback function that receives Message objects

        Example:
            def handle_message(msg: Message):
                print(f"Received: {msg.topic} - {msg.payload}")

            pubsub.on_message(handle_message)
        """
        self._message_handlers.append(handler)

    def remove_message_handler(self, handler: Callable[[Message], None]) -> None:
        """
        Remove a registered message handler

        Args:
            handler: The callback function to remove
        """
        if handler in self._message_handlers:
            self._message_handlers.remove(handler)

    async def start_listening(self) -> None:
        """
        Start listening for messages in the background

        This will spawn a background task that listens for messages
        and calls registered handlers.
        """
        if self._listening:
            return

        self._listening = True
        self._listen_task = asyncio.create_task(self._listen_loop())
        logger.info("Started listening for pub/sub messages")

    async def stop_listening(self) -> None:
        """Stop listening for messages"""
        self._listening = False

        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None

        logger.info("Stopped listening for pub/sub messages")

    async def _listen_loop(self) -> None:
        """Main listening loop for processing messages"""
        while self._listening:
            try:
                # Get message with timeout
                message = await self._pubsub.get_message(timeout=1.0)

                if message is None:
                    continue

                # Handle different message types
                if message["type"] in ["message", "pmessage"]:
                    try:
                        # Parse message
                        data = message["data"]
                        if isinstance(data, str):
                            msg = Message.from_json(data)

                            # Call all registered handlers
                            for handler in self._message_handlers:
                                try:
                                    if asyncio.iscoroutinefunction(handler):
                                        await handler(msg)
                                    else:
                                        handler(msg)
                                except Exception as e:
                                    logger.error(f"Message handler error: {e}")
                    except Exception as e:
                        logger.error(f"Failed to process message: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in listen loop: {e}")
                await asyncio.sleep(0.1)

    def get_subscribers(self, topic: str | None = None) -> Set[str]:
        """
        Get list of subscribers

        Args:
            topic: Optional topic filter (returns all subscribers to this topic)

        Returns:
            Set of subscriber IDs
        """
        if topic:
            return {
                sub_id
                for sub_id, topics in self._subscriptions.items()
                if topic in topics
            }
        return set(self._subscriptions.keys())

    def get_subscriptions(self, subscriber_id: str) -> Set[str]:
        """
        Get topics a subscriber is subscribed to

        Args:
            subscriber_id: Subscriber ID

        Returns:
            Set of topic names
        """
        return self._subscriptions.get(subscriber_id, set()).copy()

    async def close(self) -> None:
        """Close pub/sub connection and cleanup"""
        await self.stop_listening()
        await self._pubsub.close()
        self._subscriptions.clear()
        self._message_handlers.clear()
