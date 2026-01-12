# MCP Bridge 重構計畫

## 背景

現代 LLM 發展趨勢顯示，越來越多模型原生支援 Model Context Protocol (MCP)：
- Claude 3.5 Sonnet+ (Anthropic)
- GPT-4o/GPT-4.1 (OpenAI)
- Gemini 2.0 (Google)

然而，我們目前的 MCP Bridge 設計是為了讓「不具備 MCP 處理能力的模型」能夠透過 function call 格式使用 MCP 工具。這對於早期模型或輕量模型仍然有用，但不應該是預設行為。

## 設計原則

1. **直接傳遞優先**：支援 MCP 的模型應直接與 MCP Server 溝通，避免中間轉換層
2. **向後相容**：保留 function call wrapper 功能給不支援 MCP 的模型
3. **配置驅動**：透過配置控制行為，而非硬編碼
4. **清晰契約**：明確定義哪些 LLM 可以調用哪些 MCP Server

## 架構變更

### 當前架構

```
┌─────────────────────────────────────────────────────────────────────┐
│                     AgentManager                                    │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        MCP Bridge                                   │
│  • MCPStdioClient/MCPSSEClient (自實現)                             │
│  • MultiMCPToolConverter (轉換成 function call)                     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│              QwenAgentAdapter / ClaudeAgentAdapter                  │
│  所有 SDK 都接收 function call 格式                                 │
└─────────────────────────────────────────────────────────────────────┘
```

### 目標架構

```
┌─────────────────────────────────────────────────────────────────────┐
│                     AgentManager                                    │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                ┌──────────┴──────────┐
                ▼                     ▼
┌───────────────────────────┐  ┌───────────────────────────────────┐
│   MCPDirectPassage        │  │   MCPFunctionCallWrapper          │
│   (原生 MCP 支援)          │  │   (function call 包裝)            │
└───────────┬───────────────┘  └───────────────┬───────────────────┘
            │                                  │
            ▼                                  ▼
┌───────────────────────┐          ┌───────────────────────────────────┐
│ ClaudeAgentAdapter    │          │ QwenAgentAdapter                  │
│ GPTAgentAdapter       │          │ 其他不支援 MCP 的模型             │
│ GeminiAgentAdapter    │          │                                   │
└───────────────────────┘          └───────────────────────────────────┘
```

## 配置結構

### LLM 配置 (`config/llm.yaml`)

新增 `supports_mcp` 欄位：

```yaml
providers:
  claude:
    api_key: "${ANTHROPIC_API_KEY}"
    base_url: https://api.anthropic.com/v1
    supports_mcp: true  # 原生支援 MCP

  openai:
    api_key: "${OPENAI_API_KEY}"
    base_url: https://api.openai.com/v1
    supports_mcp: true  # GPT-4.1+ 支援 MCP

  deepseek:
    api_key: "${DEEPSEEK_API_KEY}"
    base_url: https://api.deepseek.com/v1
    supports_mcp: false  # 需要透過 function call

models:
  - name: claude-3-5-sonnet-20241022
    provider: claude
    max_tokens: 200000
    supports_function_calling: true
    supports_mcp: true  # 覆蓋 provider 設定

  - name: gpt-4o
    provider: openai
    max_tokens: 128000
    supports_function_calling: true
    supports_mcp: true

  - name: deepseek-chat
    provider: deepseek
    max_tokens: 128000
    supports_function_calling: true
    supports_mcp: false
```

### MCP Server 配置 (`config/mcp_servers.yaml`)

新增 `function_call_wrapper` 欄位：

```yaml
mcp_servers:
  - name: "filesystem"
    transport: "stdio"
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    function_call_wrapper: false  # 預設關閉，只給原生 MCP 模型用
    enabled: true

  - name: "github"
    transport: "stdio"
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-github"]
    function_call_wrapper: true  # 開啟包裝，給不支援 MCP 的模型用
    enabled: false

  - name: "postgres"
    transport: "stdio"
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-postgres", "postgresql://..."]
    function_call_wrapper: true  # 開啟包裝
    enabled: false
```

