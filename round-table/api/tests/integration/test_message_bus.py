# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Integration tests for Message Bus Layer

Tests Redis connectivity, Pub/Sub, Queue, and Message Router operations.

These tests require a running Redis instance.
"""

import asyncio
import os
import pytest
import time

from redis.asyncio import Redis, ConnectionPool


# Skip these tests if Redis is not available
pytestmark = pytest.mark.integration


@pytest.fixture
async def redis_client():
    """Create Redis client for testing"""
    # Try to get Redis URL from environment or use default
    redis_url = os.getenv("TEST_REDIS_URL", "redis://localhost:6379/1")

    pool = ConnectionPool.from_url(redis_url, decode_responses=True)
    client = Redis(connection_pool=pool)

    # Test connection
    try:
        await client.ping()
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")

    yield client

    # Cleanup
    await client.close()


class TestRedisConnection:
    """Test Redis connection operations"""

    @pytest.mark.asyncio
    async def test_ping_pong(self, redis_client):
        """Test basic ping/pong"""
        result = await redis_client.ping()
        assert result is True

    @pytest.mark.asyncio
    async def test_set_get(self, redis_client):
        """Test set and get operations"""
        test_key = f"test_key_{time.time()}"
        test_value = "test_value"

        await redis_client.set(test_key, test_value, ex=10)
        result = await redis_client.get(test_key)

        assert result == test_value

        # Cleanup
        await redis_client.delete(test_key)

    @pytest.mark.asyncio
    async def test_sorted_set_operations(self, redis_client):
        """Test sorted set operations (used for queues)"""
        test_key = f"test_queue_{time.time()}"

        # Add items with scores (priority)
        await redis_client.zadd(test_key, {"item1": 1, "item2": 2, "item3": 3})

        # Get items in order
        items = await redis_client.zrange(test_key, 0, -1)
        assert items == ["item1", "item2", "item3"]

        # Get and remove lowest score item
        result = await redis_client.zpopmin(test_key, count=1)
        assert len(result) == 1
        assert result[0][0] == "item1"

        # Cleanup
        await redis_client.delete(test_key)


class TestPubSub:
    """Test Pub/Sub operations"""

    @pytest.mark.asyncio
    async def test_pubsub_subscribe_publish(self, redis_client):
        """Test subscribe and publish"""
        pubsub = redis_client.pubsub()
        channel = f"test_channel_{time.time()}"

        # Subscribe
        await pubsub.subscribe(channel)
        await asyncio.sleep(0.1)  # Give time for subscription to register

        # Publish
        test_message = "test_message"
        subscribers = await redis_client.publish(channel, test_message)
        assert subscribers >= 1

        # Receive
        message = await pubsub.get_message(timeout=1.0)
        assert message is not None
        assert message["type"] == "subscribe"

        message = await pubsub.get_message(timeout=1.0)
        assert message is not None
        assert message["type"] == "message"
        assert message["data"] == test_message

        # Cleanup
        await pubsub.close()


class TestMessageRouter:
    """Test message routing operations"""

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self, redis_client):
        """Test subscribing to topics and publishing"""
        from app.message_bus import MessageRouter, AgentMessage

        router = MessageRouter(redis_client)

        # Subscribe agent to topic
        agent_id = "test_agent_123"
        topic = "test_topic"
        await router.subscribe(agent_id, [topic])

        # Verify subscription
        subscriptions = router.get_subscriptions(agent_id)
        assert topic in subscriptions

        # Publish message
        message = AgentMessage(
            from_agent="sender_agent",
            content={"type": "test", "data": "hello"},
        )

        count = await router.publish(topic, message)
        # At least the test agent should be subscribed
        assert count >= 1

    @pytest.mark.asyncio
    async def test_direct_messaging(self, redis_client):
        """Test direct agent-to-agent messaging"""
        from app.message_bus import MessageRouter, MessageType, DeliveryMode

        router = MessageRouter(redis_client)

        from_agent = "agent_a"
        to_agent = "agent_b"

        # Send direct message
        msg_id = await router.send_direct(
            from_agent=from_agent,
            to_agent=to_agent,
            content={"type": "request", "task": "test"},
            message_type=MessageType.REQUEST,
            delivery_mode=DeliveryMode.QUEUE,
        )

        assert msg_id.startswith("msg_")

        # Get pending messages
        pending = await router.get_pending(to_agent)
        assert len(pending) > 0

        # Verify message content
        found = False
        for msg in pending:
            if msg.message_id == msg_id:
                assert msg.from_agent == from_agent
                assert msg.to_agent == to_agent
                assert msg.content["type"] == "request"
                found = True
                break

        assert found, "Message not found in pending queue"

    @pytest.mark.asyncio
    async def test_broadcast_messaging(self, redis_client):
        """Test workspace broadcast"""
        from app.message_bus import MessageRouter, AgentMessage, MessageType

        router = MessageRouter(redis_client)

        workspace_id = "test_ws_123"
        from_agent = "agent_a"

        # Create separate pubsub connections for each agent to simulate multiple subscribers
        from app.message_bus import PubSubManager

        pubsub1 = PubSubManager(redis_client)
        pubsub2 = PubSubManager(redis_client)

        workspace_topic = f"workspace:{workspace_id}"

        # Subscribe both agents to workspace topic
        await pubsub1.subscribe("agent_b", [workspace_topic])
        await pubsub2.subscribe("agent_c", [workspace_topic])

        # Small delay to ensure subscriptions are registered
        import asyncio
        await asyncio.sleep(0.1)

        # Broadcast message
        count = await router.broadcast(
            from_agent=from_agent,
            workspace_id=workspace_id,
            content={"type": "announcement", "message": "hello all"},
            message_type=MessageType.NOTIFICATION,
        )

        # At least the subscribed agents should receive it
        assert count >= 2, f"Expected at least 2 subscribers, got {count}"

        await pubsub1.close()
        await pubsub2.close()

    @pytest.mark.asyncio
    async def test_queue_operations(self, redis_client):
        """Test queue enqueue/dequeue/acknowledge"""
        from app.message_bus import MessageRouter, DeliveryMode

        router = MessageRouter(redis_client)
        agent_id = "test_agent_queue"

        # Send multiple messages
        msg_ids = []
        for i in range(3):
            msg_id = await router.send_direct(
                from_agent="sender",
                to_agent=agent_id,
                content={"index": i},
                delivery_mode=DeliveryMode.QUEUE,
            )
            msg_ids.append(msg_id)

        # Get pending
        pending = await router.get_pending(agent_id)
        assert len(pending) >= 3

        # Get queue stats
        stats = await router.get_queue_stats(agent_id)
        assert stats["pending"] >= 3

    @pytest.mark.asyncio
    async def test_message_acknowledge(self, redis_client):
        """Test message acknowledgment"""
        from app.message_bus import QueueManager

        queue = QueueManager(redis_client)
        agent_id = "test_agent_ack_unique"

        # Clear any existing data
        queue_name = f"agent:{agent_id}:inbox"
        await queue.clear_queue(queue_name)

        # Enqueue message
        msg_id = await queue.enqueue(
            queue_name,
            {"from": "sender", "content": "test"},
        )

        # Verify it's in the pending queue
        pending = await queue.get_pending(queue_name)
        assert len(pending) >= 1
        assert any(msg.message_id == msg_id for msg in pending)

        # Dequeue the message (moves to processing queue)
        msg = await queue.dequeue(queue_name, timeout=0.5)
        assert msg is not None
        assert msg.message_id == msg_id

        # Now acknowledge from processing queue
        success = await queue.acknowledge(queue_name, msg_id)
        assert success is True

        # Verify message is no longer in processing queue
        processing = await queue.get_processing(queue_name)
        assert len(processing) == 0


class TestHealthChecker:
    """Test health check operations"""

    @pytest.mark.asyncio
    async def test_health_check(self, redis_client):
        """Test health check functionality"""
        from app.message_bus import HealthChecker

        checker = HealthChecker(redis_client)

        result = await checker.check()

        assert result is not None
        assert result.status is not None
        assert result.latency_ms >= 0
        assert result.timestamp > 0

    @pytest.mark.asyncio
    async def test_ping_check(self, redis_client):
        """Test ping health check"""
        from app.message_bus import HealthChecker

        checker = HealthChecker(redis_client)

        result = await checker.check_ping()

        assert result is not None
        assert result.status is not None
        assert "PING" in result.message

    @pytest.mark.asyncio
    async def test_latency_tracking(self, redis_client):
        """Test latency tracking"""
        from app.message_bus import HealthChecker

        checker = HealthChecker(redis_client)

        # Run a few checks
        for _ in range(5):
            await checker.check_ping()

        # Get stats
        stats = checker.get_latency_stats()

        assert stats["count"] == 5
        assert stats["average"] is not None
        assert stats["min"] is not None
        assert stats["max"] is not None


class TestConnectionManager:
    """Test WebSocket connection manager"""

    @pytest.mark.asyncio
    async def test_connection_tracking(self, redis_client):
        """Test connection tracking"""
        from app.websocket import ConnectionManager
        from unittest.mock import AsyncMock, MagicMock

        manager = ConnectionManager()

        # Mock WebSocket
        mock_ws = MagicMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()

        # Create connection
        conn = await manager.connect(
            mock_ws,
            user_id="user_123",
            workspace_id="ws_123",
            agent_id="agent_123",
        )

        assert conn.connection_id.startswith("conn_")
        assert conn.user_id == "user_123"
        assert conn.workspace_id == "ws_123"
        assert conn.agent_id == "agent_123"

        # Verify connection count
        assert manager.get_connection_count() == 1

        # Disconnect
        await manager.disconnect(conn.connection_id)
        assert manager.get_connection_count() == 0

    @pytest.mark.asyncio
    async def test_topic_subscription(self, redis_client):
        """Test topic subscription"""
        from app.websocket import ConnectionManager
        from unittest.mock import AsyncMock, MagicMock

        manager = ConnectionManager()

        # Mock WebSocket
        mock_ws = MagicMock()
        mock_ws.accept = AsyncMock()

        # Create connection
        conn = await manager.connect(mock_ws, agent_id="agent_123")

        # Subscribe to topics
        topics = ["topic1", "topic2"]
        await manager.subscribe(conn.connection_id, topics)

        # Verify subscriptions
        subscribers = manager.get_connections_by_topic("topic1")
        assert conn.connection_id in subscribers

        # Unsubscribe
        await manager.unsubscribe(conn.connection_id, ["topic1"])
        subscribers = manager.get_connections_by_topic("topic1")
        assert conn.connection_id not in subscribers

        # Cleanup
        await manager.disconnect(conn.connection_id)

    @pytest.mark.asyncio
    async def test_broadcast_to_topic(self, redis_client):
        """Test broadcasting to topic subscribers"""
        from app.websocket import ConnectionManager
        from unittest.mock import AsyncMock, MagicMock

        manager = ConnectionManager()

        # Mock WebSockets
        mock_ws1 = MagicMock()
        mock_ws1.accept = AsyncMock()
        mock_ws1.send_json = AsyncMock(return_value=True)

        mock_ws2 = MagicMock()
        mock_ws2.accept = AsyncMock()
        mock_ws2.send_json = AsyncMock(return_value=True)

        # Create connections
        conn1 = await manager.connect(mock_ws1, agent_id="agent_1")
        conn2 = await manager.connect(mock_ws2, agent_id="agent_2")

        # Subscribe to same topic
        await manager.subscribe(conn1.connection_id, ["test_topic"])
        await manager.subscribe(conn2.connection_id, ["test_topic"])

        # Broadcast
        test_data = {"message": "hello"}
        count = await manager.broadcast_to_topic("test_topic", test_data)

        assert count == 2

        # Verify both received message
        mock_ws1.send_json.assert_called_once()
        mock_ws2.send_json.assert_called_once()

        # Cleanup
        await manager.disconnect(conn1.connection_id)
        await manager.disconnect(conn2.connection_id)


# Run tests if this file is executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
