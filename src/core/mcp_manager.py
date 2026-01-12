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
MCP Manager - Unified MCP integration manager.

Routes agents to appropriate MCP implementation based on model capabilities:
- Native MCP models (Claude, GPT-4.1+) → MCPDirectPassage
- Non-MCP models (DeepSeek, GLM, etc.) → MCPFunctionCallWrapper
"""

from typing import Any, Dict, List, Optional, Union

from loguru import logger

from core.config import AgentConfig, ConfigManager, LLMConfig, MCPServerConfig
from core.mcp_direct_passage import MCPDirectPassage
from core.mcp_function_wrapper import MCPFunctionCallWrapper

try:
    from mcp import ClientSession
    from mcp.types import Tool
    MCP_SDK_AVAILABLE = True
except ImportError:
    MCP_SDK_AVAILABLE = False
    ClientSession = None
    Tool = None


class MCPManager:
    """
    Unified MCP manager that routes to appropriate implementation.

    This manager determines whether an agent should use:
    1. Native MCP (direct ClientSession) - for models with MCP support
    2. Function Call Wrapper - for models without MCP support

    The routing decision is based on the agent's LLM configuration and
    the MCP server configurations.
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize the MCP Manager.

        Args:
            config_manager: Optional configuration manager instance
        """
        self.config_manager = config_manager or ConfigManager()
        self._direct_passage = MCPDirectPassage(self.config_manager)
        self._function_wrapper = MCPFunctionCallWrapper(self.config_manager)
        self._is_initialized = False

    async def initialize(
        self,
        server_configs: Optional[List[MCPServerConfig]] = None
    ) -> None:
        """
        Initialize the MCP Manager.

        Initializes both the direct passage and function wrapper.
        Each will connect to their respective MCP servers based on
        the function_call_wrapper configuration.

        Args:
            server_configs: Optional list of server configs
        """
        if self._is_initialized:
            logger.warning("MCPManager already initialized")
            return

        logger.info("Initializing MCPManager...")

        # Initialize both components
        await self._direct_passage.initialize(server_configs)
        await self._function_wrapper.initialize(server_configs)

        self._is_initialized = True
        logger.info("MCPManager initialized")

    def get_tools_for_agent(
        self,
        agent_config: AgentConfig,
        llm_config: LLMConfig
    ) -> Union[List[Tool], List[Dict[str, Any]]]:
        """
        Get tools for an agent in the appropriate format.

        Args:
            agent_config: Agent configuration
            llm_config: LLM configuration

        Returns:
            - List[Tool] for native MCP models
            - List[Dict] (function call format) for non-MCP models
        """
        llm_supports_mcp = llm_config.get_model_mcp_support(agent_config.llm_model)

        if llm_supports_mcp:
            # Return tools in native MCP format
            return self._get_native_tools(agent_config.mcp_servers)
        else:
            # Return tools in function call format
            return self._function_wrapper.get_tools_for_agent(agent_config.mcp_servers)

    def _get_native_tools(self, server_names: List[str]) -> List[Tool]:
        """
        Get tools in native MCP format.

        Args:
            server_names: List of MCP server names

        Returns:
            List of Tool objects from native MCP SDK
        """
        if not MCP_SDK_AVAILABLE:
            logger.warning("MCP SDK not available, falling back to empty tool list")
            return []

        all_tools = []
        for server_name in server_names:
            # Check if server is configured for native MCP
            server_config = self.config_manager.get_mcp_server(server_name)
            if server_config and server_config.function_call_wrapper:
                # This server is configured for function call wrapper, skip
                continue

            # Get tools from direct passage (will return None if not connected)
            tools = self._direct_passage.get_server_names()
            if server_name in tools:
                # Server is connected via direct passage
                session_tools = self._direct_passage.list_tools(server_name)
                if session_tools:
                    all_tools.extend(session_tools)

        return all_tools

    async def get_mcp_session(
        self,
        server_name: str,
        agent_config: AgentConfig
    ) -> Optional[ClientSession]:
        """
        Get MCP session for an agent.

        Only returns a session for agents with native MCP support.

        Args:
            server_name: Name of the MCP server
            agent_config: Agent configuration

        Returns:
            ClientSession if available and agent supports MCP, None otherwise
        """
        if not MCP_SDK_AVAILABLE:
            return None

        llm_supports_mcp = self.config_manager.llm.get_model_mcp_support(
            agent_config.llm_model
        )

        if not llm_supports_mcp:
            # Agent doesn't support native MCP
            return None

        # Check if server is configured for native MCP
        server_config = self.config_manager.get_mcp_server(server_name)
        if server_config and server_config.function_call_wrapper:
            # Server is configured for function call wrapper
            logger.debug(
                f"[MCPManager] Server '{server_name}' has function_call_wrapper enabled, "
                f"not providing native session for agent '{agent_config.name}'"
            )
            return None

        # Get session from direct passage
        return await self._direct_passage.get_session(server_name)

    def get_function_call_tools(
        self,
        server_names: List[str],
        format: str = "openai"
    ) -> List[Dict[str, Any]]:
        """
        Get tools in function call format.

        Args:
            server_names: List of MCP server names
            format: Format type - "openai" or "qwen"

        Returns:
            List of tool definitions in function call format
        """
        if format == "openai":
            return self._function_wrapper.get_openai_tools(server_names)
        elif format == "qwen":
            return self._function_wrapper.get_qwen_tools(server_names)
        else:
            logger.warning(f"Unknown format '{format}', defaulting to openai")
            return self._function_wrapper.get_openai_tools(server_names)

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
        use_native: bool = False
    ) -> Any:
        """
        Call a tool on an MCP server.

        Args:
            server_name: Name of the MCP server
            tool_name: Name of the tool
            arguments: Tool arguments
            use_native: If True, use native MCP (for models with MCP support)

        Returns:
            Tool execution result
        """
        server_config = self.config_manager.get_mcp_server(server_name)
        if not server_config:
            raise ValueError(f"Server '{server_name}' not found")

        # Determine which implementation to use
        if use_native and not server_config.function_call_wrapper:
            # Use native MCP
            return await self._direct_passage.call_tool(server_name, tool_name, arguments)
        else:
            # Use function call wrapper
            return await self._function_wrapper.call_tool(server_name, tool_name, arguments)

    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers."""
        logger.info("Disconnecting all MCP Manager connections...")
        await self._direct_passage.disconnect_all()
        await self._function_wrapper.disconnect_all()
        self._is_initialized = False
        logger.info("All MCP Manager connections disconnected")

    # ========================================================================
    # Status and Info Methods
    # ========================================================================

    def get_status(self) -> Dict[str, Any]:
        """
        Get status of MCP Manager.

        Returns:
            Dictionary with status information
        """
        return {
            "initialized": self._is_initialized,
            "direct_passage": {
                "initialized": self._direct_passage.is_initialized,
                "servers": self._direct_passage.get_server_names(),
                "session_count": self._direct_passage.session_count,
            },
            "function_wrapper": {
                "initialized": self._function_wrapper.is_initialized,
                "servers": self._function_wrapper.get_connected_servers(),
                "server_count": self._function_wrapper.server_count,
                "tool_count": self._function_wrapper.tool_count,
            }
        }

    def get_server_status(self, server_name: str) -> Dict[str, Any]:
        """
        Get status of a specific MCP server.

        Args:
            server_name: Name of the MCP server

        Returns:
            Server status information
        """
        server_config = self.config_manager.get_mcp_server(server_name)
        if not server_config:
            return {"error": f"Server '{server_name}' not found"}

        if server_config.function_call_wrapper:
            # Server is configured for function call wrapper
            return {
                "server": server_name,
                "mode": "function_call_wrapper",
                "connected": self._function_wrapper.is_server_connected(server_name),
            }
        else:
            # Server is configured for native MCP
            return {
                "server": server_name,
                "mode": "native_mcp",
                "connected": server_name in self._direct_passage.get_server_names(),
            }

    # ========================================================================
    # Properties
    # ========================================================================

    @property
    def is_initialized(self) -> bool:
        """Check if the manager is initialized."""
        return self._is_initialized

    @property
    def direct_passage(self) -> MCPDirectPassage:
        """Get the direct passage instance."""
        return self._direct_passage

    @property
    def function_wrapper(self) -> MCPFunctionCallWrapper:
        """Get the function wrapper instance."""
        return self._function_wrapper

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"MCPManager("
            f"initialized={self._is_initialized}, "
            f"native_sessions={self._direct_passage.session_count}, "
            f"wrapper_servers={self._function_wrapper.server_count})"
        )


# Global MCP manager instance
_mcp_manager: Optional[MCPManager] = None


async def get_mcp_manager(
    config_manager: Optional[ConfigManager] = None,
    force_refresh: bool = False
) -> MCPManager:
    """
    Get the global MCP manager instance.

    Args:
        config_manager: Optional configuration manager
        force_refresh: Force re-initialization

    Returns:
        MCPManager instance
    """
    global _mcp_manager

    if _mcp_manager is None or force_refresh:
        _mcp_manager = MCPManager(config_manager)
        await _mcp_manager.initialize()

    return _mcp_manager


__all__ = ["MCPManager", "get_mcp_manager"]
