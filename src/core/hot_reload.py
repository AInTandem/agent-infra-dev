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
Hot Reload Manager for configuration changes.

Monitors config files for changes and automatically reloads components.
"""

import asyncio
import os
from pathlib import Path
from typing import Awaitable, Callable, Dict, Optional, Set

from loguru import logger
from rich.console import Console

console = Console()


class HotReloadManager:
    """
    Manages hot reloading of configuration and components.

    Monitors the config directory for file changes and triggers
    appropriate reload actions when files are modified.

    For code changes in src/, triggers application restart.
    """

    def __init__(
        self,
        config_dir: str = "config",
        src_dir: str = "src",
        check_interval: float = 1.0,
    ):
        """
        Initialize the Hot Reload Manager.

        Args:
            config_dir: Directory containing configuration files
            src_dir: Directory containing source code files
            check_interval: Seconds between checks for file changes
        """
        self.config_dir = Path(config_dir)
        self.src_dir = Path(src_dir)
        self.check_interval = check_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Track file modification times
        self._file_mtimes: Dict[str, float] = {}

        # Reload handlers for different file types
        self._handlers: Dict[str, Callable[[], Awaitable[None]]] = {}

        # Restart callback for code changes
        self._restart_callback: Optional[Callable[[], Awaitable[None]]] = None

        # Files to monitor
        self._monitored_files: Set[str] = set()

        # Code patterns to monitor
        self._code_patterns: Set[str] = set()

        # Debounce timer to avoid multiple rapid reloads
        self._reload_pending = False
        self._reload_delay = 2.0  # seconds to wait before reload

    def register_handler(
        self,
        file_pattern: str,
        handler: Callable[[], Awaitable[None]]
    ):
        """
        Register a reload handler for a specific file pattern.

        Args:
            file_pattern: File pattern (e.g., "agents.yaml", "*.yaml")
            handler: Async function to call when file changes
        """
        self._handlers[file_pattern] = handler
        logger.debug(f"Registered hot reload handler for: {file_pattern}")

    def register_restart_callback(self, callback: Callable[[], Awaitable[None]]):
        """
        Register a callback for application restart when code changes.

        Args:
            callback: Async function to call for restart
        """
        self._restart_callback = callback
        logger.debug("Registered restart callback for code changes")

    def monitor_files(self, file_patterns: list[str]):
        """
        Specify which files to monitor.

        Args:
            file_patterns: List of file patterns to monitor
        """
        self._monitored_files.clear()
        for pattern in file_patterns:
            # Handle both specific files and patterns
            if "*" in pattern:
                # Expand pattern
                for file_path in self.config_dir.glob(pattern):
                    if file_path.is_file():
                        self._monitored_files.add(file_path.name)
            else:
                self._monitored_files.add(pattern)

        # Initialize mtimes
        for filename in self._monitored_files:
            file_path = self.config_dir / filename
            if file_path.exists():
                self._file_mtimes[filename] = file_path.stat().st_mtime
                logger.debug(f"Monitoring file: {filename}")

    def monitor_code(self, patterns: list[str] = None):
        """
        Monitor source code files for changes.

        When code changes, triggers application restart.

        Args:
            patterns: List of glob patterns (default: ["**/*.py"])
        """
        if patterns is None:
            patterns = ["**/*.py"]

        self._code_patterns.clear()
        for pattern in patterns:
            # Find matching files
            for file_path in self.src_dir.rglob(pattern):
                if file_path.is_file():
                    # Use relative path as key
                    rel_path = str(file_path.relative_to(self.src_dir))
                    self._file_mtimes[f"code:{rel_path}"] = file_path.stat().st_mtime
                    self._code_patterns.add(rel_path)

        logger.info(f"Monitoring {len(self._code_patterns)} Python files in {self.src_dir}")

    async def start(self):
        """Start the hot reload monitor."""
        if self._running:
            logger.warning("Hot reload already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Hot reload monitor started")

    async def stop(self):
        """Stop the hot reload monitor."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("Hot reload monitor stopped")

    async def _monitor_loop(self):
        """Main monitoring loop."""
        try:
            while self._running:
                await asyncio.sleep(self.check_interval)

                # Check for file changes
                changed_files = await self._check_changes()

                if changed_files:
                    # Debounce: wait a bit before reloading
                    # to catch multiple file changes at once
                    await asyncio.sleep(self._reload_delay)

                    # Final check for any new changes
                    changed_files = await self._check_changes()

                    if changed_files:
                        await self._trigger_reload(changed_files)

        except asyncio.CancelledError:
            logger.debug("Hot reload monitor cancelled")
        except Exception as e:
            logger.error(f"Hot reload monitor error: {e}")

    async def _check_changes(self) -> Set[str]:
        """
        Check for file changes.

        Returns:
            Set of filenames that changed (prefixed with "code:" for source files)
        """
        changed = set()

        # Check config files
        for filename in self._monitored_files:
            file_path = self.config_dir / filename

            if not file_path.exists():
                continue

            current_mtime = file_path.stat().st_mtime
            last_mtime = self._file_mtimes.get(filename, 0)

            if current_mtime > last_mtime:
                changed.add(filename)
                self._file_mtimes[filename] = current_mtime
                logger.info(f"Detected config change in: {filename}")

        # Check code files
        for rel_path in self._code_patterns:
            file_path = self.src_dir / rel_path
            key = f"code:{rel_path}"

            if not file_path.exists():
                # File was deleted, remove from monitoring
                self._file_mtimes.pop(key, None)
                continue

            current_mtime = file_path.stat().st_mtime
            last_mtime = self._file_mtimes.get(key, 0)

            if current_mtime > last_mtime:
                changed.add(key)
                self._file_mtimes[key] = current_mtime
                logger.info(f"Detected code change in: {rel_path}")

        return changed

    async def _trigger_reload(self, changed_files: Set[str]):
        """
        Trigger reload for changed files.

        Args:
            changed_files: Set of filenames that changed (prefixed with "code:" for source)
        """
        # Separate code changes from config changes
        code_changes = {f for f in changed_files if f.startswith("code:")}
        config_changes = changed_files - code_changes

        # Handle code changes first (requires restart)
        if code_changes:
            code_files = [f.replace("code:", "") for f in code_changes]
            logger.warning(f"Code changes detected in: {', '.join(code_files)}")
            logger.info("Application restart required for code changes")

            if self._restart_callback:
                console.print("\n[yellow]Code changes detected. Restarting application...[/yellow]\n")
                try:
                    await self._restart_callback()
                except Exception as e:
                    logger.error(f"Restart callback failed: {e}")
            return

        # Handle config changes
        if config_changes:
            logger.info(f"Reloading due to config changes in: {', '.join(config_changes)}")

            # Find matching handlers
            handlers_to_run = []
            for file_pattern, handler in self._handlers.items():
                # Check if any changed file matches the pattern
                for filename in config_changes:
                    if self._matches_pattern(filename, file_pattern):
                        handlers_to_run.append(handler)
                        break

            # Run all matching handlers
            for handler in handlers_to_run:
                try:
                    logger.debug(f"Running reload handler...")
                    await handler()
                    logger.info("Reload completed successfully")
                except Exception as e:
                    logger.error(f"Reload handler failed: {e}")

    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """
        Check if filename matches pattern.

        Args:
            filename: File to check
            pattern: Pattern to match against

        Returns:
            True if filename matches pattern
        """
        if pattern == "*":
            return True

        if pattern.startswith("*"):
            # Wildcard prefix (e.g., "*.yaml")
            return filename.endswith(pattern[1:])

        if pattern.endswith("*"):
            # Wildcard suffix
            return filename.startswith(pattern[:-1])

        # Exact match
        return filename == pattern

    @property
    def is_running(self) -> bool:
        """Check if hot reload is running."""
        return self._running
