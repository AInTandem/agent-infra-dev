#!/usr/bin/env python3
"""
Test script for new MCP Manager architecture.

Tests the refactored MCP system with:
- MCPDirectPassage for native MCP models
- MCPFunctionCallWrapper for non-MCP models
- MCPManager for unified routing
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import ConfigManager, validate_agent_mcp_compatibility
from core.mcp_manager import MCPManager


async def test_mcp_manager():
    """Test MCP Manager initialization and routing."""
    print("=" * 60)
    print("MCP Manager Tests")
    print("=" * 60)
    print()

    # Load configuration
    config = ConfigManager()
    config.load_all()

    # Get enabled MCP servers
    enabled_servers = config.get_enabled_mcp_servers()
    print(f"Enabled MCP servers in config:")
    for name, server_cfg in enabled_servers.items():
        wrapper_status = "function_call_wrapper" if server_cfg.function_call_wrapper else "native MCP"
        print(f"  - {name}: {server_cfg.description} ({wrapper_status})")
    print()

    # Initialize MCP Manager
    print("Initializing MCP Manager...")
    manager = MCPManager(config)

    try:
        await manager.initialize()
    except Exception as e:
        print(f"Note: Some servers may not be available: {e}")
        print("This is expected if required environment variables are not set.")
    print()

    # Check status
    status = manager.get_status()
    print("MCP Manager Status:")
    print(f"  Initialized: {status['initialized']}")
    print(f"  Direct Passage:")
    print(f"    - Initialized: {status['direct_passage']['initialized']}")
    print(f"    - Servers: {status['direct_passage']['servers']}")
    print(f"    - Sessions: {status['direct_passage']['session_count']}")
    print(f"  Function Wrapper:")
    print(f"    - Initialized: {status['function_wrapper']['initialized']}")
    print(f"    - Servers: {status['function_wrapper']['servers']}")
    print(f"    - Server count: {status['function_wrapper']['server_count']}")
    print(f"    - Tool count: {status['function_wrapper']['tool_count']}")
    print()

    # Test configuration validation
    print("Testing configuration validation...")
    agents = config.get_enabled_agents()
    for agent_name, agent_cfg in agents.items():
        try:
            validate_agent_mcp_compatibility(
                agent_cfg,
                config.llm,
                enabled_servers
            )
            print(f"  ✓ {agent_name}: Valid configuration")
        except ValueError as e:
            print(f"  ✗ {agent_name}: {e}")
    print()

    # Test tool retrieval
    if agents:
        agent_name = list(agents.keys())[0]
        agent_cfg = agents[agent_name]

        if agent_cfg.mcp_servers:
            print(f"Testing tool retrieval for agent '{agent_name}'...")
            tools = manager.get_tools_for_agent(agent_cfg, config.llm)

            llm_supports_mcp = config.llm.get_model_mcp_support(agent_cfg.llm_model)
            tool_type = "Native MCP Tools" if llm_supports_mcp else "Function Call Tools"
            print(f"  Tool type: {tool_type}")
            print(f"  Tool count: {len(tools)}")

            if tools:
                if llm_supports_mcp:
                    # Native MCP tools (Tool objects)
                    for tool in tools[:3]:
                        print(f"    - {tool.name}: {tool.description[:50]}...")
                else:
                    # Function call tools (dict)
                    for tool in tools[:3]:
                        name = tool.get('name', tool.get('function', {}).get('name', 'unknown'))
                        desc = tool.get('description', 'No description')[:50]
                        print(f"    - {name}: {desc}...")
            print()

    # Disconnect
    print("Disconnecting all servers...")
    await manager.disconnect_all()
    print("✓ Disconnected")

    print()
    print("=" * 60)
    print("MCP Manager Tests Complete! ✓")
    print("=" * 60)


async def test_direct_passage():
    """Test MCP Direct Passage (native MCP)."""
    print("=" * 60)
    print("MCP Direct Passage Tests")
    print("=" * 60)
    print()

    from core.mcp_direct_passage import MCPDirectPassage

    config = ConfigManager()
    config.load_all()

    print("Initializing MCPDirectPassage...")
    direct = MCPDirectPassage(config)

    try:
        await direct.initialize()
    except Exception as e:
        print(f"Note: {e}")
    print()

    print(f"Initialized: {direct.is_initialized}")
    print(f"Sessions: {direct.session_count}")
    print(f"Server names: {direct.get_server_names()}")
    print()

    # List tools from connected servers
    for server_name in direct.get_server_names():
        tools = await direct.list_tools(server_name)
        if tools:
            print(f"[{server_name}] Tools ({len(tools)}):")
            for tool in tools[:5]:
                print(f"  - {tool.name}: {tool.description[:50]}...")
        print()

    await direct.disconnect_all()
    print("✓ Direct Passage test complete")
    print()


async def test_function_wrapper():
    """Test MCP Function Call Wrapper."""
    print("=" * 60)
    print("MCP Function Call Wrapper Tests")
    print("=" * 60)
    print()

    from core.mcp_function_wrapper import MCPFunctionCallWrapper

    config = ConfigManager()
    config.load_all()

    print("Initializing MCPFunctionCallWrapper...")
    wrapper = MCPFunctionCallWrapper(config)

    try:
        await wrapper.initialize()
    except Exception as e:
        print(f"Note: {e}")
    print()

    print(f"Initialized: {wrapper.is_initialized}")
    print(f"Servers: {wrapper.server_count}")
    print(f"Tools: {wrapper.tool_count}")
    print(f"Connected servers: {wrapper.get_connected_servers()}")
    print()

    # Test tool formats
    if wrapper.get_connected_servers():
        print("Testing tool format conversions...")

        # Qwen Agent format
        qwen_tools = wrapper.get_qwen_tools()
        print(f"  Qwen Agent format: {len(qwen_tools)} tools")
        if qwen_tools:
            print(f"    Example: {qwen_tools[0]['name']}")

        # OpenAI format
        openai_tools = wrapper.get_openai_tools()
        print(f"  OpenAI format: {len(openai_tools)} tools")
        if openai_tools:
            print(f"    Example: {openai_tools[0]['function']['name']}")
        print()

    await wrapper.disconnect_all()
    print("✓ Function Wrapper test complete")
    print()


async def main():
    """Run all tests."""
    # Test individual components
    await test_function_wrapper()
    await test_direct_passage()

    # Test unified manager
    await test_mcp_manager()


if __name__ == "__main__":
    asyncio.run(main())
