# Storage Adapter Layer 實作計劃

## 計劃概述

建立抽象的 Storage Adapter 層，支援兩種部署版本：
- **Personal Edition (個人版)**: SQLite 資料庫，單一 Docker 容器部署
- **Enterprise Edition (企業版)**: PostgreSQL + Redis，Docker Compose 多實例部署

同時設計 Adapter 模式以支援未來的 AI 向量資料庫整合（Qdrant, Milvus, Pinecone 等）。

---

## 當前狀態分析

### 現有架構

專案目前使用檔案系統儲存：
```
storage/
├── tasks/           # JSON 檔案儲存任務定義
└── logs/           # 文字日誌檔案
```

### 痛點與限制

1. **無法水平擴展**: 檔案系統無法在多實例間共享
2. **缺少交易支援**: 無法保證資料一致性
3. **查詢效率低**: 無法複雜查詢或索引
4. **無法整合 RAG**: 未來需要向量資料庫支援
5. **版本差異大**: 個人與企業需求不同

---

## 架構設計

### 整體架構圖

```
┌─────────────────────────────────────────────────────────────────┐
│                         Application Layer                        │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────┐│
│  │   Agent     │  │   Scheduler  │  │         GUI             ││
│  │  Manager    │  │              │  │                         ││
│  └──────┬──────┘  └──────┬───────┘  └──────────┬──────────────┘│
│         │                │                      │               │
└─────────┼────────────────┼──────────────────────┼───────────────┘
          │                │                      │
          └────────────────┴──────────────────────┘
                           │
         ┌─────────────────┴─────────────────┐
         │                                       │
    ┌────┴──────────────────────────────────┴────┐
    │         Storage Adapter Layer              │
    │  ┌──────────────────────────────────────┐  │
    │  │      StorageAdapter (Abstract)       │  │
    │  │  - save_task()                       │  │
    │  │  - get_task()                        │  │
    │  │  - list_tasks()                      │  │
    │  │  - delete_task()                     │  │
    │  │  - save_log()                        │  │
    │  │  - query_logs()                      │  │
    │  │  - initialize()                      │  │
    │  └──────────────────────────────────────┘  │
    │            ▲           ▲          ▲         │
    │            │           │          │         │
    │  ┌─────────┴───┐  ┌──┴──────┐  ─┴─────────┐│
    │  │ SQLite      │  │PostgreSQL│ │Redis Cache ││
    │  │ Adapter     │  │ Adapter  │  │ Adapter   ││
    │  └─────────────┘  └──────────┘  └───────────┘│
    └──────────────────────────────────────────────┘
                    │
    ┌───────────────┴───────────────────────────────┐
    │              Storage Backend                 │
    │  ┌──────────┐  ┌───────────┐  ┌────────────┐ │
    │  │ Personal │  │Enterprise │  │  Vector DB │ │
    │  │  SQLite  │  │PostgreSQL │  │ (Future)   │ │
    │  │          │  │+  Redis   │  │            │ │
    │  └──────────┘  └───────────┘  └────────────┘ │
    └───────────────────────────────────────────────┘
```

---

## 介面定義

### Core Storage Interface

```python
# src/storage/base_adapter.py

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

class StorageAdapter(ABC):
    """Storage adapter abstract base class"""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize storage backend"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close storage connection"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if storage is accessible"""
        pass

    # Task Management
    @abstractmethod
    async def save_task(self, task: Dict[str, Any]) -> str:
        """Save or update a task, returns task ID"""
        pass

    @abstractmethod
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by ID"""
        pass

    @abstractmethod
    async def list_tasks(
        self,
        agent_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List tasks with optional filters"""
        pass

    @abstractmethod
    async def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        pass

    @abstractmethod
    async def update_task_status(
        self,
        task_id: str,
        status: str,
        last_run: Optional[datetime] = None,
        next_run: Optional[datetime] = None
    ) -> bool:
        """Update task execution status"""
        pass

    # Log Management
    @abstractmethod
    async def save_log(
        self,
        task_id: str,
        level: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Save a log entry, returns log ID"""
        pass

    @abstractmethod
    async def query_logs(
        self,
        task_id: Optional[str] = None,
        level: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query logs with filters"""
        pass

    @abstractmethod
    async def delete_old_logs(self, before: datetime) -> int:
        """Delete logs older than specified date, returns count"""
        pass

    # Metadata (for future use)
    @abstractmethod
    async def save_metadata(self, key: str, value: Any) -> None:
        """Save metadata key-value pair"""
        pass

    @abstractmethod
    async def get_metadata(self, key: str) -> Optional[Any]:
        """Get metadata value by key"""
        pass

    # Transaction Support
    @abstractmethod
    async def begin_transaction(self) -> Any:
        """Begin a transaction"""
        pass

    @abstractmethod
    async def commit_transaction(self, transaction: Any) -> None:
        """Commit a transaction"""
        pass

    @abstractmethod
    async def rollback_transaction(self, transaction: Any) -> None:
        """Rollback a transaction"""
        pass
```

