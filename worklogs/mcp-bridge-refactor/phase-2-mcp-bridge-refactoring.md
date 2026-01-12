# Phase 2: MCP Bridge Refactoring - Work Report

## Date
2026-01-12

## Overview
Refactored the MCP Bridge into two separate components:
1. **MCPDirectPassage** - For models with native MCP support
2. **MCPFunctionCallWrapper** - For models without native MCP support

Also created a unified **MCPManager** to route agents to the appropriate implementation.

## Changes Made

### 1. New Module: `src/core/mcp_direct_passage.py`

Created `MCPDirectPassage` class that uses the official `mcp` Python SDK:

```python
class MCPDirectPassage:
    """
    Direct MCP connection for models with native MCP support.

    Uses official mcp SDK's ClientSession for direct tool access.
    """
```

Key features:
- Uses official `mcp` Python SDK (v1.8.1)
- Creates `ClientSession` instances for native MCP models
- Only connects to servers with `function_call_wrapper: false`
- Supports stdio transport (SSE to be added later)
- Returns tools in native MCP format (`mcp.types.Tool`)

### 2. New Module: `src/core/mcp_function_wrapper.py`

Created `MCPFunctionCallWrapper` class based on existing `MCPBridge` logic:

```python
class MCPFunctionCallWrapper:
    """
    Function call wrapper for models without native MCP support.

    Converts MCP tools to OpenAI-compatible function call format.
    """
```

Key features:
- Uses existing `MCPStdioClient` and `MCPSSEClient` implementations
- Converts MCP tools to function call format via `MultiMCPToolConverter`
- Only connects to servers with `function_call_wrapper: true`
- Returns tools in OpenAI/Qwen function call format
- Maintains all existing `MCPBridge` functionality

### 3. New Module: `src/core/mcp_manager.py`

Created `MCPManager` unified routing class:

```python
class MCPManager:
    """
    Unified MCP manager that routes to appropriate implementation.
    """
```

Key methods:
- `get_tools_for_agent()` - Returns tools in correct format based on model
- `get_mcp_session()` - Returns ClientSession for native MCP models
- `get_function_call_tools()` - Returns function call format tools
- `call_tool()` - Executes tools via appropriate implementation
- `get_status()` - Returns status of both components

Routing logic:
```python
if llm_supports_mcp and not server.function_call_wrapper:
    # Use MCPDirectPassage
else:
    # Use MCPFunctionCallWrapper
```

### 4. New Tests: `tests/test_mcp_manager.py`

Created comprehensive tests for the new architecture:
- `test_mcp_manager()` - Tests unified manager
- `test_direct_passage()` - Tests native MCP connection
- `test_function_wrapper()` - Tests function call wrapper
- Configuration validation tests

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AgentManager                                │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        MCPManager                                  │
│  Routes based on: llm.get_model_mcp_support() + server config      │
└───────────────┬─────────────────────────────┬───────────────────────┘
                │                             │
        ┌───────┴────────┐           ┌────────┴────────┐
        ▼                 ▼           ▼                 ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  MCPDirectPassage│  │MCPFunctionCall   │  │  MCPDirectPassage│
│   (native MCP)   │  │Wrapper           │  │   (native MCP)   │
└──────────────────┘  └──────────────────┘  └──────────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ mcp SDK Client   │  │ MCPStdioClient   │  │ Claude SDK       │
│ Session          │  │ MCPSSEClient     │  │ (via session)    │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

## Component Comparison

| Feature | MCPDirectPassage | MCPFunctionCallWrapper |
|---------|------------------|------------------------|
| **Target Models** | Claude, GPT-4.1+ | DeepSeek, GLM, Qwen, etc. |
| **MCP SDK Used** | Official `mcp` package | Custom implementation |
| **Tool Format** | `mcp.types.Tool` | Dict (function call) |
| **Servers Used** | `function_call_wrapper: false` | `function_call_wrapper: true` |
| **Connection Type** | ClientSession | MCPStdioClient/MCPSSEClient |
| **Tool Execution** | Via `session.call_tool()` | Via `client.call_tool()` |

## Configuration Examples

### For Native MCP Models (Claude)
```yaml
# config/llm.yaml
providers:
  claude:
    supports_mcp: true

models:
  - name: claude-3-5-sonnet-20241022
    provider: claude
    supports_mcp: true

# config/mcp_servers.yaml
mcp_servers:
  - name: "filesystem"
    transport: "stdio"
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    function_call_wrapper: false  # Native MCP

# config/agents.yaml
agents:
  - name: "claude_agent"
    llm_model: "claude-3-5-sonnet-20241022"  # supports_mcp: true
    mcp_servers: ["filesystem"]              # function_call_wrapper: false
```

### For Non-MCP Models (DeepSeek)
```yaml
# config/llm.yaml
providers:
  deepseek:
    supports_mcp: false

models:
  - name: deepseek-chat
    provider: deepseek
    # supports_mcp: inherits from provider (false)

# config/mcp_servers.yaml
mcp_servers:
  - name: "github"
    transport: "stdio"
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    function_call_wrapper: true  # Enable wrapper

# config/agents.yaml
agents:
  - name: "deepseek_agent"
    llm_model: "deepseek-chat"              # supports_mcp: false
    mcp_servers: ["github"]                 # function_call_wrapper: true
```

## Testing Results

### Syntax Checks
```bash
python3 -m py_compile src/core/mcp_direct_passage.py ✓
python3 -m py_compile src/core/mcp_function_wrapper.py ✓
python3 -m py_compile src/core/mcp_manager.py ✓
python3 -m py_compile tests/test_mcp_manager.py ✓
```

### Config Tests
```bash
pytest tests/test_config.py -v
============================== 2 passed in 2.45s ===============================
```

## Dependencies

The new modules depend on:
- Official `mcp==1.8.1` package (already in requirements.txt)
- Existing `MCPStdioClient`, `MCPSSEClient`, `MultiMCPToolConverter`
- Configuration models from Phase 1

## Backward Compatibility

The original `MCPBridge` class remains unchanged in `src/core/mcp_bridge.py`.
This allows gradual migration:
- Phase 2: New modules created, old code still works
- Phase 4: Will update AgentManager to use MCPManager
- Future: Can deprecate old MCPBridge after migration is complete

## Next Steps

Phase 2 is complete. Ready to proceed to:
- **Phase 3**: Agent Adapter Updates
  - Add `use_mcp_session()` method to `IAgentAdapter`
  - Update `ClaudeAgentAdapter` to use ClientSession directly
  - Update `QwenAgentAdapter` to note it doesn't support native MCP

- **Phase 4**: AgentManager Integration
  - Update `AgentManager` to use `MCPManager` instead of `MCPBridge`
  - Add configuration validation using `validate_agent_mcp_compatibility()`

## Notes

- The `MCPDirectPassage` currently only supports stdio transport
- SSE transport support for native MCP can be added later
- Error handling for missing MCP SDK is in place (ImportError with clear message)
- Session lifecycle management needs to be handled in AgentManager integration
