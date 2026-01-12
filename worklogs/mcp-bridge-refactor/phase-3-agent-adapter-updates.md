# Phase 3: Agent Adapter Updates - Work Report

## Date
2026-01-12

## Overview
Updated agent adapters to support native MCP session integration for models with MCP support.

## Changes Made

### 1. IAgentAdapter Interface Update (`src/core/agent_adapter.py`)

Added new abstract method `use_mcp_session()`:

```python
@abstractmethod
async def use_mcp_session(self, session: Any) -> None:
    """
    Use MCP session directly (for native MCP models).

    This method is called by AgentManager for agents using models
    with native MCP support. The adapter should store the session
    and use it for tool execution instead of the function call format.

    Args:
        session: MCP ClientSession from mcp Python SDK (can be None if not available)

    Note:
        - For ClaudeAgentAdapter: Stores session for native MCP tool use
        - For QwenAgentAdapter: Logs warning (Qwen SDK doesn't support native MCP)
    """
    pass
```

### 2. ClaudeAgentAdapter Update (`src/core/claude_agent_adapter.py`)

**Added MCP session storage:**
```python
# In __init__
self._mcp_sessions: List[Any] = []
```

**Implemented `use_mcp_session()` method:**
```python
async def use_mcp_session(self, session: Any) -> None:
    """
    Store MCP session for native MCP tool use.

    This method is called by AgentManager for agents using models
    with native MCP support (Claude models).
    """
    if session is not None:
        self._mcp_sessions.append(session)
        logger.debug(
            f"[{self.name}] Added MCP session (total: {len(self._mcp_sessions)})"
        )
```

The Claude agent adapter:
- Stores MCP ClientSession instances in `_mcp_sessions` list
- These sessions can be used directly with Claude API for native MCP tool calling
- Multiple sessions can be stored (one per MCP server)

### 3. QwenAgentAdapter Update (`src/core/qwen_agent_adapter.py`)

**Implemented `use_mcp_session()` method:**
```python
async def use_mcp_session(self, session: Any) -> None:
    """
    Qwen Agent SDK does not support native MCP.

    This method is called by AgentManager but should not be used
    for Qwen-based agents. Tools should be provided via the
    function call wrapper instead.
    """
    logger.warning(
        f"[{self.name}] Qwen Agent SDK does not support native MCP. "
        f"Use MCPFunctionCallWrapper instead to provide tools in function call format."
    )
```

The Qwen agent adapter:
- Logs a warning when `use_mcp_session()` is called
- Clarifies that function call wrapper should be used instead
- Maintains backward compatibility (doesn't crash if method is called)

## Integration Flow

```
AgentManager._create_agent()
    │
    ├─> Get tools via MCPManager.get_tools_for_agent()
    │
    ├─> Create adapter via AgentAdapterFactory
    │
    └─> If model supports MCP:
            For each MCP server:
                session = await mcp_manager.get_mcp_session()
                await agent.use_mcp_session(session)
```

## Usage Example

```python
# In AgentManager._create_agent()

# 1. Get tools (function call format for non-MCP, or native for MCP)
tools = mcp_manager.get_tools_for_agent(agent_config, llm_config)

# 2. Create agent
agent = AgentAdapterFactory.create_adapter(
    config=agent_config,
    llm=llm,
    tools=tools,
    mcp_manager=mcp_manager
)

# 3. For native MCP models, pass sessions directly
if llm_config.get_model_mcp_support(agent_config.llm_model):
    for server_name in agent_config.mcp_servers:
        session = await mcp_manager.get_mcp_session(server_name, agent_config)
        if session:
            await agent.use_mcp_session(session)
```

## ClaudeAdapter Future Enhancement

The current implementation stores MCP sessions. Future enhancement in Phase 4
or later would be to actually USE these sessions in the `_run_via_anthropic()` method:

```python
# Future implementation in ClaudeAgentAdapter._run_via_anthropic()

if self._mcp_sessions:
    # Pass sessions directly to Claude API
    api_params["mcp_sessions"] = self._mcp_sessions
    # Or integrate with Claude SDK's native MCP support
```

For now, the sessions are stored and can be used when Anthropic's SDK
provides direct MCP session integration.

## Testing Results

### Syntax Checks
```bash
python3 -m py_compile src/core/agent_adapter.py ✓
python3 -m py_compile src/core/claude_agent_adapter.py ✓
python3 -m py_compile src/core/qwen_agent_adapter.py ✓
```

### Config Tests
```bash
pytest tests/test_config.py -v
============================== 2 passed in 3.48s ===============================
```

## Interface Compliance

Both adapters now fully implement the updated `IAgentAdapter` interface:

| Method | ClaudeAgentAdapter | QwenAgentAdapter |
|--------|-------------------|-------------------|
| `run_async()` | ✓ | ✓ |
| `run_with_reasoning()` | ✓ | ✓ |
| `run_with_reasoning_stream()` | ✓ | ✓ |
| `get_history()` | ✓ | ✓ |
| `clear_history()` | ✓ | ✓ |
| `get_stats()` | ✓ | ✓ |
| `get_sdk_type()` | ✓ | ✓ |
| `supports_computer_use` | ✓ | ✓ |
| `supports_extended_thinking` | ✓ | ✓ |
| `use_mcp_session()` | ✓ | ✓ (logs warning) |

## Next Steps

Phase 3 is complete. Ready to proceed to:
- **Phase 4**: AgentManager Integration
  - Update `AgentManager` to use `MCPManager` instead of `MCPBridge`
  - Call `use_mcp_session()` for native MCP models
  - Add configuration validation using `validate_agent_mcp_compatibility()`

## Notes

- The Claude adapter currently stores MCP sessions but doesn't yet use them in API calls
- Full integration with Claude's native MCP will require Anthropic SDK updates
- The Qwen adapter properly warns when native MCP is attempted
- All changes maintain backward compatibility with existing agents
