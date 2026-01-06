# Qwen Agent MCP Scheduler 實作計劃

## 專案概述

使用 Qwen Agent SDK 打造本地端智能體基礎設施，支援 MCP Servers 整合、任務排程，並提供 Gradio GUI 介面。

### 核心需求
1. 在沙盒環境執行
2. 客製化 Agent（角色提示詞、MCP servers）
3. OpenAI API compatible function calls 設定 Scheduled Tasks
4. 自動執行 Scheduled Tasks
5. Gradio GUI 使用者介面

### 技術棧
- **Qwen Agent SDK**: Agent 框架
- **MCP Python SDK**: MCP Server 連接
- **APScheduler**: 任務排程
- **Gradio**: Web GUI
- **FastAPI**: OpenAI-compatible API
- **Pydantic**: 配置驗證

## 專案架構

```
agent-infra/
├── config/                    # 配置檔案目錄
│   ├── agents.yaml           # Agent 定義
│   ├── llm.yaml              # LLM 配置
│   └── mcp_servers.yaml      # MCP servers 清單
├── src/
│   ├── __init__.py
│   ├── core/                  # 核心功能
│   │   ├── agent_manager.py  # Agent 管理器
│   │   ├── mcp_bridge.py     # MCP 橋接層
│   │   ├── scheduler.py      # 任務排程器
│   │   └── sandbox.py        # 沙盒環境
│   ├── api/                   # API 層
│   │   └── openapi_server.py # OpenAI-compatible API
│   ├── agents/                # Agent 實現
│   │   └── base_agent.py     # 基礎 Agent 類
│   └── gui/                   # Gradio 介面
│       └── app.py            # Gradio 應用
├── storage/                   # 本地儲存
│   ├── tasks/                # 任務定義
│   └── logs/                 # 執行日誌
├── tests/                     # 測試
├── requirements.txt
├── pyproject.toml
└── main.py
```

## 實作步驟

---

### Phase 1: 專案初始化

#### Step 1.1: 專案結構建立
**目標**: 建立完整的目錄結構和基本檔案

**驗收標準**:
- [ ] 所有目錄已建立 (config/, src/, storage/, tests/)
- [ ] requirements.txt 包含所有必要依賴
- [ ] pyproject.toml 設定完成
- [ ] 基本的 __init__.py 檔案已建立
- [ ] README.md 專案說明

**預期成果**:
```
agent-infra/
├── config/
├── src/
│   ├── core/
│   ├── api/
│   ├── agents/
│   └── gui/
├── storage/
│   ├── tasks/
│   └── logs/
├── tests/
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

#### Step 1.2: 依賴安裝與環境設定
**目標**: 安裝所有必要依賴並建立虛擬環境

**驗收標準**:
- [ ]虛擬環境已建立
- [ ] 所有依賴已安裝且無衝突
- [ ] Qwen Agent SDK 可正常 import
- [ ] MCP SDK 可正常 import
- [ ] APScheduler 可正常 import
- [ ] Gradio 可正常 import
- [ ] FastAPI 可正常 import

**必要依賴清單**:
```txt
# Core
qwen-agent
mcp
apscheduler
gradio
fastapi
uvicorn
pydantic
pydantic-settings
pyyaml

# Testing
pytest
pytest-asyncio
```

---

### Phase 2: 配置系統

#### Step 2.1: 配置檔案結構設計
**目標**: 建立配置檔案格式和載入機制

**驗收標準**:
- [ ] config/agents.yaml 定義完成
- [ ] config/llm.yaml 定義完成
- [ ] config/mcp_servers.yaml 定義完成
- [ ] 配置載入器實現完成
- [ ] 配置驗證功能實現（Pydantic models）

**配置範例**:

```yaml
# config/agents.yaml
agents:
  - name: "researcher"
    role: "研究助理"
    system_prompt: "你是一位專業的研究助理..."
    mcp_servers: ["filesystem", "web-search"]
    llm_model: "deepseek-chat"

# config/llm.yaml
llm:
  provider: "openai_compatible"
  base_url: "https://api.deepseek.com/v1"
  api_key: "${DEEPSEEK_API_KEY}"
  default_model: "deepseek-chat"

# config/mcp_servers.yaml
mcp_servers:
  - name: "filesystem"
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"]
    env: {}
    description: "檔案系統存取"
