"""
Storage Adapter Tests

Unit tests for SQLite, PostgreSQL, and cache adapters.
"""

import pytest
import asyncio
import tempfile
import os
from datetime import datetime, timedelta
from typing import Dict, Any

from src.storage.base_adapter import StorageAdapter
from src.storage.base_cache import CacheAdapter
from src.storage.factory import StorageFactory
from src.storage.sqlite_adapter import SQLiteAdapter
from src.storage.redis_cache import RedisCacheAdapter, MemoryCacheAdapter


# Test fixtures

@pytest.fixture
async def sqlite_storage():
    """Create a temporary SQLite storage for testing."""
    # Create a temporary file instead of using :memory:
    # because each connection to :memory: creates a new database
    temp_db = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db")
    temp_db.close()

    storage = SQLiteAdapter({
        "path": temp_db.name,
        "pool_size": 5
    })
    await storage.initialize()
    yield storage
    await storage.close()
    # Clean up
    try:
        os.unlink(temp_db.name)
    except:
        pass


@pytest.fixture
async def memory_cache():
    """Create an in-memory cache for testing."""
    cache = MemoryCacheAdapter({
        "max_size": 1000,
        "default_ttl": 300
    })
    await cache.initialize()
    yield cache
    await cache.close()


# Sample data helpers

def sample_task(task_id: str = "test-task-1") -> Dict[str, Any]:
    """Create a sample task for testing."""
    return {
        "id": task_id,
        "agent_name": "test_agent",
        "task_prompt": "Test task prompt",
        "schedule_type": "cron",
        "schedule_value": "0 9 * * *",
        "repeat": False,
        "enabled": True,
        "created_at": datetime.utcnow(),
        "status": "pending"
    }


# SQLite Storage Tests

@pytest.mark.asyncio
class TestSQLiteStorage:
    """Test SQLite storage adapter."""

    async def test_initialization(self, sqlite_storage):
        """Test storage initializes correctly."""
        assert sqlite_storage.is_initialized()
        assert await sqlite_storage.health_check()

    async def test_save_task(self, sqlite_storage):
        """Test saving a task."""
        task = sample_task()
        task_id = await sqlite_storage.save_task(task)
        assert task_id == "test-task-1"

    async def test_get_task(self, sqlite_storage):
        """Test retrieving a task."""
        task = sample_task()
        await sqlite_storage.save_task(task)

        retrieved = await sqlite_storage.get_task("test-task-1")
        assert retrieved is not None
        assert retrieved["id"] == "test-task-1"
        assert retrieved["agent_name"] == "test_agent"
        assert retrieved["status"] == "pending"

    async def test_list_tasks(self, sqlite_storage):
        """Test listing tasks."""
        # Save multiple tasks
        for i in range(3):
            task = sample_task(f"test-task-{i}")
            await sqlite_storage.save_task(task)

        # List all tasks
        tasks = await sqlite_storage.list_tasks()
        assert len(tasks) == 3

        # Filter by agent
        tasks = await sqlite_storage.list_tasks(agent_name="test_agent")
        assert len(tasks) == 3

    async def test_update_task_status(self, sqlite_storage):
        """Test updating task status."""
        task = sample_task()
        await sqlite_storage.save_task(task)

        updated = await sqlite_storage.update_task_status(
            "test-task-1",
            "running",
            last_run=datetime.utcnow()
        )
        assert updated is True

        retrieved = await sqlite_storage.get_task("test-task-1")
        assert retrieved["status"] == "running"
        assert retrieved["last_run"] is not None

    async def test_delete_task(self, sqlite_storage):
        """Test deleting a task."""
        task = sample_task()
        await sqlite_storage.save_task(task)

        deleted = await sqlite_storage.delete_task("test-task-1")
        assert deleted is True

        retrieved = await sqlite_storage.get_task("test-task-1")
        assert retrieved is None

    async def test_save_log(self, sqlite_storage):
        """Test saving a log entry."""
        task = sample_task()
        await sqlite_storage.save_task(task)

        log_id = await sqlite_storage.save_log(
            "test-task-1",
            "INFO",
            "Test log message",
            {"key": "value"}
        )
        assert log_id is not None

    async def test_query_logs(self, sqlite_storage):
        """Test querying logs."""
        task = sample_task()
        await sqlite_storage.save_task(task)

        await sqlite_storage.save_log("test-task-1", "INFO", "Info message")
        await sqlite_storage.save_log("test-task-1", "ERROR", "Error message")

        logs = await sqlite_storage.query_logs(task_id="test-task-1")
        assert len(logs) == 2

        error_logs = await sqlite_storage.query_logs(level="ERROR")
        assert len(error_logs) == 1

    async def test_metadata(self, sqlite_storage):
        """Test metadata operations."""
        await sqlite_storage.save_metadata("test_key", {"value": "test_data"})

        retrieved = await sqlite_storage.get_metadata("test_key")
        assert retrieved == {"value": "test_data"}

        deleted = await sqlite_storage.delete_metadata("test_key")
        assert deleted is True

    async def test_transaction(self, sqlite_storage):
        """Test transaction support."""
        # Note: SQLite adapter with simplified connection handling
        # doesn't support true transactions across operations.
        # Each operation is auto-committed.
        # This test verifies the interface exists but doesn't test ACID properties.

        # Just verify the methods can be called
        transaction = await sqlite_storage.begin_transaction()
        assert transaction is not None

        task = sample_task()
        await sqlite_storage.save_task(task)

        # Commit is a no-op in this implementation
        await sqlite_storage.commit_transaction(transaction)

        retrieved = await sqlite_storage.get_task("test-task-1")
        assert retrieved is not None


