#!/usr/bin/env python3
"""
Quick integration test for TaskScheduler with Storage Adapter.
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
from core.task_models import ScheduleType
from storage.factory import StorageFactory


async def test_file_storage():
    """Test TaskScheduler with file-based storage (default)."""
    print("=" * 60)
    print("Test 1: File-based Storage (Backward Compatibility)")
    print("=" * 60)

    config = ConfigManager()
    scheduler = TaskScheduler(config, storage_dir="./storage/test_tasks")

    await scheduler.start()
    print("✓ Started with file-based storage")

    # Create a task
    task = await scheduler.schedule_task(
        name="Test File Task",
        agent_name="test",
        task_prompt="Test prompt",
        schedule_type=ScheduleType.ONCE,
        schedule_value="2099-01-01T00:00:00",
        enabled=False,
    )
    print(f"✓ Created task: {task.id}")

    # Verify task was saved to file
    tasks = scheduler.list_tasks()
    print(f"✓ Listed {len(tasks)} tasks")

    await scheduler.stop()
    print("✓ Stopped scheduler")
    print()


async def test_sqlite_storage():
    """Test TaskScheduler with SQLite storage adapter."""
    print("=" * 60)
    print("Test 2: SQLite Storage Adapter")
    print("=" * 60)

    # Create temporary SQLite database
    temp_db = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db")
    temp_db.close()

    try:
        # Create storage adapter
        storage = StorageFactory.create_storage({
            "type": "sqlite",
            "path": temp_db.name,
        })
        await storage.initialize()
        print("✓ Initialized SQLite storage adapter")

        # Create scheduler with storage adapter
        config = ConfigManager()
        scheduler = TaskScheduler(config, storage_adapter=storage)

        await scheduler.start()
        print("✓ Started scheduler with SQLite storage")

        # Create a task
        task = await scheduler.schedule_task(
            name="Test DB Task",
            agent_name="test",
            task_prompt="Test prompt",
            schedule_type=ScheduleType.ONCE,
            schedule_value="2099-01-01T00:00:00",
            enabled=False,
        )
        print(f"✓ Created task: {task.id}")

        # Verify task in database
        db_task = await storage.get_task(task.id)
        print(f"✓ Retrieved task from DB: {db_task['name']}")

        # Update task
        await scheduler.update_task(task.id, description="Updated description")
        updated = await storage.get_task(task.id)
        print(f"✓ Updated task in DB: {updated['description']}")

        # List tasks
        tasks = await storage.list_tasks()
        print(f"✓ Listed {len(tasks)} tasks from DB")

        await scheduler.stop()
        await storage.close()
        print("✓ Stopped scheduler and closed storage")

    finally:
        # Cleanup
        try:
            os.unlink(temp_db.name)
        except:
            pass

    print()


async def main():
    """Run all integration tests."""
    print()
    print("TaskScheduler Storage Adapter Integration Tests")
    print()

    await test_file_storage()
    await test_sqlite_storage()

    print("=" * 60)
    print("All Integration Tests Passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
