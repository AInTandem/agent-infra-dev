"""
Resource Limiter for Qwen Agent MCP Scheduler.

Provides resource monitoring and limiting capabilities.
"""

import asyncio
import psutil
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from loguru import logger


# ============================================================================
# Resource Metrics
# ============================================================================

@dataclass
class ResourceMetrics:
    """Resource usage metrics."""
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    disk_read_mb: float
    disk_write_mb: float
    network_sent_mb: float
    network_recv_mb: float
    open_files: int
    num_threads: int


# ============================================================================
# Resource Limiter
# ============================================================================

class ResourceLimiter:
    """
    Monitors and limits resource usage for agent execution.

    Features:
    - CPU usage monitoring
    - Memory usage monitoring
    - Disk I/O tracking
    - Network I/O tracking
    - Open file tracking
    - Thread count monitoring
    """

    def __init__(
        self,
        max_cpu_percent: float = 80.0,
        max_memory_mb: float = 512.0,
        max_open_files: int = 100,
        max_threads: int = 10,
        check_interval: float = 1.0,
    ):
        """
        Initialize the resource limiter.

        Args:
            max_cpu_percent: Maximum CPU usage percentage
            max_memory_mb: Maximum memory usage in MB
            max_open_files: Maximum number of open files
            max_threads: Maximum number of threads
            check_interval: Monitoring check interval in seconds
        """
        self.max_cpu_percent = max_cpu_percent
        self.max_memory_mb = max_memory_mb
        self.max_open_files = max_open_files
        self.max_threads = max_threads
        self.check_interval = check_interval

        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._violations: list = []

    @asynccontextmanager
    async def limit_resources(self, task_id: str, callback: Optional[Callable] = None):
        """
        Context manager for resource limiting.

        Args:
            task_id: Task identifier
            callback: Optional callback when limits are exceeded

        Yields:
            ResourceMetrics object
        """
        process = psutil.Process()
        self._monitoring = True

        # Start monitoring
        self._monitor_task = asyncio.create_task(
            self._monitor_resources(task_id, process, callback)
        )

        try:
            yield ResourceMetrics(
                cpu_percent=0.0,
                memory_mb=0.0,
                memory_percent=0.0,
                disk_read_mb=0.0,
                disk_write_mb=0.0,
                network_sent_mb=0.0,
                network_recv_mb=0.0,
                open_files=0,
                num_threads=0,
            )
        finally:
            # Stop monitoring
            self._monitoring = False
            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass

    async def _monitor_resources(
        self,
        task_id: str,
        process: psutil.Process,
        callback: Optional[Callable],
    ):
        """
        Monitor resource usage.

        Args:
            task_id: Task identifier
            process: Process to monitor
            callback: Optional callback for violations
        """
        # Get initial I/O counters
        try:
            io_initial = process.io_counters()
        except (psutil.AccessDenied, AttributeError):
            io_initial = None

        while self._monitoring:
            try:
                # CPU usage
                cpu_percent = process.cpu_percent(interval=0.1)

                # Memory usage
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / (1024 * 1024)
                memory_percent = process.memory_percent()

                # Open files
                try:
                    open_files = len(process.open_files())
                except (psutil.AccessDenied, AttributeError):
                    open_files = 0

                # Threads
                num_threads = process.num_threads()

                # Disk I/O
                disk_read_mb = 0.0
                disk_write_mb = 0.0
                if io_initial:
                    try:
                        io_current = process.io_counters()
                        disk_read_mb = (io_current.read_bytes - io_initial.read_bytes) / (1024 * 1024)
                        disk_write_mb = (io_current.write_bytes - io_initial.write_bytes) / (1024 * 1024)
                    except (psutil.AccessDenied, AttributeError):
                        pass

                # Check limits
                violations = []
                if cpu_percent > self.max_cpu_percent:
                    violations.append(f"CPU usage {cpu_percent:.1f}% exceeds {self.max_cpu_percent}%")

                if memory_mb > self.max_memory_mb:
                    violations.append(f"Memory usage {memory_mb:.1f}MB exceeds {self.max_memory_mb}MB")

                if open_files > self.max_open_files:
                    violations.append(f"Open files {open_files} exceeds {self.max_open_files}")

                if num_threads > self.max_threads:
                    violations.append(f"Threads {num_threads} exceeds {self.max_threads}")

                # Log violations
                if violations:
                    for violation in violations:
                        logger.warning(f"[{task_id}] Resource violation: {violation}")
                        self._violations.append({
                            "task_id": task_id,
                            "violation": violation,
                        })

                    # Call callback if provided
                    if callback:
                        await callback(task_id, violations)

                await asyncio.sleep(self.check_interval)

            except psutil.NoSuchProcess:
                logger.debug(f"Process {task_id} no longer exists")
                break
            except Exception as e:
                logger.error(f"Error monitoring resources: {e}")
                await asyncio.sleep(self.check_interval)

    def get_current_metrics(self) -> ResourceMetrics:
        """
        Get current resource metrics.

        Returns:
            ResourceMetrics object
        """
        process = psutil.Process()

        try:
            cpu_percent = process.cpu_percent(interval=0.1)
        except Exception:
            cpu_percent = 0.0

        try:
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            memory_percent = process.memory_percent()
        except Exception:
            memory_mb = 0.0
            memory_percent = 0.0

        try:
            open_files = len(process.open_files())
        except Exception:
            open_files = 0

        try:
            num_threads = process.num_threads()
        except Exception:
            num_threads = 0

        return ResourceMetrics(
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            memory_percent=memory_percent,
            disk_read_mb=0.0,
            disk_write_mb=0.0,
            network_sent_mb=0.0,
            network_recv_mb=0.0,
            open_files=open_files,
            num_threads=num_threads,
        )

    def get_violations(self) -> list:
        """Get list of resource violations."""
        return self._violations.copy()

    def clear_violations(self):
        """Clear violation history."""
        self._violations.clear()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get resource limiter statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "max_cpu_percent": self.max_cpu_percent,
            "max_memory_mb": self.max_memory_mb,
            "max_open_files": self.max_open_files,
            "max_threads": self.max_threads,
            "check_interval": self.check_interval,
            "monitoring": self._monitoring,
            "violations": len(self._violations),
            "current_metrics": self.get_current_metrics().__dict__,
        }


