#!/usr/bin/env python3
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
Main entry point for AInTandem Agent MCP Scheduler.

This application provides:
- Customizable AI agents with MCP server integration
- Task scheduling capabilities
- OpenAI-compatible API
- Gradio web interface
- Hot reload for configuration changes (development mode)
"""

import asyncio
import os
import signal
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from rich.console import Console

# Load environment variables from .env file
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from api.openapi_server import create_api_server
from core.agent_manager import AgentManager
from core.config import ConfigManager
from core.hot_reload import HotReloadManager
from core.mcp_bridge import MCPBridge
from core.storage_helpers import create_adapters_from_config
from core.task_scheduler import TaskScheduler
from core.websocket_manager import get_websocket_manager
from gui.app import GradioApp

console = Console()


class Application:
    """Main application class."""

    def __init__(self):
        """Initialize the application."""
        self.config_manager: ConfigManager = None
        self.mcp_bridge: MCPBridge = None
        self.agent_manager: AgentManager = None
        self.task_scheduler: TaskScheduler = None
        self.storage_adapter = None
        self.cache_adapter = None
        self.api_server = None
        self.gradio_app = None
        self.hot_reload: HotReloadManager = None
        self._running = False

    def _is_hot_reload_enabled(self) -> bool:
        """Check if hot reload is enabled via environment variable."""
        return os.environ.get("HOT_RELOAD_ENABLED", "false").lower() in ("true", "1", "yes", "on")

    async def initialize(self):
        """Initialize all components."""
        console.print("[bold cyan]Initializing AInTandem Agent MCP Scheduler[/bold cyan]\n")

        # 1. Load configuration
        console.print("[dim]1/7. Loading configuration...[/dim]")
        self.config_manager = ConfigManager()
        self.config_manager.load_all()
        console.print("[green]✓[/green] Configuration loaded")

        # 2. Create storage and cache adapters
        console.print("[dim]2/7. Setting up storage...[/dim]")
        self.storage_adapter, self.cache_adapter = await create_adapters_from_config(
            self.config_manager
        )
        storage_type = self.config_manager.storage.get("storage", {}).get("type", "file")
        console.print(f"[green]✓[/green] Storage configured ({storage_type})")

        # 3. Initialize MCP Bridge
        console.print("[dim]3/7. Initializing MCP Bridge...[/dim]")
        self.mcp_bridge = MCPBridge(self.config_manager)
        await self.mcp_bridge.initialize()
        mcp_count = len(self.mcp_bridge._clients)
        console.print(f"[green]✓[/green] MCP Bridge initialized ({mcp_count} servers)")

        # 4. Initialize Agent Manager
        console.print("[dim]4/7. Initializing Agent Manager...[/dim]")
        self.agent_manager = AgentManager(
            config_manager=self.config_manager,
            mcp_bridge=self.mcp_bridge,
            cache_adapter=self.cache_adapter,
        )
        await self.agent_manager.initialize(mcp_bridge=self.mcp_bridge)
        agent_count = len(self.agent_manager._agents)
        console.print(f"[green]✓[/green] Agent Manager initialized ({agent_count} agents)")

        # 5. Initialize Task Scheduler
        console.print("[dim]5/7. Initializing Task Scheduler...[/dim]")
        self.task_scheduler = TaskScheduler(
            config_manager=self.config_manager,
            agent_manager=self.agent_manager,
            storage_adapter=self.storage_adapter,
        )
        await self.task_scheduler.start()
        console.print("[green]✓[/green] Task Scheduler started")

        # 6. Create API Server
        console.print("[dim]6/7. Creating API Server...[/dim]")
        self.api_server = create_api_server(
            config_manager=self.config_manager,
            agent_manager=self.agent_manager,
            task_scheduler=self.task_scheduler,
        )
        console.print("[green]✓[/green] API Server created")

        # 7. Create Gradio App
        console.print("[dim]7/7. Creating Gradio GUI...[/dim]")
        self.gradio_app = GradioApp(
            config_manager=self.config_manager,
            agent_manager=self.agent_manager,
            task_scheduler=self.task_scheduler,
        )
        console.print("[green]✓[/green] Gradio GUI created")

        console.print("\n[bold green]All components initialized successfully![/bold green]\n")

        # Initialize Hot Reload (if enabled)
        if self._is_hot_reload_enabled():
            await self._initialize_hot_reload()
        else:
            console.print("[dim]Hot reload disabled (set HOT_RELOAD_ENABLED=true to enable)[/dim]\n")

    async def _initialize_hot_reload(self):
        """Initialize hot reload for configuration changes."""
        console.print("[dim]8/8. Initializing Hot Reload...[/dim]")

        self.hot_reload = HotReloadManager(
            config_dir="config",
            src_dir="src",
            check_interval=1.0,
        )

        # Monitor config files
        self.hot_reload.monitor_files([
            "agents.yaml",
            "llm.yaml",
            "mcp_servers.yaml",
            "app.yaml",
            "storage.yaml",
        ])

        # Monitor source code files
        self.hot_reload.monitor_code(["**/*.py"])

        # Register reload handlers
        self.hot_reload.register_handler("agents.yaml", self._reload_agents)
        self.hot_reload.register_handler("llm.yaml", self._reload_agents)
        self.hot_reload.register_handler("mcp_servers.yaml", self._reload_mcp_servers)
        self.hot_reload.register_handler("app.yaml", self._reload_config)
        self.hot_reload.register_handler("storage.yaml", self._reload_config)

        # Register restart callback for code changes
        self.hot_reload.register_restart_callback(self._restart_application)

        # Start monitoring
        await self.hot_reload.start()

        console.print("[green]✓[/green] Hot reload enabled")
        console.print("[dim]  Watching: config/*.yaml, src/**/*.py[/dim]")

    async def _reload_agents(self):
        """Reload agents when configuration changes."""
        console.print("\n[yellow]Reloading agents...[/yellow]")

        # Reload configuration
        self.config_manager.reload()
        self.config_manager.load_agents()

        # Reload agent manager
        count = await self.agent_manager.reload_all()

        console.print(f"[green]✓[/green] Reloaded {count} agents")

    async def _reload_mcp_servers(self):
        """Reload MCP servers when configuration changes."""
        console.print("\n[yellow]Reloading MCP servers...[/yellow]")

        # Note: Full MCP server reload requires restarting the application
        # For now, just log a message
        console.print("[yellow]⚠[/yellow] MCP server changes require application restart")
        logger.warning("MCP server configuration changed - restart required")

    async def _reload_config(self):
        """Reload general configuration."""
        console.print("\n[yellow]Reloading configuration...[/yellow]")

        # Reload configuration
        self.config_manager.reload()

        console.print("[green]✓[/green] Configuration reloaded")

    async def _restart_application(self):
        """Restart the application when code changes."""
        logger.info("Restarting application due to code changes...")

        # Stop all services
        await self.stop()

        # Short delay to ensure clean shutdown
        import asyncio
        await asyncio.sleep(1)

        # Re-initialize and start
        await self.initialize()
        await self.start()

    async def start(self):
        """Start all services."""
        self._running = True

        # Get configuration
        app_config = self.config_manager.app
        api_host = app_config.server.host
        api_port = app_config.server.api_port
        gui_port = app_config.server.gui_port

        # Start API Server
        import uvicorn

        api_config = uvicorn.Config(
            self.api_server.app,
            host=api_host,
            port=api_port,
            log_level="info",
        )
        api_server = uvicorn.Server(api_config)

        # Start Gradio GUI in a thread (blocking call)
        import threading

        gui_thread = None
        if self.gradio_app:
            def run_gradio():
                # Path to JavaScript file for Gradio 6 head_paths parameter
                from pathlib import Path

                js_file = Path(__file__).parent / "static" / "websocket_chat.js"

                # Prepare launch parameters
                launch_kwargs = {
                    "server_name": api_host,
                    "server_port": gui_port,
                    "share": False,
                    "quiet": True,
                    "show_error": True,
                }

                # Add head_paths if JavaScript file exists (Gradio 6.x feature)
                if js_file.exists():
                    launch_kwargs["head_paths"] = [str(js_file)]
                    print(f"[INFO] Loading WebSocket JavaScript from: {js_file}")
                else:
                    print(f"[WARNING] WebSocket JavaScript file not found: {js_file}")

                self.gradio_app.app.launch(**launch_kwargs)

            gui_thread = threading.Thread(target=run_gradio, daemon=True)
            gui_thread.start()
            # Give Gradio a moment to start
            import time
            time.sleep(2)

        # Display URLs
        console.print("[bold]Services started:[/bold]")
        console.print(f"  • API Server: [cyan]http://{api_host}:{api_port}[/cyan]")
        console.print(f"  • API Docs:   [cyan]http://{api_host}:{api_port}/docs[/cyan]")
        console.print(f"  • Gradio GUI: [cyan]http://{api_host}:{gui_port}[/cyan]")
        console.print("\n[dim]Press Ctrl+C to stop all services[/dim]\n")

        # Run API server
        await api_server.serve()

    async def stop(self):
        """Stop all services."""
        if not self._running:
            return

        console.print("\n[yellow]Shutting down...[/yellow]")

        # Stop hot reload
        if self.hot_reload:
            await self.hot_reload.stop()

        # Stop task scheduler
        if self.task_scheduler:
            await self.task_scheduler.stop()

        # Cleanup WebSocket connections
        try:
            ws_manager = get_websocket_manager()
            await ws_manager.cleanup_all()
        except Exception as e:
            logger.debug(f"WebSocket cleanup error: {e}")

        # Close storage adapter
        if self.storage_adapter:
            await self.storage_adapter.close()

        # Close cache adapter
        if self.cache_adapter:
            await self.cache_adapter.close()

        self._running = False
        console.print("[green]Shutdown complete[/green]")


async def main_async():
    """Main async entry point."""
    app = Application()

    # Setup signal handlers
    loop = asyncio.get_event_loop()

    def signal_handler():
        if app._running:
            loop.create_task(app.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        # Initialize and start
        await app.initialize()
        await app.start()
    except KeyboardInterrupt:
        await app.stop()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.exception("Application error")
        await app.stop()
        sys.exit(1)


def main():
    """Main entry point."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    main()
