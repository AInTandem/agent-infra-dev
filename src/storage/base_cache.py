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
Cache Adapter Abstract Base Class

Defines the interface for cache implementations.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any, List, Dict
from datetime import timedelta


class CacheAdapter(ABC):
    """
    Abstract base class for cache adapters.

    All cache implementations (Redis, Memcached, in-memory, etc.) must
    inherit from this class and implement all abstract methods.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the cache adapter.

        Args:
            config: Configuration dictionary for the cache backend
        """
        self.config = config
        self._initialized = False

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the cache backend.

        This should establish connections and configure settings.
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """
        Close the cache connection and cleanup resources.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the cache backend is accessible.

        Returns:
            True if healthy, False otherwise
        """
        pass

    # Basic Cache Operations

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        pass

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[timedelta] = None
    ) -> bool:
        """
        Set value in cache with optional TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live (None for no expiration)

        Returns:
            True if set successfully, False otherwise
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        pass

    # Batch Operations

    @abstractmethod
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple values from cache.

        Args:
            keys: List of cache keys

        Returns:
            Dictionary mapping found keys to values
        """
        pass

    @abstractmethod
    async def set_many(
        self,
        mapping: Dict[str, Any],
        ttl: Optional[timedelta] = None
    ) -> int:
        """
        Set multiple key-value pairs in cache.

        Args:
            mapping: Dictionary of key-value pairs
            ttl: Time-to-live for all entries

        Returns:
            Number of keys set successfully
        """
        pass

    @abstractmethod
    async def delete_many(self, keys: List[str]) -> int:
        """
        Delete multiple keys from cache.

        Args:
            keys: List of cache keys to delete

        Returns:
            Number of keys deleted
        """
        pass

    # Pattern Operations

    @abstractmethod
    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern.

        Args:
            pattern: Key pattern (e.g., "task:*", "agent:*:cache")

        Returns:
            Number of keys deleted
        """
        pass

    @abstractmethod
    async def keys(self, pattern: str = "*") -> List[str]:
        """
        Get all keys matching pattern.

        Args:
            pattern: Key pattern (default: "*")

        Returns:
            List of matching keys
        """
        pass

    # Atomic Operations

    @abstractmethod
    async def increment(self, key: str, delta: int = 1) -> Optional[int]:
        """
        Increment a counter.

        Args:
            key: Cache key
            delta: Increment amount (default: 1)

        Returns:
            New value after increment, or None if key doesn't exist
        """
        pass

    @abstractmethod
    async def get_and_set(
        self,
        key: str,
        value: Any,
        ttl: Optional[timedelta] = None
    ) -> Optional[Any]:
        """
        Get current value and set new value atomically.

        Args:
            key: Cache key
            value: New value to set
            ttl: Time-to-live for new value

        Returns:
            Old value or None if key didn't exist
        """
        pass

    # List Operations (for queues)

    @abstractmethod
    async def lpush(self, key: str, *values: Any) -> int:
        """
        Push values to the left of a list.

        Args:
            key: List key
            *values: Values to push

        Returns:
            New list length
        """
        pass

    @abstractmethod
    async def rpush(self, key: str, *values: Any) -> int:
        """
        Push values to the right of a list.

        Args:
            key: List key
            *values: Values to push

        Returns:
            New list length
        """
        pass

    @abstractmethod
    async def lpop(self, key: str) -> Optional[Any]:
        """
        Pop value from the left of a list.

        Args:
            key: List key

        Returns:
            Popped value or None if list is empty
        """
        pass

    @abstractmethod
    async def rpop(self, key: str) -> Optional[Any]:
        """
        Pop value from the right of a list.

        Args:
            key: List key

        Returns:
            Popped value or None if list is empty
        """
        pass

    @abstractmethod
    async def lrange(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """
        Get a range of elements from a list.

        Args:
            key: List key
            start: Start index (default: 0)
            end: End index (default: -1 for all)

        Returns:
            List of elements in range
        """
        pass

    @abstractmethod
    async def llen(self, key: str) -> int:
        """
        Get the length of a list.

        Args:
            key: List key

        Returns:
            List length
        """
        pass

    # Utility Methods

    def is_initialized(self) -> bool:
        """
        Check if the cache adapter has been initialized.

        Returns:
            True if initialized, False otherwise
        """
        return self._initialized

    def _serialize_value(self, value: Any) -> str:
        """
        Serialize value for storage (implementation specific).

        Args:
            value: Value to serialize

        Returns:
            Serialized string
        """
        return str(value)

    def _deserialize_value(self, value: str) -> Any:
        """
        Deserialize value from storage (implementation specific).

        Args:
            value: Serialized string

        Returns:
            Deserialized value
        """
        return value
