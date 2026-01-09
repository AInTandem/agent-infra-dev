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
MCP Bridge - Integration layer for MCP servers.

Manages connections to multiple MCP servers and provides a unified interface
 for accessing their tools, resources, and prompts.
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional, Union

from loguru import logger

from .config import ConfigManager, MCPServerConfig
from .mcp_sse_client import MCPSSEClient
from .mcp_stdio_client import MCPStdioClient
from .mcp_tool_converter import MultiMCPToolConverter

# Union type for both client types
MCPClient = Union[MCPStdioClient, MCPSSEClient]


class MCPBridge:
    """
    Bridge for managing multiple MCP servers.

    Handles:
    - Loading MCP server configurations
    - Connecting to MCP servers
    - Discovering and converting tools
    - Providing unified access to tools
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize the MCP Bridge.

        Args:
            config_manager: Optional configuration manager instance
        """
        self.config_manager = config_manager or ConfigManager()
        self._clients: Dict[str, MCPClient] = {}
        self._converter = MultiMCPToolConverter()
        self._is_initialized = False

    async def initialize(
        self,
        server_configs: Optional[List[MCPServerConfig]] = None
    ) -> None:
        """
        Initialize the MCP Bridge.

        Loads configuration and connects to enabled MCP servers.

        Args:
            server_configs: Optional list of server configs (uses config manager if None)
        """
        if self._is_initialized:
            logger.warning("MCP Bridge already initialized")
            return

        logger.info("Initializing MCP Bridge...")

        # Get server configurations
        if server_configs is None:
            server_configs = list(self.config_manager.get_enabled_mcp_servers().values())

        if not server_configs:
            logger.warning("No enabled MCP servers found in configuration")
            self._is_initialized = True
            return

        # Connect to servers
        connected_count = 0
        for config in server_configs:
            try:
                await self._connect_server(config)
                connected_count += 1
            except Exception as e:
                logger.error(f"Failed to connect to {config.name}: {e}")

        # Load tools from all connected servers
        if self._clients:
            await self._converter.load_tools_from_all_servers(self._clients)

        self._is_initialized = True
        logger.info(f"MCP Bridge initialized with {connected_count}/{len(server_configs)} servers")

    async def _connect_server(self, config: MCPServerConfig) -> None:
        """
        Connect to a single MCP server.

        Args:
            config: Server configuration
        """
        logger.info(f"Connecting to MCP server: {config.name} (transport: {config.transport})")

        # Create client based on transport type
        if config.transport == "sse":
            if not config.sse:
                raise ValueError(f"[{config.name}] SSE transport requires 'sse' configuration")

            client = MCPSSEClient(
                name=config.name,
                url=config.sse.url,
                headers=config.sse.headers,
                timeout=config.timeout,
            )
        else:  # Default to stdio
            if not config.command:
                raise ValueError(f"[{config.name}] Stdio transport requires 'command'")

            client = MCPStdioClient(
                name=config.name,
                command=config.command,
                args=config.args,
                env=config.env,
                timeout=config.timeout,
            )

        await client.connect()

        # Verify connection with ping
        if await client.ping():
            logger.info(f"[{config.name}] Connected successfully")
            logger.debug(f"[{config.name}] Capabilities: {client.capabilities}")
        else:
            logger.warning(f"[{config.name}] Connected but ping failed")

        self._clients[config.name] = client

    async def connect_server(self, name: str) -> bool:
        """
        Connect to a specific MCP server by name.

        Args:
            name: Server name from configuration

        Returns:
            True if connected successfully
        """
        if name in self._clients and self._clients[name].is_connected:
            logger.info(f"[{name}] Already connected")
            return True

        # Get server config
        config = self.config_manager.get_mcp_server(name)
        if not config:
            logger.error(f"[{name}] Server not found in configuration")
            return False

        if not config.enabled:
            logger.warning(f"[{name}] Server is disabled in configuration")
            return False

        try:
            await self._connect_server(config)

            # Load tools from this server
            await self._converter.load_tools_from_server(name, self._clients[name])

            return True
        except Exception as e:
            logger.error(f"[{name}] Failed to connect: {e}")
            return False

    async def disconnect_server(self, name: str) -> None:
        """
        Disconnect from a specific MCP server.

        Args:
            name: Server name
        """
        if name not in self._clients:
            logger.warning(f"[{name}] Not connected")
            return

        client = self._clients[name]
        await client.disconnect()
        del self._clients[name]
        logger.info(f"[{name}] Disconnected")

    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers."""
        logger.info("Disconnecting all MCP servers...")

        tasks = [client.disconnect() for client in self._clients.values()]
        await asyncio.gather(*tasks, return_exceptions=True)

        self._clients.clear()
        self._converter.clear()
        self._is_initialized = False

        logger.info("All MCP servers disconnected")

    async def reconnect_server(self, name: str) -> bool:
        """
        Reconnect to a specific MCP server.

        Args:
            name: Server name

        Returns:
            True if reconnected successfully
        """
        await self.disconnect_server(name)
        await asyncio.sleep(1)  # Brief delay
        return await self.connect_server(name)

    async def reconnect_all(self) -> int:
        """
        Reconnect to all configured MCP servers.

        Returns:
            Number of successfully reconnected servers
        """
        logger.info("Reconnecting all MCP servers...")

        # Get all enabled server configs
        configs = list(self.config_manager.get_enabled_mcp_servers().values())

        reconnected = 0
        for config in configs:
            try:
                if await self.reconnect_server(config.name):
                    reconnected += 1
            except Exception as e:
                logger.error(f"[{config.name}] Failed to reconnect: {e}")

        logger.info(f"Reconnected {reconnected}/{len(configs)} servers")
        return reconnected

    # ========================================================================
    # Tool Access Methods
    # ========================================================================

    def get_tools_for_agent(self, server_names: List[str]) -> List[Dict[str, Any]]:
        """
        Get tools available to a specific agent.

        Args:
            server_names: List of MCP server names the agent can use

        Returns:
            List of tool definitions with callable functions
        """
        tools = []

        for name in server_names:
            server_tools = self._converter.get_tools_for_servers([name])
            tools.extend(server_tools)

        logger.debug(f"Retrieved {len(tools)} tools for agent using {server_names}")
        return tools

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all tools from all connected servers."""
        return self._converter.get_all_tools()

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific tool by name."""
        return self._converter.get_tool(name)

    def get_tool_wrapper(self, name: str) -> Optional[Callable]:
        """Get the callable wrapper for a tool."""
        return self._converter.get_wrapper(name)

    def get_qwen_tools(self, server_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get tools in Qwen Agent format.

        Args:
            server_names: Optional list of server names (all if None)

        Returns:
            List of Qwen Agent compatible tool definitions
        """
        if server_names:
            tools = self._converter.get_tools_for_servers(server_names)
        else:
            tools = self._converter.get_all_tools()

        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
            }
            for tool in tools
        ]

    def get_openai_tools(self, server_names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get tools in OpenAI format.

        Args:
            server_names: Optional list of server names (all if None)

        Returns:
            List of OpenAI compatible tool definitions
        """
        if server_names:
            tools = self._converter.get_tools_for_servers(server_names)
        else:
            tools = self._converter.get_all_tools()

        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                }
            }
            for tool in tools
        ]

    # ========================================================================
    # Server Status Methods
    # ========================================================================

    def get_server_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all MCP servers.

        Returns:
            Dictionary mapping server names to their status
        """
        status = {}

        for name, client in self._clients.items():
            status[name] = {
                "connected": client.is_connected,
                "capabilities": client.capabilities,
            }

        return status

    def get_connected_servers(self) -> List[str]:
        """Get list of connected server names."""
        return [
            name for name, client in self._clients.items()
            if client.is_connected
        ]

    def is_server_connected(self, name: str) -> bool:
        """Check if a specific server is connected."""
        client = self._clients.get(name)
        return client.is_connected if client else False

    # ========================================================================
    # Direct Tool Execution
    # ========================================================================

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Any:
        """
        Call a tool on a specific MCP server.

        Args:
            server_name: Name of the MCP server
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        client = self._clients.get(server_name)
        if not client:
            raise ValueError(f"Server {server_name} not connected")

        return await client.call_tool(tool_name, arguments)

    async def call_tool_stream(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ):
        """
        Call a tool on a specific MCP server with streaming response.

        Args:
            server_name: Name of the MCP server
            tool_name: Name of the tool
            arguments: Tool arguments

        Yields:
            Streaming response chunks

        Raises:
            ValueError: If server not connected or doesn't support streaming
            TypeError: If client doesn't support streaming
        """
        client = self._clients.get(server_name)
        if not client:
            raise ValueError(f"Server {server_name} not connected")

        # Check if client supports streaming
        if isinstance(client, MCPSSEClient):
            async for chunk in client.call_tool_stream(tool_name, arguments):
                yield chunk
        else:
            raise TypeError(
                f"Streaming not supported for {type(client).__name__}. "
                f"Use SSE transport for streaming tool calls."
            )

    async def call_tool_by_full_name(
        self,
        full_tool_name: str,
        arguments: Dict[str, Any]
    ) -> Any:
        """
        Call a tool using its full name (server.tool format).

        Args:
            full_tool_name: Full tool name (e.g., "filesystem.read_file")
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        parts = full_tool_name.split(".", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid tool name format: {full_tool_name}")

        server_name, tool_name = parts
        return await self.call_tool(server_name, tool_name, arguments)

    # ========================================================================
    # Properties
    # ========================================================================

    @property
    def is_initialized(self) -> bool:
        """Check if the bridge is initialized."""
        return self._is_initialized

    @property
    def server_count(self) -> int:
        """Get number of connected servers."""
        return len(self._clients)

    @property
    def tool_count(self) -> int:
        """Get total number of available tools."""
        return len(self._converter.get_all_tools())

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"MCPBridge("
            f"initialized={self._is_initialized}, "
            f"servers={self.server_count}, "
            f"tools={self.tool_count})"
        )


# Global MCP bridge instance
_mcp_bridge: Optional[MCPBridge] = None


async def get_mcp_bridge(
    config_manager: Optional[ConfigManager] = None,
    force_refresh: bool = False
) -> MCPBridge:
    """
    Get the global MCP bridge instance.

    Args:
        config_manager: Optional configuration manager
        force_refresh: Force re-initialization

    Returns:
        MCPBridge instance
    """
    global _mcp_bridge

    if _mcp_bridge is None or force_refresh:
        _mcp_bridge = MCPBridge(config_manager)
        await _mcp_bridge.initialize()

    return _mcp_bridge
