# Real-Time Streaming Reasoning Implementation Plan (WebSocket Architecture)

## 目標
實現真正的即時 streaming，在 LLM 生成每個 reasoning step 時立即顯示，使用 WebSocket push 機制。

## 當前問題分析

### 現狀
- `run_with_reasoning()` 使用 `run_nonstream()` API
- 等待整個 reasoning loop 完成後返回完整列表
- GUI 通過 HTTP 請求獲取結果，無法服務器推送
- 用戶體驗：初始有 "thinking..." 提示，但實際顯示仍然是一次性彈出

### 根本原因
1. **HTTP 請求-響應模式**：無法實現服務器推送
2. **批處理模式**：所有 reasoning steps 收集完後才返回
3. **缺乏持久連接**：每次交互都需要重新建立連接

## 技術方案：WebSocket Push

### 架構概覽

```
┌─────────────────┐         WebSocket          ┌─────────────────┐
│   Gradio GUI    │◄────────────────────────────►│   WebSocket     │
│  (Browser)      │      歡迎、推送 reasoning      │   Handler       │
│                 │                                │  (FastAPI)      │
└─────────────────┘                                └────────┬────────┘
                                                           │
                                                           │ Async Call
                                                           ▼
                                                   ┌─────────────────┐
                                                   │  Agent Manager  │
                                                   │                 │
                                                   └────────┬────────┘
                                                            │
                                                            │ Streaming Reasoning
                                                            ▼
                                                   ┌─────────────────┐
                                                   │   BaseAgent     │
                                                   │  run_with_      │
                                                   │  reasoning_     │
                                                   │  stream()       │
                                                   └─────────────────┘
```

### 核心組件設計

#### 1. WebSocket Manager
**文件**: `src/core/websocket_manager.py`

負責管理 WebSocket 連接和消息分發：

```python
from typing import Dict, Set
from fastapi import WebSocket
import asyncio
import json

class WebSocketManager:
    """管理 WebSocket 連接和消息廣播"""

    def __init__(self):
        # session_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # session_id -> message queue (用於離線消息)
        self.message_queues: Dict[str, asyncio.Queue] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """接受新的 WebSocket 連接"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.message_queues[session_id] = asyncio.Queue()

    async def disconnect(self, session_id: str):
        """斷開連接"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.message_queues:
            del self.message_queues[session_id]

    async def send_message(self, session_id: str, message: dict):
        """發送消息到特定客戶端"""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_json(message)
        else:
            # 連接不存在，存入隊列（可選）
            if session_id in self.message_queues:
                await self.message_queues[session_id].put(message)

    async def broadcast(self, message: dict):
        """廣播消息到所有連接的客戶端"""
        for websocket in self.active_connections.values():
            try:
                await websocket.send_json(message)
            except:
                pass

    def get_connection_count(self) -> int:
        """獲取當前連接數"""
        return len(self.active_connections)
```

#### 2. WebSocket API Endpoints
**文件**: `src/api/websocket_endpoints.py`

定義 WebSocket 路由和處理邏輯：

