# Phase 3: MCP Bridge - 工作報告

**日期**: 2026-01-06
**階段**: Phase 3 - MCP Bridge
**狀態**: ✅ 完成

---

## 概述

本階段完成了 MCP (Model Context Protocol) Bridge 的實現，提供與 MCP Servers 的整合能力。

---

## 完成項目

### Step 3.1: MCP Stdio Client ✅

**驗收標準檢查**:
- [x] MCPStdioClient 類別實現
- [x] 進程啟動與管理
- [x] JSON-RPC 通訊實現
- [x] Handshaking 流程實現
- [x] 錯誤處理與重試機制
- [x] 單元測試通過

**實現功能**:
- 與 MCP Servers 的 stdio 通訊
- 非同步連接管理
- 背景任務保持連線活躍
- 連線狀態追蹤
- Server capabilities 檢測

**API 設計**:
```python
client = MCPStdioClient(name, command, args, env, cwd, timeout)
await client.connect()
await client.list_tools()
await client.call_tool(name, arguments)
await client.list_resources()
await client.read_resource(uri)
await client.disconnect()
```

---

### Step 3.2: MCP Tools 轉換器 ✅

**驗收標準檢查**:
- [x] MCPToolConverter 類別實現
- [x] Tool 轉換器實現
- [x] 參數格式轉換（JSON Schema → Python）
- [x] 非同步執行支援
- [x] 錯誤處理
- [x] 單元測試通過

**實現功能**:
- MCP tools → Qwen Agent 格式轉換
- MCP tools → OpenAI 格式轉換
- 多 MCP server 管理
- Tool wrapper 函數生成

**API 設計**:
```python
converter = MCPToolConverter(client)
converted = converter.convert_tool(tool_def)
qwen_format = converter.to_qwen_format(tool_def)
openai_format = converter.to_openai_format(tool_def)
```

---

### Step 3.3: MCP Bridge 整合 ✅

**驗收標準檢查**:
- [x] MCPBridge 類別實現
- [x] 從配置載入所有 MCP servers
- [x] 自動發現和轉換 tools
- [x] 取得特定 Agent 的 tools
- [x] 連接狀態管理
- [x] 錯誤處理與日誌
- [x] 整合測試通過

**實現功能**:
- 多 MCP server 管理與連接
- 自動工具發現與轉換
- Agent 工具分配
- Server 狀態監控
- 重連機制

**API 設計**:
```python
bridge = MCPBridge(config_manager)
await bridge.initialize()
tools = bridge.get_tools_for_agent(["filesystem", "web-search"])
all_tools = bridge.get_all_tools()
qwen_tools = bridge.get_qwen_tools()
openai_tools = bridge.get_openai_tools()
await bridge.disconnect_all()
```

---

## 技術挑戰與解決方案

### 挑戰 1: MCP SDK API 參數名稱

**問題**:
```
stdio_client() got an unexpected keyword argument 'server_params'
```

**原因**: MCP SDK 的 `stdio_client()` 函數參數名稱是 `server` 而非 `server_params`

**解決**:
```python
# 修正前
self._stdio_context = stdio_client(server_params=server_params)

# 修正後
self._stdio_context = stdio_client(server=server_params)
```

---

### 挑戰 2: Async Context Manager 管理

**問題**:
```
RuntimeError: Attempted to exit cancel scope in a different task than it was entered in
```

**原因**: MCP SDK 的 `stdio_client` 使用 `anyio.create_task_group()`，需要在同一個 async task 中進出

**解決**: 使用背景任務保持 stdio context 活躍
```python
async def _connect_and_initialize():
    async with stdio_ctx as (read_stream, write_stream):
        session = ClientSession(read_stream, write_stream)
        await session.initialize()
        self._session = session
        self._is_connected = True
        await self._should_stop.wait()

self._keep_alive_task = asyncio.create_task(_connect_and_initialize())
```

---

## 測試結果

```
============================================================
MCP Stdio Client API Tests
============================================================
✓ MCP Stdio Client API tests passed

============================================================
MCP Bridge Tests
============================================================
✓ API methods (empty state) tests passed
✓ Tool lookup tests passed
✓ Format conversion tests passed
```

**注意**: 實際 MCP server 連接可能需要：
- Node.js 和 npx 安裝
- API keys (如 BRAVE_API_KEY, GITHUB_TOKEN)
- 允許的檔案系統路徑

---

## 新增檔案

```
src/core/
├── mcp_stdio_client.py     # MCP Stdio Client 實現
├── mcp_tool_converter.py   # MCP Tools 轉換器
└── mcp_bridge.py           # MCP Bridge 整合

tests/
└── test_mcp_bridge.py      # MCP Bridge 測試
```

---

## 架構說明

### MCP 通訊流程

```
MCPBridge
    └── MCPStdioClient (per server)
        ├── Background Task (maintains stdio context)
        │   └── stdio_client context
        │       └── process (MCP server)
        └── ClientSession
            └── call_tool(), list_tools(), etc.
```

### 工具轉換流程

```
MCP Server Tool
    ↓ (MCPToolConverter)
Qwen Agent Tool / OpenAI Tool
    ├── name: str
    ├── description: str
    ├── parameters: JSON Schema
    └── function: async callable
```

---

## 下一步階段

**Phase 4: Agent Manager**
- 實現 BaseAgent 類別
- 實現 Agent Manager
- 整合 MCP Bridge 與 Agent 系統

---

## 附錄

### MCP Server 配置範例

```yaml
# config/mcp_servers.yaml
mcp_servers:
  - name: "filesystem"
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"]
    env: {}
    timeout: 30
    enabled: true
```

### 使用範例

```python
# 初始化 MCP Bridge
bridge = MCPBridge(config_manager)
await bridge.initialize()

# 取得特定 Agent 可用的 tools
tools = bridge.get_tools_for_agent(["filesystem", "web-search"])

# 呼叫工具
result = await bridge.call_tool("filesystem", "read_file", {"path": "/test.txt"})
```
