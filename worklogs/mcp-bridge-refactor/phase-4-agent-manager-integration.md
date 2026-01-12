# Phase 4: AgentManager Integration - Work Report

## Date
2026-01-12

## Overview
Updated AgentManager and main.py to use MCPManager instead of MCPBridge, enabling native MCP session support for models with MCP capability.

## Changes Made

### 1. AgentManager Update (`src/core/agent_manager.py`)

**Updated imports:**
```python
from core.config import AgentConfig, ConfigManager, validate_agent_mcp_compatibility
from core.mcp_manager import MCPManager
```

**Updated constructor:**
```python
def __init__(
    self,
    config_manager: Optional[ConfigManager] = None,
    mcp_manager: Optional[MCPManager] = None,  # Changed from mcp_bridge
    cache_adapter: Optional[Any] = None,
):
```

**Updated `_create_agent()` method:**

The key changes in `_create_agent()`:

1. **MCP Compatibility Validation:**
```python
# Validate agent-MCP compatibility if MCP servers are configured
if config.mcp_servers and self.mcp_manager:
    try:
        mcp_configs = {}
        for server_name in config.mcp_servers:
            server_config = self.config_manager.get_mcp_server(server_name)
            if server_config:
                mcp_configs[server_name] = server_config

        validate_agent_mcp_compatibility(config, llm_config, mcp_configs)
        logger.debug(f"[{config.name}] MCP compatibility validated")
    except ValueError as e:
        logger.error(f"[{config.name}] MCP compatibility check failed: {e}")
        raise
```

2. **Tool Retrieval via MCPManager:**
```python
# Get tools for this agent (format depends on LLM MCP support)
tools = []
if self.mcp_manager and config.mcp_servers:
    tools = self.mcp_manager.get_tools_for_agent(config, llm_config)
    logger.debug(f"[{config.name}] Loaded {len(tools)} tools from {config.mcp_servers}")
```

3. **Native MCP Session Passing:**
```python
# For native MCP models, pass MCP sessions directly to the agent
if config.mcp_servers and self.mcp_manager:
    llm_supports_mcp = llm_config.get_model_mcp_support(config.llm_model)
    if llm_supports_mcp:
        logger.debug(f"[{config.name}] LLM supports native MCP, passing sessions")
        for server_name in config.mcp_servers:
            session = await self.mcp_manager.get_mcp_session(server_name, config)
            if session:
                await agent.use_mcp_session(session)
                logger.debug(f"[{config.name}] Passed MCP session for '{server_name}'")
```

### 2. Main Entry Point Update (`main.py`)

**Updated imports:**
```python
from core.mcp_manager import MCPManager  # Changed from MCPBridge
```

**Updated Application class:**
```python
def __init__(self):
    """Initialize the application."""
    self.config_manager: ConfigManager = None
    self.mcp_manager: MCPManager = None  # Changed from mcp_bridge
    # ... rest of initialization
```

**Updated initialization:**
```python
# 3. Initialize MCP Manager
console.print("[dim]3/7. Initializing MCP Manager...[/dim]")
self.mcp_manager = MCPManager(self.config_manager)
await self.mcp_manager.initialize()
mcp_status = self.mcp_manager.get_status()
native_count = len(mcp_status["direct_passage"]["servers"])
wrapper_count = len(mcp_status["function_wrapper"]["servers"])
console.print(f"[green]✓[/green] MCP Manager initialized (native: {native_count}, wrapper: {wrapper_count})")

# 4. Initialize Agent Manager
console.print("[dim]4/7. Initializing Agent Manager...[/dim]")
self.agent_manager = AgentManager(
    config_manager=self.config_manager,
    mcp_manager=self.mcp_manager,  # Changed from mcp_bridge
    cache_adapter=self.cache_adapter,
)
await self.agent_manager.initialize(mcp_manager=self.mcp_manager)
```

## Integration Flow

```
Application.initialize()
    │
    ├─> Create MCPManager
    │
    ├─> Initialize MCPManager
    │       ├─> MCPDirectPassage.initialize()
    │       └─> MCPFunctionCallWrapper.initialize()
    │
    ├─> Create AgentManager with MCPManager
    │
    └─> Initialize AgentManager
            │
            └─> For each agent:
                    │
                    ├─> 1. Validate agent-MCP compatibility
                    │       validate_agent_mcp_compatibility()
                    │
                    ├─> 2. Get tools via MCPManager.get_tools_for_agent()
                    │       Routes based on LLM MCP support:
                    │       - Native MCP → MCPDirectPassage
                    │       - Non-MCP → MCPFunctionCallWrapper
                    │
                    ├─> 3. Create agent via AgentAdapterFactory
                    │
                    └─> 4. For native MCP models:
                            await agent.use_mcp_session(session)
```

## Architecture Changes

### Before (Phase 3):
```
AgentManager
    │
    ├─> MCPBridge.get_tools_for_agent()  # Only function call format
    │
    └─> AgentAdapterFactory.create_adapter(mcp_bridge=...)
```

### After (Phase 4):
```
AgentManager
    │
    ├─> MCPManager.get_tools_for_agent()  # Routes to native or wrapper
    │       ├─> MCPDirectPassage (for models with MCP support)
    │       └─> MCPFunctionCallWrapper (for models without MCP)
    │
    ├─> validate_agent_mcp_compatibility()  # New validation
    │
    ├─> AgentAdapterFactory.create_adapter(mcp_bridge=None)
    │
    └─> agent.use_mcp_session()  # For native MCP models
```

## Testing Results

### Syntax Checks
```bash
python3 -m py_compile src/core/agent_manager.py ✓
python3 -m py_compile src/core/claude_agent_adapter.py ✓
python3 -m py_compile src/core/qwen_agent_adapter.py ✓
python3 -m py_compile main.py ✓
python3 -m py_compile tests/test_mcp_manager.py ✓
```

### Import Tests
```bash
PYTHONPATH=/path/to/src python3 -c "from core.agent_manager import AgentManager, get_agent_manager"
✓ AgentManager imports OK
```

### Config Tests
```bash
pytest tests/test_config.py -v
============================== 2 passed in 3.48s ===============================
```

## Notes

### SSE Endpoints
The `api/sse_endpoints.py` and `api/openapi_server.py` continue to use `MCPBridge` for:
- Direct tool streaming (not agent-based)
- SSE-specific functionality

This is intentional as:
1. SSE endpoints are a separate feature from agent management
2. They use specific `MCPBridge` methods and internal state
3. Maintains backward compatibility for existing API users

Future enhancement could refactor SSE endpoints to also use `MCPManager`.

### AgentAdapterFactory
The `AgentAdapterFactory.create_adapter()` still accepts `mcp_bridge` parameter for backward compatibility, but AgentManager now passes `None` since MCP sessions are passed directly via `use_mcp_session()`.

### Configuration Validation
The new `validate_agent_mcp_compatibility()` function is called during agent creation to catch configuration errors early:
- Non-MCP models trying to use native-only MCP servers
- Native MCP models using function-call-only MCP servers

## Next Steps

Phase 4 is complete. Ready to proceed to:
- **Phase 5**: Configuration Validation Enhancement
  - Add more detailed validation rules
  - Improve error messages
  - Add validation tests

- **Phase 6**: Testing and Documentation
  - End-to-end integration tests
  - Update documentation
  - Create migration guide

## Files Modified

1. `src/core/agent_manager.py` - Updated to use MCPManager
2. `main.py` - Updated to use MCPManager instead of MCPBridge
