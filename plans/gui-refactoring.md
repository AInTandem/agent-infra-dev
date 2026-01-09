# GUI Refactoring Plan - Split app.py into Tab Modules

## 目標

將 `src/gui/app.py` (1477 行) 重構為模組化架構，以 tab 為單位分割成獨立模組。

## 當前問題

1. **單一檔案過大** - `app.py` 有 1477 行，難以維護
2. **責任不清** - 所有 tab 邏輯混在一起
3. **除錯困難** - WebSocket Chat 問題難以定位
4. **測試困難** - 無法針對單一 tab 進行測試

## 當前架構分析

### app.py 結構

```python
class GradioApp:
    def __init__(...)           # Lines 52-80
    def _create_interface(...)  # Lines 82-114
    def _create_chat_tab(...)          # Lines 116-165  (50 lines)
    def _create_realtime_chat_tab(...)  # Lines 167-192  (26 lines)
    def _create_agents_tab(...)        # Lines 194-230  (37 lines)
    def _create_tasks_tab(...)         # Lines 232-297  (66 lines)
    def _create_settings_tab(...)      # Lines 299-521  (223 lines)
    def _create_config_tab(...)        # Lines 626-1443 (818 lines) ⚠️
    # Helper methods...
```

### Tab 行數統計

| Tab | Lines | Description |
|-----|-------|-------------|
| Chat | 50 | Traditional chat interface |
| Real-Time Chat | 26 | WebSocket streaming chat ⚠️ 問題所在 |
| Agents | 37 | Agent management |
| Tasks | 66 | Task scheduler interface |
| Settings | 223 | System settings and status |
| Config | 818 | Configuration editing ⚠️ 最大的 tab |
| **Total** | **1220** | Tab content only |

## 重構目標架構

```
src/gui/
├── app.py                    # Main orchestrator (~200 lines)
├── tabs/
│   ├── __init__.py
│   ├── base_tab.py           # Base tab class
│   ├── chat_tab.py           # Chat tab (~100 lines)
│   ├── realtime_chat_tab.py  # Real-Time Chat tab (~150 lines)
│   ├── agents_tab.py         # Agents tab (~150 lines)
│   ├── tasks_tab.py          # Tasks tab (~200 lines)
│   ├── settings_tab.py       # Settings tab (~300 lines)
│   └── config_tab.py         # Config tab (~900 lines)
└── components/
    ├── websocket_chat.py     # Existing WebSocket component
    └── ...
```

## 重構步驟

### Phase 1: 基礎架構 (優先級: 高)

#### Step 1.1: 創建 tabs 目錄和基礎類別
**檔案**: `src/gui/tabs/__init__.py`, `src/gui/tabs/base_tab.py`

**目標**:
- 定義 `BaseTab` 介面
- 建立統一的 tab 創建模式
- 提供共享依賴注入

**預計時間**: 30 分鐘

#### Step 1.2: 重構 Chat Tab
**檔案**: `src/gui/tabs/chat_tab.py`

**目標**:
- 提取 `_create_chat_tab()` 和相關方法
- 提取 `_chat_with_agent()`, `_clear_chat_history()`
- 保持現有功能不變

**預計時間**: 45 分鐘

### Phase 2: Real-Time Chat Tab (優先級: 高 - 除錯重點)

#### Step 2.1: 重構 Real-Time Chat Tab
**檔案**: `src/gui/tabs/realtime_chat_tab.py`

**目標**:
- 提取 `_create_realtime_chat_tab()`
- 整合 `WebSocketChatComponent`
- **重點**: 易於除錯 JavaScript 載入問題

**除錯改進**:
```python
class RealtimeChatTab(BaseTab):
    def create_interface(self):
        # 清晰的組件初始化流程
        # 易於添加日誌和斷點
        pass

    def get_javascript_injection(self) -> str:
        # 獨立的 JavaScript 注入邏輯
        # 易於驗證 head_paths 是否生效
        pass
```

**預計時間**: 1 小時

### Phase 3: 其他 Tabs (優先級: 中)

#### Step 3.1: 重構 Agents Tab
**檔案**: `src/gui/tabs/agents_tab.py`

**目標**:
- 提取 `_create_agents_tab()`
- 提取 `_get_agent_choices()`, `_refresh_agents()`, `_show_agent_details()`

**預計時間**: 45 分鐘

#### Step 3.2: 重構 Tasks Tab
**檔案**: `src/gui/tabs/tasks_tab.py`

**目標**:
- 提取 `_create_tasks_tab()`
- 提取 `_create_task()`, `_refresh_tasks()`

**預計時間**: 1 小時

#### Step 3.3: 重構 Settings Tab
**檔案**: `src/gui/tabs/settings_tab.py`

**目標**:
- 提取 `_create_settings_tab()`
- 提取 `_get_system_status()`, `_get_statistics()`, `_refresh_status()`

**預計時間**: 1.5 小時

#### Step 3.4: 重構 Config Tab
**檔案**: `src/gui/tabs/config_tab.py`

**目標**:
- 提取 `_create_config_tab()` (最大的 tab!)
- 提取 `_format_args_for_form()`, `_format_env_for_form()`

**預計時間**: 2 小時

### Phase 4: 主應用程式重構 (優先級: 高)

#### Step 4.1: 簡化 app.py
**檔案**: `src/gui/app.py`

