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
MCP Stdio Client implementation.

Wraps the MCP SDK's ClientSession for communicating with MCP servers via stdio.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional

from loguru import logger
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPStdioClient:
    """
    Client for communicating with MCP servers via stdio.

    Handles process lifecycle, connection management, and JSON-RPC communication.

    Note: This client maintains an ongoing background task to keep the stdio
    context alive. Make sure to call disconnect() when done.
    """

    def __init__(
        self,
        name: str,
        command: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize the MCP stdio client.

        Args:
            name: Server name for identification
            command: Command to start the MCP server
            args: Arguments for the command
            env: Environment variables for the server process
            cwd: Working directory for the server process
            timeout: Request timeout in seconds
        """
        self.name = name
        self.command = command
        self.args = args
        self.env = env or {}
        self.cwd = cwd
        self.timeout = timeout

        self._session: Optional[ClientSession] = None
        self._is_connected = False
        self._server_capabilities: Optional[Dict[str, Any]] = None
        self._keep_alive_task: Optional[asyncio.Task] = None
        self._should_stop = asyncio.Event()

    async def connect(self) -> None:
        """
        Connect to the MCP server.

        Starts the server process and initializes the session.
        """
        if self._is_connected:
            logger.warning(f"[{self.name}] Already connected")
            return

        self._should_stop.clear()

        try:
            logger.info(f"[{self.name}] Connecting to MCP server...")

            # Create stdio server parameters
            server_params = StdioServerParameters(
                command=self.command,
                args=self.args,
                env=self.env,
                cwd=self.cwd,
            )

            # Create stdio client context
            stdio_ctx = stdio_client(server=server_params)

            # Connect and initialize session within the context
            async def _connect_and_initialize():
                async with stdio_ctx as (read_stream, write_stream):
                    logger.debug(f"[{self.name}] stdio context established, creating session...")

                    # Use ClientSession as context manager (auto-initializes)
                    async with ClientSession(read_stream, write_stream) as session:
                        logger.debug(f"[{self.name}] Session initialized successfully")

                        # Store session
                        self._session = session

                        # Probe server capabilities by testing each feature
                        try:
                            await asyncio.wait_for(session.list_tools(), timeout=2)
                            self._server_capabilities = {"tools": True, "resources": False, "prompts": False}
                            logger.debug(f"[{self.name}] Server supports tools")
                        except asyncio.TimeoutError:
                            self._server_capabilities = {"tools": False, "resources": False, "prompts": False}
                            logger.warning(f"[{self.name}] Could not probe server capabilities")

                        self._is_connected = True
                        logger.info(f"[{self.name}] Connected successfully")
                        logger.debug(f"[{self.name}] Server capabilities: {self._server_capabilities}")

                        # Wait until we should stop
                        await self._should_stop.wait()

            # Run the connection in a background task
            self._keep_alive_task = asyncio.create_task(_connect_and_initialize())

            # Wait for connection to be established (use configured timeout)
            max_wait = self.timeout  # Use the configured timeout value
            wait_interval = 0.1  # Check every 100ms
            max_attempts = int(max_wait / wait_interval)

            logger.debug(f"[{self.name}] Waiting for connection (timeout: {max_wait}s)...")

            for attempt in range(max_attempts):
                await asyncio.sleep(wait_interval)
                if self._is_connected:
                    logger.debug(f"[{self.name}] Connected after {attempt * wait_interval:.1f}s")
                    break
            else:
                raise TimeoutError(f"[{self.name}] Connection timeout after {max_wait}s")

        except Exception as e:
            logger.error(f"[{self.name}] Failed to connect: {e}")
            await self.disconnect()
            raise

    async def disconnect(self) -> None:
        """
        Disconnect from the MCP server.

        Signals the background task to stop and waits for cleanup.
        """
        if not self._is_connected and not self._keep_alive_task:
            return

        try:
            logger.info(f"[{self.name}] Disconnecting...")

            # Signal the background task to stop
            self._should_stop.set()

            # Wait for the background task to complete
            if self._keep_alive_task:
                try:
                    await asyncio.wait_for(self._keep_alive_task, timeout=5)
                except asyncio.TimeoutError:
                    logger.warning(f"[{self.name}] Timeout waiting for background task")
                    self._keep_alive_task.cancel()
                    try:
                        await self._keep_alive_task
                    except asyncio.CancelledError:
                        pass
                except Exception as e:
                    logger.warning(f"[{self.name}] Error in background task: {e}")

            # Clean up
            self._is_connected = False
            self._server_capabilities = None
            self._session = None
            self._keep_alive_task = None

            logger.info(f"[{self.name}] Disconnected")

        except Exception as e:
            logger.error(f"[{self.name}] Error during disconnect: {e}")
            # Force cleanup
            self._is_connected = False
            self._session = None
            self._keep_alive_task = None

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools from the MCP server.

        Returns:
            List of tool definitions

        Raises:
            RuntimeError: If not connected
            TimeoutError: If request times out
        """
        if not self._is_connected or not self._session:
            raise RuntimeError(f"[{self.name}] Not connected")

        try:
            result = await asyncio.wait_for(
                self._session.list_tools(),
                timeout=self.timeout
            )

            tools = []
            for tool in result.tools:
                tools.append({
                    "name": tool.name,
                    "description": tool.description or "",
                    "inputSchema": tool.inputSchema or {},
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
        if not self._is_connected or not self._session:
            raise RuntimeError(f"[{self.name}] Not connected")

        try:
            logger.debug(f"[{self.name}] Calling tool: {name} with args: {arguments}")

            result = await asyncio.wait_for(
                self._session.call_tool(name, arguments),
                timeout=self.timeout
            )

            # Extract content from result
            if hasattr(result, 'content'):
                content = result.content
            elif isinstance(result, dict):
                content = result.get('content', result)
            else:
                content = result

            logger.debug(f"[{self.name}] Tool result: {content}")
            return content

        except asyncio.TimeoutError:
            logger.error(f"[{self.name}] Timeout calling tool: {name}")
            raise TimeoutError(f"[{self.name}] Request timeout")

        except Exception as e:
            logger.error(f"[{self.name}] Error calling tool {name}: {e}")
            raise

    async def list_resources(self) -> List[Dict[str, Any]]:
        """
        List available resources from the MCP server.

        Returns:
            List of resource definitions
        """
        if not self._is_connected or not self._session:
            raise RuntimeError(f"[{self.name}] Not connected")

        try:
            result = await asyncio.wait_for(
                self._session.list_resources(),
                timeout=self.timeout
            )

            resources = []
            for resource in result.resources:
                resources.append({
                    "uri": resource.uri,
                    "name": resource.name,
                    "description": resource.description or "",
                    "mimeType": resource.mimeType or "",
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
        if not self._is_connected or not self._session:
            raise RuntimeError(f"[{self.name}] Not connected")

        try:
            logger.debug(f"[{self.name}] Reading resource: {uri}")

            result = await asyncio.wait_for(
                self._session.read_resource(uri),
                timeout=self.timeout
            )

            # Extract content from result
            if hasattr(result, 'contents'):
                contents = result.contents
            elif isinstance(result, dict):
                contents = result.get('contents', [])
            else:
                contents = [result]

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
        if not self._is_connected or not self._session:
            raise RuntimeError(f"[{self.name}] Not connected")

        try:
            result = await asyncio.wait_for(
                self._session.list_prompts(),
                timeout=self.timeout
            )

            prompts = []
            for prompt in result.prompts:
                prompts.append({
                    "name": prompt.name,
                    "description": prompt.description or "",
                    "arguments": [
                        {"name": arg.name, "description": arg.description or "", "required": arg.required}
                        for arg in (prompt.arguments or [])
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

    async def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """
        Get a prompt from the MCP server.

        Args:
            name: Prompt name
            arguments: Optional prompt arguments

        Returns:
            Prompt content
        """
        if not self._is_connected or not self._session:
            raise RuntimeError(f"[{self.name}] Not connected")

        try:
            logger.debug(f"[{self.name}] Getting prompt: {name}")

            result = await asyncio.wait_for(
                self._session.get_prompt(name, arguments or {}),
                timeout=self.timeout
            )

            # Extract messages from result
            if hasattr(result, 'messages'):
                messages = result.messages
            elif isinstance(result, dict):
                messages = result.get('messages', [])
            else:
                messages = [result]

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
        if not self._is_connected or not self._session:
            return False

        try:
            await asyncio.wait_for(
                self._session.send_ping(),
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
        return f"MCPStdioClient(name={self.name}, connected={self._is_connected})"
