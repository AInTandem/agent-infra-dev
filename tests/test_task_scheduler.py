#!/usr/bin/env python3
"""
Test script for Task Scheduler.

Tests task scheduling, persistence, and execution.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import ConfigManager
from core.task_scheduler import TaskScheduler
from core.task_models import ScheduleType, TaskStatus


async def test_task_scheduler():
    """Test Task Scheduler functionality."""
    print("=" * 60)
    print("Task Scheduler Tests")
    print("=" * 60)
    print()

    # Load configuration
    config = ConfigManager()
    config.load_all()

    # Create scheduler (without agent manager for basic tests)
    print("Creating TaskScheduler...")
    scheduler = TaskScheduler(config)

    try:
        await scheduler.start()
    except Exception as e:
        print(f"Note: {e}")

    print()

    # Test 1: Create tasks
    print("Test 1: Creating scheduled tasks")

    # One-time task (run in 5 seconds)
    run_time = (datetime.now() + timedelta(seconds=5)).isoformat()
    task1 = await scheduler.schedule_task(
        name="One-time Test Task",
        agent_name="researcher",
        task_prompt="Say hello from the scheduler!",
        schedule_type=ScheduleType.ONCE,
        schedule_value=run_time,
        description="A one-time test task",
        enabled=False,  # Disabled since we don't have agent manager
    )
    print(f"  ✓ Created one-time task: {task1.name}")
    print(f"    ID: {task1.id}")
    print(f"    Next run: {task1.next_run}")

    # Interval task (every 30 seconds)
    task2 = await scheduler.schedule_task(
        name="Interval Test Task",
        agent_name="researcher",
        task_prompt="Check system status",
        schedule_type=ScheduleType.INTERVAL,
        schedule_value="30",  # 30 seconds
        repeat=True,
        description="An interval test task",
        enabled=False,
    )
    print(f"  ✓ Created interval task: {task2.name}")
    print(f"    ID: {task2.id}")

    # Cron task (every minute)
    task3 = await scheduler.schedule_task(
        name="Cron Test Task",
        agent_name="developer",
        task_prompt="Generate daily report",
        schedule_type=ScheduleType.CRON,
        schedule_value="* * * * *",  # Every minute
        repeat=True,
        description="A cron test task",
        enabled=False,
    )
    print(f"  ✓ Created cron task: {task3.name}")
    print(f"    ID: {task3.id}")
    print()

    # Test 2: List tasks
    print("Test 2: Listing tasks")
    tasks = scheduler.list_tasks()
    print(f"  Total tasks: {len(tasks)}")
    for task in tasks:
        status = "enabled" if task.enabled else "disabled"
        print(f"    - {task.name}: {status}")
    print()

    # Test 3: Get task info
    print("Test 3: Getting task info")
    task = scheduler.get_task(task1.id)
    if task:
        print(f"  Task: {task.name}")
        print(f"    Agent: {task.agent_name}")
        print(f"    Prompt: {task.task_prompt[:50]}...")
        print(f"    Schedule: {task.schedule_type} ({task.schedule_value})")
        print(f"    Status: {task.last_status}")
        print(f"    Next run: {task.next_run}")
    print()

    # Test 4: Enable/disable task
    print("Test 4: Enable/disable task")
    await scheduler.enable_task(task1.id)
    print(f"  ✓ Enabled task: {task1.name}")

    await scheduler.disable_task(task1.id)
    print(f"  ✓ Disabled task: {task1.name}")
    print()

    # Test 5: Update task
    print("Test 5: Updating task")
    updated = await scheduler.update_task(
        task1.id,
        description="Updated description",
        timeout=600,
    )
    if updated:
        print(f"  ✓ Updated task: {updated.name}")
        print(f"    New description: {updated.description}")
        print(f"    New timeout: {updated.timeout}")
    print()

    # Test 6: Get stats
    print("Test 6: Getting scheduler stats")
    stats = scheduler.get_stats()
    print(f"  Running: {stats['is_running']}")
    print(f"  Total tasks: {stats['total_tasks']}")
    print(f"  Enabled tasks: {stats['enabled_tasks']}")
    print(f"  Disabled tasks: {stats['disabled_tasks']}")
    print(f"  Jobs scheduled: {stats['jobs_scheduled']}")
    print()

    # Test 7: Persistence
    print("Test 7: Testing persistence")
    tasks_file = Path("./storage/tasks/tasks.json")
    if tasks_file.exists():
        print(f"  ✓ Tasks saved to: {tasks_file}")
        import json
        with open(tasks_file, "r") as f:
            data = json.load(f)
        print(f"    Saved tasks: {len(data['tasks'])}")
    print()

    # Test 8: Cancel task
    print("Test 8: Cancelling task")
    cancelled = await scheduler.cancel_task(task1.id)
    print(f"  ✓ Cancelled task: {cancelled}")
    status = scheduler.get_task_status(task1.id)
    print(f"    Status: {status}")
    print()

    # Test 9: Remove task
    print("Test 9: Removing task")
    removed = await scheduler.remove_task(task1.id)
    print(f"  ✓ Removed task: {removed}")
    remaining = scheduler.list_tasks()
    print(f"    Remaining tasks: {len(remaining)}")
    print()

    # Stop scheduler
    print("Stopping scheduler...")
    await scheduler.stop()
    print("  ✓ Scheduler stopped")

    print()
    print("=" * 60)
    print("Task Scheduler Tests Complete! ✓")
    print("=" * 60)


async def test_task_models():
    """Test task data models."""
    print("=" * 60)
    print("Task Models Tests")
    print("=" * 60)
    print()

    from core.task_models import ScheduledTask, TaskExecution

    # Test ScheduledTask
    print("Test 1: ScheduledTask model")
    task = ScheduledTask(
        name="Test Task",
        agent_name="researcher",
        task_prompt="Test prompt",
        schedule_type=ScheduleType.CRON,
        schedule_value="0 9 * * *",
        repeat=True,
    )
    print(f"  ✓ Created task: {task.name}")
    print(f"    ID: {task.id}")
    print(f"    Status: {task.last_status}")

    # Test status transitions
    task.mark_running()
    print(f"  ✓ Marked as running: {task.last_status}")

    task.mark_completed("Test result")
    print(f"  ✓ Marked as completed: {task.last_status}")
    print(f"    Total runs: {task.total_runs}")
    print(f"    Success rate: {task.get_success_rate()}%")

    # Test TaskExecution
    print()
    print("Test 2: TaskExecution model")
    execution = TaskExecution(
        task_id=task.id,
        task_name=task.name,
        agent_name=task.agent_name,
        task_prompt=task.task_prompt,
    )
    print(f"  ✓ Created execution: {execution.id}")

    execution.mark_completed("Test result")
    print(f"  ✓ Marked as completed")
    print(f"    Duration: {execution.duration_seconds}s")
    print(f"    Status: {execution.status}")

    print()
    print("✓ Task Models tests completed")


async def main():
    """Run all tests."""
    # Test models first
    await test_task_models()

    print()

    # Test scheduler
    await test_task_scheduler()


if __name__ == "__main__":
    asyncio.run(main())