**目標**:
- 移除所有 tab 創建方法
- 改為 tab 模組實例化
- 保持清晰的依賴注入

**重構後結構**:
```python
class GradioApp:
    def __init__(self, config_manager, agent_manager, task_scheduler):
        # Initialize tabs
        self.tabs = {
            "chat": ChatTab(config_manager, agent_manager, task_scheduler),
            "realtime_chat": RealtimeChatTab(config_manager, agent_manager),
            "agents": AgentsTab(config_manager, agent_manager),
            "tasks": TasksTab(config_manager, agent_manager, task_scheduler),
            "settings": SettingsTab(config_manager, agent_manager, task_scheduler),
            "config": ConfigTab(config_manager),
        }

    def _create_interface(self) -> gr.Blocks:
        with gr.Blocks(...) as app:
            gr.Markdown("# 🤖 AInTandem Agent MCP Scheduler")

            with gr.Tabs():
                for tab_name, tab in self.tabs.items():
                    with gr.Tab(tab.title):
                        tab.create()

        return app
```

**預計時間**: 1 小時

### Phase 5: 除錯與測試 (優先級: 高)

#### Step 5.1: 修復 JavaScript 載入問題
**重點**: Real-Time Chat Tab

**診斷步驟**:
1. 驗證 `head_paths` 是否正確傳遞
2. 檢查瀏覽器 HTML source 是否包含 JavaScript
3. 添加載入失敗的fallback機制

**可能解決方案**:
```python
# 方案 A: 使用 gr.Blocks 的 js 參數 (如果 head_paths 失敗)
demo.launch(js=javascript_code)

# 方案 B: 使用事件監聽器的 js 參數
connect_btn.click(..., js="(x) => { console.log('JS loaded'); return x; }")

# 方案 C: 使用自訂組件的 JavaScript
```

**預計時間**: 1-2 小時

#### Step 5.2: 測試所有 Tabs
- 每個 tab 獨立測試
- 整合測試
- 回歸測試

**預計時間**: 1 小時

## BaseTab 介面設計

```python
from abc import ABC, abstractmethod
import gradio as gr

class BaseTab(ABC):
    """Base class for all Gradio tabs"""

    def __init__(
        self,
        config_manager: ConfigManager,
        agent_manager: AgentManager,
        task_scheduler: Optional[TaskScheduler] = None
    ):
        self.config_manager = config_manager
        self.agent_manager = agent_manager
        self.task_scheduler = task_scheduler

    @property
    @abstractmethod
    def title(self) -> str:
        """Tab title (e.g., '💬 Chat')"""
        pass

    @property
    def description(self) -> Optional[str]:
        """Optional tab description"""
        return None

    @abstractmethod
    def create(self) -> gr.Blocks:
        """Create and return the Gradio interface for this tab"""
        pass

    def get_custom_css(self) -> str:
        """Optional custom CSS for this tab"""
        return ""

    def get_custom_js(self) -> str:
        """Optional custom JavaScript for this tab"""
        return ""
```

## 預期效益

1. **可維護性**
   - 每個 tab 獨立檔案，易於理解和修改
   - 清晰的責任劃分

2. **可測試性**
   - 可以針對單一 tab 進行單元測試
   - 更容易模擬依賴

3. **除錯效率**
   - Real-Time Chat 問題可以快速定位
   - 更容易添加日誌和斷點

4. **團隊協作**
   - 不同 tab 可以由不同開發者維護
   - 減少 merge conflict

## 風險評估

### 高風險
1. **破壞現有功能**
   - **緩解**: 逐步遷移，保持向後兼容
   - **緩解**: 每個 phase 完成後測試

2. **循環依賴**
   - **緩解**: 使用依賴注入模式
   - **緩解**: 清晰的模組邊界

### 中風險
1. **配置傳遞複雜度**
   - **緩解**: BaseTab 統一依賴注入

2. **Gradio 狀態管理**
   - **緩解**: 保持現有狀態管理模式

## 時間估算

| Phase | 任務 | 預計時間 |
|-------|------|----------|
| Phase 1 | 基礎架構 | 1.25 小時 |
| Phase 2 | Real-Time Chat Tab | 1 小時 |
| Phase 3 | 其他 Tabs | 5 小時 |
| Phase 4 | 主應用程式重構 | 1 小時 |
| Phase 5 | 除錯與測試 | 2-3 小時 |
| **總計** | | **10-11 小時** |

## 建議實施順序

### MVP (除錯優先)
**Phase 1 → Phase 2 → Phase 4 → Phase 5**
- 建立基礎架構
- 先重構 Real-Time Chat Tab (除錯重點)
- 簡化主應用程式
- 修復 JavaScript 載入問題

### 完整版
完成所有 phases，包括其他 tabs 的重構。

## 下一步行動

1. ✅ 提交現有變更
2. 📝 創建重構計劃 (本文件)
3. 🔧 開始 Phase 1: 創建基礎架構
4. 🐛 優先處理 Real-Time Chat Tab 除錯

## 參考資料

- Gradio Custom Components: https://www.gradio.app/docs/gradio/custom-components
- Python Abstract Base Classes: https://docs.python.org/3/library/abc.html
- Dependency Injection Pattern: https://en.wikipedia.org/wiki/Dependency_injection
