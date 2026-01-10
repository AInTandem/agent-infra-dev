# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Health check utilities for the message bus

Provides monitoring and health status tracking for Redis connections
and message bus operations.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError, RedisError, TimeoutError

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    status: HealthStatus
    latency_ms: float
    message: str
    timestamp: float
    details: dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "status": self.status.value,
            "latency_ms": round(self.latency_ms, 2),
            "message": self.message,
            "timestamp": self.timestamp,
            "details": self.details,
        }


class HealthChecker:
    """
    Health checker for Redis and message bus operations

    Features:
    - Connection health monitoring
    - Latency tracking
    - Operation verification
    - Historical health tracking
    - Configurable thresholds

    Usage:
        checker = HealthChecker(redis_client)

        # Perform health check
        result = await checker.check()
        print(f"Status: {result.status}, Latency: {result.latency_ms}ms")

        # Check specific operations
        ping_result = await checker.check_ping()
        pubsub_result = await checker.check_pubsub()
        queue_result = await checker.check_queue()
    """

    def __init__(
        self,
        redis_client: Redis,
        latency_warning_threshold: float = 50.0,
        latency_critical_threshold: float = 200.0,
        timeout: float = 5.0,
    ):
        """
        Initialize health checker

        Args:
            redis_client: Redis client instance
            latency_warning_threshold: Latency threshold (ms) for degraded status
            latency_critical_threshold: Latency threshold (ms) for unhealthy status
            timeout: Timeout in seconds for health check operations
        """
        self._redis = redis_client
        self._latency_warning = latency_warning_threshold
        self._latency_critical = latency_critical_threshold
        self._timeout = timeout

        # Historical tracking
        self._latency_history: list[float] = []
        self._max_history = 100

    async def check(self) -> HealthCheckResult:
        """
        Perform comprehensive health check

        Returns:
            HealthCheckResult with overall status
        """
        start_time = time.time()
        details = {}
        issues = []

        # Check basic connection
        ping_ok = await self._check_ping_with_timeout()
        if not ping_ok:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                latency_ms=(time.time() - start_time) * 1000,
                message="Redis connection failed",
                timestamp=time.time(),
            )

        # Check operations
        ping_result = await self.check_ping()
        details["ping"] = ping_result.to_dict()
        if ping_result.status != HealthStatus.HEALTHY:
            issues.append(f"Ping: {ping_result.message}")

        # Check write/read
        write_result = await self.check_write_read()
        details["write_read"] = write_result.to_dict()
        if write_result.status != HealthStatus.HEALTHY:
            issues.append(f"Write/Read: {write_result.message}")

        # Check pub/sub
        pubsub_result = await self.check_pubsub()
        details["pubsub"] = pubsub_result.to_dict()
        if pubsub_result.status != HealthStatus.HEALTHY:
            issues.append(f"Pub/Sub: {pubsub_result.message}")

        # Check queue operations
        queue_result = await self.check_queue()
        details["queue"] = queue_result.to_dict()
        if queue_result.status != HealthStatus.HEALTHY:
            issues.append(f"Queue: {queue_result.message}")

        # Determine overall status
        latency_ms = (time.time() - start_time) * 1000

        if issues:
            status = HealthStatus.UNHEALTHY
            message = "; ".join(issues)
        elif latency_ms > self._latency_critical:
            status = HealthStatus.UNHEALTHY
            message = f"High latency: {latency_ms:.2f}ms"
        elif latency_ms > self._latency_warning:
            status = HealthStatus.DEGRADED
            message = f"Elevated latency: {latency_ms:.2f}ms"
        else:
            status = HealthStatus.HEALTHY
            message = "All systems operational"

        # Update latency history
        self._update_latency_history(latency_ms)

        return HealthCheckResult(
            status=status,
            latency_ms=latency_ms,
            message=message,
            timestamp=time.time(),
            details=details,
        )

    async def check_ping(self) -> HealthCheckResult:
        """Check Redis PING operation"""
        start_time = time.time()

        try:
            await asyncio.wait_for(self._redis.ping(), timeout=self._timeout)
            latency_ms = (time.time() - start_time) * 1000

            # Update latency history
            self._update_latency_history(latency_ms)

            status = self._status_from_latency(latency_ms)
            message = f"PING successful in {latency_ms:.2f}ms"

            return HealthCheckResult(
                status=status,
                latency_ms=latency_ms,
                message=message,
                timestamp=time.time(),
            )

        except (asyncio.TimeoutError, TimeoutError):
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                latency_ms=self._timeout * 1000,
                message="PING timeout",
                timestamp=time.time(),
            )
        except RedisError as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                latency_ms=(time.time() - start_time) * 1000,
                message=f"PING failed: {e}",
                timestamp=time.time(),
            )

    async def check_write_read(self) -> HealthCheckResult:
        """Check Redis write/read operations"""
        start_time = time.time()
        test_key = "health_check_test"
        test_value = f"test_{time.time()}"

        try:
            # Write
            await asyncio.wait_for(
                self._redis.set(test_key, test_value, ex=10),
                timeout=self._timeout,
            )

            # Read
            result = await asyncio.wait_for(
                self._redis.get(test_key),
                timeout=self._timeout,
            )

            latency_ms = (time.time() - start_time) * 1000

            if result != test_value:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    latency_ms=latency_ms,
                    message=f"Write/Read mismatch: expected '{test_value}', got '{result}'",
                    timestamp=time.time(),
                )

            status = self._status_from_latency(latency_ms)
            message = f"Write/Read successful in {latency_ms:.2f}ms"

            return HealthCheckResult(
                status=status,
                latency_ms=latency_ms,
                message=message,
                timestamp=time.time(),
            )

        except (asyncio.TimeoutError, TimeoutError):
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                latency_ms=self._timeout * 1000,
                message="Write/Read timeout",
                timestamp=time.time(),
            )
        except RedisError as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                latency_ms=(time.time() - start_time) * 1000,
                message=f"Write/Read failed: {e}",
                timestamp=time.time(),
            )

    async def check_pubsub(self) -> HealthCheckResult:
        """Check Redis Pub/Sub operations"""
        start_time = time.time()
        test_channel = f"health_check_test_{int(time.time())}"

        try:
            pubsub = self._redis.pubsub()
            await asyncio.wait_for(
                pubsub.subscribe(test_channel),
                timeout=self._timeout,
            )

            # Publish test message
            await asyncio.wait_for(
                self._redis.publish(test_channel, "test"),
                timeout=self._timeout,
            )

            # Try to get message
            try:
                msg = await asyncio.wait_for(
                    pubsub.get_message(timeout=0.5),
                    timeout=1.0,
                )
            except asyncio.TimeoutError:
                msg = None

            await pubsub.close()

            latency_ms = (time.time() - start_time) * 1000

            status = self._status_from_latency(latency_ms)
            message = f"Pub/Sub check successful in {latency_ms:.2f}ms"

            return HealthCheckResult(
                status=status,
                latency_ms=latency_ms,
                message=message,
                timestamp=time.time(),
            )

        except (asyncio.TimeoutError, TimeoutError):
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                latency_ms=self._timeout * 1000,
                message="Pub/Sub timeout",
                timestamp=time.time(),
            )
        except RedisError as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                latency_ms=(time.time() - start_time) * 1000,
                message=f"Pub/Sub failed: {e}",
                timestamp=time.time(),
            )

    async def check_queue(self) -> HealthCheckResult:
        """Check Redis queue operations (sorted set)"""
        start_time = time.time()
        test_queue = f"health_check_queue_{int(time.time())}"

        try:
            # Enqueue
            await asyncio.wait_for(
                self._redis.zadd(test_queue, {"test": 1}),
                timeout=self._timeout,
            )

            # Dequeue
            result = await asyncio.wait_for(
                self._redis.zpopmin(test_queue, count=1),
                timeout=self._timeout,
            )

            latency_ms = (time.time() - start_time) * 1000

            if not result:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    latency_ms=latency_ms,
                    message="Queue operation returned no data",
                    timestamp=time.time(),
                )

            status = self._status_from_latency(latency_ms)
            message = f"Queue operation successful in {latency_ms:.2f}ms"

            return HealthCheckResult(
                status=status,
                latency_ms=latency_ms,
                message=message,
                timestamp=time.time(),
            )

        except (asyncio.TimeoutError, TimeoutError):
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                latency_ms=self._timeout * 1000,
                message="Queue operation timeout",
                timestamp=time.time(),
            )
        except RedisError as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                latency_ms=(time.time() - start_time) * 1000,
                message=f"Queue operation failed: {e}",
                timestamp=time.time(),
            )

    async def _check_ping_with_timeout(self) -> bool:
        """Quick check if Redis is responding"""
        try:
            await asyncio.wait_for(self._redis.ping(), timeout=1.0)
            return True
        except (asyncio.TimeoutError, RedisError):
            return False

    def _status_from_latency(self, latency_ms: float) -> HealthStatus:
        """Determine health status from latency"""
        if latency_ms > self._latency_critical:
            return HealthStatus.UNHEALTHY
        elif latency_ms > self._latency_warning:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    def _update_latency_history(self, latency_ms: float) -> None:
        """Update latency history for tracking"""
        self._latency_history.append(latency_ms)
        if len(self._latency_history) > self._max_history:
            self._latency_history.pop(0)

    def get_average_latency(self) -> Optional[float]:
        """Get average latency from history"""
        if not self._latency_history:
            return None
        return sum(self._latency_history) / len(self._latency_history)

    def get_latency_stats(self) -> dict:
        """Get latency statistics"""
        if not self._latency_history:
            return {
                "count": 0,
                "average": None,
                "min": None,
                "max": None,
            }

        return {
            "count": len(self._latency_history),
            "average": round(sum(self._latency_history) / len(self._latency_history), 2),
            "min": round(min(self._latency_history), 2),
            "max": round(max(self._latency_history), 2),
        }