```

---

#### Step 2.2: 配置管理器實現
**目標**: 實現配置載入、驗證、環境變數替換

**驗收標準**:
- [ ] ConfigManager 類別實現
- [ ] 環境變數替換功能 (${VAR_NAME})
- [ ] 配置驗證功能
- [ ] 配置熱重載（可選）
- [ ] 單元測試通過

**API 設計**:
```python
class ConfigManager:
    def load_config(self, config_type: str) -> dict
    def get_agents(self) -> List[AgentConfig]
    def get_mcp_servers(self) -> List[MCPServerConfig]
    def get_llm_config(self) -> LLMConfig
    def reload(self)
```

---

### Phase 3: MCP Bridge 實現

#### Step 3.1: MCP Stdio Client
**目標**: 實現與 MCP Server 的 stdio 通訊

**驗收標準**:
- [ ] MCPStdioClient 類別實現
- [ ] 進程啟動與管理
- [ ] JSON-RPC 通訊實現
- [ ] Handshaking 流程實現
- [ ] 錯誤處理與重試機制
- [ ] 單元測試通過

**API 設計**:
```python
class MCPStdioClient:
    async def connect(self) -> None
    async def disconnect(self) -> None
    async def list_tools(self) -> List[Tool]
    async def call_tool(self, name: str, arguments: dict) -> Any
    async def list_resources(self) -> List[Resource]
    async def call_resource(self, uri: str) -> Any
    @property
    def is_connected(self) -> bool
```

---

#### Step 3.2: MCP Tools 轉換器
**目標**: 將 MCP tools 轉換為 Qwen Agent 可用格式

**驗收標準**:
- [ ] Tool 轉換器實現
- [ ] 參數格式轉換（JSON Schema → Python）
- [ ] 非同步執行支援
- [ ] 錯誤處理
- [ ] 單元測試通過

**轉換邏輯**:
```python
class MCPToolConverter:
    def convert_tool(self, mcp_tool: MCPTool, client: MCPStdioClient) -> dict
    def wrap_as_callable(self, tool: MCPTool, client: MCPStdioClient) -> Callable
    def convert_schema(self, json_schema: dict) -> dict
```

---

#### Step 3.3: MCP Bridge 整合
**目標**: 整合 MCP Client 和轉換器，提供統一介面

**驗收標準**:
- [ ] MCPBridge 類別實現
- [ ] 從配置載入所有 MCP servers
- [ ] 自動發現和轉換 tools
- [ ] 取得特定 Agent 的 tools
- [ ] 連接狀態管理
- [ ] 錯誤處理與日誌
- [ ] 整合測試通過

**API 設計**:
```python
class MCPBridge:
    async def load_servers(self, config: List[MCPServerConfig]) -> None
    async def connect_all(self) -> None
    async def disconnect_all(self) -> None
    def get_tools_for_agent(self, server_names: List[str]) -> List[Tool]
    def get_server_status(self) -> Dict[str, str]
```

---

### Phase 4: Agent Manager 實現

#### Step 4.1: 基礎 Agent 類別
**目標**: 建立繼承 Qwen Agent 的基礎類別

**驗收標準**:
- [ ] BaseAgent 類別實現（繼承 qwen-agent）
- [ ] 角色提示詞設定
- [ ] Tools 註冊機制
- [ ] 記憶管理（可選）
- [ ] 執行日誌記錄
- [ ] 單元測試通過

**API 設計**:
```python
class BaseAgent:
    def __init__(self, config: AgentConfig, tools: List[Tool], llm: Any)
    async def run(self, prompt: str) -> AgentResponse
    def set_system_prompt(self, prompt: str)
    def add_tool(self, tool: Tool)
    def get_history(self) -> List[Message]
    def clear_history(self)
```

---

#### Step 4.2: Agent Manager 實現
**目標**: 管理多個 Agent 實例

**驗收標準**:
- [ ] AgentManager 類別實現
- [ ] 從配置建立 Agent
- [ ] Agent 註冊與取得
- [ ] Agent 生命週期管理
- [ ] 動態新增/移除 Agent
- [ ] 整合測試通過

**API 設計**:
```python
class AgentManager:
    async def initialize(self, config: List[AgentConfig], mcp_bridge: MCPBridge) -> None
    def get_agent(self, name: str) -> BaseAgent
    def list_agents(self) -> List[str]
    async def create_agent(self, config: AgentConfig) -> BaseAgent
    async def remove_agent(self, name: str) -> None
