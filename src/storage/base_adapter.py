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
Storage Adapter Abstract Base Class

Defines the interface for all storage implementations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, AsyncIterator
from datetime import datetime
import json


class StorageAdapter(ABC):
    """
    Abstract base class for storage adapters.

    All storage implementations (SQLite, PostgreSQL, etc.) must inherit
    from this class and implement all abstract methods.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the storage adapter.

        Args:
            config: Configuration dictionary for the storage backend
        """
        self.config = config
        self._initialized = False

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the storage backend.

        This should create necessary tables, indexes, and connections.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """
        Close the storage connection and cleanup resources.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the storage backend is accessible.

        Returns:
            True if healthy, False otherwise
        """
        pass

    # Task Management Methods

    @abstractmethod
    async def save_task(self, task: Dict[str, Any]) -> str:
        """
        Save or update a task.

        Args:
            task: Task dictionary with all required fields

        Returns:
            Task ID
        """
        pass

    @abstractmethod
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a task by ID.

        Args:
            task_id: Unique task identifier

        Returns:
            Task dictionary or None if not found
        """
        pass

    @abstractmethod
    async def list_tasks(
        self,
        agent_name: Optional[str] = None,
        status: Optional[str] = None,
        enabled: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List tasks with optional filters.

        Args:
            agent_name: Filter by agent name
            status: Filter by status (pending, running, completed, failed)
            enabled: Filter by enabled status
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of task dictionaries
        """
        pass

    @abstractmethod
    async def delete_task(self, task_id: str) -> bool:
        """
        Delete a task.

        Args:
            task_id: Task ID to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def update_task_status(
        self,
        task_id: str,
        status: str,
        last_run: Optional[datetime] = None,
        next_run: Optional[datetime] = None,
        result: Optional[str] = None,
        error: Optional[str] = None
    ) -> bool:
        """
        Update task execution status.

        Args:
            task_id: Task ID to update
            status: New status (pending, running, completed, failed)
            last_run: Last execution time
            next_run: Next scheduled execution time
            result: Execution result (optional)
            error: Error message if failed (optional)

        Returns:
            True if updated, False if not found
        """
        pass

    @abstractmethod
    async def get_tasks_due(self, before: datetime) -> List[Dict[str, Any]]:
        """
        Get tasks that are due for execution.

        Args:
            before: Get tasks with next_run before this time

        Returns:
            List of due task dictionaries
        """
        pass

    # Log Management Methods

    @abstractmethod
    async def save_log(
        self,
        task_id: str,
        level: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save a log entry.

        Args:
            task_id: Associated task ID
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            metadata: Optional metadata dictionary

        Returns:
            Log entry ID
        """
        pass

    @abstractmethod
    async def query_logs(
        self,
        task_id: Optional[str] = None,
        level: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query logs with filters.

        Args:
            task_id: Filter by task ID
            level: Filter by log level
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of results

        Returns:
            List of log dictionaries
        """
        pass

    @abstractmethod
    async def delete_old_logs(self, before: datetime) -> int:
        """
        Delete logs older than specified date.

        Args:
            before: Delete logs before this time

        Returns:
            Number of deleted logs
        """
        pass

    # Metadata Methods

    @abstractmethod
    async def save_metadata(self, key: str, value: Any) -> None:
        """
        Save metadata key-value pair.

        Args:
            key: Metadata key
            value: Metadata value (will be JSON serialized)
        """
        pass

    @abstractmethod
    async def get_metadata(self, key: str) -> Optional[Any]:
        """
        Get metadata value by key.

        Args:
            key: Metadata key

        Returns:
            Metadata value or None if not found
        """
        pass

    @abstractmethod
    async def delete_metadata(self, key: str) -> bool:
        """
        Delete metadata key.

        Args:
            key: Metadata key to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    # Transaction Support

    @abstractmethod
    async def begin_transaction(self) -> Any:
        """
        Begin a transaction.

        Returns:
            Transaction object (implementation-specific)
        """
        pass

    @abstractmethod
    async def commit_transaction(self, transaction: Any) -> None:
        """
        Commit a transaction.

        Args:
            transaction: Transaction object from begin_transaction()
        """
        pass

    @abstractmethod
    async def rollback_transaction(self, transaction: Any) -> None:
        """
        Rollback a transaction.

        Args:
            transaction: Transaction object from begin_transaction()
        """
        pass

    # Utility Methods

    def is_initialized(self) -> bool:
        """
        Check if the storage adapter has been initialized.

        Returns:
            True if initialized, False otherwise
        """
        return self._initialized

    def _serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """
        Serialize datetime to ISO format string.

        Args:
            dt: Datetime object or None

        Returns:
            ISO format string or None
        """
        return dt.isoformat() if dt else None

    def _deserialize_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """
        Deserialize ISO format string to datetime.

        Args:
            dt_str: ISO format string or None

        Returns:
            Datetime object or None
        """
        return datetime.fromisoformat(dt_str) if dt_str else None

    def _serialize_metadata(self, metadata: Optional[Dict[str, Any]]) -> Optional[str]:
        """
        Serialize metadata to JSON string.

        Args:
            metadata: Metadata dictionary or None

        Returns:
            JSON string or None
        """
        return json.dumps(metadata) if metadata else None

    def _deserialize_metadata(self, metadata_str: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Deserialize JSON string to metadata dictionary.

        Args:
            metadata_str: JSON string or None

        Returns:
            Metadata dictionary or None
        """
        return json.loads(metadata_str) if metadata_str else None