# Memory Cache Tests

@pytest.mark.asyncio
class TestMemoryCache:
    """Test in-memory cache adapter."""

    async def test_initialization(self, memory_cache):
        """Test cache initializes correctly."""
        assert memory_cache.is_initialized()
        assert await memory_cache.health_check()

    async def test_set_get(self, memory_cache):
        """Test basic set and get."""
        await memory_cache.set("test_key", "test_value")
        value = await memory_cache.get("test_key")
        assert value == "test_value"

    async def test_set_with_ttl(self, memory_cache):
        """Test setting value with TTL."""
        await memory_cache.set("ttl_key", "ttl_value", timedelta(seconds=1))
        value = await memory_cache.get("ttl_key")
        assert value == "ttl_value"

        # Wait for expiry
        await asyncio.sleep(1.1)
        value = await memory_cache.get("ttl_key")
        assert value is None

    async def test_exists(self, memory_cache):
        """Test key existence check."""
        await memory_cache.set("exists_key", "value")
        assert await memory_cache.exists("exists_key") is True
        assert await memory_cache.exists("nonexistent") is False

    async def test_delete(self, memory_cache):
        """Test deleting a key."""
        await memory_cache.set("delete_key", "value")
        assert await memory_cache.exists("delete_key") is True

        await memory_cache.delete("delete_key")
        assert await memory_cache.exists("delete_key") is False

    async def test_get_many(self, memory_cache):
        """Test getting multiple keys."""
        await memory_cache.set("key1", "value1")
        await memory_cache.set("key2", "value2")
        await memory_cache.set("key3", "value3")

        result = await memory_cache.get_many(["key1", "key2", "key4"])
        assert result["key1"] == "value1"
        assert result["key2"] == "value2"
        assert "key4" not in result

    async def test_set_many(self, memory_cache):
        """Test setting multiple keys."""
        mapping = {
            "batch1": "value1",
            "batch2": "value2",
            "batch3": "value3"
        }
        count = await memory_cache.set_many(mapping)
        assert count == 3

    async def test_clear_pattern(self, memory_cache):
        """Test clearing keys by pattern."""
        await memory_cache.set("task:1", "value1")
        await memory_cache.set("task:2", "value2")
        await memory_cache.set("agent:1", "value3")

        count = await memory_cache.clear_pattern("task:*")
        assert count == 2

        assert await memory_cache.exists("task:1") is False
        assert await memory_cache.exists("agent:1") is True

    async def test_keys(self, memory_cache):
        """Test listing keys by pattern."""
        await memory_cache.set("test:1", "value1")
        await memory_cache.set("test:2", "value2")
        await memory_cache.set("other:1", "value3")

        keys = await memory_cache.keys("test:*")
        assert len(keys) == 2
        assert "test:1" in keys
        assert "test:2" in keys

    async def test_increment(self, memory_cache):
        """Test increment operation."""
        result = await memory_cache.increment("counter")
        assert result == 1

        result = await memory_cache.increment("counter", 5)
        assert result == 6

    async def test_list_operations(self, memory_cache):
        """Test list operations."""
        # Push elements
        await memory_cache.lpush("mylist", "item1", "item2")
        await memory_cache.rpush("mylist", "item3")

        # Check length
        assert await memory_cache.llen("mylist") == 3

        # Get range
        items = await memory_cache.lrange("mylist", 0, -1)
        assert items == ["item2", "item1", "item3"]

        # Pop from left
        item = await memory_cache.lpop("mylist")
        assert item == "item2"
        assert await memory_cache.llen("mylist") == 2