```python
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

router = APIRouter(prefix="/ws", tags=["websocket"])

# Global WebSocket manager
ws_manager = WebSocketManager()

@router.websocket("/chat/{session_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket,
    session_id: str,
    agent_name: str = "researcher"
):
    """
    WebSocket 端點用於實時聊天和 reasoning

    連接後可以發送消息，接收實時 reasoning steps
    """
    await ws_manager.connect(websocket, session_id)
    logger.info(f"[WS] Client connected: session={session_id}, agent={agent_name}")

    try:
        while True:
            # 接收客戶端消息
            data = await websocket.receive_json()

            message_type = data.get("type")
            payload = data.get("payload", {})

            if message_type == "chat":
                # 處理聊天請求
                user_message = payload.get("message")
                enable_reasoning = payload.get("enable_reasoning", True)

                # 啟動後台任務處理 reasoning
                asyncio.create_task(
                    handle_reasoning_request(
                        session_id,
                        agent_name,
                        user_message,
                        enable_reasoning
                    )
                )

            elif message_type == "ping":
                # 心跳檢測
                await ws_manager.send_message(session_id, {"type": "pong"})

    except WebSocketDisconnect:
        await ws_manager.disconnect(session_id)
        logger.info(f"[WS] Client disconnected: session={session_id}")

async def handle_reasoning_request(
    session_id: str,
    agent_name: str,
    message: str,
    enable_reasoning: bool
):
    """
    處理 reasoning 請求並推送 steps
    """
    try:
        # 發送開始消息
        await ws_manager.send_message(session_id, {
            "type": "reasoning_start",
            "data": {
                "agent": agent_name,
                "message": message
            }
        })

        # 獲取 agent
        agent = agent_manager.get_agent(agent_name)
        if not agent:
            await ws_manager.send_message(session_id, {
                "type": "error",
                "data": {"message": f"Agent '{agent_name}' not found"}
            })
            return

        if enable_reasoning:
            # 使用 streaming reasoning
            async for step in agent.run_with_reasoning_stream(message):
                # 推送每個 step
                await ws_manager.send_message(session_id, {
                    "type": "reasoning_step",
                    "data": step
                })
        else:
            # 非 streaming 模式
            response = await agent.run_async(message)
            content = "".join(msg.content for msg in response)
            await ws_manager.send_message(session_id, {
                "type": "response",
                "data": {"content": content}
            })

        # 發送完成消息
        await ws_manager.send_message(session_id, {
            "type": "reasoning_complete",
            "data": {}
        })

    except Exception as e:
        logger.exception(f"[WS] Error handling reasoning: {e}")
        await ws_manager.send_message(session_id, {
            "type": "error",
            "data": {"message": str(e)}
        })
```

#### 3. Streaming Reasoning Implementation
**文件**: `src/agents/base_agent.py`

新增 `run_with_reasoning_stream()` 方法：

