#!/usr/bin/env python3
"""
Test script for Agent Manager.

Tests agent creation, management, and execution.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import ConfigManager
from core.agent_manager import AgentManager
from agents.base_agent import BaseAgent


async def test_agent_manager():
    """Test Agent Manager initialization and agent management."""
    print("=" * 60)
    print("Agent Manager Tests")
    print("=" * 60)
    print()

    # Load configuration
    config = ConfigManager()
    config.load_all()

    # Get enabled agents
    enabled_agents = config.get_enabled_agents()
    print(f"Enabled agents in config:")
    for name, agent_cfg in enabled_agents.items():
        print(f"  - {name}: {agent_cfg.role}")
        print(f"    MCP servers: {agent_cfg.mcp_servers}")
    print()

    # Initialize Agent Manager (without MCP Bridge for now)
    print("Initializing Agent Manager...")
    agent_manager = AgentManager(config)

    try:
        await agent_manager.initialize()
    except Exception as e:
        print(f"Note: Some initialization issues may occur: {e}")
    print()

    # Check created agents
    agents = agent_manager.list_agents()
    print(f"Created agents ({len(agents)}):")
    for name in agents:
        agent = agent_manager.get_agent(name)
        stats = agent.get_stats()
        print(f"  - {name}:")
        print(f"    Role: {stats['role']}")
        print(f"    Tools: {stats['tool_count']}")
        print(f"    MCP servers: {stats['mcp_servers']}")
    print()

    if not agents:
        print("No agents created. This may be due to missing LLM configuration.")
        print()
        print("Note: Agent tests require:")
        print("  - Valid LLM API configuration")
        print("  - MCP Bridge for tool integration")
        print()

        # Test dynamic agent creation
        print("Testing dynamic agent creation...")
        test_agent = await agent_manager.create_agent(
            name="test_agent",
            role="Test Agent",
            system_prompt="You are a helpful test assistant.",
            mcp_servers=[],
            llm_model="qwen-turbo",  # Use a supported model name
            description="A test agent for verification",
        )
        print(f"✓ Created test agent: {test_agent.name}")
        print(f"  Stats: {test_agent.get_stats()}")
        print()

    # Test agent methods
    if agents:
        agent_name = agents[0]
        agent = agent_manager.get_agent(agent_name)

        print(f"Testing agent methods for '{agent_name}':")

        # Test get_history
        history = agent.get_history_dict()
        print(f"  History length: {len(history)}")

        # Test get_tools
        tools = agent.get_tools()
        print(f"  Available tools: {len(tools)}")
        for tool in tools[:3]:
            print(f"    - {tool['name']}")
        if len(tools) > 3:
            print(f"    ... and {len(tools) - 3} more")

        # Test to_dict
        agent_dict = agent.to_dict()
        print(f"  Serialization: {list(agent_dict.keys())}")

        print()

    # Test get_all_agent_info
    all_info = agent_manager.get_all_agent_info()
    print(f"All agents info: {len(all_info)} agents")
    for info in all_info:
        print(f"  - {info['name']}: {info['role']}")
    print()

    print("✓ Agent Manager tests completed")


async def test_base_agent():
    """Test BaseAgent class directly."""
    print("=" * 60)
    print("BaseAgent Tests")
    print("=" * 60)
    print()

    from core.config import AgentConfig

    # Create a test agent config
    config = AgentConfig(
        name="test",
        role="Test Assistant",
        description="A test assistant",
        system_prompt="You are a helpful assistant for testing.",
        mcp_servers=[],
        llm_model="qwen-turbo",  # Use a supported model name
    )

    print("Creating BaseAgent...")
    agent = BaseAgent(config=config, llm=None, tools=[])

    print(f"✓ Agent created: {agent.name}")
    print(f"  Role: {agent.role}")
    print(f"  Description: {agent.description}")
    print(f"  System prompt: {agent.system_prompt[:50]}...")
    print()

    # Test methods
    print("Testing BaseAgent methods:")

    # Test history
    print(f"  Initial history: {len(agent.get_history())} messages")

    # Test tools
    tools = agent.get_tools()
    print(f"  Available tools: {len(tools)}")

    # Test stats
    stats = agent.get_stats()
    print(f"  Stats: {stats}")

    # Test to_dict
    agent_dict = agent.to_dict()
    print(f"  Serialization keys: {list(agent_dict.keys())}")

    print()

    # Test add/remove tool
    print("Testing tool management:")
    test_tool = {
        "name": "test_tool",
        "description": "A test tool",
        "parameters": {
            "type": "object",
            "properties": {
                "input": {"type": "string"}
            }
        },
        "function": lambda **kwargs: {"result": "test"},
    }

    agent.add_tool(test_tool)
    print(f"  After add_tool: {len(agent.get_tools())} tools")

    agent.remove_tool("test_tool")
    print(f"  After remove_tool: {len(agent.get_tools())} tools")

    print()

    print("✓ BaseAgent tests completed")


async def main():
    """Run all tests."""
    # Test BaseAgent first
    await test_base_agent()

    print()

    # Test Agent Manager
    await test_agent_manager()


if __name__ == "__main__":
    asyncio.run(main())
