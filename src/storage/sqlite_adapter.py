"""
SQLite Storage Adapter

Implements StorageAdapter interface using SQLite database.
Designed for personal edition with single-container deployment.
"""

import aiosqlite
import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from .base_adapter import StorageAdapter
from .factory import register_storage_adapter
from .config import SQLiteConfig

logger = logging.getLogger(__name__)


# SQL Schema
SCHEMA_SQL = """
-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    task_prompt TEXT NOT NULL,
    schedule_type TEXT NOT NULL,
    schedule_value TEXT NOT NULL,
    repeat INTEGER DEFAULT 0,
    repeat_interval TEXT,
    enabled INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    last_run TEXT,
    next_run TEXT,
    status TEXT DEFAULT 'pending',
    result TEXT,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_agent ON tasks(agent_name);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_enabled ON tasks(enabled);
CREATE INDEX IF NOT EXISTS idx_tasks_next_run ON tasks(next_run);

-- Logs table
CREATE TABLE IF NOT EXISTS logs (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_logs_task ON logs(task_id);
CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_created ON logs(created_at);

-- Metadata table
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


@register_storage_adapter("sqlite")
class SQLiteAdapter(StorageAdapter):
    """
    SQLite storage adapter implementation.

    Features:
    - Embedded database (no separate service needed)
    - WAL mode for better concurrency
    - Connection pooling via aiosqlite
    - Full transaction support
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # Parse configuration
        if "path" not in config and "sqlite" in config:
            config.update(config["sqlite"])

        self.db_path = config.get("path", "./storage/data.db")
        self.enable_wal = config.get("enable_wal", True)
        self.journal_mode = config.get("journal_mode", "WAL").upper()

        # Ensure directory exists
        self.db_dir = os.path.dirname(self.db_path)
        if self.db_dir:
            os.makedirs(self.db_dir, exist_ok=True)

    async def initialize(self) -> None:
        """Initialize the SQLite database and create schema."""
        if self._initialized:
            return

        logger.info(f"Initializing SQLite adapter at {self.db_path}")

        # Create connection and schema
        async with aiosqlite.connect(self.db_path) as conn:
            # Set journal mode
            await conn.execute(f"PRAGMA journal_mode={self.journal_mode}")
            if self.enable_wal:
                await conn.execute("PRAGMA synchronous=NORMAL")
            else:
                await conn.execute("PRAGMA synchronous=FULL")

            # Create schema
            await conn.executescript(SCHEMA_SQL)
            await conn.commit()

        self._initialized = True
        logger.info("SQLite adapter initialized successfully")

    async def close(self) -> None:
        """Close the adapter."""
        self._initialized = False
        logger.info("SQLite adapter closed")

    async def health_check(self) -> bool:
        """Check if database is accessible."""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    # Task Management

    async def save_task(self, task: Dict[str, Any]) -> str:
        """Save or update a task."""
        async with aiosqlite.connect(self.db_path) as conn:
            task_id = task.get("id")
            if not task_id:
                raise ValueError("Task must have an 'id' field")

            # Serialize datetime fields
            created_at = self._serialize_datetime(task.get("created_at"))
            last_run = self._serialize_datetime(task.get("last_run"))
            next_run = self._serialize_datetime(task.get("next_run"))

            await conn.execute(
                """
                INSERT INTO tasks (
                    id, agent_name, task_prompt, schedule_type, schedule_value,
                    repeat, repeat_interval, enabled, created_at, last_run,
                    next_run, status, result, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    agent_name = excluded.agent_name,
                    task_prompt = excluded.task_prompt,
                    schedule_type = excluded.schedule_type,
                    schedule_value = excluded.schedule_value,
                    repeat = excluded.repeat,
                    repeat_interval = excluded.repeat_interval,
                    enabled = excluded.enabled,
                    last_run = excluded.last_run,
                    next_run = excluded.next_run,
                    status = excluded.status,
                    result = excluded.result,
                    error = excluded.error
                """,
                (
                    task_id,
                    task.get("agent_name"),
                    task.get("task_prompt"),
                    task.get("schedule_type"),
                    task.get("schedule_value"),
                    1 if task.get("repeat", False) else 0,
                    task.get("repeat_interval"),
                    1 if task.get("enabled", True) else 0,
                    created_at or datetime.utcnow().isoformat(),
                    last_run,
                    next_run,
                    task.get("status", "pending"),
                    task.get("result"),
                    task.get("error")
                )
            )
            await conn.commit()

            logger.debug(f"Saved task: {task_id}")
            return task_id

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by ID."""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (task_id,)
            )
            row = await cursor.fetchone()

            if row:
                return self._row_to_task(row)
            return None

    async def list_tasks(
        self,
        agent_name: Optional[str] = None,
        status: Optional[str] = None,
        enabled: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List tasks with optional filters."""
        async with aiosqlite.connect(self.db_path) as conn:
            query = "SELECT * FROM tasks WHERE 1=1"
            params = []

            if agent_name:
                query += " AND agent_name = ?"
                params.append(agent_name)

            if status:
                query += " AND status = ?"
                params.append(status)

            if enabled is not None:
                query += " AND enabled = ?"
                params.append(1 if enabled else 0)

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()

            return [self._row_to_task(row) for row in rows]

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(
                "DELETE FROM tasks WHERE id = ?",
                (task_id,)
            )
            await conn.commit()

            deleted = cursor.rowcount > 0
            if deleted:
                logger.debug(f"Deleted task: {task_id}")
            return deleted

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        last_run: Optional[datetime] = None,
        next_run: Optional[datetime] = None,
        result: Optional[str] = None,
        error: Optional[str] = None
    ) -> bool:
        """Update task execution status."""
        async with aiosqlite.connect(self.db_path) as conn:
            updates = ["status = ?"]
            params = [status]

            if last_run is not None:
                updates.append("last_run = ?")
                params.append(self._serialize_datetime(last_run))

            if next_run is not None:
                updates.append("next_run = ?")
                params.append(self._serialize_datetime(next_run))

            if result is not None:
                updates.append("result = ?")
                params.append(result)

            if error is not None:
                updates.append("error = ?")
                params.append(error)

            params.append(task_id)

            query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
            cursor = await conn.execute(query, params)
            await conn.commit()

            updated = cursor.rowcount > 0
            if updated:
                logger.debug(f"Updated task {task_id} status to {status}")
            return updated

    async def get_tasks_due(self, before: datetime) -> List[Dict[str, Any]]:
        """Get tasks due for execution."""
        async with aiosqlite.connect(self.db_path) as conn:
            before_str = self._serialize_datetime(before)

            cursor = await conn.execute(
                """
                SELECT * FROM tasks
                WHERE enabled = 1 AND next_run IS NOT NULL AND next_run <= ?
                ORDER BY next_run ASC
                """,
                (before_str,)
            )
            rows = await cursor.fetchall()

            return [self._row_to_task(row) for row in rows]

    # Log Management

    async def save_log(
        self,
        task_id: str,
        level: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Save a log entry."""
        import uuid
        log_id = str(uuid.uuid4())

        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                INSERT INTO logs (id, task_id, level, message, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    log_id,
                    task_id,
                    level,
                    message,
                    self._serialize_metadata(metadata),
                    datetime.utcnow().isoformat()
                )
            )
            await conn.commit()

            return log_id

    async def query_logs(
        self,
        task_id: Optional[str] = None,
        level: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query logs with filters."""
        async with aiosqlite.connect(self.db_path) as conn:
            query = "SELECT * FROM logs WHERE 1=1"
            params = []

            if task_id:
                query += " AND task_id = ?"
                params.append(task_id)

            if level:
                query += " AND level = ?"
                params.append(level)

            if start_time:
                query += " AND created_at >= ?"
                params.append(self._serialize_datetime(start_time))

            if end_time:
                query += " AND created_at <= ?"
                params.append(self._serialize_datetime(end_time))

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()

            return [self._row_to_log(row) for row in rows]

    async def delete_old_logs(self, before: datetime) -> int:
        """Delete logs older than specified date."""
        async with aiosqlite.connect(self.db_path) as conn:
            before_str = self._serialize_datetime(before)

            cursor = await conn.execute(
                "DELETE FROM logs WHERE created_at < ?",
                (before_str,)
            )
            await conn.commit()

            deleted = cursor.rowcount
            logger.debug(f"Deleted {deleted} old logs")
            return deleted

    # Metadata

    async def save_metadata(self, key: str, value: Any) -> None:
        """Save metadata key-value pair."""
        async with aiosqlite.connect(self.db_path) as conn:
            value_str = self._serialize_metadata(value) if not isinstance(value, str) else value

            await conn.execute(
                """
                INSERT INTO metadata (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (key, value_str, datetime.utcnow().isoformat())
            )
            await conn.commit()

    async def get_metadata(self, key: str) -> Optional[Any]:
        """Get metadata value by key."""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(
                "SELECT value FROM metadata WHERE key = ?",
                (key,)
            )
            row = await cursor.fetchone()

            if row:
                value = row[0]
                # Try to deserialize as JSON
                try:
                    return self._deserialize_metadata(value)
                except:
                    return value
            return None

    async def delete_metadata(self, key: str) -> bool:
        """Delete metadata key."""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(
                "DELETE FROM metadata WHERE key = ?",
                (key,)
            )
            await conn.commit()

            return cursor.rowcount > 0

    # Transaction Support

    async def begin_transaction(self) -> Any:
        """Begin a transaction."""
        conn = await aiosqlite.connect(self.db_path)
        await conn.execute("BEGIN")
        return conn

    async def commit_transaction(self, transaction: Any) -> None:
        """Commit a transaction."""
        await transaction.commit()
        await transaction.close()

    async def rollback_transaction(self, transaction: Any) -> None:
        """Rollback a transaction."""
        await transaction.rollback()
        await transaction.close()

    # Helper Methods

    def _row_to_task(self, row: tuple) -> Dict[str, Any]:
        """Convert database row to task dictionary."""
        columns = [
            "id", "agent_name", "task_prompt", "schedule_type", "schedule_value",
            "repeat", "repeat_interval", "enabled", "created_at", "last_run",
            "next_run", "status", "result", "error"
        ]
        task = dict(zip(columns, row))

        # Convert integer flags
        task["repeat"] = bool(task["repeat"])
        task["enabled"] = bool(task["enabled"])

        # Deserialize datetime fields
        if task.get("created_at"):
            task["created_at"] = self._deserialize_datetime(task["created_at"])
        if task.get("last_run"):
            task["last_run"] = self._deserialize_datetime(task["last_run"])
        if task.get("next_run"):
            task["next_run"] = self._deserialize_datetime(task["next_run"])

        return task

    def _row_to_log(self, row: tuple) -> Dict[str, Any]:
        """Convert database row to log dictionary."""
        columns = ["id", "task_id", "level", "message", "metadata", "created_at"]
        log = dict(zip(columns, row))

        # Deserialize metadata
        if log.get("metadata"):
            log["metadata"] = self._deserialize_metadata(log["metadata"])

        # Deserialize datetime
        if log.get("created_at"):
            log["created_at"] = self._deserialize_datetime(log["created_at"])

        return log
