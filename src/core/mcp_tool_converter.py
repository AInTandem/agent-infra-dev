"""
MCP Tool converter implementation.

Converts MCP tools to formats compatible with Qwen Agent and other frameworks.
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from .mcp_stdio_client import MCPStdioClient


class MCPToolConverter:
    """
    Converter for MCP tools to various agent framework formats.

    Wraps MCP tools as callable functions that agents can use.
    """

    def __init__(self, client: MCPStdioClient):
        """
        Initialize the converter.

        Args:
            client: MCP stdio client for the server
        """
        self.client = client
        self._converted_tools: Dict[str, Dict[str, Any]] = {}

    def convert_tool(self, tool_def: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert an MCP tool definition to a Qwen Agent compatible format.

        Args:
            tool_def: MCP tool definition (name, description, inputSchema)

        Returns:
            Converted tool with name, description, function, and parameters
        """
        name = tool_def["name"]
        description = tool_def.get("description", "")
        input_schema = tool_def.get("inputSchema", {})

        # Create async callable wrapper
        async def wrapper(**kwargs):
            """Wrapper function that calls the MCP tool."""
            try:
                result = await self.client.call_tool(name, kwargs)
                return result
            except Exception as e:
                logger.error(f"[{self.client.name}] Tool {name} error: {e}")
                return {"error": str(e)}

        # Build the converted tool
        converted = {
            "name": name,
            "description": description,
            "function": wrapper,
            "parameters": self._convert_schema(input_schema),
        }

        # Cache the converted tool
        self._converted_tools[name] = converted

        logger.debug(f"[{self.client.name}] Converted tool: {name}")
        return converted

    def _convert_schema(self, json_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert JSON Schema to a more agent-friendly format.

        Args:
            json_schema: Original JSON Schema

        Returns:
            Simplified parameter schema
        """
        if not json_schema:
            return {"type": "object", "properties": {}}

        # Extract type and properties
        schema_type = json_schema.get("type", "object")

        converted = {"type": schema_type}

        if schema_type == "object":
            converted["properties"] = json_schema.get("properties", {})
            converted["required"] = json_schema.get("required", [])
        elif schema_type == "array":
            converted["items"] = json_schema.get("items", {})
        else:
            # Primitive types
            pass

        # Add other constraints
        for key in ["enum", "format", "pattern", "minLength", "maxLength", "minimum", "maximum"]:
            if key in json_schema:
                converted[key] = json_schema[key]

        return converted

    def convert_tools(self, tool_defs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert multiple MCP tool definitions.

        Args:
            tool_defs: List of MCP tool definitions

        Returns:
            List of converted tools
        """
        converted = []
        for tool_def in tool_defs:
            try:
                converted_tool = self.convert_tool(tool_def)
                converted.append(converted_tool)
            except Exception as e:
                logger.error(f"Error converting tool {tool_def.get('name')}: {e}")

        logger.info(f"[{self.client.name}] Converted {len(converted)} tools")
        return converted

    def to_qwen_format(self, tool_def: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert an MCP tool to Qwen Agent's tool format.

        Qwen Agent expects:
        {
            "name": str,
            "description": str,
            "parameters": dict (JSON Schema)
        }

        Args:
            tool_def: MCP tool definition

        Returns:
            Qwen Agent compatible tool definition
        """
        converted = self.convert_tool(tool_def)

        return {
            "name": converted["name"],
            "description": converted["description"],
            "parameters": converted["parameters"],
        }

    def to_openai_format(self, tool_def: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert an MCP tool to OpenAI function calling format.

        OpenAI format:
        {
            "type": "function",
            "function": {
                "name": str,
                "description": str,
                "parameters": dict (JSON Schema)
            }
        }

        Args:
            tool_def: MCP tool definition

        Returns:
            OpenAI compatible tool definition
        """
        converted = self.convert_tool(tool_def)

        return {
            "type": "function",
            "function": {
                "name": converted["name"],
                "description": converted["description"],
                "parameters": converted["parameters"],
            }
        }

    def to_openrouter_format(self, tool_def: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert an MCP tool to OpenRouter/librechat format.

        Similar to OpenAI format but slightly different structure.

        Args:
            tool_def: MCP tool definition

        Returns:
            OpenRouter compatible tool definition
        """
        return self.to_openai_format(tool_def)

    def get_wrapper_function(self, tool_name: str) -> Optional[Callable]:
        """
        Get the wrapper function for a converted tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Async callable function or None if not found
        """
        if tool_name in self._converted_tools:
            return self._converted_tools[tool_name]["function"]
        return None

    def get_all_wrappers(self) -> Dict[str, Callable]:
        """
        Get all wrapper functions.

        Returns:
            Dictionary mapping tool names to async callables
        """
        return {
            name: tool["function"]
            for name, tool in self._converted_tools.items()
        }

    def clear_cache(self) -> None:
        """Clear the converted tools cache."""
        self._converted_tools.clear()
        logger.debug(f"[{self.client.name}] Cleared tool cache")


class MultiMCPToolConverter:
    """
    Converter for multiple MCP servers.

    Manages tool conversion from multiple MCP servers.
    """

    def __init__(self):
        """Initialize the multi-server converter."""
        self._converters: Dict[str, MCPToolConverter] = {}
        self._all_tools: Dict[str, Dict[str, Any]] = {}

    def add_server(self, name: str, client: MCPStdioClient) -> MCPToolConverter:
        """
        Add an MCP server and create its converter.

        Args:
            name: Server name
            client: MCP stdio client

        Returns:
            The created converter
        """
        converter = MCPToolConverter(client)
        self._converters[name] = converter
        return converter

    async def load_tools_from_server(
        self,
        name: str,
        client: MCPStdioClient
    ) -> List[Dict[str, Any]]:
        """
        Load and convert tools from an MCP server.

        Args:
            name: Server name
            client: MCP stdio client

        Returns:
            List of converted tools
        """
        if name not in self._converters:
            self.add_server(name, client)

        converter = self._converters[name]

        # Get tools from server
        tool_defs = await client.list_tools()

        # Convert tools
        converted_tools = converter.convert_tools(tool_defs)

        # Store with server prefix
        for tool in converted_tools:
            prefixed_name = f"{name}.{tool['name']}"
            tool["name"] = prefixed_name
            tool["server_name"] = name
            tool["original_name"] = tool_def = next(
                (t for t in tool_defs if t["name"] == tool.get("original_name", tool["name"].split(".")[-1])),
                {}
            ).get("name", prefixed_name.split(".")[-1])
            self._all_tools[prefixed_name] = tool

        logger.info(f"[{name}] Loaded and converted {len(converted_tools)} tools")
        return converted_tools

    async def load_tools_from_all_servers(
        self,
        clients: Dict[str, MCPStdioClient]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Load and convert tools from all MCP servers.

        Args:
            clients: Dictionary mapping server names to clients

        Returns:
            Dictionary mapping server names to their converted tools
        """
        results = {}

        for name, client in clients.items():
            if not client.is_connected:
                logger.warning(f"[{name}] Skipping disconnected server")
                continue

            try:
                tools = await self.load_tools_from_server(name, client)
                results[name] = tools
            except Exception as e:
                logger.error(f"[{name}] Error loading tools: {e}")
                results[name] = []

        total_tools = sum(len(tools) for tools in results.values())
        logger.info(f"Loaded total of {total_tools} tools from {len(results)} servers")

        return results

    def get_tools_for_servers(self, server_names: List[str]) -> List[Dict[str, Any]]:
        """
        Get all tools from specific servers.

        Args:
            server_names: List of server names

        Returns:
            List of tools from the specified servers
        """
        tools = []
        for name in server_names:
            for tool_name, tool in self._all_tools.items():
                if tool.get("server_name") == name:
                    tools.append(tool)
        return tools

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all converted tools from all servers."""
        return list(self._all_tools.values())

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific tool by name.

        Args:
            name: Tool name (with or without server prefix)

        Returns:
            Tool definition or None
        """
        # Try direct lookup
        if name in self._all_tools:
            return self._all_tools[name]

        # Try to find by original name
        for tool in self._all_tools.values():
            if tool.get("original_name") == name or tool.get("name") == name:
                return tool

        return None

    def get_wrapper(self, name: str) -> Optional[Callable]:
        """
        Get the wrapper function for a tool.

        Args:
            name: Tool name

        Returns:
            Async callable or None
        """
        tool = self.get_tool(name)
        if tool:
            return tool.get("function")
        return None

    def to_qwen_tools_list(self) -> List[Dict[str, Any]]:
        """
        Convert all tools to Qwen Agent format list.

        Returns:
            List of Qwen Agent compatible tool definitions
        """
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
            }
            for tool in self._all_tools.values()
        ]

    def to_openai_tools_list(self) -> List[Dict[str, Any]]:
        """
        Convert all tools to OpenAI format list.

        Returns:
            List of OpenAI compatible tool definitions
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                }
            }
            for tool in self._all_tools.values()
        ]

    def clear(self) -> None:
        """Clear all converters and tools."""
        self._converters.clear()
        self._all_tools.clear()
        logger.debug("Cleared all converters and tools")
