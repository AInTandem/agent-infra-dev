# Phase 5: Task Scheduler - 工作報告

**日期**: 2026-01-06
**階段**: Phase 5 - Task Scheduler
**狀態**: ✅ 完成

---

## 概述

本階段完成了任務排程系統的實現，使用 APScheduler 提供 Cron、Interval 和一次性任務排程功能，並支援任務持久化。

---

## 完成項目

### Step 5.1: 任務資料模型 ✅

**驗收標準檢查**:
- [x] ScheduledTask 資料模型（Pydantic）
- [x] TaskExecution 資料模型
- [x] ScheduleType 枚舉（CRON, INTERVAL, ONCE）
- [x] TaskStatus 枚舉
- [x] 狀態轉換方法
- [x] 單元測試通過

**實現功能**:
- 三種排程類型支援（Cron, Interval, Once）
- 任務狀態追蹤
- 執行歷史記錄
- 統計資訊收集（成功率、執行次數等）
- APScheduler trigger 轉換

**資料模型設計**:
```python
class ScheduledTask(BaseModel):
    id: str
    name: str
    agent_name: str
    task_prompt: str
    schedule_type: ScheduleType
    schedule_value: str
    repeat: bool
    enabled: bool
    created_at: datetime
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    last_status: TaskStatus
    total_runs: int
    successful_runs: int
    failed_runs: int
```

---

### Step 5.2: APScheduler 整合 ✅

**驗收標準檢查**:
- [x] TaskScheduler 類別實現
- [x] Cron 排程支援
- [x] Interval 排程支援
- [x] 一次性任務支援
- [x] 單元測試通過

**實現功能**:
- APScheduler AsyncIOScheduler 整合
- 任務執行邏輯（與 Agent 整合）
- 自動重試機制
- 任務狀態管理
- 並發控制（max_instances=1）

**排程範例**:
```python
# Cron: 每天早上 9 點
task = await scheduler.schedule_task(
    name="Daily Report",
    agent_name="analyst",
    task_prompt="Generate daily report",
    schedule_type=ScheduleType.CRON,
    schedule_value="0 9 * * *",
    repeat=True,
)

# Interval: 每 5 分鐘
task = await scheduler.schedule_task(
    name="Status Check",
    agent_name="developer",
    task_prompt="Check system status",
    schedule_type=ScheduleType.INTERVAL,
    schedule_value="300",  # seconds
    repeat=True,
)

# Once: 指定時間執行
task = await scheduler.schedule_task(
    name="One-time Backup",
    agent_name="developer",
    task_prompt="Run backup",
    schedule_type=ScheduleType.ONCE,
    schedule_value="2026-01-06T20:00:00",
    repeat=False,
)
```

---

### Step 5.3: 任務持久化 ✅

**驗收標準檢查**:
- [x] 任務持久化到 JSON 檔案
- [x] 應用啟動時載入任務
- [x] DateTime 序列化/反序列化
- [x] 自動保存（任務變更時）

**實現功能**:
- JSON 格式持久化
- 自動任務恢復
- 修改自動保存
- DateTime ISO 格式轉換

**儲存格式**:
```json
{
  "tasks": [
    {
      "id": "uuid",
      "name": "Daily Report",
      "agent_name": "analyst",
      "task_prompt": "Generate daily report",
      "schedule_type": "cron",
      "schedule_value": "0 9 * * *",
      "enabled": true,
      "created_at": "2026-01-06T10:00:00",
      "next_run": "2026-01-07T09:00:00",
      "last_status": "pending"
    }
  ],
  "updated_at": "2026-01-06T10:00:00"
}
```

---

## 測試結果

```
============================================================
Task Models Tests
============================================================
✓ ScheduledTask model creation
✓ Status transitions (running, completed)
✓ Statistics tracking (total_runs, success_rate)
✓ TaskExecution model creation
✓ Duration tracking

============================================================
Task Scheduler Tests
============================================================
✓ One-time task scheduling
✓ Interval task scheduling (30 seconds)
✓ Cron task scheduling (every minute)
✓ Task listing (3 tasks)
✓ Task info retrieval
✓ Enable/disable functionality
✓ Task update (description, timeout)
✓ Scheduler stats (running, total_tasks, jobs_scheduled)
✓ Task persistence to JSON
✓ Task cancellation
✓ Task removal
```

---

## 技術挑戰與解決方案

### 挑戰 1: DateTime JSON 序列化

**問題**:
```
Object of type datetime is not JSON serializable
```

**原因**: Pydantic 的 `model_dump()` 不會自動使用 `json_encoders`

**解決**: 手動轉換 datetime 為 ISO 格式
```python
for key, value in task_dict.items():
    if isinstance(value, datetime):
        task_dict[key] = value.isoformat()
```

---

### 挑戰 2: ConfigManager 屬性訪問

**問題**:
```
'ConfigManager' object has no attribute 'scheduler'
```

**原因**: Scheduler 配置在 `app.scheduler` 而非直接在 `config_manager`

**解決**:
```python
app_config = self.config_manager.app
scheduler_config = app_config.scheduler
```

---

## 架構說明

### 任務執行流程

```
TaskScheduler
    ├── APScheduler (AsyncIOScheduler)
    │   └── Jobs (CronTrigger, IntervalTrigger, DateTrigger)
    ├── ScheduledTask storage
    │   └── JSON persistence
    └── TaskExecution history
        └── Execution records
```

### 排程觸發流程

```
APScheduler trigger fires
    ↓
_execute_task(task_id)
    ↓
Get agent from AgentManager
    ↓
agent.run_async(task_prompt)
    ↓
Mark completed/failed
    ↓
Update next_run time
    ↓
Save to persistence
```

---

## 新增檔案

```
src/core/
├── task_models.py       # Task data models
└── task_scheduler.py    # Task Scheduler implementation

tests/
└── test_task_scheduler.py  # Task Scheduler tests
```

---

## 下一步階段

**Phase 6: OpenAI-Compatible API**
- 實現 FastAPI 伺服器
- Chat Completions API
- Scheduled Task function calls
- Agent 選擇機制

---

## 附錄

### Cron 表達式範例

```python
# 每天早上 9 點
"0 9 * * *"

# 每週一早上 9 點
"0 9 * * 1"

# 每月 1 號凌晨
"0 0 1 * *"

# 每 5 分鐘
"*/5 * * * *"

# 工作日每小時
"0 9-17 * * 1-5"
```

### 使用範例

```python
# 初始化
scheduler = TaskScheduler(config_manager, agent_manager)
await scheduler.start()

# 建立排程任務
task = await scheduler.schedule_task(
    name="Daily Report",
    agent_name="analyst",
    task_prompt="Generate daily sales report",
    schedule_type=ScheduleType.CRON,
    schedule_value="0 9 * * *",
    repeat=True,
    description="Daily sales report generation",
)

# 查看任務
tasks = scheduler.list_tasks()
for task in tasks:
    print(f"{task.name}: {task.next_run}")

# 停用任務
await scheduler.disable_task(task.id)

# 移除任務
await scheduler.remove_task(task.id)

# 停止排程器
await scheduler.stop()
```