### Agent 配置驗證規則

```yaml
# 有效的配置組合：

# 案例 1: 原生 MCP 模型 + 原生 MCP Server
- name: "claude_agent"
  llm_model: "claude-3-5-sonnet-20241022"  # supports_mcp: true
  mcp_servers: ["filesystem"]              # function_call_wrapper: false

# 案例 2: 不支援 MCP 的模型 + function call wrapper
- name: "legacy_agent"
  llm_model: "deepseek-chat"               # supports_mcp: false
  mcp_servers: ["github"]                  # function_call_wrapper: true

# 無效的配置組合（應該拋出錯誤）：

# ❌ 錯誤: 不支援 MCP 的模型嘗試使用原生 MCP Server
- name: "invalid_agent"
  llm_model: "deepseek-chat"               # supports_mcp: false
  mcp_servers: ["filesystem"]              # function_call_wrapper: false
  # 錯誤: Model 'deepseek-chat' does not support MCP, but 'filesystem' server
  #       does not have function_call_wrapper enabled
```

## 實現步驟

### Phase 1: 配置層擴展

**目標**: 擴展配置結構以支援新的欄位

1. **更新 LLM 配置模型** (`src/core/config.py`)
   ```python
   class LLMProviderConfig(BaseModel):
       # ... 現有欄位 ...
       supports_mcp: bool = Field(
           default=False,
           description="Whether this provider has native MCP support"
       )

   class LLMModelConfig(BaseModel):
       # ... 現有欄位 ...
       supports_mcp: Optional[bool] = Field(
           default=None,
           description="Override provider's MCP support setting"
       )
   ```

2. **更新 MCP Server 配置模型** (`src/core/config.py`)
   ```python
   class MCPServerConfig(BaseModel):
       # ... 現有欄位 ...
       function_call_wrapper: bool = Field(
           default=False,
           description="Enable function call wrapper for non-MCP models"
       )
   ```

3. **新增配置驗證邏輯**
   ```python
   def validate_agent_mcp_compatibility(
       agent_config: AgentConfig,
       llm_config: LLMConfig,
       mcp_configs: Dict[str, MCPServerConfig]
   ) -> None:
       """Validate that agent's LLM can use its configured MCP servers."""

       # Check if LLM supports MCP
       llm_supports_mcp = llm_config.get_model_mcp_support(agent_config.llm_model)

       for server_name in agent_config.mcp_servers:
           server = mcp_configs.get(server_name)
           if not server:
               continue

           # Native MCP model requires wrapper to be disabled
           if llm_supports_mcp and server.function_call_wrapper:
               logger.warning(
                   f"[{agent_config.name}] Model {agent_config.llm_model} has native "
                   f"MCP support, but {server_name} has function_call_wrapper enabled. "
                   f"This may cause unnecessary overhead."
               )

           # Non-MCP model requires wrapper to be enabled
           if not llm_supports_mcp and not server.function_call_wrapper:
               raise ValueError(
                   f"[{agent_config.name}] Model {agent_config.llm_model} does not "
                   f"support MCP, but {server_name} does not have function_call_wrapper "
                   f"enabled. Either enable function_call_wrapper for {server_name} or "
                   f"use a different MCP server/model."
               )
   ```

### Phase 2: MCP Bridge 重構

**目標**: 將 MCP Bridge 拆分為直接傳遞和包裝兩種模式