```python
async def run_with_reasoning_stream(
    self,
    prompt: str,
    session_id: Optional[str] = None,
    max_iterations: int = 20,
    **kwargs
) -> AsyncIterator[Dict[str, Any]]:
    """
    Run agent with continuous reasoning - streaming version.

    Yields reasoning steps as they complete, enabling real-time push.

    Yields:
        Dict containing:
        - type: "thought" | "tool_use" | "tool_result" | "final_answer"
        - content: The content of the step
        - tool_name: Tool name (for tool_use/tool_result steps)
        - iteration: Iteration number
        - timestamp: ISO timestamp
    """
    import time
    from qwen_agent.llm.schema import FUNCTION

    logger.info(f"[{self.name}] Starting streaming reasoning: {prompt[:50]}...")

    # Yield start event
    yield {
        "type": "start",
        "message": "Starting reasoning process",
        "timestamp": time.time()
    }

    message = Message(role="user", content=prompt)
    self._add_to_history(message)

    iteration = 0

    try:
        while iteration < max_iterations:
            iteration += 1
            logger.debug(f"[{self.name}] Reasoning iteration {iteration}/{max_iterations}")

            # Yield iteration start
            yield {
                "type": "iteration_start",
                "iteration": iteration,
                "timestamp": time.time()
            }

            # Use streaming API
            response_stream = self._assistant.run(self._history, **kwargs)

            # Accumulate chunks and detect complete messages
            accumulated_messages = []
            tool_used_this_iteration = False
            assistant_message = None

            for chunk in response_stream:
                if not chunk:
                    continue

                # Accumulate messages from this chunk
                for msg in chunk:
                    if isinstance(msg, dict):
                        msg = Message(**msg)

                    accumulated_messages.append(msg)

                    # Check if we have a complete message to yield
                    if hasattr(msg, 'role'):
                        if msg.role == "assistant":
                            assistant_message = msg

                            # Check for tool calls
                            tool_calls = getattr(msg, 'tool_calls', None) or getattr(msg, 'function_call', None)

                            if tool_calls:
                                tool_used_this_iteration = True
                                # Extract and yield tool_use
                                if isinstance(tool_calls, list):
                                    for tc in tool_calls:
                                        tc_name = tc.get("name", "unknown") if isinstance(tc, dict) else getattr(tc, "name", "unknown")
                                        yield {
                                            "type": "tool_use",
                                            "tool_name": tc_name,
                                            "content": msg.content or "",
                                            "iteration": iteration,
                                            "timestamp": time.time()
                                        }
                                        logger.info(f"[{self.name}] Tool use: {tc_name}")
                                else:
                                    tc_name = tool_calls.get("name", "unknown") if isinstance(tool_calls, dict) else getattr(tool_calls, "name", "unknown")
                                    yield {
                                        "type": "tool_use",
                                        "tool_name": tc_name,
                                        "content": msg.content or "",
                                        "iteration": iteration,
                                        "timestamp": time.time()
                                    }
                                        logger.info(f"[{self.name}] Tool use: {tc_name}")

                            elif msg.content:
                                # Yield thought
                                yield {
                                    "type": "thought",
                                    "content": msg.content,
                                    "iteration": iteration,
                                    "timestamp": time.time()
                                }
                                logger.debug(f"[{self.name}] Thought: {msg.content[:100]}...")

                        elif msg.role == FUNCTION:
                            tool_name = getattr(msg, 'name', 'unknown')
                            # Yield tool_result
                            yield {
                                "type": "tool_result",
                                "tool_name": tool_name,
                                "content": msg.content or "",
                                "iteration": iteration,
                                "timestamp": time.time()
                            }
                            logger.debug(f"[{self.name}] Tool result from {tool_name}")

                    # Add to history
                    self._add_to_history(msg)

            # Yield iteration end
            yield {
                "type": "iteration_end",
                "iteration": iteration,
                "timestamp": time.time()
            }

            # Check if iteration is complete
            if not tool_used_this_iteration:
                if assistant_message and assistant_message.content:
                    yield {
                        "type": "final_answer",
                        "content": assistant_message.content,
                        "iteration": iteration,
                        "timestamp": time.time()
                    }
                    logger.info(f"[{self.name}] Final answer reached")
                break

        if iteration >= max_iterations:
            logger.warning(f"[{self.name}] Max iterations ({max_iterations}) reached")
            yield {
                "type": "max_iterations_reached",
                "max_iterations": max_iterations,
                "timestamp": time.time()
            }

        # Yield complete event
        yield {
            "type": "complete",
            "total_iterations": iteration,
            "timestamp": time.time()
        }

        logger.info(f"[{self.name}] Streaming reasoning completed with {iteration} iterations")

    except Exception as e:
        logger.error(f"[{self.name}] Error in streaming reasoning: {e}")
        yield {
            "type": "error",
            "error": str(e),
            "timestamp": time.time()
        }
        raise
```

#### 4. Gradio WebSocket Client
**文件**: `src/gui/websocket_client.py`

Gradio 組件用於連接 WebSocket 並顯示實時更新：