# ============================================================================
# System Resource Monitor
# ============================================================================

class SystemResourceMonitor:
    """
    Monitors system-wide resource usage.
    """

    @staticmethod
    def get_system_stats() -> Dict[str, Any]:
        """
        Get system-wide resource statistics.

        Returns:
            Dictionary with system statistics
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
        except Exception:
            cpu_percent = 0.0

        try:
            memory = psutil.virtual_memory()
            memory_stats = {
                "total_mb": memory.total / (1024 * 1024),
                "available_mb": memory.available / (1024 * 1024),
                "percent": memory.percent,
                "used_mb": memory.used / (1024 * 1024),
            }
        except Exception:
            memory_stats = {}

        try:
            disk = psutil.disk_usage("/")
            disk_stats = {
                "total_mb": disk.total / (1024 * 1024),
                "used_mb": disk.used / (1024 * 1024),
                "free_mb": disk.free / (1024 * 1024),
                "percent": disk.percent,
            }
        except Exception:
            disk_stats = {}

        try:
            cpu_count = psutil.cpu_count()
        except Exception:
            cpu_count = 0

        return {
            "cpu": {
                "percent": cpu_percent,
                "count": cpu_count,
            },
            "memory": memory_stats,
            "disk": disk_stats,
        }


# ============================================================================
# Factory Functions
# ============================================================================

def create_resource_limiter(
    max_cpu_percent: float = 80.0,
    max_memory_mb: float = 512.0,
    max_open_files: int = 100,
    max_threads: int = 10,
    check_interval: float = 1.0,
) -> ResourceLimiter:
    """
    Create a resource limiter.

    Args:
        max_cpu_percent: Maximum CPU usage percentage
        max_memory_mb: Maximum memory usage in MB
        max_open_files: Maximum number of open files
        max_threads: Maximum number of threads
        check_interval: Monitoring check interval in seconds

    Returns:
        ResourceLimiter instance
    """
    return ResourceLimiter(
        max_cpu_percent=max_cpu_percent,
        max_memory_mb=max_memory_mb,
        max_open_files=max_open_files,
        max_threads=max_threads,
        check_interval=check_interval,
    )
