# Dual SDK Architecture

This document describes the dual SDK architecture that allows agents to use either Qwen Agent SDK or Claude Agent SDK based on their requirements.

## Overview

The AInTandem Agent MCP Scheduler supports a **unified agent adapter interface** that abstracts away the differences between Qwen Agent SDK and Claude Agent SDK. This allows:

1. **Per-agent SDK selection** - Choose the best SDK for each agent
2. **Unified API** - Both SDKs implement the same `IAgentAdapter` interface
3. **Feature specialization** - Use Claude SDK for Computer Use, Qwen SDK for multi-LLM support

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AgentManager                            │
│  (Manages agent lifecycle, delegates creation to factory)        │
└───────────────────────────────────┬─────────────────────────────┘
                                    │
                                    ▼
                        ┌───────────────────────────────┐
                        │    AgentAdapterFactory      │
                        │  (Determines SDK to use)      │
                        └───────────────┬───────────────┘
                                        │
                            ┌───────────┴────────────┐
                            ▼                        ▼
                    ┌─────────────────┐    ┌─────────────────┐
                    │QwenAgentAdapter │    │ClaudeAgentAdapter│
                    │  (Qwen SDK)     │    │  (Claude SDK)    │
                    └────────┬────────┘    └────────┬────────┘
                             │                      │
                             ▼                      ▼
                    ┌─────────────────┐    ┌─────────────────┐
                    │   BaseAgent    │    │  Claude API     │
                    │  (existing)     │    │  (Anthropic)    │
                    └─────────────────┘    │  - Computer Use │
                                            │  - Extended     │
                                            │    Thinking     │
                                            └─────────────────┘
```

## Components

### 1. IAgentAdapter Interface

**File**: `src/core/agent_adapter.py`

The unified interface that all agent adapters must implement:

```python
class IAgentAdapter(ABC):
    async def run_async(prompt: str) -> List[Any]
    async def run_with_reasoning(prompt: str) -> List[ReasoningStep]
    async def run_with_reasoning_stream(prompt: str) -> AsyncIterator[ReasoningStep]
    def get_history() -> List[Dict[str, str]]
    def clear_history() -> None
    def get_stats() -> Dict[str, Any]
    def get_sdk_type() -> AgentSDKType
    @property
    def supports_computer_use() -> bool
    @property
    def supports_extended_thinking() -> bool
```

### 2. QwenAgentAdapter

**File**: `src/core/qwen_agent_adapter.py`

Wraps the existing `BaseAgent` class to conform to `IAgentAdapter`.

**Key Features**:
- Multi-LLM support (OpenAI, DeepSeek, GLM, etc.)
- MCP tool integration
- Backward compatible with existing agents

**When to Use**:
- Agents using non-Claude models
- Cost optimization (cheaper models)
- High-volume automated tasks

### 3. ClaudeAgentAdapter

**File**: `src/core/claude_agent_adapter.py`

Direct integration with Anthropic's Claude API.

**Key Features**:
- **Computer Use**: Direct browser/system control
- **Extended Thinking**: Deep reasoning before response
- Native tool calling with Claude's format
- MCP tool integration

**When to Use**:
- Web automation tasks
- Complex reasoning tasks
- Tasks requiring visual understanding
- Agents that need browser interaction

### 4. AgentAdapterFactory

**File**: `src/core/agent_adapter.py`

Factory that creates the appropriate adapter based on configuration:

```python
def create_adapter(config, llm, tools, mcp_bridge) -> IAgentAdapter:
    # SDK selection logic:
    # 1. Check config.sdk field
    # 2. Auto-detect from model name (if not specified)
    # 3. Override for Computer Use requirement
    pass
```

## Configuration

### Agent Configuration (`config/agents.yaml`)

```yaml
agents:
  # Qwen SDK agent (default)
  - name: "researcher"
    role: "研究助理"
    llm_model: "glm-4.7"
    sdk: "qwen"  # Optional - auto-detected
    mcp_servers: ["filesystem"]
    enabled: true

  # Claude SDK agent with Computer Use
  - name: "browser_assistant"
    role: "網頁操作助理"
    llm_model: "claude-3-5-sonnet-20241022"
    sdk: "claude"  # Required for Claude features
    computer_use_enabled: true
    extended_thinking_enabled: true
    mcp_servers: ["filesystem"]
    enabled: false
```

### LLM Configuration (`config/llm.yaml`)

Add Claude provider:

```yaml
providers:
  claude:
    api_key: "${ANTHROPIC_API_KEY}"
    base_url: https://api.anthropic.com/v1
    description: Anthropic Claude - Computer Use & Extended Thinking

models:
  - name: claude-3-5-sonnet-20241022
    provider: claude
    max_tokens: 200000
    supports_function_calling: true
    supports_streaming: true
