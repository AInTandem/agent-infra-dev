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
MCP Direct Passage - Native MCP connection for models with MCP support.

This module provides direct MCP ClientSession connections for models
that have native MCP support (Claude, GPT-4.1+, etc.), avoiding
the need for function call format conversion.
"""

import asyncio
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.types import Tool
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    ClientSession = None
    StdioServerParameters = None
    Tool = None

from core.config import ConfigManager, MCPServerConfig


class MCPDirectPassage:
    """
    Direct MCP connection for models with native MCP support.

    This class uses the official mcp Python SDK to create ClientSession
    instances that can be passed directly to agent adapters for models
    with native MCP support.

    This avoids the overhead of converting MCP tools to function call
    format and back.
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the MCP Direct Passage manager.

        Args:
            config_manager: Configuration manager instance
        """
        if not MCP_AVAILABLE:
            raise ImportError(
                "mcp package is required for MCPDirectPassage. "
                "Install with: pip install mcp"
            )

        self.config_manager = config_manager
        self._sessions: Dict[str, ClientSession] = {}
        self._is_initialized = False

    async def initialize(
        self,
        server_configs: Optional[List[MCPServerConfig]] = None
    ) -> None:
        """
        Initialize the MCP Direct Passage manager.

        Args:
            server_configs: Optional list of server configs (uses config manager if None)
        """
        if self._is_initialized:
            logger.warning("MCPDirectPassage already initialized")
            return

        logger.info("Initializing MCPDirectPassage...")

        # Get server configurations
        if server_configs is None:
            server_configs = list(self.config_manager.get_enabled_mcp_servers().values())

        if not server_configs:
            logger.warning("No enabled MCP servers found in configuration")
            self._is_initialized = True
            return

        # Filter to only servers without function_call_wrapper
        # (servers with wrapper enabled are for MCPFunctionCallWrapper)
        native_servers = [
            cfg for cfg in server_configs
            if not cfg.function_call_wrapper
        ]

        if not native_servers:
            logger.info("No MCP servers configured for native MCP (all have function_call_wrapper enabled)")
            self._is_initialized = True
            return

        # Connect to servers
        connected_count = 0
        for config in native_servers:
            try:
                await self._connect_server(config)
                connected_count += 1
            except Exception as e:
                logger.error(f"Failed to connect to {config.name} for native MCP: {e}")

        self._is_initialized = True
        logger.info(f"MCPDirectPassage initialized with {connected_count}/{len(native_servers)} native servers")

    async def _connect_server(self, config: MCPServerConfig) -> None:
        """
        Connect to a single MCP server using official mcp SDK.

        Args:
            config: Server configuration
        """
        logger.info(f"[DirectPassage] Connecting to MCP server: {config.name} (transport: {config.transport})")

        if config.transport == "stdio":
            # Use stdio client
            params = StdioServerParameters(
                command=config.command,
                args=config.args,
                env=config.env,
            )

            # Create read/write streams
            stdio_streams = stdio_client(params)
            read_stream, write_stream = await stdio_streams.__aenter__()

            # Create and initialize session
            session = ClientSession(read_stream, write_stream)
            await session.initialize()

            self._sessions[config.name] = session
            logger.info(f"[DirectPassage] {config.name} connected successfully")

        else:
            logger.warning(
                f"[DirectPassage] {config.name} uses transport '{config.transport}' "
                f"which is not yet supported for native MCP. "
                f"Currently only 'stdio' transport is supported."
            )

    async def get_session(self, server_name: str) -> Optional[ClientSession]:
        """
        Get MCP ClientSession for a server.

        Args:
            server_name: Name of the MCP server

        Returns:
            ClientSession instance or None if not found
        """
        return self._sessions.get(server_name)

    async def list_tools(self, server_name: str) -> Optional[List[Tool]]:
        """
        List tools from an MCP server (in native MCP format).

        Args:
            server_name: Name of the MCP server

        Returns:
            List of Tool objects or None
        """
        session = self._sessions.get(server_name)
        if not session:
            logger.warning(f"[DirectPassage] No session found for {server_name}")
            return None

        try:
            result = await session.list_tools()
            return result.tools
        except Exception as e:
            logger.error(f"[DirectPassage] Error listing tools from {server_name}: {e}")
            return None

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Any:
        """
        Call a tool on an MCP server.

        Args:
            server_name: Name of the MCP server
            tool_name: Name of the tool
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        session = self._sessions.get(server_name)
        if not session:
            raise ValueError(f"[DirectPassage] No session found for {server_name}")

        logger.debug(f"[DirectPassage] Calling tool {tool_name} on {server_name}")
        return await session.call_tool(tool_name, arguments)

    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers."""
        logger.info("Disconnecting all MCP Direct Passage sessions...")

        tasks = []
        for name, session in self._sessions.items():
            try:
                # Close each session
                if hasattr(session, '_message_handler'):
                    tasks.append(session._message_handler.close())
            except Exception as e:
                logger.error(f"Error closing session {name}: {e}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._sessions.clear()
        self._is_initialized = False
        logger.info("All MCP Direct Passage sessions disconnected")

    @property
    def is_initialized(self) -> bool:
        """Check if the manager is initialized."""
        return self._is_initialized

    @property
    def session_count(self) -> int:
        """Get the number of active sessions."""
        return len(self._sessions)

    def get_server_names(self) -> List[str]:
        """Get list of connected server names."""
        return list(self._sessions.keys())

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"MCPDirectPassage("
            f"initialized={self._is_initialized}, "
            f"sessions={self.session_count})"
        )


__all__ = ["MCPDirectPassage"]