```

---

### Phase 5: Task Scheduler 實現

#### Step 5.1: APScheduler 整合
**目標**: 使用 APScheduler 建立排程系統

**驗收標準**:
- [ ] TaskScheduler 類別實現
- [ ] Cron 排程支援
- [ ] Interval 排程支援
- [ ] 一次性任務支援
- [ ] 任務持久化（JSON/SQLite）
- [ ] 單元測試通過

**API 設計**:
```python
class TaskScheduler:
    async def start(self) -> None
    async def stop(self) -> None
    def schedule_task(self, task: ScheduledTask) -> str
    def cancel_task(self, task_id: str) -> bool
    def list_tasks(self) -> List[ScheduledTask]
    def get_task_status(self, task_id: str) -> str
```

---

#### Step 5.2: Scheduled Task 定義與執行
**目標**: 定義任務格式並實現執行邏輯

**驗收標準**:
- [ ] ScheduledTask 資料模型（Pydantic）
- [ ] 任務執行器實現
- [ ] Agent 呼叫整合
- [ ] 執行結果記錄
- [ ] 錯誤處理與重試
- [ ] 執行日誌記錄
- [ ] 整合測試通過

**資料模型**:
```python
class ScheduledTask(BaseModel):
    id: str
    agent_name: str
    task_prompt: str
    schedule_type: Literal["cron", "interval", "once"]
    schedule_value: str  # cron expression or seconds
    repeat: bool = False
    repeat_interval: Optional[str] = None
    enabled: bool = True
    created_at: datetime
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
```

---

### Phase 6: OpenAI-Compatible API

#### Step 6.1: FastAPI Server 設定
**目標**: 建立 FastAPI 伺服器

**驗收標準**:
- [ ] FastAPI 應用程式建立
- [ ] CORS 設定
- [ ] 中間件設定（日誌、錯誤處理）
- [ ] API 文檔自動生成
- [ ] 健康檢查端點

---

#### Step 6.2: Chat Completions API
**目標**: 實現 OpenAI-compatible chat completions 端點

**驗收標準**:
- [ ] POST /v1/chat/completions 端點實現
- [ ] OpenAI 請求/回應格式支援
- [ ] Stream/Non-stream 模式支援
- [ ] Function calling 支援
- [ ] Agent 選擇機制
- [ ] 整合測試通過

**API 規格**:
```python
@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest) -> ChatCompletionResponse
```

---

#### Step 6.3: Scheduled Task Functions
**目標**: 實現管理排程任務的 function calls

**驗收標準**:
- [ ] create_scheduled_task function 實現
- [ ] list_tasks function 實現
- [ ] cancel_task function 實現
- [ ] update_task function 實現
- [ ] Function schema 定義
- [ ] 整合測試通過

**Function Schema**:
```python
scheduled_task_functions = [
    {
        "name": "create_scheduled_task",
        "description": "建立一個定時執行的 Agent 任務",
        "parameters": {
            "type": "object",
            "properties": {
                "agent_name": {"type": "string"},
                "task_prompt": {"type": "string"},
                "schedule_time": {"type": "string"},
                "repeat": {"type": "boolean"},
                "repeat_interval": {"type": "string"}
            },
            "required": ["agent_name", "task_prompt", "schedule_time"]
        }
    },
    # ... 其他 functions
]
```

---

### Phase 7: Gradio GUI

#### Step 7.1: Gradio 基礎介面
**目標**: 建立 Gradio 基礎佈局

**驗收標準**:
- [ ] Gradio 應用程式建立
- [ ] Tab 佈局設計（Chat, Agents, Tasks, Settings）
- [ ] 主題設定
- [ ] 基礎組件配置

---

#### Step 7.2: Chat 介面實現
**目標**: 實現與 Agent 對話的介面

**驗收標準**:
- [ ] ChatInterface 組件實現
- [ ] Agent 選擇下拉選單
- [ ] 對話歷史顯示
- [ ] 即時回應顯示
- [ ] Markdown 渲染
- [ ] 清除歷史按鈕

---

#### Step 7.3: Agent 管理 UI
**目標**: 實現 Agent 管理介面

**驗收標準**:
- [ ] Agent 列表顯示
- [ ] Agent 配置編輯介面
- [ ] 新增/刪除 Agent 功能
- [ ] Agent 狀態顯示（可用 tools, MCP servers）

---

#### Step 7.4: Task 管理 UI
**目標**: 實現排程任務管理介面

**驗收標準**:
- [ ] 任務列表顯示
- [ ] 任務創建表單
- [ ] 任務編輯/刪除功能
- [ ] 任務狀態顯示（下次執行時間、執行歷史）
- [ ] 啟用/停用任務切換

---

#### Step 7.5: Settings UI
**目標**: 實現系統設定介面

**驗收標準**:
- [ ] LLM 配置編輯
- [ ] MCP Server 管理介面
- [ ] 系統日誌查看器
- [ ] 配置匯入/匯出

---

### Phase 8: 沙盒環境

#### Step 8.1: 基礎沙盒隔離
**目標**: 實現基礎的執行隔離

**驗收標準**:
- [ ] 沙盒執行器類別實現
- [ ] 資源目錄隔離
- [ ] 環境變數隔離
- [ ] 權限控制

---

#### Step 8.2: 進階沙盒功能（可選）
**目標**: 增強沙盒安全性

**驗收標準**:
- [ ] Docker 容器整合（可選）
- [ ] 資源限制（CPU, 記憶體）
- [ ] 網路存取控制
- [ ] 檔案系統存取控制

---

### Phase 9: 測試與文檔

#### Step 9.1: 測試覆蓋
**目標**: 完善測試覆蓋率

**驗收標準**:
- [x] 單元測試覆蓋率 > 80%
- [x] 整合測試完成
- [x] E2E 測試完成
- [x] 測試文檔完成

---

#### Step 9.2: 使用文檔
**目標**: 完善使用文檔

**驗收標準**:
- [x] README.md 更新
- [x] 安裝指南完成
- [x] 使用指南完成
- [x] API 文檔完成
- [x] 配置說明完成
- [x] 故障排除指南

---

### Phase 10: Docker 打包

#### Step 10.1: Dockerfile
**目標**: 建立 Docker 映像定義

**驗收標準**:
- [x] 多階段構建 Dockerfile
- [x] 非 root 用戶執行
- [x] 健康檢查配置
- [x] 優化的映像大小
- [x] 環境變數配置

---

#### Step 10.2: Docker Compose
**目標**: 建立服務編排配置

**驗收標準**:
- [x] docker-compose.yml 配置
- [x] 環境變數管理
- [x] 數據卷持久化
- [x] 網路配置
- [x] 可選服務 (Nginx, Redis, PostgreSQL)

---

#### Step 10.3: Docker 部署文檔
**目標**: 建立 Docker 部署指南

**驗收標準**:
- [x] DOCKER.md 部署指南
- [x] 構建和運行說明
- [x] 生產環境部署
- [x] 故障排除
- [x] CI/CD 整合範例

---

## 里程碑

| 里程碑 | 目標 | 預期驗收標準 | 狀態 |
|--------|------|-------------|------|
| M1: 專案初始化 | 可運行的骨架專案 | 依賴安裝完成，基本結構建立 | ✅ |
| M2: MCP 整合 | MCP Servers 可正常連接 | 可透過配置載入 MCP servers 並取得 tools | ✅ |
| M3: Agent 系統 | 可執行的 Agent | 可透過配置建立 Agent 並執行任務 | ✅ |
| M4: 排程系統 | 可運行的排程任務 | 可建立並執行排程任務 | ✅ |
| M5: API 層 | OpenAI-compatible API | 可透過 API 與 Agent 互動 | ✅ |
| M6: GUI | 完整的 Gradio 介面 | 可透過 GUI 管理系統 | ✅ |
| M7: 完成 | 生產就緒 | 測試通過，文檔完整 | ✅ |
| M8: Docker | 容器化部署 | 可透過 Docker 一鍵部署 | ✅ |

---

## 風險與緩解

| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| Qwen Agent SDK 不相容 | 高 | 使用 Adapter 模式包裝，必要时替換為其他框架 |
| MCP Server 連接問題 | 中 | 實現重試機制，提供詳細錯誤日誌 |
| APScheduler 效能問題 | 中 | 提供分佈式選項（Celery）作為替代 |
| 沙盒環境複雜度 | 中 | 先實現基礎隔離，進階功能作為可選 |

---

## 附錄

### 參考資料
- [Qwen Agent SDK 文檔](https://github.com/QwenLM/Qwen-Agent)
- [MCP Protocol 規範](https://modelcontextprotocol.io/)
- [APScheduler 文檔](https://apscheduler.readthedocs.io/)
- [Gradio 文檔](https://www.gradio.app/docs)

### 相關 Issue/PR
- (待填寫)
