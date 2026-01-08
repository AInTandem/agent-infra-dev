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
Redis Cache Adapter

Implements CacheAdapter interface using Redis.
Designed for enterprise edition with high-performance caching.
"""

import json
import logging
from typing import List, Optional, Dict, Any
from datetime import timedelta

from redis.asyncio import Redis, ConnectionPool
from redis.exceptions import RedisError

from .base_cache import CacheAdapter
from .factory import register_cache_adapter

logger = logging.getLogger(__name__)


@register_cache_adapter("redis")
class RedisCacheAdapter(CacheAdapter):
    """
    Redis cache adapter implementation.

    Features:
    - High-performance caching
    - Connection pooling
    - Async operations
    - TTL support
    - Pattern-based operations
    - List operations for queues
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # Parse configuration
        if "redis" in config:
            redis_config = config["redis"]
            config.update(redis_config)

        self.host = config.get("host", "localhost")
        self.port = config.get("port", 6379)
        self.db = config.get("db", 0)
        self.password = config.get("password")
        self.pool_size = config.get("pool_size", 10)
        self.socket_timeout = config.get("socket_timeout", 5.0)
        self.socket_connect_timeout = config.get("socket_connect_timeout", 5.0)
        self.decode_responses = config.get("decode_responses", True)
        self.ssl = config.get("ssl", False)

        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None

    async def initialize(self) -> None:
        """Initialize the Redis connection pool."""
        if self._initialized:
            return

        logger.info(f"Initializing Redis cache at {self.host}:{self.port}/{self.db}")

        # Create connection pool
        self._pool = ConnectionPool(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            socket_timeout=self.socket_timeout,
            socket_connect_timeout=self.socket_connect_timeout,
            decode_responses=self.decode_responses,
            max_connections=self.pool_size,
            ssl=self.ssl
        )

        # Create Redis client
        self._client = Redis(connection_pool=self._pool)

        # Test connection
        try:
            await self._client.ping()
            self._initialized = True
            logger.info("Redis cache initialized successfully")
        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def close(self) -> None:
        """Close the Redis connection pool."""
        if self._client:
            await self._client.close()
            self._client = None

        if self._pool:
            await self._pool.aclose()  # Note: aclose() for async pool
            self._pool = None

        self._initialized = False
        logger.info("Redis cache closed")

    async def health_check(self) -> bool:
        """Check if Redis is accessible."""
        try:
            if self._client:
                await self._client.ping()
                return True
            return False
        except RedisError as e:
            logger.error(f"Health check failed: {e}")
            return False

    # Basic Cache Operations

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        try:
            value = await self._client.get(key)
            if value is None:
                return None

            # Try to deserialize JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        except RedisError as e:
            logger.error(f"Error getting key {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[timedelta] = None
    ) -> bool:
        """Set value in cache with optional TTL."""
        try:
            # Serialize value
            if isinstance(value, (dict, list)):
                serialized = json.dumps(value)
            elif isinstance(value, str):
                serialized = value
            else:
                serialized = json.dumps({"_value": value})

            # Set with optional TTL
            if ttl:
                ttl_seconds = int(ttl.total_seconds())
                await self._client.setex(key, ttl_seconds, serialized)
            else:
                await self._client.set(key, serialized)

            return True
        except RedisError as e:
            logger.error(f"Error setting key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            result = await self._client.delete(key)
            return result > 0
        except RedisError as e:
            logger.error(f"Error deleting key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        try:
            result = await self._client.exists(key)
            return result > 0
        except RedisError as e:
            logger.error(f"Error checking key {key}: {e}")
            return False

    # Batch Operations

    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache."""
        try:
            if not keys:
                return {}

            values = await self._client.mget(keys)
            result = {}

            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        result[key] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        result[key] = value

            return result
        except RedisError as e:
            logger.error(f"Error getting multiple keys: {e}")
            return {}

    async def set_many(
        self,
        mapping: Dict[str, Any],
        ttl: Optional[timedelta] = None
    ) -> int:
        """Set multiple key-value pairs in cache."""
        try:
            if not mapping:
                return 0

            # Serialize all values
            serialized = {}
            for key, value in mapping.items():
                if isinstance(value, (dict, list)):
                    serialized[key] = json.dumps(value)
                elif isinstance(value, str):
                    serialized[key] = value
                else:
                    serialized[key] = json.dumps({"_value": value})

            # Use pipeline for batch operation
            async with self._client.pipeline(transaction=False) as pipe:
                for key, value in serialized.items():
                    if ttl:
                        ttl_seconds = int(ttl.total_seconds())
                        await pipe.setex(key, ttl_seconds, value)
                    else:
                        await pipe.set(key, value)
                await pipe.execute()

            return len(mapping)
        except RedisError as e:
            logger.error(f"Error setting multiple keys: {e}")
            return 0

    async def delete_many(self, keys: List[str]) -> int:
        """Delete multiple keys from cache."""
        try:
            if not keys:
                return 0

            result = await self._client.delete(*keys)
            return result
        except RedisError as e:
            logger.error(f"Error deleting multiple keys: {e}")
            return 0

    # Pattern Operations

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        try:
            keys = []
            async for key in self._client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                return await self.delete_many(keys)
            return 0
        except RedisError as e:
            logger.error(f"Error clearing pattern {pattern}: {e}")
            return 0

    async def keys(self, pattern: str = "*") -> List[str]:
        """Get all keys matching pattern."""
        try:
            keys = []
            async for key in self._client.scan_iter(match=pattern):
                keys.append(key)
            return keys
        except RedisError as e:
            logger.error(f"Error scanning keys: {e}")
            return []

    # Atomic Operations

    async def increment(self, key: str, delta: int = 1) -> Optional[int]:
        """Increment a counter."""
        try:
            if delta == 1:
                return await self._client.incr(key)
            else:
                return await self._client.incrby(key, delta)
        except RedisError as e:
            logger.error(f"Error incrementing key {key}: {e}")
            return None

    async def get_and_set(
        self,
        key: str,
        value: Any,
        ttl: Optional[timedelta] = None
    ) -> Optional[Any]:
        """Get current value and set new value atomically."""
        try:
            # Get old value
            old_value = await self.get(key)

            # Set new value
            await self.set(key, value, ttl)

            return old_value
        except RedisError as e:
            logger.error(f"Error in get_and_set for key {key}: {e}")
            return None

    # List Operations

    async def lpush(self, key: str, *values: Any) -> int:
        """Push values to the left of a list."""
        try:
            serialized = [self._serialize_list_value(v) for v in values]
            return await self._client.lpush(key, *serialized)
        except RedisError as e:
            logger.error(f"Error in lpush for key {key}: {e}")
            return 0

    async def rpush(self, key: str, *values: Any) -> int:
        """Push values to the right of a list."""
        try:
            serialized = [self._serialize_list_value(v) for v in values]
            return await self._client.rpush(key, *serialized)
        except RedisError as e:
            logger.error(f"Error in rpush for key {key}: {e}")
            return 0

    async def lpop(self, key: str) -> Optional[Any]:
        """Pop value from the left of a list."""
        try:
            value = await self._client.lpop(key)
            if value is None:
                return None
            return self._deserialize_list_value(value)
        except RedisError as e:
            logger.error(f"Error in lpop for key {key}: {e}")
            return None

    async def rpop(self, key: str) -> Optional[Any]:
        """Pop value from the right of a list."""
        try:
            value = await self._client.rpop(key)
            if value is None:
                return None
            return self._deserialize_list_value(value)
        except RedisError as e:
            logger.error(f"Error in rpop for key {key}: {e}")
            return None

    async def lrange(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """Get a range of elements from a list."""
        try:
            values = await self._client.lrange(key, start, end)
            return [self._deserialize_list_value(v) for v in values]
        except RedisError as e:
            logger.error(f"Error in lrange for key {key}: {e}")
            return []

    async def llen(self, key: str) -> int:
        """Get the length of a list."""
        try:
            return await self._client.llen(key)
        except RedisError as e:
            logger.error(f"Error in llen for key {key}: {e}")
            return 0

    # Helper Methods

    def _serialize_list_value(self, value: Any) -> str:
        """Serialize value for list storage."""
        if isinstance(value, (dict, list)):
            return json.dumps(value, separators=(",", ":"))
        elif isinstance(value, str):
            return value
        else:
            return json.dumps({"_v": value}, separators=(",", ":"))

    def _deserialize_list_value(self, value: str) -> Any:
        """Deserialize value from list storage."""
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value


@register_cache_adapter("memory")
class MemoryCacheAdapter(CacheAdapter):
    """
    In-memory cache adapter for testing/development.

    Features:
    - No external dependencies
    - Thread-safe operations
    - TTL support
    - Pattern matching (basic)
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        if "memory" in config:
            config.update(config["memory"])

        self.max_size = config.get("max_size", 1000)
        self.default_ttl = config.get("default_ttl", 300)

        self._cache: Dict[str, tuple[Any, Optional[float]]] = {}
        self._lists: Dict[str, List[Any]] = {}
        self._counters: Dict[str, int] = {}

    async def initialize(self) -> None:
        """Initialize the memory cache."""
        self._initialized = True
        logger.info("Memory cache initialized")

    async def close(self) -> None:
        """Clear the memory cache."""
        self._cache.clear()
        self._lists.clear()
        self._counters.clear()
        self._initialized = False
        logger.info("Memory cache closed")

    async def health_check(self) -> bool:
        """Memory cache is always healthy."""
        return True

    # Basic Operations
    async def get(self, key: str) -> Optional[Any]:
        value, expiry = self._cache.get(key, (None, None))

        if value is None:
            return None

        if expiry is not None and expiry < self._now():
            del self._cache[key]
            return None

        return value

    async def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> bool:
        if len(self._cache) >= self.max_size and key not in self._cache:
            return False

        expiry = None
        if ttl:
            expiry = self._now() + ttl.total_seconds()
        elif self.default_ttl:
            expiry = self._now() + self.default_ttl

        self._cache[key] = (value, expiry)
        return True

    async def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    async def exists(self, key: str) -> bool:
        value, expiry = self._cache.get(key, (None, None))
        return value is not None and (expiry is None or expiry >= self._now())

    # Batch Operations
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        result = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value
        return result

    async def set_many(self, mapping: Dict[str, Any], ttl: Optional[timedelta] = None) -> int:
        count = 0
        for key, value in mapping.items():
            if await self.set(key, value, ttl):
                count += 1
        return count

    async def delete_many(self, keys: List[str]) -> int:
        count = 0
        for key in keys:
            if await self.delete(key):
                count += 1
        return count

    # Pattern Operations
    async def clear_pattern(self, pattern: str) -> int:
        import fnmatch
        to_delete = [k for k in self._cache.keys() if fnmatch.fnmatch(k, pattern)]
        for key in to_delete:
            del self._cache[key]
        return len(to_delete)

    async def keys(self, pattern: str = "*") -> List[str]:
        import fnmatch
        return [k for k in self._cache.keys() if fnmatch.fnmatch(k, pattern)]

    # Atomic Operations
    async def increment(self, key: str, delta: int = 1) -> Optional[int]:
        current = self._counters.get(key, 0)
        new_value = current + delta
        self._counters[key] = new_value
        return new_value

    async def get_and_set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> Optional[Any]:
        old_value = await self.get(key)
        await self.set(key, value, ttl)
        return old_value

    # List Operations
    async def lpush(self, key: str, *values: Any) -> int:
        if key not in self._lists:
            self._lists[key] = []
        # Insert values in reverse order so first value ends up at index 0
        for value in values:
            self._lists[key].insert(0, value)
        return len(self._lists[key])

    async def rpush(self, key: str, *values: Any) -> int:
        if key not in self._lists:
            self._lists[key] = []
        self._lists[key].extend(values)
        return len(self._lists[key])

    async def lpop(self, key: str) -> Optional[Any]:
        if key not in self._lists or not self._lists[key]:
            return None
        return self._lists[key].pop(0)

    async def rpop(self, key: str) -> Optional[Any]:
        if key not in self._lists or not self._lists[key]:
            return None
        return self._lists[key].pop()

    async def lrange(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        if key not in self._lists:
            return []
        lst = self._lists[key]
        if end == -1:
            return lst[start:]
        return lst[start:end + 1]

    async def llen(self, key: str) -> int:
        return len(self._lists.get(key, []))

    # Helper
    def _now(self) -> float:
        import time
        return time.time()
