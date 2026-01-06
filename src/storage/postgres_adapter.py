"""
PostgreSQL Storage Adapter

Implements StorageAdapter interface using PostgreSQL database.
Designed for enterprise edition with multi-instance deployment.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, select, update, delete
from sqlalchemy.pool import NullPool

from .base_adapter import StorageAdapter
from .factory import register_storage_adapter
from .config import PostgreSQLConfig

logger = logging.getLogger(__name__)


# PostgreSQL Schema
SCHEMA_SQL = """
-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id VARCHAR(255) PRIMARY KEY,
    agent_name VARCHAR(255) NOT NULL,
    task_prompt TEXT NOT NULL,
    schedule_type VARCHAR(50) NOT NULL,
    schedule_value TEXT NOT NULL,
    repeat BOOLEAN DEFAULT FALSE,
    repeat_interval VARCHAR(255),
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    last_run TIMESTAMP WITH TIME ZONE,
    next_run TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'pending',
    result TEXT,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_agent ON tasks(agent_name);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_enabled ON tasks(enabled);
CREATE INDEX IF NOT EXISTS idx_tasks_next_run ON tasks(next_run) WHERE next_run IS NOT NULL;

-- Logs table
CREATE TABLE IF NOT EXISTS logs (
    id VARCHAR(255) PRIMARY KEY,
    task_id VARCHAR(255) NOT NULL,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_logs_task FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_logs_task ON logs(task_id);
CREATE INDEX IF NOT EXISTS idx_logs_level ON logs(level);
CREATE INDEX IF NOT EXISTS idx_logs_created ON logs(created_at);

-- Metadata table
CREATE TABLE IF NOT EXISTS metadata (
    key VARCHAR(255) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
"""


@register_storage_adapter("postgresql")
class PostgreSQLAdapter(StorageAdapter):
    """
    PostgreSQL storage adapter implementation.

    Features:
    - Production-ready PostgreSQL backend
    - Connection pooling via SQLAlchemy
    - Async operations via asyncpg
    - JSONB support for metadata
    - Full transaction support
    - Multi-instance safe
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # Parse configuration
        if "postgresql" in config:
            pg_config = config["postgresql"]
            config.update(pg_config)

        self.host = config.get("host", "localhost")
        self.port = config.get("port", 5432)
        self.database = config.get("database", "qwen_agent")
        self.user = config.get("user", "qwen")
        self.password = config.get("password", "")
        self.pool_size = config.get("pool_size", 20)
        self.max_overflow = config.get("max_overflow", 40)
        self.pool_recycle = config.get("pool_recycle", 3600)
        self.echo = config.get("echo", False)

        # Build connection URL
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[sessionmaker] = None

    def _build_url(self) -> str:
        """Build PostgreSQL connection URL."""
        password_part = f":{self.password}" if self.password else ""
        return f"postgresql+asyncpg://{self.user}{password_part}@{self.host}:{self.port}/{self.database}"

    async def initialize(self) -> None:
        """Initialize the PostgreSQL database and create schema."""
        if self._initialized:
            return

        logger.info(f"Initializing PostgreSQL adapter at {self.host}:{self.port}/{self.database}")

        # Create async engine
        self._engine = create_async_engine(
            self._build_url(),
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            pool_recycle=self.pool_recycle,
            pool_pre_ping=True,  # Verify connections before using
            echo=self.echo
        )

        # Create session factory
        self._session_factory = sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        # Create schema
        async with self._engine.begin() as conn:
            await conn.execute(text(SCHEMA_SQL))

        self._initialized = True
        logger.info("PostgreSQL adapter initialized successfully")

    async def close(self) -> None:
        """Close the database connection and pool."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

        self._initialized = False
        logger.info("PostgreSQL adapter closed")

    async def health_check(self) -> bool:
        """Check if database is accessible."""
        try:
            async with self._engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def _get_session(self) -> AsyncSession:
        """Get a new database session."""
        if not self._session_factory:
            raise RuntimeError("Adapter not initialized")
        return self._session_factory()

    # Task Management

    async def save_task(self, task: Dict[str, Any]) -> str:
        """Save or update a task."""
        task_id = task.get("id")
        if not task_id:
            raise ValueError("Task must have an 'id' field")

        async with self._get_session() as session:
            # Check if task exists
            result = await session.execute(
                select(text("1")).select_from(text("tasks")).where(text("id = :id")),
                {"id": task_id}
            )
            exists = result.first() is not None

            if exists:
                # Update
                await session.execute(
                    update(text("tasks"))
                    .where(text("id = :id"))
                    .values(
                        agent_name=task.get("agent_name"),
                        task_prompt=task.get("task_prompt"),
                        schedule_type=task.get("schedule_type"),
                        schedule_value=task.get("schedule_value"),
                        repeat=task.get("repeat", False),
                        repeat_interval=task.get("repeat_interval"),
                        enabled=task.get("enabled", True),
                        last_run=self._serialize_datetime(task.get("last_run")),
                        next_run=self._serialize_datetime(task.get("next_run")),
                        status=task.get("status", "pending"),
                        result=task.get("result"),
                        error=task.get("error")
                    ),
                    {"id": task_id}
                )
            else:
                # Insert
                await session.execute(
                    text("""
                        INSERT INTO tasks (
                            id, agent_name, task_prompt, schedule_type, schedule_value,
                            repeat, repeat_interval, enabled, created_at, last_run,
                            next_run, status, result, error
                        ) VALUES (
                            :id, :agent_name, :task_prompt, :schedule_type, :schedule_value,
                            :repeat, :repeat_interval, :enabled, :created_at, :last_run,
                            :next_run, :status, :result, :error
                        )
                    """),
                    {
                        "id": task_id,
                        "agent_name": task.get("agent_name"),
                        "task_prompt": task.get("task_prompt"),
                        "schedule_type": task.get("schedule_type"),
                        "schedule_value": task.get("schedule_value"),
                        "repeat": task.get("repeat", False),
                        "repeat_interval": task.get("repeat_interval"),
                        "enabled": task.get("enabled", True),
                        "created_at": self._serialize_datetime(task.get("created_at")) or datetime.utcnow(),
                        "last_run": self._serialize_datetime(task.get("last_run")),
                        "next_run": self._serialize_datetime(task.get("next_run")),
                        "status": task.get("status", "pending"),
                        "result": task.get("result"),
                        "error": task.get("error")
                    }
                )

            await session.commit()
            logger.debug(f"Saved task: {task_id}")
            return task_id

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by ID."""
        async with self._get_session() as session:
            result = await session.execute(
                select(text("*")).select_from(text("tasks")).where(text("id = :id")),
                {"id": task_id}
            )
            row = result.first()

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
        async with self._get_session() as session:
            query = "SELECT * FROM tasks WHERE 1=1"
            params = {}

            if agent_name:
                query += " AND agent_name = :agent_name"
                params["agent_name"] = agent_name

            if status:
                query += " AND status = :status"
                params["status"] = status

            if enabled is not None:
                query += " AND enabled = :enabled"
                params["enabled"] = enabled

            query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            params["limit"] = limit
            params["offset"] = offset

            result = await session.execute(text(query), params)
            rows = result.fetchall()

            return [self._row_to_task(row) for row in rows]

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        async with self._get_session() as session:
            result = await session.execute(
                delete(text("tasks")).where(text("id = :id")),
                {"id": task_id}
            )
            await session.commit()

            deleted = result.rowcount > 0
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
        async with self._get_session() as session:
            updates = {"status": status}

            if last_run is not None:
                updates["last_run"] = last_run

            if next_run is not None:
                updates["next_run"] = next_run

            if result is not None:
                updates["result"] = result

            if error is not None:
                updates["error"] = error

            result = await session.execute(
                update(text("tasks"))
                .where(text("id = :id"))
                .values(**updates),
                {"id": task_id}
            )
            await session.commit()

            updated = result.rowcount > 0
            if updated:
                logger.debug(f"Updated task {task_id} status to {status}")
            return updated

    async def get_tasks_due(self, before: datetime) -> List[Dict[str, Any]]:
        """Get tasks due for execution."""
        async with self._get_session() as session:
            result = await session.execute(
                select(text("*"))
                .select_from(text("tasks"))
                .where(text("enabled = TRUE AND next_run IS NOT NULL AND next_run <= :before"))
                .order_by(text("next_run ASC")),
                {"before": before}
            )
            rows = result.fetchall()

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

        async with self._get_session() as session:
            await session.execute(
                text("""
                    INSERT INTO logs (id, task_id, level, message, metadata, created_at)
                    VALUES (:id, :task_id, :level, :message, :metadata, :created_at)
                """),
                {
                    "id": log_id,
                    "task_id": task_id,
                    "level": level,
                    "message": message,
                    "metadata": metadata if metadata else None,
                    "created_at": datetime.utcnow()
                }
            )
            await session.commit()

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
        async with self._get_session() as session:
            query = "SELECT * FROM logs WHERE 1=1"
            params = {}

            if task_id:
                query += " AND task_id = :task_id"
                params["task_id"] = task_id

            if level:
                query += " AND level = :level"
                params["level"] = level

            if start_time:
                query += " AND created_at >= :start_time"
                params["start_time"] = start_time

            if end_time:
                query += " AND created_at <= :end_time"
                params["end_time"] = end_time

            query += " ORDER BY created_at DESC LIMIT :limit"
            params["limit"] = limit

            result = await session.execute(text(query), params)
            rows = result.fetchall()

            return [self._row_to_log(row) for row in rows]

    async def delete_old_logs(self, before: datetime) -> int:
        """Delete logs older than specified date."""
        async with self._get_session() as session:
            result = await session.execute(
                delete(text("logs")).where(text("created_at < :before")),
                {"before": before}
            )
            await session.commit()

            deleted = result.rowcount
            logger.debug(f"Deleted {deleted} old logs")
            return deleted

    # Metadata

    async def save_metadata(self, key: str, value: Any) -> None:
        """Save metadata key-value pair."""
        async with self._get_session() as session:
            await session.execute(
                text("""
                    INSERT INTO metadata (key, value, updated_at)
                    VALUES (:key, :value, :updated_at)
                    ON CONFLICT (key) DO UPDATE
                    SET value = EXCLUDED.value, updated_at = EXCLUDED.updated_at
                """),
                {
                    "key": key,
                    "value": value if isinstance(value, (dict, list)) else {"_value": value},
                    "updated_at": datetime.utcnow()
                }
            )
            await session.commit()

    async def get_metadata(self, key: str) -> Optional[Any]:
        """Get metadata value by key."""
        async with self._get_session() as session:
            result = await session.execute(
                select(text("value")).select_from(text("metadata")).where(text("key = :key")),
                {"key": key}
            )
            row = result.first()

            if row:
                value = row[0]
                # Handle wrapped scalar values
                if isinstance(value, dict) and "_value" in value and len(value) == 1:
                    return value["_value"]
                return value
            return None

    async def delete_metadata(self, key: str) -> bool:
        """Delete metadata key."""
        async with self._get_session() as session:
            result = await session.execute(
                delete(text("metadata")).where(text("key = :key")),
                {"key": key}
            )
            await session.commit()

            return result.rowcount > 0

    # Transaction Support

    async def begin_transaction(self) -> Any:
        """Begin a transaction."""
        session = self._get_session()
        await session.begin()
        return session

    async def commit_transaction(self, transaction: Any) -> None:
        """Commit a transaction."""
        await transaction.commit()

    async def rollback_transaction(self, transaction: Any) -> None:
        """Rollback a transaction."""
        await transaction.rollback()

    # Helper Methods

    def _row_to_task(self, row: tuple) -> Dict[str, Any]:
        """Convert database row to task dictionary."""
        # Row is a RowProxy with keys
        if hasattr(row, "_mapping"):
            task = dict(row._mapping)
        else:
            # Fallback for different SQLAlchemy versions
            task = {key: row[i] for i, key in enumerate([
                "id", "agent_name", "task_prompt", "schedule_type", "schedule_value",
                "repeat", "repeat_interval", "enabled", "created_at", "last_run",
                "next_run", "status", "result", "error"
            ])}

        return task

    def _row_to_log(self, row: tuple) -> Dict[str, Any]:
        """Convert database row to log dictionary."""
        if hasattr(row, "_mapping"):
            log = dict(row._mapping)
        else:
            log = {key: row[i] for i, key in enumerate([
                "id", "task_id", "level", "message", "metadata", "created_at"
            ])}

        return log
