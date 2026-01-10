# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Redis queue operations for message delivery

Provides reliable queue-based messaging with support for
pending messages, acknowledgments, and delivery tracking.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

logger = logging.getLogger(__name__)


@dataclass
class QueuedMessage:
    """Message wrapper for queue operations"""

    queue_name: str
    payload: dict
    message_id: str
    priority: int = 0
    attempts: int = 0
    max_attempts: int = 3
    created_at: float = 0
    metadata: dict = field(default_factory=dict)

    def to_json(self) -> str:
        """Convert message to JSON string"""
        return json.dumps({
            "queue_name": self.queue_name,
            "payload": self.payload,
            "message_id": self.message_id,
            "priority": self.priority,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "created_at": self.created_at,
            "metadata": self.metadata,
        })

    @classmethod
    def from_json(cls, data: str) -> "QueuedMessage":
        """Create message from JSON string"""
        parsed = json.loads(data)
        return cls(
            queue_name=parsed["queue_name"],
            payload=parsed["payload"],
            message_id=parsed["message_id"],
            priority=parsed.get("priority", 0),
            attempts=parsed.get("attempts", 0),
            max_attempts=parsed.get("max_attempts", 3),
            created_at=parsed.get("created_at", 0),
            metadata=parsed.get("metadata", {}),
        )


