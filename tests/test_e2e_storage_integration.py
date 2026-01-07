#!/usr/bin/env python3
"""
End-to-end integration test for Storage Adapter Layer.

Tests the complete flow from config loading to adapter creation and usage.
"""

import asyncio
import sys
import tempfile
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import ConfigManager
from core.task_scheduler import TaskScheduler
from core.agent_manager import AgentManager
from core.storage_helpers import create_storage_from_config, create_cache_from_config
from core.task_models import ScheduleType
from storage.factory import StorageFactory
from storage.redis_cache import MemoryCacheAdapter


async def test_e2e_with_sqlite_and_memory_cache():
    """Test E2E with SQLite storage and MemoryCache."""
    print("=" * 60)
    print("E2E Test: SQLite Storage + MemoryCache")
    print("=" * 60)

    # Create temporary config
    temp_db = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db")
    temp_db.close()

    temp_config = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml")
    temp_config.write(f"""
storage:
  type: sqlite
  sqlite:
    path: "{temp_db.name}"
cache:
  type: memory
  max_size: 1000
  default_ttl: 300
""")
    temp_config.close()

    try:
        # Load config
        config = ConfigManager()
        config._storage_config = config.load_storage_config.__func__(config)
        # Manually set the config
        import yaml
        with open(temp_config.name, "r") as f:
            config._storage_config = yaml.safe_load(f)

        # Create adapters from config
        storage = await create_storage_from_config(config)
        cache = await create_cache_from_config(config)

        print("✓ Created adapters from config")
        print(f"  Storage: {type(storage).__name__}")
        print(f"  Cache: {type(cache).__name__}")

        # Create TaskScheduler with storage
        scheduler = TaskScheduler(config, storage_adapter=storage)
        await scheduler.start()
        print("✓ Started TaskScheduler with SQLite storage")

        # Create a task
        task = await scheduler.schedule_task(
            name="E2E Test Task",
            agent_name="test",
            task_prompt="Test prompt for E2E",
            schedule_type=ScheduleType.CRON,
            schedule_value="0 9 * * *",
            enabled=False,
        )
        print(f"✓ Created task: {task.id}")

        # Verify task in database
        db_task = await storage.get_task(task.id)
        assert db_task is not None
        assert db_task["name"] == "E2E Test Task"
        print("✓ Verified task in database")

        # Create AgentManager with cache
        agent_manager = AgentManager(config, cache_adapter=cache)
        await agent_manager.initialize()
        print("✓ Started AgentManager with MemoryCache")

        # Verify cache is available
        assert agent_manager.has_cache
        print("✓ Verified cache is available")

        # Test cache operations
        cache_stats = await agent_manager.get_cache_stats()
        print(f"✓ Cache stats: {cache_stats}")

        # Cleanup
        await scheduler.stop()
        await cache.close()
        await storage.close()
        print("✓ Cleaned up resources")

        print()
        return True

    finally:
        os.unlink(temp_config.name)
        try:
            os.unlink(temp_db.name)
        except:
            pass


async def test_e2e_backward_compatible():
    """Test E2E with file-based storage (backward compatibility)."""
    print("=" * 60)
    print("E2E Test: File-based Storage (Backward Compatible)")
    print("=" * 60)

    # Create config with file-based storage
    temp_config = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml")
    temp_config.write("""
storage:
  type: file
cache:
  type: none
""")
    temp_config.close()

    try:
        # Load config
        config = ConfigManager()
        import yaml
        with open(temp_config.name, "r") as f:
            config._storage_config = yaml.safe_load(f)

        # Create adapters from config
        storage = await create_storage_from_config(config)
        cache = await create_cache_from_config(config)

        print("✓ Created adapters from config")
        print(f"  Storage: {storage}")  # Should be None
        print(f"  Cache: {cache}")  # Should be None

        # Create TaskScheduler without storage adapter
        scheduler = TaskScheduler(config, storage_adapter=storage)
        await scheduler.start()
        print("✓ Started TaskScheduler with file-based storage")

        # Create a task
        task = await scheduler.schedule_task(
            name="File-based Task",
            agent_name="test",
            task_prompt="Test prompt for file storage",
            schedule_type=ScheduleType.CRON,
            schedule_value="0 9 * * *",
            enabled=False,
        )
        print(f"✓ Created task: {task.id}")

        # Verify task is in memory
        assert scheduler.get_task(task.id) is not None
        print("✓ Verified task in scheduler")

        # Create AgentManager without cache
        agent_manager = AgentManager(config, cache_adapter=cache)
        await agent_manager.initialize()
        print("✓ Started AgentManager without cache")

        # Verify cache is not available
        assert not agent_manager.has_cache
        print("✓ Verified cache is not available")

        # Cleanup
        await scheduler.stop()
        print("✓ Cleaned up resources")

        print()
        return True

    finally:
        os.unlink(temp_config.name)


async def test_e2e_factory_registration():
    """Test that all adapters are registered in factory."""
    print("=" * 60)
    print("E2E Test: Factory Registration")
    print("=" * 60)

    # Import storage module to trigger registration
    from storage import sqlite_adapter, postgres_adapter, redis_cache

    # Check registered adapters
    storage_types = StorageFactory.list_storage_adapters()
    cache_types = StorageFactory.list_cache_adapters()

    print(f"✓ Registered storage adapters: {storage_types}")
    print(f"✓ Registered cache adapters: {cache_types}")

    # Verify required adapters are registered
    assert "sqlite" in storage_types
    assert "postgresql" in storage_types
    assert "memory" in cache_types
    assert "redis" in cache_types
    print("✓ All required adapters are registered")

    print()
    return True


async def main():
    """Run all E2E tests."""
    print()
    print("=" * 60)
    print("Storage Adapter Layer - E2E Integration Tests")
    print("=" * 60)
    print()

    results = []

    results.append(await test_e2e_factory_registration())
    results.append(await test_e2e_with_sqlite_and_memory_cache())
    results.append(await test_e2e_backward_compatible())

    print("=" * 60)
    if all(results):
        print("All E2E Tests Passed! ✓")
    else:
        print("Some E2E Tests Failed! ✗")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
