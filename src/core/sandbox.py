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
Sandbox Environment Manager for AInTandem Agent MCP Scheduler.

Provides execution isolation, resource limits, and security policies.
"""

import asyncio
import os
import resource
import subprocess
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


# ============================================================================
# Sandbox Configuration
# ============================================================================

class SandboxConfig:
    """Sandbox configuration settings."""

    def __init__(
        self,
        enabled: bool = True,
        max_memory_mb: int = 512,
        max_cpu_time: int = 30,
        max_wall_time: int = 60,
        max_processes: int = 10,
        allowed_paths: Optional[List[str]] = None,
        blocked_paths: Optional[List[str]] = None,
        network_access: bool = True,
        tmp_dir: Optional[str] = None,
    ):
        """
        Initialize sandbox configuration.

        Args:
            enabled: Enable sandbox restrictions
            max_memory_mb: Maximum memory in MB
            max_cpu_time: Maximum CPU time in seconds
            max_wall_time: Maximum wall clock time in seconds
            max_processes: Maximum number of processes
            allowed_paths: List of allowed file paths
            blocked_paths: List of blocked file paths
            network_access: Allow network access
            tmp_dir: Temporary directory for sandbox
        """
        self.enabled = enabled
        self.max_memory_mb = max_memory_mb
        self.max_cpu_time = max_cpu_time
        self.max_wall_time = max_wall_time
        self.max_processes = max_processes
        self.allowed_paths = allowed_paths or []
        self.blocked_paths = blocked_paths or [
            "/etc/passwd",
            "/etc/shadow",
            "/etc/sudoers",
            "~/.ssh",
        ]
        self.network_access = network_access
        self.tmp_dir = tmp_dir or tempfile.gettempdir()


# ============================================================================
# Sandbox Manager
# ============================================================================

class SandboxManager:
    """
    Manages sandbox environment for agent execution.

    Features:
    - Process isolation (using subprocess)
    - Resource limits (memory, CPU, time)
    - File system access control
    - Network access control
    - Temporary directory management
    """

    def __init__(self, config: Optional[SandboxConfig] = None):
        """
        Initialize the sandbox manager.

        Args:
            config: Sandbox configuration
        """
        self.config = config or SandboxConfig()
        self._active_sandboxes: Dict[str, Dict[str, Any]] = {}

    @asynccontextmanager
    async def create_sandbox(self, task_id: str):
        """
        Create a sandboxed execution environment.

        Args:
            task_id: Task identifier

        Yields:
            Sandbox context dictionary
        """
        if not self.config.enabled:
            yield {"task_id": task_id, "sandboxed": False}
            return

        sandbox_info = {
            "task_id": task_id,
            "sandboxed": True,
            "tmp_dir": None,
            "original_limits": {},
        }

        try:
            # Create temporary directory
            tmp_dir = Path(self.config.tmp_dir) / f"sandbox_{task_id}"
            tmp_dir.mkdir(parents=True, exist_ok=True)
            sandbox_info["tmp_dir"] = str(tmp_dir)

            # Set resource limits
            sandbox_info["original_limits"] = self._set_resource_limits()

            logger.info(f"Sandbox created for task {task_id}: {tmp_dir}")
            self._active_sandboxes[task_id] = sandbox_info

            yield sandbox_info

        finally:
            # Cleanup
            self._cleanup_sandbox(task_id)

    def _cleanup_sandbox(self, task_id: str):
        """
        Cleanup sandbox resources.

        Args:
            task_id: Task identifier
        """
        if task_id not in self._active_sandboxes:
            return

        sandbox_info = self._active_sandboxes[task_id]

        # Restore original resource limits
        if sandbox_info.get("original_limits"):
            self._restore_resource_limits(sandbox_info["original_limits"])

        # Clean up temporary directory
        if sandbox_info.get("tmp_dir"):
            tmp_path = Path(sandbox_info["tmp_dir"])
            if tmp_path.exists():
                try:
                    import shutil
                    shutil.rmtree(tmp_path)
                    logger.info(f"Cleaned up sandbox: {tmp_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup sandbox {tmp_path}: {e}")

        # Remove from active sandboxes
        del self._active_sandboxes[task_id]

    def _set_resource_limits(self) -> Dict[str, int]:
        """
        Set resource limits for the current process.

        Returns:
            Dictionary of original limits
        """
        original_limits = {}

        try:
            # Memory limit (bytes)
            if self.config.max_memory_mb > 0:
                memory_limit = self.config.max_memory_mb * 1024 * 1024
                original_limits["memory"] = resource.getrlimit(resource.RLIMIT_AS)
                resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
                logger.debug(f"Set memory limit: {self.config.max_memory_mb}MB")

            # CPU time limit (seconds)
            if self.config.max_cpu_time > 0:
                original_limits["cpu"] = resource.getrlimit(resource.RLIMIT_CPU)
                resource.setrlimit(resource.RLIMIT_CPU, (self.config.max_cpu_time, self.config.max_cpu_time))
                logger.debug(f"Set CPU time limit: {self.config.max_cpu_time}s")

            # Process limit
            if self.config.max_processes > 0:
                original_limits["processes"] = resource.getrlimit(resource.RLIMIT_NPROC)
                resource.setrlimit(resource.RLIMIT_NPROC, (self.config.max_processes, self.config.max_processes))
                logger.debug(f"Set process limit: {self.config.max_processes}")

        except (ValueError, resource.error) as e:
            logger.warning(f"Failed to set resource limits: {e}")

        return original_limits

    def _restore_resource_limits(self, original_limits: Dict[str, tuple]):
        """
        Restore original resource limits.

        Args:
            original_limits: Dictionary of original limits
        """
        try:
            if "memory" in original_limits:
                resource.setrlimit(resource.RLIMIT_AS, original_limits["memory"])

            if "cpu" in original_limits:
                resource.setrlimit(resource.RLIMIT_CPU, original_limits["cpu"])

            if "processes" in original_limits:
                resource.setrlimit(resource.RLIMIT_NPROC, original_limits["processes"])

            logger.debug("Restored original resource limits")

        except (ValueError, resource.error) as e:
            logger.warning(f"Failed to restore resource limits: {e}")

    async def execute_in_sandbox(
        self,
        task_id: str,
        command: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        input_data: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a command in a sandboxed environment.

        Args:
            task_id: Task identifier
            command: Command to execute
            cwd: Working directory
            env: Environment variables
            input_data: Input data for the command

        Returns:
            Dictionary with execution results
        """
        if not self.config.enabled:
            return await self._execute_command(command, cwd, env, input_data)

        # Create sandbox environment
        with self.create_sandbox(task_id) as sandbox:
            # Use sandbox temp directory if not specified
            if not cwd and sandbox.get("tmp_dir"):
                cwd = sandbox["tmp_dir"]

            # Prepare environment
            if env is None:
                env = os.environ.copy()

            # Restrict network if needed
            if not self.config.network_access:
                # Set proxy to invalid address to block network
                env["http_proxy"] = "http://invalid:0"
                env["https_proxy"] = "http://invalid:0"

            # Execute with timeout
            try:
                result = await asyncio.wait_for(
                    self._execute_command(command, cwd, env, input_data),
                    timeout=self.config.max_wall_time,
                )
                return result

            except asyncio.TimeoutError:
                return {
                    "success": False,
                    "error": f"Execution timeout ({self.config.max_wall_time}s)",
                    "timeout": True,
                }

    async def _execute_command(
        self,
        command: List[str],
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        input_data: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a command.

        Args:
            command: Command to execute
            cwd: Working directory
            env: Environment variables
            input_data: Input data for the command

        Returns:
            Dictionary with execution results
        """
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=cwd,
                env=env,
                stdin=asyncio.subprocess.PIPE if input_data else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate(
                input_data.encode() if input_data else None
            )

            return {
                "success": process.returncode == 0,
                "returncode": process.returncode,
                "stdout": stdout.decode(),
                "stderr": stderr.decode(),
            }

        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def check_path_access(self, path: str, mode: str = "read") -> bool:
        """
        Check if path access is allowed.

        Args:
            path: Path to check
            mode: Access mode (read, write, execute)

        Returns:
            True if access is allowed
        """
        if not self.config.enabled:
            return True

        # Check blocked paths
        for blocked in self.config.blocked_paths:
            if path.startswith(blocked) or path == blocked:
                logger.warning(f"Path access blocked: {path}")
                return False

        # Check allowed paths
        if self.config.allowed_paths:
            allowed = False
            for allowed_path in self.config.allowed_paths:
                if path.startswith(allowed_path):
                    allowed = True
                    break
            if not allowed:
                logger.warning(f"Path access not in allowed list: {path}")
                return False

        return True

    def get_sandbox_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about an active sandbox.

        Args:
            task_id: Task identifier

        Returns:
            Sandbox information or None
        """
        return self._active_sandboxes.get(task_id)

    def list_active_sandboxes(self) -> List[str]:
        """
        List all active sandbox IDs.

        Returns:
            List of task IDs with active sandboxes
        """
        return list(self._active_sandboxes.keys())

    def get_stats(self) -> Dict[str, Any]:
        """
        Get sandbox statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "enabled": self.config.enabled,
            "active_sandboxes": len(self._active_sandboxes),
            "max_memory_mb": self.config.max_memory_mb,
            "max_cpu_time": self.config.max_cpu_time,
            "max_wall_time": self.config.max_wall_time,
            "max_processes": self.config.max_processes,
            "network_access": self.config.network_access,
        }


# ============================================================================
# Factory Functions
# ============================================================================

def create_sandbox_manager(config: Optional[SandboxConfig] = None) -> SandboxManager:
    """
    Create a sandbox manager.

    Args:
        config: Sandbox configuration

    Returns:
        SandboxManager instance
    """
    return SandboxManager(config)
