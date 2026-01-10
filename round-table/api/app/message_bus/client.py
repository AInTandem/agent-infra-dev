# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Redis client management with connection pooling

Provides singleton Redis client with connection pooling, health monitoring,
and automatic reconnection logic.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

import redis.asyncio as aioredis
from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import ConnectionError as RedisConnectionError, RedisError

from ..config import settings

logger = logging.getLogger(__name__)

_global_client: Optional[Redis] = None
_global_pool: Optional[ConnectionPool] = None
_lock = asyncio.Lock()


class RedisClient:
    """
    Redis client wrapper with connection pooling and health monitoring

    Features:
    - Automatic connection pooling
    - Connection health checks
    - Automatic reconnection on failure
    - Context manager support
    """

    def __init__(
        self,
        url: str | None = None,
        pool_size: int = 10,
        pool_timeout: int = 5,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        retry_on_timeout: bool = True,
        health_check_interval: int = 30,
    ):
        """
        Initialize Redis client configuration

        Args:
            url: Redis connection URL (defaults to settings.REDIS_URL)
            pool_size: Maximum connection pool size
            pool_timeout: Timeout in seconds for getting connection from pool
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Socket connection timeout in seconds
            retry_on_timeout: Whether to retry commands on timeout
            health_check_interval: Interval in seconds for health checks
        """
        self.url = url or settings.redis_url
        self.pool_size = pool_size
        self.pool_timeout = pool_timeout
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.retry_on_timeout = retry_on_timeout
        self.health_check_interval = health_check_interval

        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None
        self._health_task: Optional[asyncio.Task] = None
        self._is_healthy = True

    async def connect(self) -> Redis:
        """
        Establish Redis connection with connection pooling

        Returns:
            Redis client instance

        Raises:
            RedisConnectionError: If connection fails
        """
        if self._client is not None:
            return self._client

        try:
            # Create connection pool
            self._pool = ConnectionPool.from_url(
                self.url,
                max_connections=self.pool_size,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
                retry_on_timeout=self.retry_on_timeout,
                decode_responses=True,  # Auto-decode bytes to strings
            )

            # Create Redis client
            self._client = Redis(connection_pool=self._pool)

            # Test connection
            await self._client.ping()

            logger.info(f"Connected to Redis at {self.url}")

            # Start health check task
            self._health_task = asyncio.create_task(self._health_check_loop())

            return self._client

        except RedisConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._pool = None
            self._client = None
            raise

    async def disconnect(self) -> None:
        """Close Redis connection and cleanup resources"""
        # Cancel health check task
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
            self._health_task = None

        # Close client connection
        if self._client:
            await self._client.aclose()
            self._client = None

        # Close connection pool
        if self._pool:
            await self._pool.aclose()
            self._pool = None

        logger.info("Disconnected from Redis")

    async def _health_check_loop(self) -> None:
        """Periodic health check task"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                if self._client:
                    await self._client.ping()
                    self._is_healthy = True
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Redis health check failed: {e}")
                self._is_healthy = False

    def is_healthy(self) -> bool:
        """Check if Redis connection is healthy"""
        return self._is_healthy and self._client is not None

    async def execute_command(self, *args, **kwargs) -> any:
        """
        Execute Redis command with automatic retry on connection failure

        Args:
            *args: Command arguments
            **kwargs: Command keyword arguments

        Returns:
            Command result

        Raises:
            RedisConnectionError: If command fails after retries
        """
        if not self._client:
            await self.connect()

        max_retries = 3
        for attempt in range(max_retries):
            try:
                return await self._client.execute_command(*args, **kwargs)
            except RedisConnectionError as e:
                if attempt == max_retries - 1:
                    self._is_healthy = False
                    raise
                logger.warning(f"Redis command failed, retrying ({attempt + 1}/{max_retries}): {e}")
                await asyncio.sleep(0.5 * (attempt + 1))

    @property
    def client(self) -> Redis:
        """Get underlying Redis client (must be connected first)"""
        if self._client is None:
            raise RedisConnectionError("Redis client not connected. Call connect() first.")
        return self._client

    @asynccontextmanager
    async def get_connection(self):
        """
        Context manager for getting a connection from the pool

        Usage:
            async with redis_client.get_connection() as conn:
                await conn.ping()
        """
        if not self._client:
            await self.connect()

        yield self._client


# Singleton instances
_redis_client_wrapper: Optional[RedisClient] = None


async def get_redis_client() -> Redis:
    """
    Get global Redis client singleton

    Returns:
        Redis client instance

    Example:
        redis = await get_redis_client()
        await redis.set("key", "value")
        value = await redis.get("key")
    """
    global _redis_client_wrapper

    async with _lock:
        if _redis_client_wrapper is None:
            _redis_client_wrapper = RedisClient()

        if _redis_client_wrapper._client is None:
            await _redis_client_wrapper.connect()

        return _redis_client_wrapper.client


async def close_redis_client() -> None:
    """Close global Redis client connection"""
    global _redis_client_wrapper

    async with _lock:
        if _redis_client_wrapper:
            await _redis_client_wrapper.disconnect()
            _redis_client_wrapper = None


async def redis_health_check() -> bool:
    """
    Check if Redis connection is healthy

    Returns:
        True if healthy, False otherwise
    """
    global _redis_client_wrapper

    if _redis_client_wrapper:
        return _redis_client_wrapper.is_healthy()

    return False