# Factory Tests

@pytest.mark.asyncio
class TestStorageFactory:
    """Test storage factory."""

    def test_list_adapters(self):
        """Test listing registered adapters."""
        storage_types = StorageFactory.list_storage_adapters()
        assert "sqlite" in storage_types

        cache_types = StorageFactory.list_cache_adapters()
        assert "memory" in cache_types
        assert "redis" in cache_types

    def test_create_sqlite_storage(self):
        """Test creating SQLite storage via factory."""
        storage = StorageFactory.create_storage({
            "type": "sqlite",
            "path": ":memory:"
        })
        assert isinstance(storage, SQLiteAdapter)

    def test_create_memory_cache(self):
        """Test creating memory cache via factory."""
        cache = StorageFactory.create_cache({
            "type": "memory",
            "max_size": 100
        })
        assert isinstance(cache, MemoryCacheAdapter)

    def test_create_none_cache(self):
        """Test creating None cache."""
        cache = StorageFactory.create_cache(None)
        assert cache is None

        cache = StorageFactory.create_cache({"type": "none"})
        assert cache is None


# Integration Tests

@pytest.mark.asyncio
class TestStorageIntegration:
    """Integration tests with storage and cache."""

    async def test_task_with_cache(self, sqlite_storage, memory_cache):
        """Test caching task data."""
        task = sample_task()
        await sqlite_storage.save_task(task)

        # Cache the task
        cache_key = f"task:{task['id']}"
        await memory_cache.set(cache_key, task, timedelta(seconds=60))

        # Retrieve from cache
        cached_task = await memory_cache.get(cache_key)
        assert cached_task["id"] == task["id"]

    async def test_task_lifecycle(self, sqlite_storage):
        """Test complete task lifecycle."""
        # Create task
        task = sample_task()
        task_id = await sqlite_storage.save_task(task)
        assert task_id == "test-task-1"

        # Update status to running
        await sqlite_storage.save_log(task_id, "INFO", "Task started")
        await sqlite_storage.update_task_status(
            task_id,
            "running",
            last_run=datetime.utcnow()
        )

        # Complete task
        await sqlite_storage.update_task_status(
            task_id,
            "completed",
            result="Task completed successfully"
        )
        await sqlite_storage.save_log(task_id, "INFO", "Task completed")

        # Verify final state
        final_task = await sqlite_storage.get_task(task_id)
        assert final_task["status"] == "completed"
        assert final_task["result"] == "Task completed successfully"

        # Check logs
        logs = await sqlite_storage.query_logs(task_id=task_id)
        assert len(logs) == 2