```python
import gradio as gr
import json
import asyncio
from typing import Callable, Optional

class GradioWebSocketClient:
    """
    Gradio WebSocket 客戶端組件

    提供實時聊天和 reasoning 顯示
    """

    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.connected = False

    def create_interface(self, on_message_callback: Callable):
        """
        創建 Gradio 界面

        Args:
            on_message_callback: 接收 reasoning step 時的回調
        """
        with gr.Blocks() as interface:
            gr.Markdown("# 🤖 Real-Time Agent Chat")

            with gr.Row():
                with gr.Column(scale=1):
                    # Agent 選擇
                    agent_dropdown = gr.Dropdown(
                        label="Select Agent",
                        choices=["researcher", "developer", "writer"],
                        value="researcher"
                    )

                    # Reasoning toggle
                    reasoning_toggle = gr.Checkbox(
                        label="Enable Continuous Reasoning",
                        value=True
                    )

                    # 消息輸入
                    message_input = gr.Textbox(
                        label="Your Message",
                        placeholder="Type your message here...",
                        lines=2
                    )

                    # 發送按鈕
                    send_btn = gr.Button("Send", variant="primary")

                with gr.Column(scale=2):
                    # 實時顯示區域
                    chat_output = gr.Markdown(
                        label="Agent Response",
                        value="*Waiting for message...*"
                    )

                    # 狀態指示器
                    status_indicator = gr.Textbox(
                        label="Status",
                        value="Disconnected",
                        interactive=False
                    )

            # 事件處理
            send_btn.click(
                fn=lambda msg, agent, reasoning: on_message_callback({
                    "type": "send_message",
                    "message": msg,
                    "agent": agent,
                    "enable_reasoning": reasoning
                }),
                inputs=[message_input, agent_dropdown, reasoning_toggle],
                outputs=[chat_output]
            )

        return interface

    @staticmethod
    def get_javascript_client(ws_url: str) -> str:
        """
        返回 JavaScript 客戶端代碼

        這段代碼將在瀏覽器中運行，處理 WebSocket 連接
        """
        return f"""
        class AgentWebSocketClient {{
            constructor(url) {{
                this.url = url;
                this.ws = null;
                this.reconnectAttempts = 0;
                this.maxReconnectAttempts = 5;
                this.messageHandlers = {{}};
            }}

            connect() {{
                this.ws = new WebSocket(this.url);

                this.ws.onopen = () => {{
                    console.log('[WS] Connected');
                    this.reconnectAttempts = 0;
                    this.updateStatus('Connected', 'success');
                }};

                this.ws.onmessage = (event) => {{
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                }};

                this.ws.onerror = (error) => {{
                    console.error('[WS] Error:', error);
                    this.updateStatus('Error', 'error');
                }};

                this.ws.onclose = () => {{
                    console.log('[WS] Disconnected');
                    this.updateStatus('Disconnected', 'normal');
                    this.attemptReconnect();
                }};
            }}

            disconnect() {{
                if (this.ws) {{
                    this.ws.close();
                }}
            }}

            attemptReconnect() {{
                if (this.reconnectAttempts < this.maxReconnectAttempts) {{
                    this.reconnectAttempts++;
                    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000);
                    console.log(`[WS] Reconnecting in ${{delay}}ms...`);

                    setTimeout(() => {{
                        this.connect();
                    }}, delay);
                }}
            }}

            sendMessage(message, agent, enableReasoning) {{
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {{
                    this.ws.send(JSON.stringify({{
                        type: 'chat',
                        payload: {{
                            message: message,
                            agent_name: agent,
                            enable_reasoning: enableReasoning
                        }}
                    }}));
                }} else {{
                    console.error('[WS] Not connected');
                }}
            }}

            handleMessage(data) {{
                const handler = this.messageHandlers[data.type];
                if (handler) {{
                    handler(data);
                }}
            }}

            on(type, handler) {{
                this.messageHandlers[type] = handler;
            }}

            updateStatus(text, type) {{
                // 更新 Gradio UI
                if (window.updateStatus) {{
                    window.updateStatus(text, type);
                }}
            }}
        }}

        // 初始化客戶端
        const client = new AgentWebSocketClient('{ws_url}');
        client.connect();
        """

    def create_custom_component(self):
        """
        創建自定義 Gradio 組件，整合 WebSocket 客戶端

        使用 gr.HTML + JavaScript 實現實時更新
        """
        js_code = self.get_javascript_client(self.ws_url)

        html_template = f"""
        <div id="websocket-chat">
            <script>
                {js_code}

                // 處理 reasoning steps
                client.on('reasoning_start', (data) => {{
                    console.log('Reasoning started for agent:', data.agent);
                    updateChatOutput('🤔 Agent is starting to think...\\n\\n');
                }});

                client.on('reasoning_step', (data) => {{
                    const stepData = data.data;
                    let formatted = '';

                    if (stepData.type === 'thought') {{
                        formatted = `🤔 **Thinking:**\\n${{stepData.content}}\\n\\n`;
                    }} else if (stepData.type === 'tool_use') {{
                        formatted = `🔧 **Using tool:** `${{stepData.tool_name}}`\\n\\n`;
                    }} else if (stepData.type === 'tool_result') {{
                        const content = stepData.content.length > 500
                            ? stepData.content.substring(0, 500) + '...[truncated]'
                            : stepData.content;
                        formatted = `📊 **Result from `${{stepData.tool_name}}`:**\\n```${{content}}```\\n\\n`;
                    }} else if (stepData.type === 'final_answer') {{
                        formatted = `✅ **Final Answer:**\\n${{stepData.content}}`;
                    }}

                    appendChatOutput(formatted);
                }});

                client.on('reasoning_complete', () => {{
                    console.log('Reasoning completed');
                    updateStatus('Completed', 'success');
                }});

                client.on('error', (data) => {{
                    console.error('Error:', data.data.message);
                    updateChatOutput(`❌ Error: ${{data.data.message}}`);
                }});

                // 輔助函數
                function updateChatOutput(content) {{
                    const output = document.querySelector('[data-testid="markdown"]');
                    if (output) {{
                        output.innerHTML = content;
                    }}
                }}

                function appendChatOutput(content) {{
                    const output = document.querySelector('[data-testid="markdown"]');
                    if (output) {{
                        output.innerHTML += content;
                    }}
                }}

                function updateStatus(text, type) {{
                    const status = document.querySelector('[data-testid="status"]');
                    if (status) {{
                        status.textContent = text;
                        status.className = `status status-${{type}}`;
                    }}
                }}

                // 發送消息函數（從 Gradio 調用）
                window.sendMessage = (message, agent, reasoning) => {{
                    client.sendMessage(message, agent, reasoning);
                }};
            </script>

            <div class="chat-container">
                <div id="chat-output" data-testid="markdown" class="markdown">
                    *Connecting to agent...*
                </div>
                <div id="status-display" data-testid="status" class="status">
                    Connecting...
                </div>
            </div>

            <style>
                .chat-container {{
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    padding: 16px;
                    min-height: 300px;
                }}
                .status {{
                    padding: 8px;
                    border-radius: 4px;
                    margin-top: 16px;
                    font-weight: bold;
                }}
                .status-success {{ background-color: #d4edda; color: #155724; }}
                .status-error {{ background-color: #f8d7da; color: #721c24; }}
                .status-normal {{ background-color: #e2e3e5; color: #383d41; }}
            </style>
        </div>
        """

        return gr.HTML(html_template)
```