### Cache Interface

```python
# src/storage/base_cache.py

from abc import ABC, abstractmethod
from typing import Optional, Any, List
from datetime import timedelta

class CacheAdapter(ABC):
    """Cache adapter abstract base class"""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize cache backend"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close cache connection"""
        pass

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[timedelta] = None
    ) -> bool:
        """Set value in cache with optional TTL"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        pass

    @abstractmethod
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern, returns count"""
        pass
```

### Vector Store Interface (Future)

```python
# src/storage/base_vector_store.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class VectorStoreAdapter(ABC):
    """Vector store adapter for RAG support"""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize vector store"""
        pass

    @abstractmethod
    async def add_documents(
        self,
        documents: List[str],
        metadata: List[Dict[str, Any]],
        embeddings: Optional[List[List[float]]] = None
    ) -> List[str]:
        """Add documents to vector store, returns document IDs"""
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search similar documents"""
        pass

    @abstractmethod
    async def delete_documents(self, document_ids: List[str]) -> int:
        """Delete documents by IDs, returns count"""
        pass
```

---

## 實作步驟

### Step 1: Storage Adapter Interface

**目標**: 建立抽象介面和工廠模式

**驗收標準**:
- [ ] `StorageAdapter` 抽象類別完成
- [ ] `CacheAdapter` 抽象類別完成
- [ ] `VectorStoreAdapter` 抽象類別完成（預留）
- [ ] `StorageFactory` 工廠類別完成
- [ ] 配置系統整合完成
- [ ] 單元測試通過

**估計工時**: 3 小時

**檔案結構**:
```
src/storage/
├── __init__.py
├── base_adapter.py      # StorageAdapter ABC
├── base_cache.py        # CacheAdapter ABC
├── base_vector_store.py # VectorStoreAdapter ABC
└── factory.py           # StorageFactory
```

---

### Step 2: SQLite Adapter (Personal Edition)

**目標**: 實現 SQLite 適配器，支援單機部署

**驗收標準**:
- [ ] `SQLiteAdapter` 類別實現
- [ ] 資料庫 Schema 設計完成
- [ ] 資料庫 Migration 機制完成
- [ ] 交易支援實現
- [ ] 連接池管理（SQLite）
- [ ] 單元測試通過

**估計工時**: 4 小時

**資料庫 Schema**:
```sql
-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    task_prompt TEXT NOT NULL,
    schedule_type TEXT NOT NULL,
    schedule_value TEXT NOT NULL,
    repeat INTEGER DEFAULT 0,
    repeat_interval TEXT,
    enabled INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_run TIMESTAMP,
    next_run TIMESTAMP,
    status TEXT DEFAULT 'pending'
);

CREATE INDEX idx_tasks_agent ON tasks(agent_name);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_enabled ON tasks(enabled);

-- Logs table
CREATE TABLE IF NOT EXISTS logs (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata TEXT,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX idx_logs_task ON logs(task_id);
CREATE INDEX idx_logs_level ON logs(level);
CREATE INDEX idx_logs_created ON logs(created_at);

-- Metadata table
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

**檔案**: `src/storage/sqlite_adapter.py`

---

### Step 3: PostgreSQL Adapter (Enterprise Edition)

**目標**: 實現 PostgreSQL 適配器，支援多實例部署

**驗收標準**:
- [ ] `PostgreSQLAdapter` 類別實現
- [ ] SQLAlchemy 整合完成
- [ ] 連接池配置完成
- [ ] 交易支援實現
- [ ] 資料庫 Migration 機制（Alembic）
- [ ] 單元測試通過

**估計工時**: 5 小時

**檔案**: `src/storage/postgres_adapter.py`

**額外功能**:
```python
# Connection pooling
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