```

## SDK Feature Matrix

| Feature | Qwen SDK | Claude SDK |
|---------|-----------|-------------|
| **Multi-LLM Support** | ✅ OpenAI, DeepSeek, GLM, Ollama, etc. | ❌ Claude models only |
| **Computer Use** | ❌ | ✅ Browser automation |
| **Extended Thinking** | ❌ | ✅ Deep reasoning |
| **MCP Integration** | ✅ Via MCPTool wrapper | ✅ Via tool conversion |
| **Function Calling** | ✅ OpenAI-compatible | ✅ Claude native format |
| **Streaming** | ✅ Via Qwen Agent | ✅ Via Anthropic client |
| **Response Caching** | ✅ Via AgentManager | ✅ Via AgentManager |
| **Tool Execution** | ✅ Async with threading | ✅ Async with asyncio |
| **Cost** | 💰 Low (free/cheap models) | 💸💸 High (premium) |

## Usage Examples

### Example 1: Mixed SDK Deployment

```yaml
agents:
  # Cost-effective research agent (Qwen SDK + GLM)
  - name: "researcher"
    llm_model: "glm-4-flash"
    sdk: "qwen"
    mcp_servers: ["filesystem", "web-search"]
    enabled: true

  # High-quality coding agent (Qwen SDK + DeepSeek)
  - name: "developer"
    llm_model: "deepseek-chat"
    sdk: "qwen"
    mcp_servers: ["filesystem", "github"]
    enabled: true

  # Browser automation agent (Claude SDK + Computer Use)
  - name: "browser_automation"
    llm_model: "claude-3-5-sonnet-20241022"
    sdk: "claude"
    computer_use_enabled: true
    mcp_servers: ["filesystem"]
    enabled: false
```

### Example 2: Auto-Detection

```yaml
# SDK is automatically detected from model name
agents:
  # Uses Qwen SDK (model name doesn't contain "claude")
  - name: "analyst"
    llm_model: "gpt-4"
    # sdk: auto-detected as "qwen"

  # Uses Claude SDK (model name contains "claude")
  - name: "reasoning_agent"
    llm_model: "claude-3-opus-20240229"
    # sdk: auto-detected as "claude"
    extended_thinking_enabled: true
```

### Example 3: Programmatic Usage

```python
from core.agent_manager import AgentManager
from core.config import ConfigManager

# Initialize
config_manager = ConfigManager()
agent_manager = AgentManager(config_manager)
await agent_manager.initialize()

# Use agent (SDK is transparent to caller)
agent = agent_manager.get_agent("browser_assistant")
response = await agent.run_async("Navigate to example.com and fill the form")

# Check agent capabilities
if agent.supports_computer_use:
    print("This agent can control the browser!")
```

## Implementation Details

### SDK Selection Logic

The `AgentAdapterFactory` uses this logic to determine SDK:

```python
def determine_sdk(config) -> AgentSDKType:
    # 1. Explicit SDK specification
    if config.sdk:
        return AgentSDKType(config.sdk)

    # 2. Auto-detect from model name
    if "claude" in config.llm_model.lower():
        return AgentSDKType.CLAUDE

    # 3. Default to Qwen
    return AgentSDKType.QWEN

    # 4. Override for Computer Use requirement
    if config.computer_use_enabled:
        return AgentSDKType.CLAUDE
```

### MCP Tool Integration

Both adapters support MCP tools, but with different implementations:

**QwenAgentAdapter**:
- Wraps MCP tools as `MCPTool(BaseTool)`
- Uses Qwen Agent's tool format
- Executes tools via threading (for async compatibility)

**ClaudeAgentAdapter**:
- Converts MCP tools to Claude tool format
- Uses Anthropic's tool schema
- Executes tools via asyncio

### Computer Use Implementation

The Claude SDK adapter includes placeholder Computer Use implementation:

```python
async def _execute_computer_use(self, tool_input: Dict[str, Any]) -> str:
    """
    Execute Computer Use action.

    TODO: Implement actual browser automation:
    - Using Puppeteer MCP server
    - Or Anthropic's Computer Use SDK
    - Or custom browser controller
    """
    action = tool_input.get("action", "")
    return f"Computer Use executed: {action}"
```

To enable actual Computer Use:

1. **Option A**: Use Puppeteer MCP server
2. **Option B**: Integrate Anthropic's Computer Use SDK
3. **Option C**: Build custom browser controller

## Migration Guide

### Migrating Existing Agents

Existing agents will continue to work without changes:

```yaml
# This still works - defaults to Qwen SDK
- name: "my_agent"
  llm_model: "glm-4.7"
  system_prompt: "..."
```

### Adding Claude SDK Support

1. Install the SDK:
   ```bash
   pip install anthropic
   ```

2. Configure API key:
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-...
   ```

3. Add Claude provider to `config/llm.yaml`

4. Create or modify agent:
   ```yaml
   - name: "claude_agent"
     llm_model: "claude-3-5-sonnet-20241022"
     sdk: "claude"
     extended_thinking_enabled: true
   ```

## Troubleshooting

### ImportError: anthropic package not installed

```bash
pip install anthropic
```

### ANTHROPIC_API_KEY not found

```bash
export ANTHROPIC_API_KEY=your_key_here
```

Or add to `.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
```

### Computer Use not working

1. Verify agent has `sdk: "claude"` and `computer_use_enabled: true`
2. Verify model supports Computer Use (claude-3-5-sonnet-20241022 or later)
3. Check logs for Computer Use implementation errors

### Wrong SDK being used

1. Check agent configuration
2. Verify `sdk` field is set correctly
3. Check logs for SDK type: `[agent_name] QWEN agent created` or `[agent_name] CLAUDE agent created`

## Future Enhancements

- [ ] Full Computer Use implementation with browser automation
- [ ] Extended Thinking visualization in GUI
- [ ] SDK-specific performance metrics
- [ ] Automatic SDK selection based on task type
- [ ] Claude Artifacts support in chat interface
- [ ] Tool execution timeout per SDK
