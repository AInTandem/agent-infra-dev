#!/usr/bin/env python3
"""
Test script for OpenAI-compatible API.

Tests API endpoints with and without function calling.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import ConfigManager
from core.agent_manager import AgentManager
from core.task_scheduler import TaskScheduler
from api.openapi_server import create_api_server, get_scheduled_task_functions


async def test_api_server():
    """Test API Server functionality."""
    print("=" * 60)
    print("API Server Tests")
    print("=" * 60)
    print()

    # Initialize components
    config = ConfigManager()
    config.load_all()

    agent_manager = AgentManager(config)
    await agent_manager.initialize()

    task_scheduler = TaskScheduler(config)
    await task_scheduler.start()

    # Create API server
    print("Creating API server...")
    api = create_api_server(config, agent_manager, task_scheduler)
    print("✓ API server created")
    print()

    # Test 1: Get scheduled task functions
    print("Test 1: Scheduled Task Functions")
    functions = get_scheduled_task_functions()
    print(f"  Available functions: {len(functions)}")
    for func in functions:
        func_name = func["function"]["name"]
        func_desc = func["function"]["description"]
        print(f"    - {func_name}: {func_desc}")
    print()

    # Test 2: Function execution
    print("Test 2: Function Execution")

    # Create a test task
    from datetime import datetime, timedelta
    run_time = (datetime.now() + timedelta(seconds=10)).isoformat()

    result = await api._execute_function(
        "create_scheduled_task",
        {
            "name": "API Test Task",
            "agent_name": "researcher",
            "task_prompt": "Test from API",
            "schedule_type": "once",
            "schedule_value": run_time,
            "repeat": False,
            "description": "Created via API",
        }
    )
    print(f"  ✓ create_scheduled_task: {result}")

    # List tasks
    result = await api._execute_function("list_scheduled_tasks", {})
    print(f"  ✓ list_scheduled_tasks:\n{result}")

    # Get the created task ID
    tasks = task_scheduler.list_tasks()
    if tasks:
        test_task_id = tasks[-1].id

        # Enable task
        result = await api._execute_function("enable_task", {"task_id": test_task_id})
        print(f"  ✓ enable_task: {result}")

        # Disable task
        result = await api._execute_function("disable_task", {"task_id": test_task_id})
        print(f"  ✓ disable_task: {result}")

        # Cancel task
        result = await api._execute_function("cancel_task", {"task_id": test_task_id})
        print(f"  ✓ cancel_task: {result}")

    print()

    # Test 3: Chat completion (messages to prompt)
    print("Test 3: Messages to Prompt Conversion")
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ]
    from api.openapi_server import ChatMessage

    chat_messages = [ChatMessage(**m) for m in messages]
    prompt = api._messages_to_prompt(chat_messages)
    print(f"  Converted prompt:\n    {prompt}")
    print()

    # Test 4: FastAPI routes
    print("Test 4: FastAPI Routes")
    routes = []
    for route in api.app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            routes.append(f"{list(route.methods)[0]} {route.path}")
    for route in sorted(routes):
        print(f"  {route}")
    print()

    # Test 5: Agent endpoints
    print("Test 5: Agent Endpoints")
    agents = agent_manager.list_agents()
    print(f"  Available agents: {len(agents)}")
    for agent_name in agents:
        print(f"    - {agent_name}")
    print()

    # Stop scheduler
    await task_scheduler.stop()

    print()
    print("=" * 60)
    print("API Server Tests Complete! ✓")
    print("=" * 60)


def test_function_schemas():
    """Test function schema definitions."""
    print("=" * 60)
    print("Function Schema Tests")
    print("=" * 60)
    print()

    functions = get_scheduled_task_functions()

    print("Scheduled Task Functions Schema:")
    for func in functions:
        print()
        func_obj = func["function"]
        print(f"  Function: {func_obj['name']}")
        print(f"  Description: {func_obj['description']}")
        print(f"  Parameters:")
        params = func_obj['parameters']
        required = params.get('required', [])
        for param_name, param_spec in params.get('properties', {}).items():
            req = " (required)" if param_name in required else ""
            print(f"    - {param_name}{req}: {param_spec.get('type', 'unknown')}")
            if 'enum' in param_spec:
                print(f"      Enum: {param_spec['enum']}")
            if 'description' in param_spec:
                print(f"      Desc: {param_spec['description']}")

    print()
    print("✓ Function schemas verified")


async def main():
    """Run all tests."""
    # Test function schemas first
    test_function_schemas()

    print()

    # Test API server
    await test_api_server()


if __name__ == "__main__":
    asyncio.run(main())
