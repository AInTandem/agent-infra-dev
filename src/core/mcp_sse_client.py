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
MCP SSE Client implementation.

Communicates with MCP servers via Server-Sent Events (SSE) transport.
"""

import asyncio
import json
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx
from loguru import logger


class MCPSSEClient:
    """
    Client for communicating with MCP servers via SSE.

    Supports streaming responses for tool calls and maintains
    a persistent connection to the SSE endpoint.
    """

    def __init__(
        self,
        name: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
    ):
        """
        Initialize the MCP SSE client.

        Args:
            name: Server name for identification
            url: SSE endpoint URL
            headers: Optional HTTP headers for requests
            timeout: Request timeout in seconds
        """
        self.name = name
        self.url = url
        self.headers = headers or {}
        self.timeout = timeout

        self._is_connected = False
        self._server_capabilities: Optional[Dict[str, Any]] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._message_id = 0

    async def connect(self) -> None:
        """
        Connect to the MCP SSE server.

        Initializes the HTTP client and verifies connectivity.
        """
        if self._is_connected:
            logger.warning(f"[{self.name}] Already connected")
            return

        try:
            logger.info(f"[{self.name}] Connecting to MCP SSE server: {self.url}")

            # Create HTTP client
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers=self.headers,
            )

            # Verify connection by listing tools
            tools = await self.list_tools()
            self._is_connected = True

            # Set capabilities based on available tools
            self._server_capabilities = {
                "tools": len(tools) > 0,
                "resources": False,
                "prompts": False,
            }

            logger.info(f"[{self.name}] Connected successfully")
            logger.debug(f"[{self.name}] Server capabilities: {self._server_capabilities}")

        except Exception as e:
            logger.error(f"[{self.name}] Failed to connect: {e}")
            await self.disconnect()
            raise

    async def disconnect(self) -> None:
        """
        Disconnect from the MCP SSE server.

        Closes the HTTP client connection.
        """
        if not self._is_connected:
            return

        try:
            logger.info(f"[{self.name}] Disconnecting...")

            if self._client:
                await self._client.aclose()
                self._client = None

            self._is_connected = False
            self._server_capabilities = None

            logger.info(f"[{self.name}] Disconnected")

        except Exception as e:
            logger.error(f"[{self.name}] Error during disconnect: {e}")
            # Force cleanup
            self._is_connected = False
            self._client = None

    async def _send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a JSON-RPC request via SSE POST.

        Args:
            method: JSON-RPC method name
            params: Method parameters

        Returns:
            JSON-RPC response

        Raises:
            RuntimeError: If not connected
            httpx.HTTPError: If HTTP request fails
        """
        if not self._is_connected or not self._client:
            raise RuntimeError(f"[{self.name}] Not connected")

        self._message_id += 1

        payload = {
            "jsonrpc": "2.0",
            "id": self._message_id,
            "method": method,
            "params": params,
        }

        logger.debug(f"[{self.name}] Sending request: {method}")

        try:
            response = await self._client.post(
                self.url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()

            result = response.json()
            logger.debug(f"[{self.name}] Received response: {result}")
            return result

        except httpx.HTTPError as e:
            logger.error(f"[{self.name}] HTTP error: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"[{self.name}] Invalid JSON response: {e}")
            raise

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools from the MCP server.

        Returns:
            List of tool definitions

        Raises:
            RuntimeError: If not connected
            TimeoutError: If request times out
        """
        try:
            response = await asyncio.wait_for(
                self._send_request("tools/list", {}),
                timeout=self.timeout
            )

            if "error" in response:
                raise RuntimeError(f"[{self.name}] Server error: {response['error']}")

            tools_data = response.get("result", {})
            tools = []

            for tool in tools_data.get("tools", []):
                tools.append({
                    "name": tool.get("name"),
                    "description": tool.get("description", ""),
                    "inputSchema": tool.get("inputSchema", {}),
                })

            logger.debug(f"[{self.name}] Retrieved {len(tools)} tools")
            return tools

        except asyncio.TimeoutError:
            logger.error(f"[{self.name}] Timeout listing tools")
            raise TimeoutError(f"[{self.name}] Request timeout")

        except Exception as e:
            logger.error(f"[{self.name}] Error listing tools: {e}")
            raise

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool on the MCP server.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            RuntimeError: If not connected
            TimeoutError: If request times out
        """
        try:
            logger.debug(f"[{self.name}] Calling tool: {name} with args: {arguments}")

            response = await asyncio.wait_for(
                self._send_request("tools/call", {
                    "name": name,
                    "arguments": arguments,
                }),
                timeout=self.timeout
            )

            if "error" in response:
                raise RuntimeError(f"[{self.name}] Server error: {response['error']}")

            # Extract content from result
            result = response.get("result", {})
            content = result.get("content", result)

            logger.debug(f"[{self.name}] Tool result: {content}")
            return content

        except asyncio.TimeoutError:
            logger.error(f"[{self.name}] Timeout calling tool: {name}")
            raise TimeoutError(f"[{self.name}] Request timeout")

        except Exception as e:
            logger.error(f"[{self.name}] Error calling tool {name}: {e}")
            raise

    async def call_tool_stream(
        self,
        name: str,
        arguments: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Call a tool on the MCP server with streaming response.

        Args:
            name: Tool name
            arguments: Tool arguments

        Yields:
            Streaming response chunks

        Raises:
            RuntimeError: If not connected
            TimeoutError: If request times out
        """
        if not self._is_connected or not self._client:
            raise RuntimeError(f"[{self.name}] Not connected")

        self._message_id += 1

        payload = {
            "jsonrpc": "2.0",
            "id": self._message_id,
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments,
            },
        }

        logger.debug(f"[{self.name}] Calling tool with stream: {name}")

        try:
            async with self._client.stream(
                "POST",
                self.url,
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                response.raise_for_status()

                # Read SSE events
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    # SSE format: "data: {json}"
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        try:
                            chunk = json.loads(data_str)
                            yield chunk
                        except json.JSONDecodeError:
                            logger.warning(f"[{self.name}] Invalid SSE data: {data_str}")
                            continue

        except asyncio.TimeoutError:
            logger.error(f"[{self.name}] Timeout in streaming tool call: {name}")
            raise TimeoutError(f"[{self.name}] Request timeout")

        except Exception as e:
            logger.error(f"[{self.name}] Error in streaming tool call {name}: {e}")
            raise

    async def list_resources(self) -> List[Dict[str, Any]]:
        """
        List available resources from the MCP server.

        Returns:
            List of resource definitions
        """
        try:
            response = await asyncio.wait_for(
                self._send_request("resources/list", {}),
                timeout=self.timeout
            )

            if "error" in response:
                raise RuntimeError(f"[{self.name}] Server error: {response['error']}")

            resources_data = response.get("result", {})
            resources = []

            for resource in resources_data.get("resources", []):
                resources.append({
                    "uri": resource.get("uri"),
                    "name": resource.get("name"),
                    "description": resource.get("description", ""),
                    "mimeType": resource.get("mimeType", ""),
                })

            logger.debug(f"[{self.name}] Retrieved {len(resources)} resources")
            return resources

        except asyncio.TimeoutError:
            logger.error(f"[{self.name}] Timeout listing resources")
            raise TimeoutError(f"[{self.name}] Request timeout")

        except Exception as e:
            logger.error(f"[{self.name}] Error listing resources: {e}")
            raise

    async def read_resource(self, uri: str) -> Any:
        """
        Read a resource from the MCP server.

        Args:
            uri: Resource URI

        Returns:
            Resource content
        """
        try:
            logger.debug(f"[{self.name}] Reading resource: {uri}")

            response = await asyncio.wait_for(
                self._send_request("resources/read", {"uri": uri}),
                timeout=self.timeout
            )

            if "error" in response:
                raise RuntimeError(f"[{self.name}] Server error: {response['error']}")

            result = response.get("result", {})
            contents = result.get("contents", [])

            logger.debug(f"[{self.name}] Resource content length: {len(str(contents))}")
            return contents

        except asyncio.TimeoutError:
            logger.error(f"[{self.name}] Timeout reading resource: {uri}")
            raise TimeoutError(f"[{self.name}] Request timeout")

        except Exception as e:
            logger.error(f"[{self.name}] Error reading resource {uri}: {e}")
            raise

    async def list_prompts(self) -> List[Dict[str, Any]]:
        """
        List available prompts from the MCP server.

        Returns:
            List of prompt definitions
        """
        try:
            response = await asyncio.wait_for(
                self._send_request("prompts/list", {}),
                timeout=self.timeout
            )

            if "error" in response:
                raise RuntimeError(f"[{self.name}] Server error: {response['error']}")

            prompts_data = response.get("result", {})
            prompts = []

            for prompt in prompts_data.get("prompts", []):
                prompts.append({
                    "name": prompt.get("name"),
                    "description": prompt.get("description", ""),
                    "arguments": [
                        {
                            "name": arg.get("name"),
                            "description": arg.get("description", ""),
                            "required": arg.get("required", False),
                        }
                        for arg in prompt.get("arguments", [])
                    ],
                })

            logger.debug(f"[{self.name}] Retrieved {len(prompts)} prompts")
            return prompts

        except asyncio.TimeoutError:
            logger.error(f"[{self.name}] Timeout listing prompts")
            raise TimeoutError(f"[{self.name}] Request timeout")

        except Exception as e:
            logger.error(f"[{self.name}] Error listing prompts: {e}")
            raise

    async def get_prompt(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Get a prompt from the MCP server.

        Args:
            name: Prompt name
            arguments: Optional prompt arguments

        Returns:
            Prompt content
        """
        try:
            logger.debug(f"[{self.name}] Getting prompt: {name}")

            response = await asyncio.wait_for(
                self._send_request("prompts/get", {
                    "name": name,
                    "arguments": arguments or {},
                }),
                timeout=self.timeout
            )

            if "error" in response:
                raise RuntimeError(f"[{self.name}] Server error: {response['error']}")

            result = response.get("result", {})
            messages = result.get("messages", [])

            logger.debug(f"[{self.name}] Prompt messages count: {len(messages)}")
            return messages

        except asyncio.TimeoutError:
            logger.error(f"[{self.name}] Timeout getting prompt: {name}")
            raise TimeoutError(f"[{self.name}] Request timeout")

        except Exception as e:
            logger.error(f"[{self.name}] Error getting prompt {name}: {e}")
            raise

    async def ping(self) -> bool:
        """
        Send a ping to the MCP server.

        Returns:
            True if ping successful
        """
        if not self._is_connected or not self._client:
            return False

        try:
            await asyncio.wait_for(
                self._send_request("ping", {}),
                timeout=5
            )
            return True
        except Exception as e:
            logger.warning(f"[{self.name}] Ping failed: {e}")
            return False

    @property
    def is_connected(self) -> bool:
        """Check if connected to the MCP server."""
        return self._is_connected

    @property
    def capabilities(self) -> Dict[str, bool]:
        """Get server capabilities."""
        if not self._is_connected:
            return {}
        return self._server_capabilities or {}

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    def __repr__(self) -> str:
        """String representation."""
        return f"MCPSSEClient(name={self.name}, url={self.url}, connected={self._is_connected})"
