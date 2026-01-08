# Copyright (c) 2025 AInTandem
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Task Scheduler implementation using APScheduler.

Manages scheduled agent tasks with persistence support.
Supports both file-based and database storage via StorageAdapter.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from core.config import ConfigManager
from core.task_models import ScheduleType, ScheduledTask, TaskExecution, TaskStatus

# Import StorageAdapter if available
try:
    from storage.base_adapter import StorageAdapter
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False
    StorageAdapter = None  # type: ignore


class TaskScheduler:
    """
    Task scheduler for managing scheduled agent tasks.

    Features:
    - Cron, interval, and one-time scheduling
    - Task persistence to file or database (via StorageAdapter)
    - Automatic retry on failure
    - Execution history tracking
    """

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        agent_manager: Any = None,  # AgentManager instance
        storage_dir: str = "./storage/tasks",
        storage_adapter: Optional["StorageAdapter"] = None,
    ):
        """
        Initialize the TaskScheduler.

        Args:
            config_manager: Configuration manager instance
            agent_manager: AgentManager instance for executing tasks
            storage_dir: Directory for task persistence (file-based fallback)
            storage_adapter: Optional StorageAdapter for database persistence
        """
        self.config_manager = config_manager or ConfigManager()
        self.agent_manager = agent_manager
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Storage adapter (if provided)
        self.storage_adapter = storage_adapter
        self._use_db_storage = storage_adapter is not None

        # Task storage
        self._tasks: Dict[str, ScheduledTask] = {}
        self._executions: List[TaskExecution] = []

        # APScheduler
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._scheduler_id_map: Dict[str, str] = {}  # task_id -> job_id

        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the task scheduler."""
        if self._scheduler and self._scheduler.running:
            logger.warning("TaskScheduler already running")
            return

        logger.info("Starting TaskScheduler...")

        # Initialize storage adapter if provided
        if self.storage_adapter and not self.storage_adapter.is_initialized():
            await self.storage_adapter.initialize()
            storage_type = type(self.storage_adapter).__name__
            logger.info(f"Using {storage_type} for task persistence")
        elif not self._use_db_storage:
            logger.info("Using file-based storage for tasks")

        # Get scheduler configuration
        app_config = self.config_manager.app
        scheduler_config = app_config.scheduler
        timezone = scheduler_config.timezone

        # Create APScheduler
        self._scheduler = AsyncIOScheduler(timezone=timezone)

        # Load persisted tasks
        await self._load_tasks()

        # Schedule all enabled tasks
        for task in self._tasks.values():
            if task.enabled:
                await self._schedule_task(task)

        # Start the scheduler
        self._scheduler.start()

        logger.info(f"TaskScheduler started with {len(self._tasks)} tasks")

    async def stop(self) -> None:
        """Stop the task scheduler."""
        if not self._scheduler or not self._scheduler.running:
            return

        logger.info("Stopping TaskScheduler...")

        # Save tasks before stopping
        await self._save_tasks()

        # Stop the scheduler
        self._scheduler.shutdown(wait=False)

        # Close storage adapter if used
        if self.storage_adapter:
            await self.storage_adapter.close()
            logger.info("Storage adapter closed")

        logger.info("TaskScheduler stopped")

    async def schedule_task(
        self,
        name: str,
        agent_name: str,
        task_prompt: str,
        schedule_type: ScheduleType,
        schedule_value: str,
        repeat: bool = False,
        repeat_interval: Optional[str] = None,
        description: str = "",
        enabled: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ScheduledTask:
        """
        Schedule a new task.

        Args:
            name: Task name
            agent_name: Agent to execute the task
            task_prompt: Prompt for the agent
            schedule_type: Type of schedule (cron, interval, once)
            schedule_value: Schedule value (cron expression, interval seconds, or datetime)
            repeat: Whether to repeat the task
            repeat_interval: Repeat interval (for interval scheduling)
            description: Task description
            enabled: Whether the task is enabled
            metadata: Additional metadata

        Returns:
            Created ScheduledTask
        """
        async with self._lock:
            # Create task
            task = ScheduledTask(
                name=name,
                agent_name=agent_name,
                task_prompt=task_prompt,
                schedule_type=schedule_type,
                schedule_value=schedule_value,
                repeat=repeat,
                repeat_interval=repeat_interval,
                description=description,
                enabled=enabled,
                metadata=metadata or {},
            )

            # Calculate next run time
            task.next_run = task.calculate_next_run()

            # Store task
            self._tasks[task.id] = task

            # Schedule if enabled
            if enabled:
                await self._schedule_task(task)

            # Persist
            await self._save_tasks()

            logger.info(f"Scheduled task: {task.name} ({task.id})")
            return task

    async def _schedule_task(self, task: ScheduledTask) -> None:
        """Schedule a task with APScheduler."""
        if not self._scheduler:
            return

        try:
            # Create trigger based on schedule type
            if task.schedule_type == ScheduleType.CRON:
                trigger = task.to_cron_trigger()
            elif task.schedule_type == ScheduleType.INTERVAL:
                trigger = task.to_interval_trigger()
            elif task.schedule_type == ScheduleType.ONCE:
                trigger = task.to_date_trigger()
            else:
                logger.error(f"Unknown schedule type: {task.schedule_type}")
                return

            # Add job to scheduler
            job = self._scheduler.add_job(
                self._execute_task,
                trigger=trigger,
                args=[task.id],
                id=task.id,
                name=task.name,
                max_instances=1,
            )

            self._scheduler_id_map[task.id] = job.id

            logger.debug(f"Scheduled job for task {task.name}: {job.id}")

        except Exception as e:
            logger.error(f"Failed to schedule task {task.name}: {e}")

    async def _execute_task(self, task_id: str) -> None:
        """Execute a scheduled task."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                logger.error(f"Task not found: {task_id}")
                return

            if not task.enabled:
                logger.debug(f"Task {task.name} is disabled, skipping")
                return

        # Create execution record
        execution = TaskExecution(
            task_id=task.id,
            task_name=task.name,
            agent_name=task.agent_name,
            task_prompt=task.task_prompt,
        )

        logger.info(f"Executing task: {task.name} ({task.id})")

        try:
            # Mark task as running
            task.mark_running()

            # Get agent
            if not self.agent_manager:
                raise RuntimeError("AgentManager not configured")

            agent = self.agent_manager.get_agent(task.agent_name)
            if not agent:
                raise ValueError(f"Agent not found: {task.agent_name}")

            # Execute agent with continuous reasoning
            reasoning_steps = await agent.run_with_reasoning(task.task_prompt)

            # Format reasoning steps into result
            result_parts = []
            for step in reasoning_steps:
                step_type = step.get("type", "unknown")

                if step_type == "thought":
                    content = step.get("content", "")
                    if content and content.strip():
                        result_parts.append(f"[Thinking] {content}")

                elif step_type == "tool_use":
                    tool_name = step.get("tool_name", "unknown")
                    content = step.get("content", "")
                    result_parts.append(f"[Tool: {tool_name}] {content}")

                elif step_type == "tool_result":
                    tool_name = step.get("tool_name", "unknown")
                    content = step.get("content", "")
                    # Truncate long results
                    if content and len(content) > 1000:
                        content = content[:1000] + "...[truncated]"
                    result_parts.append(f"[Result from {tool_name}]\n{content}")

            result = "\n\n".join(result_parts) if result_parts else "No reasoning steps generated"

            # Mark as completed
            task.mark_completed(result)
            execution.mark_completed(result)

            logger.info(f"Task {task.name} completed successfully")

            # For one-time tasks, disable after execution
            if task.schedule_type == ScheduleType.ONCE:
                task.enabled = False
                await self._remove_scheduled_task(task.id)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Task {task.name} failed: {error_msg}")

            # Mark as failed
            task.mark_failed(error_msg)
            execution.mark_failed(error_msg)

            # Retry if configured
            if task.failed_runs < task.max_retries:
                logger.info(f"Retrying task {task.name} (attempt {task.failed_runs}/{task.max_retries})")
                # Retry will happen on next scheduled run

        finally:
            # Store execution
            self._executions.append(execution)

            # Calculate next run time
            task.next_run = task.calculate_next_run()

            # Persist
            await self._save_tasks()

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                logger.warning(f"Task not found: {task_id}")
                return False

            # Remove from scheduler
            await self._remove_scheduled_task(task_id)

            # Mark as cancelled
            task.mark_cancelled()

            # Persist
            await self._save_tasks()

            logger.info(f"Cancelled task: {task.name} ({task_id})")
            return True

    async def _remove_scheduled_task(self, task_id: str) -> None:
        """Remove a task from the scheduler."""
        if not self._scheduler:
            return

        if task_id in self._scheduler_id_map:
            try:
                self._scheduler.remove_job(self._scheduler_id_map[task_id])
                del self._scheduler_id_map[task_id]
            except Exception as e:
                logger.warning(f"Failed to remove job for task {task_id}: {e}")

    async def remove_task(self, task_id: str) -> bool:
        """Remove a task completely."""
        async with self._lock:
            # Cancel first
            await self.cancel_task(task_id)

            # Remove from storage
            if task_id in self._tasks:
                task_name = self._tasks[task_id].name
                del self._tasks[task_id]

                # Persist
                await self._save_tasks()

                logger.info(f"Removed task: {task_name} ({task_id})")
                return True

            return False

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def list_tasks(self, enabled_only: bool = False) -> List[ScheduledTask]:
        """List all tasks."""
        tasks = list(self._tasks.values())
        if enabled_only:
            tasks = [t for t in tasks if t.enabled]
        return tasks

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get the status of a task."""
        task = self._tasks.get(task_id)
        if task:
            return task.last_status
        return None

    def get_executions(
        self,
        task_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[TaskExecution]:
        """Get execution history."""
        executions = self._executions

        if task_id:
            executions = [e for e in executions if e.task_id == task_id]

        # Return most recent first
        executions = sorted(executions, key=lambda e: e.started_at, reverse=True)
        return executions[:limit]

    async def enable_task(self, task_id: str) -> bool:
        """Enable a task."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            task.enabled = True
            await self._schedule_task(task)
            await self._save_tasks()

            logger.info(f"Enabled task: {task.name} ({task_id})")
            return True

    async def disable_task(self, task_id: str) -> bool:
        """Disable a task."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            task.enabled = False
            await self._remove_scheduled_task(task_id)
            await self._save_tasks()

            logger.info(f"Disabled task: {task.name} ({task_id})")
            return True

    async def update_task(
        self,
        task_id: str,
        **updates
    ) -> Optional[ScheduledTask]:
        """Update a task."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None

            # Remove old schedule
            await self._remove_scheduled_task(task_id)

            # Update fields
            for key, value in updates.items():
                if hasattr(task, key):
                    setattr(task, key, value)

            task.updated_at = datetime.now()
            task.next_run = task.calculate_next_run()

            # Reschedule if enabled
            if task.enabled:
                await self._schedule_task(task)

            # Persist
            await self._save_tasks()

            logger.info(f"Updated task: {task.name} ({task_id})")
            return task

    async def _load_tasks(self) -> None:
        """Load tasks from persistence."""
        if self._use_db_storage and self.storage_adapter:
            # Load from database via StorageAdapter
            await self._load_tasks_from_db()
        else:
            # Load from file
            await self._load_tasks_from_file()

    async def _load_tasks_from_db(self) -> None:
        """Load tasks from database via StorageAdapter."""
        try:
            # Load tasks using StorageAdapter
            # The storage adapter stores tasks with the format we need
            tasks_data = await self.storage_adapter.list_tasks()

            for task_dict in tasks_data:
                # Convert from storage format to ScheduledTask
                task = ScheduledTask(
                    id=task_dict.get("id", task_dict.get("task_id")),
                    name=task_dict.get("name", ""),
                    agent_name=task_dict.get("agent_name", ""),
                    task_prompt=task_dict.get("task_prompt", ""),
                    schedule_type=ScheduleType(task_dict.get("schedule_type", "cron")),
                    schedule_value=task_dict.get("schedule_value", ""),
                    repeat=task_dict.get("repeat", False),
                    repeat_interval=task_dict.get("repeat_interval"),
                    description=task_dict.get("description", ""),
                    enabled=task_dict.get("enabled", True),
                    status=task_dict.get("status"),
                    created_at=datetime.fromisoformat(task_dict["created_at"]) if task_dict.get("created_at") else datetime.now(),
                    last_run=datetime.fromisoformat(task_dict["last_run"]) if task_dict.get("last_run") else None,
                    next_run=datetime.fromisoformat(task_dict["next_run"]) if task_dict.get("next_run") else None,
                )
                self._tasks[task.id] = task

            logger.info(f"Loaded {len(self._tasks)} tasks from database")

        except Exception as e:
            logger.error(f"Failed to load tasks from database: {e}")

    async def _load_tasks_from_file(self) -> None:
        """Load tasks from file."""
        tasks_file = self.storage_dir / "tasks.json"

        if not tasks_file.exists():
            return

        try:
            with open(tasks_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for task_data in data.get("tasks", []):
                task = ScheduledTask(**task_data)
                self._tasks[task.id] = task

            logger.info(f"Loaded {len(self._tasks)} tasks from file")

        except Exception as e:
            logger.error(f"Failed to load tasks from file: {e}")

    async def _save_tasks(self) -> None:
        """Save tasks to persistence."""
        if self._use_db_storage and self.storage_adapter:
            # Save to database via StorageAdapter
            await self._save_tasks_to_db()
        else:
            # Save to file
            await self._save_tasks_to_file()

    async def _save_tasks_to_db(self) -> None:
        """Save tasks to database via StorageAdapter."""
        try:
            for task in self._tasks.values():
                # Convert ScheduledTask to storage format
                # Note: datetime objects are passed as-is, adapter handles serialization
                task_dict = {
                    "id": task.id,
                    "name": task.name,
                    "agent_name": task.agent_name,
                    "task_prompt": task.task_prompt,
                    "schedule_type": task.schedule_type.value if hasattr(task.schedule_type, 'value') else task.schedule_type,
                    "schedule_value": task.schedule_value,
                    "repeat": task.repeat,
                    "repeat_interval": task.repeat_interval,
                    "description": task.description,
                    "enabled": task.enabled,
                    "status": task.last_status.value if task.last_status else "pending",
                    "created_at": task.created_at if task.created_at else datetime.now(),
                    "last_run": task.last_run,
                    "next_run": task.next_run,
                    "result": task.last_result if task.last_status == TaskStatus.COMPLETED else None,
                    "error": task.last_error if task.last_status == TaskStatus.FAILED else None,
                }

                await self.storage_adapter.save_task(task_dict)

        except Exception as e:
            logger.error(f"Failed to save tasks to database: {e}")

    async def _save_tasks_to_file(self) -> None:
        """Save tasks to file."""
        tasks_file = self.storage_dir / "tasks.json"

        try:
            # Convert tasks to dict with datetime serialization
            tasks_data = []
            for task in self._tasks.values():
                task_dict = task.model_dump()
                # Convert datetime fields to ISO format
                for key, value in task_dict.items():
                    if isinstance(value, datetime):
                        task_dict[key] = value.isoformat()
                    elif isinstance(value, TaskStatus):
                        task_dict[key] = value.value
                tasks_data.append(task_dict)

            data = {
                "tasks": tasks_data,
                "updated_at": datetime.now().isoformat(),
            }

            with open(tasks_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Failed to save tasks to file: {e}")

    @property
    def is_running(self) -> bool:
        """Check if the scheduler is running."""
        return self._scheduler is not None and self._scheduler.running

    @property
    def task_count(self) -> int:
        """Get the number of tasks."""
        return len(self._tasks)

    def get_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        return {
            "is_running": self.is_running,
            "total_tasks": len(self._tasks),
            "enabled_tasks": sum(1 for t in self._tasks.values() if t.enabled),
            "disabled_tasks": sum(1 for t in self._tasks.values() if not t.enabled),
            "total_executions": len(self._executions),
            "jobs_scheduled": len(self._scheduler_id_map) if self._scheduler else 0,
        }


# Global task scheduler instance
_task_scheduler: Optional[TaskScheduler] = None


async def get_task_scheduler(
    config_manager: Optional[ConfigManager] = None,
    agent_manager: Any = None,
    storage_adapter: Optional["StorageAdapter"] = None,
) -> TaskScheduler:
    """
    Get the global task scheduler instance.

    Args:
        config_manager: Optional configuration manager
        agent_manager: Optional agent manager
        storage_adapter: Optional storage adapter for database persistence

    Returns:
        TaskScheduler instance
    """
    global _task_scheduler

    if _task_scheduler is None:
        _task_scheduler = TaskScheduler(
            config_manager=config_manager,
            agent_manager=agent_manager,
            storage_adapter=storage_adapter,
        )
        await _task_scheduler.start()

    return _task_scheduler
