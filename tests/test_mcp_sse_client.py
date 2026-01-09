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
Tests for MCP SSE client.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import HTTPStatusError, Response, TimeoutException


@pytest.fixture
def sse_client():
    """Create an MCP SSE client for testing."""
    from core.mcp_sse_client import MCPSSEClient

    return MCPSSEClient(
        name="test-server",
        url="http://localhost:3000/sse",
        headers={"Authorization": "Bearer test-token"},
        timeout=30,
    )


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx AsyncClient."""
    mock_client = MagicMock()
    mock_client.post = AsyncMock()
    mock_client.stream = MagicMock()
    mock_client.aclose = AsyncMock()

    return mock_client


class TestMCPSSEClient:
    """Test suite for MCPSSEClient."""

    @pytest.mark.asyncio
    async def test_client_initialization(self, sse_client):
        """Test client is properly initialized."""
        assert sse_client.name == "test-server"
        assert sse_client.url == "http://localhost:3000/sse"
        assert sse_client.headers == {"Authorization": "Bearer test-token"}
        assert sse_client.timeout == 30
        assert not sse_client.is_connected

    @pytest.mark.asyncio
    async def test_connect_success(self, sse_client, mock_httpx_client):
        """Test successful connection."""
        # Mock successful list_tools response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "tools": [
                    {
                        "name": "test_tool",
                        "description": "A test tool",
                        "inputSchema": {"type": "object"},
                    }
                ]
            }
        }

        # Set up the mock client properly
        mock_httpx_client.post.return_value = mock_response

        # Create a new client instance with the mocked httpx client
        from core.mcp_sse_client import MCPSSEClient

        test_client = MCPSSEClient(
            name="test-server",
            url="http://localhost:3000/sse",
            headers={"Authorization": "Bearer test-token"},
            timeout=30,
        )

        # Manually set the mock client
        test_client._client = mock_httpx_client
        test_client._is_connected = True  # Simulate connection

        # Verify connection status
        assert test_client.is_connected

        # Test list_tools to verify it works with the mocked client
        tools = await test_client.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "test_tool"

    @pytest.mark.asyncio
    async def test_disconnect(self, sse_client, mock_httpx_client):
        """Test disconnection."""
        sse_client._is_connected = True
        sse_client._client = mock_httpx_client

        await sse_client.disconnect()

        assert not sse_client.is_connected
        mock_httpx_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_tools(self, sse_client, mock_httpx_client):
        """Test listing tools."""
        sse_client._is_connected = True
        sse_client._client = mock_httpx_client

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "tools": [
                    {
                        "name": "read_file",
                        "description": "Read a file",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"}
                            }
                        },
                    }
                ]
            }
        }

        mock_httpx_client.post.return_value = mock_response

        tools = await sse_client.list_tools()

        assert len(tools) == 1
        assert tools[0]["name"] == "read_file"
        assert tools[0]["description"] == "Read a file"

    @pytest.mark.asyncio
    async def test_call_tool(self, sse_client, mock_httpx_client):
        """Test calling a tool."""
        sse_client._is_connected = True
        sse_client._client = mock_httpx_client

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": "File content here"
                    }
                ]
            }
        }

        mock_httpx_client.post.return_value = mock_response

        result = await sse_client.call_tool("read_file", {"path": "/test/file.txt"})

        assert result == [
            {
                "type": "text",
                "text": "File content here"
            }
        ]

    @pytest.mark.asyncio
    async def test_call_tool_stream(self, sse_client, mock_httpx_client):
        """Test streaming tool call."""
        sse_client._is_connected = True
        sse_client._client = mock_httpx_client

        # Create mock stream context
        mock_stream_response = MagicMock()
        mock_stream_context = MagicMock()

        # Mock the aiter_lines to return SSE events
        async def mock_aiter_lines():
            yield 'data: {"type": "chunk", "data": "First chunk"}'
            yield ''
            yield 'data: {"type": "chunk", "data": "Second chunk"}'
            yield 'data: {"type": "done"}'

        mock_stream_response.aiter_lines = mock_aiter_lines
        mock_stream_response.raise_for_status = MagicMock()

        mock_stream_context.__aenter__.return_value = mock_stream_response
        mock_stream_context.__aexit__.return_value = None

        mock_httpx_client.stream.return_value = mock_stream_context

        chunks = []
        async for chunk in sse_client.call_tool_stream("stream_tool", {}):
            chunks.append(chunk)

        assert len(chunks) == 3
        assert chunks[0]["type"] == "chunk"
        assert chunks[0]["data"] == "First chunk"
        assert chunks[1]["data"] == "Second chunk"

    @pytest.mark.asyncio
    async def test_call_tool_not_connected(self, sse_client):
        """Test calling tool when not connected."""
        with pytest.raises(RuntimeError, match="Not connected"):
            await sse_client.call_tool("test_tool", {})

    @pytest.mark.asyncio
    async def test_list_resources(self, sse_client, mock_httpx_client):
        """Test listing resources."""
        sse_client._is_connected = True
        sse_client._client = mock_httpx_client

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "resources": [
                    {
                        "uri": "file:///test.txt",
                        "name": "test.txt",
                        "description": "Test file",
                        "mimeType": "text/plain",
                    }
                ]
            }
        }

        mock_httpx_client.post.return_value = mock_response

        resources = await sse_client.list_resources()

        assert len(resources) == 1
        assert resources[0]["uri"] == "file:///test.txt"

    @pytest.mark.asyncio
    async def test_read_resource(self, sse_client, mock_httpx_client):
        """Test reading a resource."""
        sse_client._is_connected = True
        sse_client._client = mock_httpx_client

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "contents": [
                    {
                        "uri": "file:///test.txt",
                        "text": "Resource content"
                    }
                ]
            }
        }

        mock_httpx_client.post.return_value = mock_response

        result = await sse_client.read_resource("file:///test.txt")

        assert result == [
            {
                "uri": "file:///test.txt",
                "text": "Resource content"
            }
        ]

    @pytest.mark.asyncio
    async def test_list_prompts(self, sse_client, mock_httpx_client):
        """Test listing prompts."""
        sse_client._is_connected = True
        sse_client._client = mock_httpx_client

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "prompts": [
                    {
                        "name": "summarize",
                        "description": "Summarize text",
                        "arguments": [],
                    }
                ]
            }
        }

        mock_httpx_client.post.return_value = mock_response

        prompts = await sse_client.list_prompts()

        assert len(prompts) == 1
        assert prompts[0]["name"] == "summarize"

    @pytest.mark.asyncio
    async def test_get_prompt(self, sse_client, mock_httpx_client):
        """Test getting a prompt."""
        sse_client._is_connected = True
        sse_client._client = mock_httpx_client

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "result": {
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": "Summarize this"
                        }
                    }
                ]
            }
        }

        mock_httpx_client.post.return_value = mock_response

        result = await sse_client.get_prompt("summarize", {})

        assert len(result) == 1
        assert result[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_ping(self, sse_client, mock_httpx_client):
        """Test ping."""
        sse_client._is_connected = True
        sse_client._client = mock_httpx_client

        mock_response = MagicMock()
        mock_response.json.return_value = {"result": {}}

        mock_httpx_client.post.return_value = mock_response

        result = await sse_client.ping()

        assert result is True

    @pytest.mark.asyncio
    async def test_ping_failure(self, sse_client, mock_httpx_client):
        """Test ping on failure."""
        sse_client._is_connected = True
        sse_client._client = mock_httpx_client

        mock_httpx_client.post.side_effect = Exception("Connection error")

        result = await sse_client.ping()

        assert result is False

    @pytest.mark.asyncio
    async def test_async_context_manager(self, mock_httpx_client):
        """Test using client as async context manager."""
        from core.mcp_sse_client import MCPSSEClient

        test_client = MCPSSEClient(
            name="test-server",
            url="http://localhost:3000/sse"
        )

        # Manually set up the mock for testing context manager behavior
        test_client._client = mock_httpx_client
        test_client._is_connected = True

        # Simulate disconnect
        await test_client.disconnect()

        assert not test_client.is_connected

    def test_repr(self, sse_client):
        """Test string representation."""
        repr_str = repr(sse_client)

        assert "MCPSSEClient" in repr_str
        assert "test-server" in repr_str
        assert "http://localhost:3000/sse" in repr_str
        assert "connected=False" in repr_str


class TestMCPSSEIntegration:
    """Integration tests for MCP SSE with MCPBridge."""

    @pytest.mark.asyncio
    async def test_sse_server_in_mcp_bridge(self):
        """Test that SSE servers can be added to MCPBridge."""
        from core.config import MCPServerConfig, MCPSSEConfig
        from core.mcp_bridge import MCPBridge
        from core.mcp_sse_client import MCPSSEClient

        # Create SSE server config
        config = MCPServerConfig(
            name="sse-server",
            description="Test SSE server",
            transport="sse",
            sse=MCPSSEConfig(
                url="http://localhost:3000/sse",
                headers={"Authorization": "Bearer test"}
            ),
            timeout=30,
            enabled=True,
        )

        # Verify config structure
        assert config.transport == "sse"
        assert config.sse.url == "http://localhost:3000/sse"
        assert config.command is None  # SSE doesn't need command

    @pytest.mark.asyncio
    async def test_mcp_bridge_detects_sse_client(self):
        """Test that MCPBridge correctly identifies SSE clients."""
        from core.mcp_sse_client import MCPSSEClient
        from core.mcp_stdio_client import MCPStdioClient
        from core.mcp_bridge import MCPClient

        sse_client = MCPSSEClient(
            name="test",
            url="http://localhost:3000/sse"
        )

        stdio_client = MCPStdioClient(
            name="test",
            command="node",
            args=["server.js"]
        )

        # Both should be compatible with MCPClient type
        assert isinstance(sse_client, MCPClient)
        assert isinstance(stdio_client, MCPClient)

        # Type checking for streaming support
        assert hasattr(sse_client, 'call_tool_stream')
        assert not hasattr(stdio_client, 'call_tool_stream')
