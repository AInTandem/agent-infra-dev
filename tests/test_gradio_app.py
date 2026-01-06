#!/usr/bin/env python3
"""
Test script for Gradio GUI application.

Tests the Gradio interface components and functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import ConfigManager
from core.agent_manager import AgentManager
from core.task_scheduler import TaskScheduler
from gui.app import create_gradio_app


async def test_gradio_app():
    """Test Gradio application functionality."""
    print("=" * 60)
    print("Gradio App Tests")
    print("=" * 60)
    print()

    # Initialize components
    config = ConfigManager()
    config.load_all()

    agent_manager = AgentManager(config)
    await agent_manager.initialize()

    task_scheduler = TaskScheduler(config)
    await task_scheduler.start()

    # Create Gradio app
    print("Creating Gradio app...")
    app = create_gradio_app(config, agent_manager, task_scheduler)
    print("✓ Gradio app created")
    print()

    # Test 1: App structure
    print("Test 1: App Structure")
    print(f"  App type: {type(app)}")
    print(f"  App title: {app.title}")
    print(f"  Blocks children: {len(app.blocks)}")
    print()

    # Test 2: Agent choices
    print("Test 2: Agent Choices")
    agents = agent_manager.list_agents()
    print(f"  Available agents: {len(agents)}")
    for agent in agents:
        print(f"    - {agent}")
    print()

    # Test 3: Task list refresh
    print("Test 3: Task List Refresh")
    tasks = task_scheduler.list_tasks()
    print(f"  Current tasks: {len(tasks)}")
    print()

    # Test 4: System status
    print("Test 4: System Status")
    print(f"  Scheduler running: {task_scheduler.is_running}")
    print(f"  Total agents: {len(agents)}")
    print(f"  Total tasks: {len(tasks)}")
    print()

    # Test 5: Statistics
    print("Test 5: Statistics")
    task_stats = task_scheduler.get_stats()
    print(f"  Total tasks: {task_stats['total_tasks']}")
    print(f"  Enabled tasks: {task_stats['enabled_tasks']}")
    print(f"  Disabled tasks: {task_stats['disabled_tasks']}")
    agent_stats = agent_manager.get_all_stats()
    print(f"  Total agents: {len(agent_stats)}")
    print()

    # Test 6: Route check (if running)
    print("Test 6: App Launch Info")
    print("  To launch the Gradio app, run:")
    print("    python -m gui.app")
    print("  Or use the launch command:")
    print("    app.launch()")
    print()

    # Stop scheduler
    await task_scheduler.stop()

    print()
    print("=" * 60)
    print("Gradio App Tests Complete! ✓")
    print("=" * 60)


def test_app_components():
    """Test app component initialization."""
    print("=" * 60)
    print("App Components Tests")
    print("=" * 60)
    print()

    # Test import
    print("Test 1: Import Check")
    try:
        from gui.app import GradioApp, create_gradio_app
        print("  ✓ GradioApp imported")
        print("  ✓ create_gradio_app imported")
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return
    print()

    # Test 2: Gradio availability
    print("Test 2: Gradio Version")
    try:
        import gradio as gr
        print(f"  ✓ Gradio version: {gr.__version__}")
        print(f"  ✓ Soft theme available: {gr.themes.Soft()}")
    except Exception as e:
        print(f"  ✗ Gradio test failed: {e}")
    print()

    # Test 3: Check dependencies
    print("Test 3: Dependencies Check")
    try:
        from core.config import ConfigManager
        from core.agent_manager import AgentManager
        from core.task_scheduler import TaskScheduler
        print("  ✓ All core dependencies available")
    except ImportError as e:
        print(f"  ✗ Dependency check failed: {e}")
    print()

    print("=" * 60)
    print("App Components Tests Complete! ✓")
    print("=" * 60)


async def main():
    """Run all tests."""
    # Test components first
    test_app_components()

    print()

    # Test app functionality
    await test_gradio_app()


if __name__ == "__main__":
    asyncio.run(main())