1. **創建 MCP Direct Passage 模組**
   ```python
   # src/core/mcp_direct_passage.py
   from mcp import ClientSession, StdioServerParameters
   from mcp.client.stdio import stdio_client
   from mcp.client.sse import sse_client

   class MCPDirectPassage:
       """
       Direct MCP connection for models with native MCP support.

       This passes MCP sessions directly to the agent adapter without
       converting tools to function call format.
       """

       def __init__(self, config_manager: ConfigManager):
           self.config_manager = config_manager
           self._sessions: Dict[str, ClientSession] = {}

       async def get_session(self, server_name: str) -> ClientSession:
           """Get or create MCP ClientSession for a server."""
           if server_name in self._sessions:
               return self._sessions[server_name]

           config = self.config_manager.get_mcp_server(server_name)
           if not config:
               raise ValueError(f"MCP server {server_name} not found")

           # Create session based on transport
           if config.transport == "sse":
               # SSE transport
               async with sse_client(config.sse.url) as (read, write):
                   session = ClientSession(read, write)
                   await session.initialize()
                   self._sessions[server_name] = session
                   return session
           else:
               # Stdio transport
               params = StdioServerParameters(
                   command=config.command,
                   args=config.args,
                   env=config.env,
               )
               async with stdio_client(params) as (read, write):
                   session = ClientSession(read, write)
                   await session.initialize()
                   self._sessions[server_name] = session
                   return session

       async def list_tools(self, server_name: str) -> List[Tool]:
           """List tools from MCP server (in native MCP format)."""
           session = await self.get_session(server_name)
           result = await session.list_tools()
           return result.tools

       async def call_tool(
           self,
           server_name: str,
           tool_name: str,
           arguments: Dict[str, Any]
       ) -> CallToolResult:
           """Call tool on MCP server."""
           session = await self.get_session(server_name)
           return await session.call_tool(tool_name, arguments)
   ```

2. **重構現有 MCPBridge 為 Function Call Wrapper**
   ```python
   # src/core/mcp_function_wrapper.py
   class MCPFunctionCallWrapper:
       """
       Function call wrapper for models without native MCP support.

       Converts MCP tools to OpenAI-compatible function call format.
       """

       def __init__(self, config_manager: ConfigManager):
           self.config_manager = config_manager
           self._clients: Dict[str, MCPClient] = {}
           self._converter = MultiMCPToolConverter()

       # 將現有 MCPBridge 的邏輯移到這裡
       # ...
   ```

3. **創建統一的 MCP Manager**
   ```python
   # src/core/mcp_manager.py
   class MCPManager:
       """
       Unified MCP manager that routes to appropriate implementation.

       Routes agents to either:
       - MCPDirectPassage (for models with native MCP support)
       - MCPFunctionCallWrapper (for models without MCP support)
       """

       def __init__(self, config_manager: ConfigManager):
           self.config_manager = config_manager
           self._direct_passage = MCPDirectPassage(config_manager)
           self._function_wrapper = MCPFunctionCallWrapper(config_manager)

       def get_tools_for_agent(
           self,
           agent_config: AgentConfig,
           llm_config: LLMConfig
       ) -> Union[List[Tool], List[Dict[str, Any]]]:
           """
           Get tools for an agent in the appropriate format.

           Returns:
               - List[Tool] for native MCP models
               - List[Dict] (function call format) for non-MCP models
           """
           llm_supports_mcp = llm_config.get_model_mcp_support(agent_config.llm_model)

           if llm_supports_mcp:
               # Return tools in native MCP format
               return self._get_native_tools(agent_config.mcp_servers)
           else:
               # Return tools in function call format
               return self._function_wrapper.get_openai_tools(agent_config.mcp_servers)

       def get_mcp_session(
           self,
           server_name: str,
           agent_config: AgentConfig
       ) -> Union[ClientSession, None]:
           """
           Get MCP session for an agent.

           Only returns a session for agents with native MCP support.
           """
           llm_supports_mcp = self.config_manager.llm.get_model_mcp_support(
               agent_config.llm_model
           )

           if llm_supports_mcp:
               return await self._direct_passage.get_session(server_name)
           return None
   ```

### Phase 3: Agent Adapter 更新

