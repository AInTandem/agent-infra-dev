#!/usr/bin/env python3
"""
Main entry point for Qwen Agent MCP Scheduler.

This application provides:
- Customizable AI agents with MCP server integration
- Task scheduling capabilities
- OpenAI-compatible API
- Gradio web interface
"""

import asyncio
import sys
from pathlib import Path

from loguru import logger
from rich.console import Console

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

console = Console()


def main():
    """Main entry point."""
    console.print("[bold blue]Qwen Agent MCP Scheduler[/bold blue]\n", "")
    console.print("Starting application...", "")

    # TODO: Initialize components
    # 1. Load configuration
    # 2. Initialize MCP Bridge
    # 3. Initialize Agent Manager
    # 4. Initialize Task Scheduler
    # 5. Start API Server
    # 6. Start Gradio GUI

    console.print("\n[green]Application started successfully![/green]")
    console.print("\n[cyan]Press Ctrl+C to stop[/cyan]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
        sys.exit(0)
