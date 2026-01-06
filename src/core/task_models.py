"""
Task data models for scheduled agent tasks.

Defines the structure for scheduled tasks using APScheduler.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ScheduleType(str, Enum):
    """Types of task schedules."""
    CRON = "cron"
    INTERVAL = "interval"
    ONCE = "once"


class TaskStatus(str, Enum):
    """Status of a scheduled task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DISABLED = "disabled"


class ScheduledTask(BaseModel):
    """
    A scheduled task for agent execution.

    Represents a task that will be executed at a specific time or interval.
    """

    # Identification
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str = ""

    # Agent configuration
    agent_name: str
    task_prompt: str

    # Schedule configuration
    schedule_type: ScheduleType
    schedule_value: str  # Cron expression or interval (e.g., "0 9 * * *" or "300")

    # Repeat configuration
    repeat: bool = False
    repeat_interval: Optional[str] = None  # For interval scheduling (e.g., "300" for every 5 minutes)

    # Execution configuration
    enabled: bool = True
    max_retries: int = 3
    timeout: int = 300  # 5 minutes

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Runtime tracking
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    last_status: TaskStatus = TaskStatus.PENDING

    # Execution results
    last_result: Optional[str] = None
    last_error: Optional[str] = None

    # Statistics
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0

    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        use_enum_values = True

    def mark_running(self) -> None:
        """Mark task as running."""
        self.last_status = TaskStatus.RUNNING
        self.updated_at = datetime.now()

    def mark_completed(self, result: Optional[str] = None) -> None:
        """Mark task as completed successfully."""
        self.last_status = TaskStatus.COMPLETED
        self.last_run = datetime.now()
        self.last_result = result
        self.total_runs += 1
        self.successful_runs += 1
        self.updated_at = datetime.now()

    def mark_failed(self, error: str) -> None:
        """Mark task as failed."""
        self.last_status = TaskStatus.FAILED
        self.last_run = datetime.now()
        self.last_error = error
        self.total_runs += 1
        self.failed_runs += 1
        self.updated_at = datetime.now()

    def mark_cancelled(self) -> None:
        """Mark task as cancelled."""
        self.last_status = TaskStatus.CANCELLED
        self.updated_at = datetime.now()

    def calculate_next_run(self) -> Optional[datetime]:
        """
        Calculate the next run time based on schedule.

        Returns:
            Next run datetime or None if task doesn't repeat
        """
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger

        if not self.enabled:
            return None

        if self.schedule_type == ScheduleType.CRON:
            try:
                trigger = CronTrigger.from_crontab(self.schedule_value)
                # Get next fire time after now
                next_time = trigger.get_next_fire_time(None, datetime.now())
                return next_time
            except Exception:
                return None

        elif self.schedule_type == ScheduleType.INTERVAL:
            try:
                seconds = int(self.schedule_value)
                if self.last_run:
                    return self.last_run.replace(second=0, microsecond=0) + \
                           __import__('datetime').timedelta(seconds=seconds)
                else:
                    return datetime.now() + __import__('datetime').timedelta(seconds=seconds)
            except Exception:
                return None

        elif self.schedule_type == ScheduleType.ONCE:
            # One-time tasks don't have next run after execution
            if self.total_runs > 0:
                return None
            # Parse the schedule_value as a datetime string
            try:
                return datetime.fromisoformat(self.schedule_value)
            except Exception:
                return None

        return None

    def to_cron_trigger(self):
        """
        Convert to APScheduler CronTrigger.

        Returns:
            CronTrigger instance
        """
        from apscheduler.triggers.cron import CronTrigger

        if self.schedule_type != ScheduleType.CRON:
            raise ValueError(f"Task {self.id} is not a cron task")

        return CronTrigger.from_crontab(self.schedule_value)

    def to_interval_trigger(self):
        """
        Convert to APScheduler IntervalTrigger.

        Returns:
            IntervalTrigger instance
        """
        from apscheduler.triggers.interval import IntervalTrigger

        if self.schedule_type != ScheduleType.INTERVAL:
            raise ValueError(f"Task {self.id} is not an interval task")

        seconds = int(self.schedule_value)
        return IntervalTrigger(seconds=seconds)

    def to_date_trigger(self):
        """
        Convert to APScheduler DateTrigger (for one-time tasks).

        Returns:
            DateTrigger instance
        """
        from apscheduler.triggers.date import DateTrigger

        if self.schedule_type != ScheduleType.ONCE:
            raise ValueError(f"Task {self.id} is not a one-time task")

        run_date = datetime.fromisoformat(self.schedule_value)
        return DateTrigger(run_date=run_date)

    def get_success_rate(self) -> float:
        """Get the success rate as a percentage."""
        if self.total_runs == 0:
            return 0.0
        return (self.successful_runs / self.total_runs) * 100


class TaskExecution(BaseModel):
    """Record of a single task execution."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str
    task_name: str
    agent_name: str
    task_prompt: str

    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    status: TaskStatus = TaskStatus.RUNNING
    result: Optional[str] = None
    error: Optional[str] = None

    # Tool usage tracking
    tools_used: List[str] = Field(default_factory=list)

    # Token usage (if available)
    tokens_used: Optional[int] = None

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        use_enum_values = True

    def mark_completed(self, result: Optional[str] = None) -> None:
        """Mark execution as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        self.result = result

    def mark_failed(self, error: str) -> None:
        """Mark execution as failed."""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.now()
        self.duration_seconds = (self.completed_at - self.started_at).total_seconds()
        self.error = error