**目標**: 更新各個 Agent Adapter 以支援直接 MCP 傳遞

1. **更新 IAgentAdapter 介面**
   ```python
   # src/core/agent_adapter.py
   class IAgentAdapter(ABC):
       # ... 現有方法 ...

       @abstractmethod
       async def use_mcp_session(
           self,
           session: ClientSession,
       ) -> None:
           """
           Use MCP session directly (for native MCP models).

           Args:
               session: MCP ClientSession from mcp Python SDK
           """
           pass
   ```

2. **更新 ClaudeAgentAdapter**
   ```python
   # src/core/claude_agent_adapter.py
   class ClaudeAgentAdapter(IAgentAdapter):
       def __init__(self, ...):
           # ...
           self._mcp_sessions: List[ClientSession] = []

       async def use_mcp_session(self, session: ClientSession) -> None:
           """Store MCP session for direct use."""
           self._mcp_sessions.append(session)

       async def _run_via_anthropic(self, messages, tools, **kwargs):
           """Run using native Anthropic client with MCP."""
           # Build API parameters
           api_params = {
               "model": self._config.llm_model,
               "messages": messages,
               "max_tokens": kwargs.get('max_tokens', 8192),
           }

           # Use MCP sessions directly if available
           if self._mcp_sessions:
               # Claude API can accept MCP sessions directly
               # (implementation depends on Anthropic SDK)
               api_params["mcp_sessions"] = self._mcp_sessions
           elif tools:
               # Fall back to tool definitions
               api_params["tools"] = tools

           response = await asyncio.to_thread(
               self._client.messages.create,
               **api_params
           )
           # ...
   ```

3. **更新 QwenAgentAdapter**
   ```python
   # src/core/qwen_agent_adapter.py
   class QwenAgentAdapter(IAgentAdapter):
       async def use_mcp_session(self, session: ClientSession) -> None:
           """
           Qwen Agent SDK does not support native MCP.

           This method should not be called. Tools should be provided
           in function call format via MCPFunctionCallWrapper.
           """
           logger.warning(
               f"[{self.name}] Qwen Agent SDK does not support native MCP. "
               f"Use MCPFunctionCallWrapper instead."
           )
   ```

### Phase 4: AgentManager 整合

**目標**: 更新 AgentManager 以使用新的 MCPManager

```python
# src/core/agent_manager.py
class AgentManager:
    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        mcp_manager: Optional[MCPManager] = None,  # Changed from MCPBridge
        cache_adapter: Optional[Any] = None,
    ):
        self.config_manager = config_manager or ConfigManager()
        self.mcp_manager = mcp_manager or MCPManager(self.config_manager)
        self.cache_adapter = cache_adapter
        # ...

    async def _create_agent(self, config: AgentConfig) -> IAgentAdapter:
        """Create an agent with appropriate MCP integration."""
        # Validate agent-MCP compatibility
        validate_agent_mcp_compatibility(
            config,
            self.config_manager.llm,
            self.config_manager.get_enabled_mcp_servers()
        )

        # Get tools in appropriate format
        tools = self.mcp_manager.get_tools_for_agent(
            config,
            self.config_manager.llm
        )

        # Get LLM instance
        llm = self._get_llm_for_agent(config)

        # Create agent via factory
        agent = AgentAdapterFactory.create_adapter(
            config=config,
            llm=llm,
            tools=tools,
            mcp_manager=self.mcp_manager  # Pass manager instead of bridge
        )

        # For native MCP models, pass sessions directly
        if self.config_manager.llm.get_model_mcp_support(config.llm_model):
            for server_name in config.mcp_servers:
                session = await self.mcp_manager.get_mcp_session(
                    server_name, config
                )
                if session:
                    await agent.use_mcp_session(session)

        return agent
```

### Phase 5: 配置驗證強化

**目標**: 確保配置明確且正確

1. **簡化的預設值**
   - `supports_mcp` 預設為 `false`
   - `function_call_wrapper` 預設為 `false`