## 實施步驟

### Phase 1: 基礎設施 (高優先級)

#### Step 1.1: 實現 WebSocket Manager
**文件**: `src/core/websocket_manager.py`

**任務**:
1. 創建 `WebSocketManager` 類
2. 實現連接管理（連接、斷開、廣播）
3. 添加消息隊列支持
4. 實現心跳檢測機制

**預計時間**: 1-2 小時

#### Step 1.2: 創建 WebSocket API Endpoints
**文件**: `src/api/websocket_endpoints.py`

**任務**:
1. 定義 `/ws/chat/{session_id}` 端點
2. 實現消息處理邏輯
3. 添加錯誤處理和日誌
4. 集成 WebSocket Manager

**預計時間**: 2-3 小時

#### Step 1.3: 更新 Main Application
**文件**: `main.py`

**任務**:
1. 註冊 WebSocket 路由
2. 初始化 WebSocket Manager
3. 添加 CORS 支持（如果需要）

**預計時間**: 30 分鐘

### Phase 2: Streaming Reasoning 實現 (高優先級)

#### Step 2.1: 實現 `run_with_reasoning_stream()`
**文件**: `src/agents/base_agent.py`

**任務**:
1. 創建 async generator 方法
2. 使用 `run()` streaming API
3. 實現步驟邊界檢測
4. 添加時間戳和元數據
5. 異常處理

