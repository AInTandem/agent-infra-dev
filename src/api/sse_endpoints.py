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
SSE endpoints for streaming MCP tool calls.

Provides Server-Sent Events endpoints for real-time streaming
of MCP tool execution results.
"""

import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field


# ============================================================================
# Request/Response Models
# ============================================================================

class StreamToolCallRequest(BaseModel):
    """Request model for streaming tool call."""
    server_name: str = Field(..., description="MCP server name")
    tool_name: str = Field(..., description="Tool name to call")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class StreamToolCallByFullNameRequest(BaseModel):
    """Request model for streaming tool call by full name."""
    full_tool_name: str = Field(..., description="Full tool name (e.g., 'server.tool')")


# ============================================================================
# Router
# ============================================================================

router = APIRouter(prefix="/sse", tags=["SSE"])

# Global MCP bridge reference (will be set during initialization)
_mcp_bridge = None


def set_mcp_bridge(bridge):
    """Set the global MCP bridge instance."""
    global _mcp_bridge
    _mcp_bridge = bridge


def get_mcp_bridge():
    """Get the global MCP bridge instance."""
    if _mcp_bridge is None:
        raise RuntimeError("MCP bridge not initialized")
    return _mcp_bridge


# ============================================================================
# SSE Endpoints
# ============================================================================


@router.post("/tools/call")
async def stream_tool_call(request: StreamToolCallRequest, http_request: Request):
    """
    Stream MCP tool call results via SSE.

    This endpoint provides real-time streaming of tool execution results
    using Server-Sent Events (SSE).

    **Request Format:**
    ```json
    {
        "server_name": "filesystem",
        "tool_name": "read_file",
        "arguments": {"path": "/path/to/file.txt"}
    }
    ```

    **Response Format (SSE):**
    Each event is sent as `data: {json}` with the following structure:
    ```json
    {
        "type": "chunk" | "error" | "done",
        "data": { ... },
        "timestamp": "2025-01-09T12:00:00Z"
    }
    ```

    **Note:** Streaming is only supported for MCP servers configured with
    SSE transport. Stdio-based servers will return an error.
    """
    from datetime import datetime
    import asyncio

    mcp_bridge = get_mcp_bridge()

    # Verify server exists and is connected
    if not mcp_bridge.is_server_connected(request.server_name):
        raise HTTPException(
            status_code=404,
            detail=f"MCP server '{request.server_name}' not connected"
        )

    async def event_generator():
        """Generate SSE events for tool call results."""
        try:
            # Send start event
            yield _format_sse_event({
                "type": "start",
                "server": request.server_name,
                "tool": request.tool_name,
                "timestamp": datetime.utcnow().isoformat()
            })

            # Stream tool call results
            chunk_count = 0
            async for chunk in mcp_bridge.call_tool_stream(
                request.server_name,
                request.tool_name,
                request.arguments
            ):
                # Check if client disconnected
                if await http_request.is_disconnected():
                    logger.info(f"[SSE] Client disconnected during tool call")
                    break

                chunk_count += 1
                yield _format_sse_event({
                    "type": "chunk",
                    "data": chunk,
                    "index": chunk_count,
                    "timestamp": datetime.utcnow().isoformat()
                })

            # Send completion event
            yield _format_sse_event({
                "type": "done",
                "total_chunks": chunk_count,
                "timestamp": datetime.utcnow().isoformat()
            })

        except TypeError as e:
            # Client doesn't support streaming
            yield _format_sse_event({
                "type": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"[SSE] Error streaming tool call: {e}")
            yield _format_sse_event({
                "type": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.post("/tools/call/by-name")
async def stream_tool_call_by_full_name(
    request: StreamToolCallByFullNameRequest,
    http_request: Request
):
    """
    Stream MCP tool call results via SSE using full tool name.

    Similar to `/sse/tools/call` but accepts full tool name in
    `server.tool` format.

    **Request Format:**
    ```json
    {
        "full_tool_name": "filesystem.read_file"
    }
    ```
    """
    from datetime import datetime

    mcp_bridge = get_mcp_bridge()

    # Parse full tool name
    parts = request.full_tool_name.split(".", 1)
    if len(parts) != 2:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tool name format: {request.full_tool_name}"
        )

    server_name, tool_name = parts

    # Verify server exists and is connected
    if not mcp_bridge.is_server_connected(server_name):
        raise HTTPException(
            status_code=404,
            detail=f"MCP server '{server_name}' not connected"
        )

    async def event_generator():
        """Generate SSE events for tool call results."""
        try:
            # Send start event
            yield _format_sse_event({
                "type": "start",
                "server": server_name,
                "tool": tool_name,
                "timestamp": datetime.utcnow().isoformat()
            })

            # Stream tool call results
            chunk_count = 0
            async for chunk in mcp_bridge.call_tool_stream(
                server_name,
                tool_name,
                {}
            ):
                # Check if client disconnected
                if await http_request.is_disconnected():
                    logger.info(f"[SSE] Client disconnected during tool call")
                    break

                chunk_count += 1
                yield _format_sse_event({
                    "type": "chunk",
                    "data": chunk,
                    "index": chunk_count,
                    "timestamp": datetime.utcnow().isoformat()
                })

            # Send completion event
            yield _format_sse_event({
                "type": "done",
                "total_chunks": chunk_count,
                "timestamp": datetime.utcnow().isoformat()
            })

        except TypeError as e:
            # Client doesn't support streaming
            yield _format_sse_event({
                "type": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"[SSE] Error streaming tool call: {e}")
            yield _format_sse_event({
                "type": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/tools")
async def list_tools():
    """
    List all available MCP tools with streaming support information.

    Returns a list of all tools from connected servers, indicating
    which ones support streaming (SSE transport).
    """
    mcp_bridge = get_mcp_bridge()

    tools = mcp_bridge.get_all_tools()
    server_status = mcp_bridge.get_server_status()

    # Enhance tool info with streaming capability
    enhanced_tools = []
    for tool in tools:
        tool_name = tool["name"]
        server_name = tool.get("server_name", "")

        # Check if server uses SSE transport
        supports_streaming = False
        if server_name in server_status:
            client = mcp_bridge._clients.get(server_name)
            if client:
                supports_streaming = hasattr(client, 'call_tool_stream')

        enhanced_tools.append({
            **tool,
            "supports_streaming": supports_streaming,
        })

    return {
        "object": "list",
        "data": enhanced_tools
    }


@router.get("/servers")
async def list_servers():
    """
    List all connected MCP servers with transport information.

    Returns server status including transport type (stdio/sse) and
    streaming capability.
    """
    mcp_bridge = get_mcp_bridge()

    server_status = mcp_bridge.get_server_status()

    enhanced_status = {}
    for name, status in server_status.items():
        client = mcp_bridge._clients.get(name)
        transport = "unknown"
        supports_streaming = False

        if client:
            if hasattr(client, 'url'):
                transport = "sse"
                supports_streaming = True
            else:
                transport = "stdio"

        enhanced_status[name] = {
            **status,
            "transport": transport,
            "supports_streaming": supports_streaming,
        }

    return {
        "object": "list",
        "data": enhanced_status
    }


# ============================================================================
# Utility Functions
# ============================================================================

def _format_sse_event(data: Dict[str, Any]) -> str:
    """
    Format data as an SSE event.

    Args:
        data: Event data to format

    Returns:
        Formatted SSE event string
    """
    json_str = json.dumps(data, ensure_ascii=False)
    return f"data: {json_str}\n\n"