2. **嚴格的驗證規則**
   - 不支援 MCP 的模型 + 未開啟 wrapper 的 Server = **直接錯誤**
   - 無需警告或降級處理

3. **清晰的錯誤訊息**
   ```python
   raise ValueError(
       f"Configuration error: Model '{agent_config.llm_model}' does not support MCP, "
       f"but server '{server_name}' does not have function_call_wrapper enabled. "
       f"Either set function_call_wrapper: true for '{server_name}' or use a "
       f"model with native MCP support."
   )
   ```

### Phase 6: 測試與文件

**目標**: 確保正確性和可用性

1. **單元測試**
   ```python
   # tests/test_mcp_manager.py
   def test_native_mcp_model_gets_native_tools():
       """Native MCP models get Tool objects."""
       ...

   def test_function_call_model_gets_wrapped_tools():
       """Non-MCP models get function call format."""
       ...

   def test_invalid_configuration_raises_error():
       """Invalid LLM-MCP combinations raise errors."""
       ...
   ```

2. **整合測試**
   ```python
   # tests/test_mcp_integration.py
   async def test_claude_with_native_mcp():
       """Test Claude agent with native MCP tools."""
       ...

   async def test_qwen_with_wrapped_mcp():
       """Test Qwen agent with function call wrapped tools."""
       ...
   ```

3. **文件更新**
   - 更新 `docs/DUAL_SDK_ARCHITECTURE.md`
   - 新增 `docs/MCP_INTEGRATION.md`
   - 更新 README.md 中的 MCP 說明

## 向後相容性

由於專案尚未對外發布，**不考慮向後相容性**。

直接採用新的配置格式：
- `supports_mcp` 預設為 `false`（需手動標記支援的模型）
- `function_call_wrapper` 預設為 `false`（預設使用原生 MCP）
- 無效的 LLM-MCP 組合直接拋出錯誤，無需警告

## 實現時程

| Phase | 任務 | 預計工作量 |
|-------|------|-----------|
| 1 | 配置層擴展 | 1-2 天 |
| 2 | MCP Bridge 重構 | 4-5 天 |
| 3 | Agent Adapter 更新 | 2-3 天 |
| 4 | AgentManager 整合 | 1-2 天 |
| 5 | 配置驗證強化 | 1 天 |
| 6 | 測試與文件 | 2-3 天 |

**總計**: 約 2 週（移除向後相容考量後大幅縮短）

## 依賴項

1. **外部套件**
   ```bash
   pip install mcp  # 官方 MCP Python SDK
   ```

2. **測試依賴**
   - 需要實際的 MCP Server 進行整合測試
   - 可以使用 `@modelcontextprotocol/server-filesystem` 作為測試目標

## 風險與緩解

| 風險 | 影響 | 緩解措施 |
|------|------|----------|
| Anthropic SDK MCP 整合方式變更 | 高 | 持續追蹤官方文件，保持彈性 |
| MCP SDK 本身的 bug | 中 | 使用穩定版本，有錯誤處理 |
| 配置複雜度增加 | 低 | 清晰的錯誤訊息和完整文件 |

## 成功標準

1. ✅ 原生 MCP 模型可以直接使用 MCP session，無需轉換
2. ✅ 不支援 MCP 的模型可透過 function call wrapper 使用 MCP 工具
3. ✅ 配置驗證能夠阻擋無效的 LLM-MCP 組合（直接錯誤）
4. ✅ 文件完整說明兩種使用方式
5. ✅ 所有測試通過

## 未來擴展

1. **自動檢測**: 自動檢測模型是否支援 MCP，無需手動配置
2. **效能監控**: 比較直接傳遞 vs function call wrapper 的效能差異
3. **混合模式**: 同一個 agent 可以同時使用原生 MCP 和 wrapper
4. **快取優化**: 對於原生 MCP，優化 session 重用