**預計時間**: 3-4 小時

#### Step 2.2: 向後兼容包裝
**文件**: `src/agents/base_agent.py`

**任務**:
1. 更新現有 `run_with_reasoning()` 使用 stream 版本
2. 收集所有 steps 並返回列表
3. 確保現有測試通過

**預計時間**: 1 小時

#### Step 2.3: 單元測試
**文件**: `tests/test_streaming_reasoning.py`

**任務**:
1. 測試每個 step 類型正確 yield
2. 測試異常情況處理
3. 測試向後兼容性

**預計時間**: 2 小時

### Phase 3: Gradio WebSocket 客戶端 (高優先級)

#### Step 3.1: 創建 WebSocket Client 組件
**文件**: `src/gui/websocket_client.py`

**任務**:
1. 實現 JavaScript WebSocket 客戶端
2. 創建 Gradio HTML 組件
3. 實現實時更新邏輯
4. 添加重連機制

**預計時間**: 3-4 小時

#### Step 3.2: 整合到現有 GUI
**文件**: `src/gui/app.py`

**任務**:
1. 添加新的 "Real-Time Chat" tab
2. 保留原有 Chat tab 作為備選
3. 添加切換功能

**預計時間**: 2 小時

### Phase 4: Task Scheduler 集成 (中優先級)

#### Step 4.1: WebSocket 推送 Task 執行進度
**文件**: `src/core/task_scheduler.py`

**任務**:
1. 使用 WebSocket 推送 task 執行狀態
2. 推送 reasoning steps
3. 支持任務完成通知

**預計時間**: 2 小時

### Phase 5: 優化和潤色 (低優先級)

#### Step 5.1: 性能優化
**任務**:
1. 連接池管理
2. 消息壓縮（大文本）
3. 心跳優化

**預計時間**: 2 小時

#### Step 5.2: 用戶體驗改進
**任務**:
1. 添加進度指示器
2. 支持中斷/取消
3. 歷史記錄查看

**預計時間**: 2-3 小時

#### Step 5.3: 錯誤處理和監控
**任務**:
1. 優雅的錯誤提示
2. 連接狀態監控
3. 調試工具

**預計時間**: 2 小時

## 時間估算

| Phase | 任務 | 預計時間 |
|-------|------|----------|
| Phase 1 | 基礎設施（WebSocket Manager + API） | 3.5-5.5 小時 |
| Phase 2 | Streaming Reasoning 實現 | 6-7 小時 |
| Phase 3 | Gradio WebSocket 客戶端 | 5-6 小時 |
| Phase 4 | Task Scheduler 集成 | 2 小時 |
| Phase 5 | 優化和潤色 | 6-8 小時 |
| **總計** | | **22.5-28.5 小時** |

## 依賴關係

```
Phase 1 (基礎設施)
    ↓
Phase 2 (Streaming Reasoning) ← 可並行於 Phase 3
Phase 3 (Gradio 客戶端) ← 可並行於 Phase 2
    ↓
Phase 4 (Task Scheduler) ← 依賴 Phase 1, 2
    ↓
Phase 5 (優化) ← 依賴 Phase 1-4
```

## 建議實施順序

### MVP (最小可行產品)
**Phase 1.1 + 1.2 + 2.1 + 3.1** (約 12-15 小時)
- WebSocket 基礎設施
- 基本的 streaming reasoning
- 簡單的 Gradio 客戶端
- 驗證端到端流程

### 完整版
完成所有 phases，包括：
- 完整的 GUI 整合
- Task scheduler 支持
- 性能優化和用戶體驗改進

## 優勢與挑戰

