# Phase 8: Sandbox Environment - 工作報告

**日期**: 2026-01-06
**階段**: Phase 8 - Sandbox Environment
**狀態**: ✅ 完成

---

## 概述

本階段完成了沙盒環境實現，提供執行隔離、資源限制和安全策略功能，確保 Agent 執行的安全性和可控性。

---

## 完成項目

### Step 8.1: 沙盒環境管理器 ✅

**驗收標準檢查**:
- [x] SandboxConfig 配置類別
- [x] SandboxManager 管理器實現
- [x] 沙盒上下文管理器
- [x] 臨時目錄管理
- [x] 資源限制設定
- [x] 路徑存取控制
- [x] 測試通過

**實現功能**:
- 臨時目錄創建與清理
- 資源限制設定（記憶體、CPU、進程數）
- 路徑存取控制（允許/阻止列表）
- 網路存取控制
- 沙盒狀態追蹤

**配置選項**:
```python
SandboxConfig(
    enabled=True,           # 啟用沙盒限制
    max_memory_mb=512,      # 最大記憶體 512MB
    max_cpu_time=30,        # 最大 CPU 時間 30秒
    max_wall_time=60,       # 最大執行時間 60秒
    max_processes=10,       # 最大進程數 10
    network_access=True,    # 允許網路存取
)
```

---

### Step 8.2: 資源限制 ✅

**驗收標準檢查**:
- [x] ResourceLimiter 類別實現
- [x] CPU 使用率監控
- [x] 記憶體使用率監控
- [x] 開啟檔案數監控
- [x] 執行緒數監控
- [x] 磁碟 I/O 追蹤
- [x] 系統資源監控
- [x] 測試通過

**實現功能**:
- 即時資源監控（CPU、記憶體、檔案、執行緒）
- 磁碟 I/O 追蹤（讀取/寫入）
- 違規檢測與回調
- 系統統計資訊

**監控指標**:
```python
ResourceMetrics(
    cpu_percent=0.1,        # CPU 使用率
    memory_mb=21.6,         # 記憶體使用量 (MB)
    memory_percent=0.3,     # 記憶體使用率
    open_files=0,           # 開啟檔案數
    num_threads=1,          # 執行緒數
    disk_read_mb=0.0,       # 磁碟讀取 (MB)
    disk_write_mb=0.0,      # 磁碟寫入 (MB)
)
```

---

### Step 8.3: 安全策略 ✅

**驗收標準檢查**:
- [x] SecurityPolicy 配置類別
- [x] SecurityValidator 驗證器實現
- [x] 輸入驗證（危險指令、敏感檔案）
- [x] 指令驗證
- [x] 檔案路徑驗證
- [x] URL 驗證
- [x] 輸入/輸出清理
- [x] 違規追蹤
- [x] 測試通過

**實現功能**:
- 危險指令偵測（rm -rf /, eval, exec 等）
- 敏感檔案保護（/etc/passwd, ~/.ssh, .env 等）
- 指令執行控制
- 檔案寫入控制
- 網路存取控制
- 域名白名單/黑名單
- 輸入清理（移除 null bytes、過多空白）
- 輸出清理（移除 ANSI 轉義碼）

**安全策略預設**:
```python
SecurityPolicy(
    allow_command_execution=False,  # 不允許指令執行
    allow_file_write=True,          # 允許檔案寫入
    allow_network_access=True,      # 允許網路存取
    blocked_domains=[               # 阻止的域名
        "malware.com",
        "evil.com",
    ],
)
```

---

## 測試結果

```
============================================================
Sandbox Manager Tests
============================================================
✓ Sandbox manager created
✓ Sandbox created with temp directory
✓ Sandbox cleaned up properly
✓ Path access control (/etc/passwd blocked, /tmp allowed)
✓ Active sandboxes tracked
✓ Sandbox stats retrieved

============================================================
Resource Limiter Tests
============================================================
✓ Resource limiter created
✓ Current metrics retrieved (CPU: 0.1%, Memory: 21.6MB)
✓ Resource limiting context working
✓ System stats retrieved (CPU: 9.9%, Memory: 77.4%, Disk: 13.0%)
✓ Limiter stats retrieved

============================================================
Security Validator Tests
============================================================
✓ Default policy created
✓ Strict policy created
✓ Input validation (dangerous commands blocked)
✓ Sensitive file access blocked
✓ Command validation working
✓ File path validation working
✓ URL validation (domains filtered)
✓ Input sanitization working
✓ 5 violations tracked correctly
```

---

## 技術亮點

1. **異步上下文管理器**: 使用 `@asynccontextmanager` 實現沙盒資源自動管理
2. **資源監控**: 使用 `psutil` 實現跨平台資源監控
3. **模式匹配**: 使用正則表達式偵測危險指令和敏感檔案
4. **違規追蹤**: 記錄所有安全違規事件供審計
5. **靈活配置**: 支援多層級安全策略（預設、嚴格、自訂）

---

## 安全功能

### 輸入驗證
- 長度限制（10,000 字元）
- 危險指令偵測
- 敏感檔案存取偵測
- Null bytes 移除

### 指令執行
- 指令白名單機制
- 危險指令攔截
- 執行超時控制

### 檔案系統
- 敏感路徑保護
- 檔案大小限制（10MB）
- 寫入權限控制

### 網路存取
- 域名黑名單
- 域名白名單
- 可選完全禁用

---

## 新增檔案

```
src/core/
├── sandbox.py              # 沙盒環境管理器
├── resource_limiter.py     # 資源限制器
└── security.py             # 安全策略驗證器

tests/
└── test_sandbox.py         # 沙盒環境測試
```

---

## 使用範例

### 沙盒執行

```python
from core.sandbox import SandboxConfig, SandboxManager

config = SandboxConfig(
    enabled=True,
    max_memory_mb=256,
    network_access=False,
)
sandbox = SandboxManager(config)

async with sandbox.create_sandbox("task_123") as ctx:
    # 執行受保護的任務
    print(f"Temp dir: {ctx['tmp_dir']}")
# 沙盒自動清理
```

### 資源限制

```python
from core.resource_limiter import ResourceLimiter

limiter = ResourceLimiter(
    max_cpu_percent=50.0,
    max_memory_mb=256.0,
)

async with limiter.limit_resources("task_123"):
    # 執行受監控的任務
    pass
```

### 安全驗證

```python
from core.security import SecurityValidator

validator = SecurityValidator()

# 驗證輸入
valid, error = validator.validate_input("rm -rf /")
if not valid:
    print(f"Blocked: {error}")

# 驗證檔案路徑
valid, error = validator.validate_file_path("/etc/passwd")
if not valid:
    print(f"Blocked: {error}")
```

---

## 下一步階段

**Phase 9: 測試與文檔**
- 整合測試
- 完整文檔
- 部署指南
- 使用範例

---

## 附錄

### 測試依賴

新增 `psutil` 依賴用於資源監控：

```
psutil==7.2.1
```

### 資源限制注意事項

1. **記憶體限制**: 在某些系統上可能無法設定低於當前限制的值
2. **CPU 時間**: 僅影響當前進程，不影響子進程
3. **檔案描述符**: 系統範圍限制可能優先於進程限制

### 安全策略建議

**生產環境**:
- 使用嚴格策略（`create_strict_policy()`）
- 禁用指令執行
- 限制網路存取
- 使用域名白名單

**開發環境**:
- 使用預設策略（`create_default_policy()`）
- 允許檔案寫入
- 允許網路存取
- 啟用違規日誌