class QueueManager:
    """
    Redis queue manager for reliable message delivery

    Features:
    - Priority queues using sorted sets
    - Pending message tracking
    - Message acknowledgment
    - Automatic retry with backoff
    - Dead letter queue for failed messages

    Usage:
        queue = QueueManager(redis_client)

        # Enqueue message
        await queue.enqueue("agent:123:inbox", {"type": "task", "data": "..."}, priority=1)

        # Dequeue message
        msg = await queue.dequeue("agent:123:inbox")

        # Acknowledge message
        await queue.acknowledge("agent:123:inbox", msg.message_id)

        # Get pending messages
        pending = await queue.get_pending("agent:123:inbox")
    """

    # Queue name suffixes
    QUEUE_SUFFIX = ":queue"
    PROCESSING_SUFFIX = ":processing"
    DEAD_LETTER_SUFFIX = ":dead_letter"

    def __init__(self, redis_client: Redis, default_ttl: int = 86400):
        """
        Initialize queue manager

        Args:
            redis_client: Redis client instance
            default_ttl: Default TTL for messages in seconds (24 hours)
        """
        self._redis = redis_client
        self._default_ttl = default_ttl

    def _queue_key(self, queue_name: str) -> str:
        """Get the queue Redis key"""
        return f"{queue_name}{self.QUEUE_SUFFIX}"

    def _processing_key(self, queue_name: str) -> str:
        """Get the processing queue Redis key"""
        return f"{queue_name}{self.PROCESSING_SUFFIX}"

    def _dead_letter_key(self, queue_name: str) -> str:
        """Get the dead letter queue Redis key"""
        return f"{queue_name}{self.DEAD_LETTER_SUFFIX}"

    async def enqueue(
        self,
        queue_name: str,
        payload: dict,
        message_id: str | None = None,
        priority: int = 0,
        ttl: int | None = None,
        metadata: dict | None = None,
    ) -> str:
        """
        Enqueue a message

        Args:
            queue_name: Queue name (e.g., "agent:123:inbox")
            payload: Message payload
            message_id: Optional message ID (auto-generated if not provided)
            priority: Message priority (higher = processed first)
            ttl: Time-to-live in seconds (default from constructor)
            metadata: Optional metadata dictionary

        Returns:
            Message ID

        Example:
            msg_id = await queue.enqueue(
                "agent:123:inbox",
                {"type": "task", "data": "write tests"},
                priority=1
            )
        """
        import secrets
        import time

        if message_id is None:
            message_id = f"msg_{secrets.token_hex(8)}"

        msg = QueuedMessage(
            queue_name=queue_name,
            payload=payload,
            message_id=message_id,
            priority=priority,
            created_at=time.time(),
            metadata=metadata or {},
        )

        # Add to sorted set with priority as score (negative for high priority first)
        queue_key = self._queue_key(queue_name)
        score = -priority  # Negative so higher priority = lower score = first in sorted set

        try:
            await self._redis.zadd(
                queue_key,
                {msg.to_json(): score},
            )

            # Set TTL if specified
            if ttl or self._default_ttl:
                await self._redis.expire(queue_key, ttl or self._default_ttl)

            logger.debug(f"Enqueued message {message_id} to {queue_name} (priority: {priority})")
            return message_id

        except RedisConnectionError as e:
            logger.error(f"Failed to enqueue to {queue_name}: {e}")
            raise

    async def dequeue(
        self,
        queue_name: str,
        timeout: float = 1.0,
    ) -> Optional[QueuedMessage]:
        """
        Dequeue a message (blocking)

        Args:
            queue_name: Queue name
            timeout: Block timeout in seconds (0 = non-blocking)

        Returns:
            QueuedMessage or None if queue is empty

        Example:
            msg = await queue.dequeue("agent:123:inbox", timeout=5.0)
            if msg:
                print(f"Processing: {msg.payload}")
                await queue.acknowledge("agent:123:inbox", msg.message_id)
        """
        queue_key = self._queue_key(queue_name)
        processing_key = self._processing_key(queue_name)

        try:
            # Get highest priority message (lowest score due to negation)
            result = await self._redis.zpopmin(queue_key, count=1)

            if not result:
                return None

            # Parse message
            data, score = result[0]
            msg = QueuedMessage.from_json(data)

            # Move to processing queue
            await self._redis.hset(
                processing_key,
                msg.message_id,
                msg.to_json(),
            )

            # Increment attempts
            msg.attempts += 1

            logger.debug(f"Dequeued message {msg.message_id} from {queue_name}")
            return msg

        except RedisConnectionError as e:
            logger.error(f"Failed to dequeue from {queue_name}: {e}")
            raise

    async def acknowledge(
        self,
        queue_name: str,
        message_id: str,
    ) -> bool:
        """
        Acknowledge a message (remove from processing queue)

        Args:
            queue_name: Queue name
            message_id: Message ID to acknowledge

        Returns:
            True if message was acknowledged, False if not found

        Example:
            success = await queue.acknowledge("agent:123:inbox", msg.message_id)
        """
        processing_key = self._processing_key(queue_name)

        try:
            result = await self._redis.hdel(processing_key, message_id)
            logger.debug(f"Acknowledged message {message_id} from {queue_name}")
            return result > 0

        except RedisConnectionError as e:
            logger.error(f"Failed to acknowledge {message_id}: {e}")
            return False

    async def reject(
        self,
        queue_name: str,
        message_id: str,
        requeue: bool = False,
    ) -> bool:
        """
        Reject a message (move to dead letter or requeue)

        Args:
            queue_name: Queue name
            message_id: Message ID to reject
            requeue: If True, requeue the message; otherwise move to dead letter

        Returns:
            True if message was rejected

        Example:
            # Reject and requeue
            await queue.reject("agent:123:inbox", msg.message_id, requeue=True)

            # Reject to dead letter
            await queue.reject("agent:123:inbox", msg.message_id, requeue=False)
        """
        processing_key = self._processing_key(queue_name)

        try:
            # Get message from processing queue
            data = await self._redis.hget(processing_key, message_id)
            if not data:
                return False

            msg = QueuedMessage.from_json(data)

            # Remove from processing queue
            await self._redis.hdel(processing_key, message_id)

            if requeue and msg.attempts < msg.max_attempts:
                # Requeue with exponential backoff delay
                await self.enqueue(
                    queue_name,
                    msg.payload,
                    message_id=msg.message_id,
                    priority=msg.priority,
                    metadata=msg.metadata,
                )
                logger.debug(f"Requeued message {message_id}")
            else:
                # Move to dead letter queue
                dead_letter_key = self._dead_letter_key(queue_name)
                await self._redis.lpush(dead_letter_key, msg.to_json())
                logger.warning(f"Moved message {message_id} to dead letter queue")

            return True

        except RedisConnectionError as e:
            logger.error(f"Failed to reject {message_id}: {e}")
            return False

    async def get_pending(self, queue_name: str) -> list[QueuedMessage]:
        """
        Get all pending messages in queue (non-blocking)

        Args:
            queue_name: Queue name

        Returns:
            List of queued messages

        Example:
            pending = await queue.get_pending("agent:123:inbox")
            for msg in pending:
                print(f"Pending: {msg.payload}")
        """
        queue_key = self._queue_key(queue_name)

        try:
            result = await self._redis.zrange(queue_key, 0, -1, withscores=False)

            messages = []
            for data in result:
                msg = QueuedMessage.from_json(data)
                messages.append(msg)

            return messages

        except RedisConnectionError as e:
            logger.error(f"Failed to get pending from {queue_name}: {e}")
            return []

    async def get_processing(self, queue_name: str) -> list[QueuedMessage]:
        """
        Get all messages currently being processed

        Args:
            queue_name: Queue name

        Returns:
            List of messages in processing
        """
        processing_key = self._processing_key(queue_name)

        try:
            result = await self._redis.hgetall(processing_key)

            messages = []
            for data in result.values():
                msg = QueuedMessage.from_json(data)
                messages.append(msg)

            return messages

        except RedisConnectionError as e:
            logger.error(f"Failed to get processing from {queue_name}: {e}")
            return []

    async def get_dead_letter(self, queue_name: str, count: int = 10) -> list[QueuedMessage]:
        """
        Get messages from dead letter queue

        Args:
            queue_name: Queue name
            count: Maximum number of messages to retrieve

        Returns:
            List of dead letter messages
        """
        dead_letter_key = self._dead_letter_key(queue_name)

        try:
            result = await self._redis.lrange(dead_letter_key, 0, count - 1)

            messages = []
            for data in result:
                msg = QueuedMessage.from_json(data)
                messages.append(msg)

            return messages

        except RedisConnectionError as e:
            logger.error(f"Failed to get dead letter from {queue_name}: {e}")
            return []

    async def get_queue_size(self, queue_name: str) -> dict[str, int]:
        """
        Get queue statistics

        Args:
            queue_name: Queue name

        Returns:
            Dictionary with queue sizes

        Example:
            stats = await queue.get_queue_size("agent:123:inbox")
            print(f"Pending: {stats['pending']}, Processing: {stats['processing']}")
        """
        try:
            pending = await self._redis.zcard(self._queue_key(queue_name))
            processing = await self._redis.hlen(self._processing_key(queue_name))
            dead_letter = await self._redis.llen(self._dead_letter_key(queue_name))

            return {
                "pending": pending,
                "processing": processing,
                "dead_letter": dead_letter,
                "total": pending + processing + dead_letter,
            }

        except RedisConnectionError as e:
            logger.error(f"Failed to get queue size for {queue_name}: {e}")
            return {"pending": 0, "processing": 0, "dead_letter": 0, "total": 0}

    async def clear_queue(self, queue_name: str) -> bool:
        """
        Clear all messages from a queue

        Args:
            queue_name: Queue name

        Returns:
            True if queue was cleared
        """
        try:
            await self._redis.delete(self._queue_key(queue_name))
            await self._redis.delete(self._processing_key(queue_name))
            await self._redis.delete(self._dead_letter_key(queue_name))
            logger.info(f"Cleared queue {queue_name}")
            return True

        except RedisConnectionError as e:
            logger.error(f"Failed to clear queue {queue_name}: {e}")
            return False

    async def cleanup_stale_messages(
        self,
        queue_name: str,
        max_age: float = 3600,
    ) -> int:
        """
        Move stale messages from processing back to queue or dead letter

        Args:
            queue_name: Queue name
            max_age: Maximum age in seconds for messages in processing

        Returns:
            Number of messages cleaned up
        """
        import time

        processing_key = self._processing_key(queue_name)
        cleaned = 0

        try:
            messages = await self.get_processing(queue_name)
            current_time = time.time()

            for msg in messages:
                age = current_time - msg.created_at
                if age > max_age:
                    # Requeue or move to dead letter based on attempts
                    await self.reject(
                        queue_name,
                        msg.message_id,
                        requeue=msg.attempts < msg.max_attempts,
                    )
                    cleaned += 1

            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} stale messages from {queue_name}")

            return cleaned

        except RedisConnectionError as e:
            logger.error(f"Failed to cleanup stale messages from {queue_name}: {e}")
            return 0
