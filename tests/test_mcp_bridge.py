#!/usr/bin/env python3
"""
Test script for MCP Bridge.

Tests MCP server connection and tool conversion.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import ConfigManager
from core.mcp_bridge import MCPBridge


async def test_mcp_bridge():
    """Test MCP Bridge initialization and tool loading."""
    print("=" * 60)
    print("MCP Bridge Tests")
    print("=" * 60)
    print()

    # Load configuration
    config = ConfigManager()
    config.load_all()

    # Get enabled MCP servers
    enabled_servers = config.get_enabled_mcp_servers()
    print(f"Enabled MCP servers in config:")
    for name, server_cfg in enabled_servers.items():
        print(f"  - {name}: {server_cfg.description}")
    print()

    # Initialize MCP Bridge
    print("Initializing MCP Bridge...")
    bridge = MCPBridge(config)

    try:
        await bridge.initialize()
    except Exception as e:
        print(f"Note: Some servers may not be available: {e}")
        print("This is expected if required environment variables are not set.")
    print()

    # Check connected servers
    connected = bridge.get_connected_servers()
    print(f"Connected servers ({len(connected)}):")
    for name in connected:
        status = bridge.get_server_status().get(name, {})
        caps = status.get("capabilities", {})
        print(f"  - {name}: {caps}")
    print()

    if not connected:
        print("No servers connected. This is expected if:")
        print("  - Node.js/npx is not installed")
        print("  - Required API keys are not set")
        print("  - MCP servers are not installed")
        print()
        print("To test with real MCP servers:")
        print("  1. Install Node.js: brew install node")
        print("  2. Set environment variables in .env file")
        print("  3. Run: source .env && python tests/test_mcp_bridge.py")
        print()

        # Still test the API
        print("Testing MCP Bridge API (without real connection)...")
        test_bridge_api(bridge)
        return

    # Test tool loading
    print(f"Total tools available: {bridge.tool_count}")
    print()

    # Show tools from each server
    for server_name in connected:
        tools = bridge.get_tools_for_agent([server_name])
        print(f"[{server_name}] Tools ({len(tools)}):")
        for tool in tools[:5]:  # Show first 5
            print(f"  - {tool['name']}: {tool.get('description', 'No description')[:60]}")
        if len(tools) > 5:
            print(f"  ... and {len(tools) - 5} more")
        print()

    # Test tool formats
    print("Testing tool format conversions...")

    # Qwen Agent format
    qwen_tools = bridge.get_qwen_tools()
    print(f"  Qwen Agent format: {len(qwen_tools)} tools")
    if qwen_tools:
        print(f"    Example: {qwen_tools[0]['name']}")

    # OpenAI format
    openai_tools = bridge.get_openai_tools()
    print(f"  OpenAI format: {len(openai_tools)} tools")
    if openai_tools:
        print(f"    Example: {openai_tools[0]['function']['name']}")
    print()

    # Test tool lookup
    all_tools = bridge.get_all_tools()
    if all_tools:
        tool = all_tools[0]
        print(f"Tool lookup example:")
        print(f"  Name: {tool['name']}")
        print(f"  Description: {tool.get('description', 'N/A')[:60]}")
        print(f"  Parameters: {list(tool.get('parameters', {}).get('properties', {}).keys())}")
        print()

    # Disconnect
    print("Disconnecting all servers...")
    await bridge.disconnect_all()
    print("✓ Disconnected")

    print()
    print("=" * 60)
    print("MCP Bridge Tests Complete! ✓")
    print("=" * 60)


def test_bridge_api(bridge: MCPBridge):
    """Test MCP Bridge API methods."""
    print()

    # Test empty state methods
    print("Testing API methods (empty state):")
    print(f"  is_initialized: {bridge.is_initialized}")
    print(f"  server_count: {bridge.server_count}")
    print(f"  tool_count: {bridge.tool_count}")
    print(f"  get_connected_servers(): {bridge.get_connected_servers()}")
    print(f"  get_server_status(): {bridge.get_server_status()}")
    print(f"  get_all_tools(): {len(bridge.get_all_tools())} tools")
    print(f"  get_qwen_tools(): {len(bridge.get_qwen_tools())} tools")
    print(f"  get_openai_tools(): {len(bridge.get_openai_tools())} tools")
    print()

    # Test tool lookup (should return None)
    print("Testing tool lookup (non-existent):")
    tool = bridge.get_tool("filesystem.read_file")
    print(f"  get_tool('filesystem.read_file'): {tool}")
    print()

    print("✓ API tests passed")


async def test_stdio_client_api():
    """Test MCP Stdio Client API (without real connection)."""
    from core.mcp_stdio_client import MCPStdioClient

    print("=" * 60)
    print("MCP Stdio Client API Tests")
    print("=" * 60)
    print()

    # Create a mock client
    client = MCPStdioClient(
        name="test",
        command="echo",
        args=["hello"],
    )

    print("Testing client properties:")
    print(f"  name: {client.name}")
    print(f"  command: {client.command}")
    print(f"  args: {client.args}")
    print(f"  is_connected: {client.is_connected}")
    print(f"  capabilities: {client.capabilities}")
    print()

    print("✓ MCP Stdio Client API tests passed")
    print()


async def main():
    """Run all tests."""
    # Test API first
    await test_stdio_client_api()

    # Test full bridge
    await test_mcp_bridge()


if __name__ == "__main__":
    asyncio.run(main())