engine = create_async_engine(
    "postgresql+asyncpg://user:pass@localhost/dbname",
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections
    pool_recycle=3600    # Recycle after 1 hour
)
```

---

### Step 4: Redis Cache (Enterprise Edition)

**目標**: 實現 Redis 緩存適配器

**驗收標準**:
- [ ] `RedisCacheAdapter` 類別實現
- [ ] 連接池配置完成
- [ ] TTL 支援實現
- [ ] Pipeline 支援實現
- [ ] 單元測試通過

**估計工時**: 3 小時

**檔案**: `src/storage/redis_cache.py`

**緩存策略**:
```python
# Task cache
CACHE_KEY_TASK = "task:{task_id}"
TTL_TASK = 300  # 5 minutes

# Task list cache
CACHE_KEY_TASK_LIST = "tasks:{agent_name}:{status}"
TTL_TASK_LIST = 60  # 1 minute

# Agent response cache
CACHE_KEY_RESPONSE = "response:{agent_name}:{prompt_hash}"
TTL_RESPONSE = 600  # 10 minutes
```

---

### Step 5: 整合與測試

**目標**: 整合 Storage Adapter 到現有系統

**驗收標準**:
- [ ] Agent Manager 整合 Storage Adapter
- [ ] Task Scheduler 整合 Storage Adapter
- [ ] GUI 支援切換 Storage Backend
- [ ] 配置檔案支援兩種版本
- [ ] 整合測試通過
- [ ] E2E 測試通過

**估計工時**: 4 小時

**配置範例**:
```yaml
# config/storage.yaml (Personal Edition)
storage:
  type: "sqlite"
  sqlite:
    path: "./storage/data.db"
    pool_size: 5

# config/storage.yaml (Enterprise Edition)
storage:
  type: "postgresql"
  postgresql:
    host: "${DB_HOST}"
    port: 5432
    database: "qwen_agent"
    user: "${DB_USER}"
    password: "${DB_PASSWORD}"
    pool_size: 20
    max_overflow: 40

  cache:
    type: "redis"
    redis:
      host: "${REDIS_HOST}"
      port: 6379
      db: 0
      password: "${REDIS_PASSWORD}"
      pool_size: 10
```

---

## 部署策略

### Personal Edition (個人版)

**特點**:
- 單一 Docker 容器
- SQLite 嵌入式資料庫
- 無需額外服務
- 適合個人使用

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

# Install SQLite dependencies
RUN apt-get update && apt-get install -y sqlite3

COPY requirements.txt .
RUN pip install -r requirements.txt

# SQLite storage will be at /app/storage/data.db
VOLUME ["/app/storage"]

CMD ["python", "-m", "src.main", "--storage", "sqlite"]
```

**啟動**:
```bash
docker run -d \
  -v qwen-data:/app/storage \
  -p 8000:8000 \
  -p 7860:7860 \
  qwen-agent-scheduler:personal
```

---

### Enterprise Edition (企業版)

**特點**:
- Docker Compose 編排
- PostgreSQL 資料庫
- Redis 緩存
- 支援多實例
- 適合商業使用

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: qwen_agent
      POSTGRES_USER: qwen
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U qwen"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  qwen-agent-1:
    image: qwen-agent-scheduler:enterprise
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - STORAGE_TYPE=postgresql
      - DB_HOST=postgres
      - DB_PASSWORD=${DB_PASSWORD}
      - REDIS_HOST=redis
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    ports:
      - "8001:8000"

  qwen-agent-2:
    image: qwen-agent-scheduler:enterprise
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - STORAGE_TYPE=postgresql
      - DB_HOST=postgres
      - DB_PASSWORD=${DB_PASSWORD}
      - REDIS_HOST=redis
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    ports:
      - "8002:8000"

  nginx:
    image: nginx:alpine
    depends_on:
      - qwen-agent-1
      - qwen-agent-2
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    ports:
      - "80:80"

volumes:
  postgres-data:
  redis-data:
```

**啟動**:
```bash
docker-compose --profile enterprise up -d
```

---

## 未來擴展

### 向量資料庫整合

**支援的向量資料庫**:
- **Qdrant**: 開源，易於部署
- **Milvus**: 開源，高效能
- **Pinecone**: 託管服務
- **Weaviate**: 開源，GraphQL API
- **Chroma**: 輕量級，易於整合

**RAG 使用案例**:
1. **知識庫檢索**: 從文檔中檢索相關資訊
2. **對話歷史**: 儲存和檢索過往對話
3. **工具使用記錄**: 檢索類似的工具使用案例
4. **任務執行範例**: 從過往任務中學習

**介面整合**:
```python
# Future: src/storage/qdrant_adapter.py
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

class QdrantVectorStore(VectorStoreAdapter):
    def __init__(self, config: QdrantConfig):
        self.client = QdrantClient(
            url=config.url,
            api_key=config.api_key
        )

    async def add_documents(self, documents, metadata, embeddings=None):
        # Implementation using Qdrant client
        pass
```

---

## 遷移策略

### 從檔案系統遷移到 SQLite

```bash
# Migration script
python scripts/migrate_to_sqlite.py --source ./storage --dest ./storage/data.db
```

### 從 SQLite 遷移到 PostgreSQL

```bash
# Database dump
python scripts/export_sqlite.py --db ./storage/data.db --output dump.sql

# Import to PostgreSQL
psql -h localhost -U qwen -d qwen_agent -f dump.sql
```

---

## 測試計劃

### 單元測試

```python
# tests/storage/test_sqlite_adapter.py
# tests/storage/test_postgres_adapter.py
# tests/storage/test_redis_cache.py
# tests/storage/test_factory.py
```

### 整合測試

```python
# tests/integration/test_storage_integration.py
async def test_task_lifecycle():
    # Test creating, reading, updating, deleting tasks
    pass

async def test_log_query():
    # Test log querying and filtering
    pass

async def test_cache_invalidation():
    # Test cache invalidation on task updates
    pass
```

### 效能測試

```python
# tests/performance/test_storage_performance.py
async def benchmark_task_operations():
    # Benchmark CRUD operations
    pass

async def benchmark_concurrent_access():
    # Test concurrent access patterns
    pass
```

---

## 文檔更新

### 需要更新的文檔

1. **README.md**:
   - 新增 Personal vs Enterprise 版本說明
   - 更新安裝步驟
   - 更新配置範例

2. **DEPLOYMENT.md**:
   - 新增 Personal Edition 部署指南
   - 新增 Enterprise Edition 部署指南
   - 更新遷移指南

3. **新增 STORAGE.md**:
   - Storage Adapter 詳細說明
   - 資料庫 Schema 說明
   - 緩存策略說明
   - 遷移指南

---

## 時間估算

| 步驟 | 任務 | 估計工時 |
|------|------|---------|
| 1 | Storage Adapter Interface | 3 小時 |
| 2 | SQLite Adapter | 4 小時 |
| 3 | PostgreSQL Adapter | 5 小時 |
| 4 | Redis Cache | 3 小時 |
| 5 | 整合與測試 | 4 小時 |
| **總計** | | **19 小時** |

---

## 風險與緩解

| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| SQLAlchemy 版本相容性 | 中 | 鎖定版本，完整測試 |
| SQLite 並發限制 | 低 | 使用 WAL 模式，限制連接池 |
| PostgreSQL 連接池耗盡 | 中 | 監控連接使用，自動回收 |
| Redis 單點故障 | 中 | 提供無 Redis 模式 |
| 遷移資料遺失 | 高 | 完整備份，驗證遷移 |

---

## 里程碑

| 里程碑 | 目標 | 驗收標準 | 狀態 |
|--------|------|---------|------|
| M1 | Interface Design | 抽象介面完成，工廠模式實現 | ⏳ 待開始 |
| M2 | SQLite Adapter | SQLite 適配器可用，測試通過 | ⏳ 待開始 |
| M3 | PostgreSQL Adapter | PostgreSQL 適配器可用，測試通過 | ⏳ 待開始 |
| M4 | Redis Cache | Redis 緩存可用，測試通過 | ⏳ 待開始 |
| M5 | Integration | 系統整合完成，E2E 測試通過 | ⏳ 待開始 |

---

## 相關 Issue/PR

- (待填寫)
