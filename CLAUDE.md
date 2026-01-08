# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AInTandem Agent MCP Scheduler is a local agent infrastructure built with Qwen Agent SDK, featuring:
- Customizable AI agents with MCP (Model Context Protocol) server integration
- Task scheduling with Cron, Interval, and One-time scheduling
- OpenAI-compatible REST API
- Gradio web interface
- Dual-edition storage: Personal (SQLite) and Enterprise (PostgreSQL + Redis)

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Testing
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_task_scheduler.py

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test function
pytest tests/test_config.py::test_load_storage_config
```

### Code Quality
```bash
# Format code (line length: 100)
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

### Running the Application
```bash
# Start all services (API + GUI)
python main.py

# Start individual components
python -m api.openapi_server     # API server on :8000
python -m gui.app                # GUI on :7860
```

## Architecture

### Storage Adapter Layer

The project uses a factory pattern with decorator-based registration for storage adapters. All adapters implement `StorageAdapter` interface from `src/storage/base_adapter.py`.

**Key Pattern**: Adapters are auto-registered via decorators when modules are imported:
```python
@register_storage_adapter("sqlite")
class SQLiteAdapter(StorageAdapter):
    ...
```

**Critical**: To ensure adapters are registered, import them in `src/storage/__init__.py`:
```python
from . import sqlite_adapter  # noqa: F401
from . import postgres_adapter  # noqa: F401
```

**Storage Types**:
- `sqlite` - Personal edition, embedded database
- `postgresql` - Enterprise edition, connection pooling
- `file` - Legacy JSON file storage (backward compatible)

**Cache Types**:
- `memory` - In-memory LRU cache
- `redis` - Distributed Redis cache

### Configuration System

Configuration is YAML-based with environment variable substitution using `${VAR_NAME}` syntax. The `ConfigManager` class in `src/core/config.py` loads configs from `config/` directory:

- `llm.yaml` - LLM provider settings
- `agents.yaml` - Agent definitions
- `mcp_servers.yaml` - MCP server configurations
- `app.yaml` - Application settings
- `storage.yaml` - Storage & cache configuration (edition switching)

**Environment Substitution**: Use `substitute_env_recursive()` for config values containing `${VAR}` or `$VAR`.

### Task Scheduling with Storage Integration

`TaskScheduler` supports dual storage modes:
1. **Database mode** (when `storage_adapter` is provided): Uses `StorageAdapter` for persistence
2. **File mode** (backward compatible): Uses JSON files in `storage/tasks/`

**DateTime Handling**: Always pass datetime objects (not pre-serialized strings) to storage adapters. Each adapter handles its own serialization:
- SQLite: ISO format strings
- PostgreSQL: timestamp objects

### MCP Integration

`MCPBridge` manages connections to MCP servers via `MCPStdioClient`. Tools are converted through `MultiMCPToolConverter` to provide unified function calling interface.

### Agent Manager with Cache

`AgentManager` supports optional response caching via `CacheAdapter`:
- Cache keys: SHA256 hash of `agent_name:prompt:sorted_kwargs`
- Format: `agent_response:{agent_name}:{hash_digest[:16]}`
- Default TTL: 600 seconds

### Dual Edition Switching

Edition is controlled by `config/storage.yaml`:

**Personal Edition** (default, no config needed):
```yaml
storage:
  type: sqlite
  sqlite:
    path: "./storage/data.db"
cache:
  type: memory
```

**Enterprise Edition**:
```yaml
storage:
  type: postgresql
  postgresql:
    host: "${DB_HOST}"
    port: 5432
    database: qwen_agent
    user: "${DB_USER}"
    password: "${DB_PASSWORD}"
cache:
  type: redis
  redis:
    host: "${REDIS_HOST}"
    port: 6379
```

## Important Implementation Notes

### Backward Compatibility
- `TaskScheduler` and `AgentManager` work without storage/cache adapters (file/memory fallback)
- Missing `storage.yaml` defaults to file-based storage
- All existing tests pass without storage adapters

### Storage Adapter Integration Pattern
1. Create adapter using `create_storage_from_config()` helper
2. Pass to component constructor: `TaskScheduler(config, storage_adapter=storage)`
3. Component checks `if storage_adapter is not None` to determine mode
4. Call `await storage_adapter.initialize()` before use
5. Call `await storage_adapter.close()` on shutdown

### Test Structure
- Unit tests: `tests/test_*.py` - Test individual components
- Storage tests: `tests/test_storage_adapters.py` - Test adapter implementations
- Integration tests: `tests/test_*_integration.py` - Test component + adapter integration
- E2E tests: `tests/test_e2e_*.py` - Test complete workflows

### Path Handling
- Always use `pathlib.Path` for file paths
- Create directories with `Path.mkdir(parents=True, exist_ok=True)`
- `sys.path.insert(0, str(Path(__file__).parent / "src"))` for imports from main.py

### Async/Await Patterns
- All storage and cache operations are async
- Use `asyncio.Lock()` for thread safety in async contexts
- APScheduler uses `AsyncIOScheduler` for async task execution
