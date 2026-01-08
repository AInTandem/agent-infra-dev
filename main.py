#!/usr/bin/env python3
"""
Main entry point for AInTandem Agent MCP Scheduler.

This application provides:
- Customizable AI agents with MCP server integration
- Task scheduling capabilities
- OpenAI-compatible API
- Gradio web interface
"""

import asyncio
import signal
import sys
from pathlib import Path

from loguru import logger
from rich.console import Console

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from api.openapi_server import create_api_server
from core.agent_manager import AgentManager
from core.config import ConfigManager
from core.mcp_bridge import MCPBridge
from core.storage_helpers import create_adapters_from_config
from core.task_scheduler import TaskScheduler
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
        self._running = False

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
                self.gradio_app.app.launch(
                    server_name=api_host,
                    server_port=gui_port,
                    share=False,
                    quiet=True,
                    show_error=True,
                )

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

        # Stop task scheduler
        if self.task_scheduler:
            await self.task_scheduler.stop()

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