### 優勢
1. **真正的實時推送**：無輪詢，無延遲
2. **雙向通信**：客戶端可隨時發送控制指令（如中斷）
3. **可擴展性**：支持多客戶端、廣播
4. **持久連接**：減少連接建立開銷

### 挑戰
1. **架構複雜度**：需要管理連接狀態
2. **錯誤恢復**：網絡中斷時需要重連
3. **狀態同步**：確保客戶端顯示與服務器一致
4. **資源管理**：長連接需要合理清理

## 技術棧

### 後端
- **FastAPI WebSocket**：WebSocket 服務器
- **AsyncIO**：異步處理
- **Qwen Agent SDK**：streaming API

### 前端
- **原生 WebSocket API**：瀏覽器 WebSocket 支持
- **Gradio HTML**：自定義 HTML/JavaScript 組件
- **JavaScript ES6+**：現代 JavaScript 特性

## 成功標準

### 功能性
- ✅ WebSocket 連接穩定
- ✅ Reasoning steps 實時推送
- ✅ 支持中斷/取消
- ✅ 多客戶端並發

### 性能
- ✅ 首個 step 延遲 < 1 秒
- ✅ 連接建立 < 500ms
- ✅ 支持至少 100 並發連接

### 可靠性
- ✅ 自動重連機制
- ✅ 優雅的錯誤處理
- ✅ 連接狀態可視化

## 風險評估

### 高風險
1. **狀態管理**：客戶端與服務器狀態可能不一致
   - **緩解**：使用事件編號和確認機制

2. **資源洩漏**：未正確清理的連接
   - **緩解**：實施定期清理和超時機制

### 中風險
1. **瀏覽器兼容性**：不同瀏覽器 WebSocket 實現差異
   - **緩解**：使用 polyfill 和特性檢測

2. **網絡不穩定**：移動網絡頻繁斷線
   - **緩解**：智能重連和離線緩存

### 低風險
1. **Gradio 限制**：可能與 Gradio 的某些功能衝突
   - **緩解**：保留原有 Chat tab 作為備選

## 替代方案對比

| 方案 | 優點 | 缺點 | 複雜度 |
|------|------|------|--------|
| **WebSocket** | 真實時、雙向、可擴展 | 架構複雜、需管理狀態 | 高 |
| Server-Sent Events | 簡單、自動重連 | 單向、HTTP 限制 | 中 |
| Long Polling | 簡單、兼容性好 | 延遲高、資源消耗 | 低 |
| Async Generator | 簡潔、Pythonic | 需要線程通信 | 中 |

**選擇**：WebSocket 雖然複雜度最高，但提供了最佳的功能和用戶體驗。

## 參考資料

- FastAPI WebSocket 文檔: https://fastapi.tiangolo.com/advanced/websockets/
- WebSocket API (MDN): https://developer.mozilla.org/en-US/docs/Web/API/WebSocket
- Qwen Agent Streaming: https://github.com/QwenLM/Qwen-Agent
- Gradio Custom Components: https://www.gradio.app/docs/gradio/custom-components

## 附錄：消息格式規範

### 客戶端 → 服務端

```json
{
  "type": "chat",
  "payload": {
    "message": "用戶消息",
    "agent_name": "researcher",
    "enable_reasoning": true
  }
}
```

```json
{
  "type": "ping",
  "payload": {}
}
```

### 服務端 → 客戶端

```json
{
  "type": "reasoning_start",
  "data": {
    "agent": "researcher",
    "message": "原始問題"
  }
}
```

```json
{
  "type": "reasoning_step",
  "data": {
    "type": "thought",
    "content": "思考內容",
    "iteration": 1,
    "timestamp": 1641234567.123
  }
}
```

```json
{
  "type": "reasoning_complete",
  "data": {
    "total_iterations": 3
  }
}
```

```json
{
  "type": "error",
  "data": {
    "message": "錯誤描述"
  }
}
```

```json
{
  "type": "pong",
  "data": {}
}
```
