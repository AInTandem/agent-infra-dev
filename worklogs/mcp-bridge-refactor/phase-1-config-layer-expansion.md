# Phase 1: Configuration Layer Expansion - Work Report

## Date
2026-01-12

## Overview
Extended the configuration layer to support MCP capability detection and function call wrapper configuration.

## Changes Made

### 1. LLMProviderConfig Updates (`src/core/config.py`)
- Added `supports_mcp` field to indicate whether provider has native MCP support
- Default value: `false` (conservative approach)

```python
supports_mcp: bool = Field(
    default=False,
    description="Whether this provider has native MCP support"
)
```

### 2. LLMModelConfig Updates (`src/core/config.py`)
- Added `supports_mcp` field (Optional[bool]) to override provider setting
- `None` = use provider setting (default)
- `true/false` = explicit override

```python
supports_mcp: Optional[bool] = Field(
    default=None,
    description="Override provider's MCP support setting. None = use provider setting."
)
```

### 3. LLMConfig Updates (`src/core/config.py`)
- Added `get_model_mcp_support(model_name: str) -> bool` method
- Checks model config first, then falls back to provider config
- Returns `False` if model not found (with warning)

```python
def get_model_mcp_support(self, model_name: str) -> bool:
    """Check if a model supports native MCP."""
    # Implementation prioritizes model-level override, then provider setting
```

### 4. MCPServerConfig Updates (`src/core/config.py`)
- Added `function_call_wrapper` field
- Default value: `false` (native MCP is the default/preferred mode)

```python
function_call_wrapper: bool = Field(
    default=False,
    description="Enable function call wrapper for models without native MCP support"
)
```

### 5. Configuration Validation Function (`src/core/config.py`)
- Added `validate_agent_mcp_compatibility()` function
- Validates that LLM-MCP combinations are compatible
- Raises `ValueError` for incompatible combinations
- Logs informational messages for suboptimal (but valid) combinations

```python
def validate_agent_mcp_compatibility(
    agent_config: AgentConfig,
    llm_config: LLMConfig,
    mcp_configs: Dict[str, MCPServerConfig]
) -> None:
    """Validate that agent's LLM can use its configured MCP servers."""
```

### 6. Test Updates (`tests/test_config.py`)
- Updated `test_config_manager()` to use new LLMConfig structure
- Changed from `llm_cfg.provider` to `llm_cfg.providers` (dict)
- Removed dependency on "web-search" MCP server (may not be configured)

## Testing Results

### Syntax Check
```bash
python3 -m py_compile src/core/config.py
✓ Syntax check passed
```

### Unit Tests
```bash
PYTHONPATH=/path/to/src python3 -m pytest tests/test_config.py -v
============================== 2 passed in 2.14s ===============================
```

Both tests passed:
1. `test_env_substitution` - Environment variable substitution
2. `test_config_manager` - Configuration manager loading

## Validation Logic

### Valid Combinations
1. **Native MCP Model + Native MCP Server** ✓
   - `supports_mcp: true` + `function_call_wrapper: false`
   - Optimal: Direct MCP connection

2. **Non-MCP Model + Wrapped MCP Server** ✓
   - `supports_mcp: false` + `function_call_wrapper: true`
   - Valid: Tools converted to function call format

### Invalid Combinations (Raises Error)
1. **Non-MCP Model + Native MCP Server** ✗
   - `supports_mcp: false` + `function_call_wrapper: false`
   - Error: Model cannot use native MCP

### Warning (Informational)
1. **Native MCP Model + Wrapped MCP Server** ⚠
   - `supports_mcp: true` + `function_call_wrapper: true`
   - Warning: Unnecessary overhead (works but not optimal)

## Configuration File Structure

### Example LLM Configuration (`config/llm.yaml`)
```yaml
providers:
  claude:
    api_key: "${ANTHROPIC_API_KEY}"
    base_url: https://api.anthropic.com/v1
    supports_mcp: true  # Native MCP support

  deepseek:
    api_key: "${DEEPSEEK_API_KEY}"
    base_url: https://api.deepseek.com/v1
    supports_mcp: false  # No native MCP

models:
  - name: claude-3-5-sonnet-20241022
    provider: claude
    supports_mcp: true  # Explicit (can also rely on provider)

  - name: deepseek-chat
    provider: deepseek
    # supports_mcp: null - uses provider setting (false)
```

### Example MCP Server Configuration (`config/mcp_servers.yaml`)
```yaml
mcp_servers:
  - name: "filesystem"
    transport: "stdio"
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    function_call_wrapper: false  # Default: native MCP only

  - name: "github"
    transport: "stdio"
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    function_call_wrapper: true  # Enable for non-MCP models
```

## Next Steps

Phase 1 is complete. Ready to proceed to:
- **Phase 2**: MCP Bridge Refactoring
  - Create `MCPDirectPassage` class for native MCP
  - Refactor existing `MCPBridge` to `MCPFunctionCallWrapper`
  - Create unified `MCPManager`

## Notes

- All configuration changes are backward compatible (new fields have defaults)
- The validation logic is strict: incompatible combinations will raise errors
- No migration needed since project is not yet released
