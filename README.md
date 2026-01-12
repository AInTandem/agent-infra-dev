# AInTandem Agent MCP Scheduler

A comprehensive local agent infrastructure built with Qwen Agent SDK, featuring **Dual SDK Architecture** (Qwen + Claude), MCP server integration, task scheduling, OpenAI-compatible API, Gradio GUI, and dual-edition storage support.

## Features

- **🔄 Dual SDK Architecture**: Choose between Qwen Agent SDK or Claude Agent SDK per agent
  - **Qwen SDK**: Support for multiple LLM providers (OpenAI, DeepSeek, GLM, etc.)
  - **Claude SDK**: Native support for Computer Use and Extended Thinking
  - **Unified Interface**: Both SDKs implement the same `IAgentAdapter` interface
- **Customizable Agents**: Define agents with custom system prompts and MCP server integrations
- **MCP Server Integration**: Seamlessly integrate Model Context Protocol servers via YAML configuration
  - **Dual Transport Support**: Stdio for local servers, SSE for remote/streaming servers
  - **Streaming Tool Execution**: Real-time streaming responses via Server-Sent Events (SSE)
- **⚡ WebSocket Streaming Chat**: Real-time agent reasoning with live step-by-step display
  - See agent's thought process as it happens
  - Color-coded reasoning steps (thoughts, tool use, results)
  - Auto-reconnect on connection loss
- **Task Scheduling**: Schedule automated agent tasks with Cron, Interval, and One-time scheduling
- **OpenAI-Compatible API**: REST API compatible with OpenAI's chat completions and function calling
- **Gradio GUI**: User-friendly web interface with modular tab architecture
- **Sandbox Execution**: Isolated execution environment with resource limits and security policies
- **Dual Edition Storage**: Support for both Personal (SQLite) and Enterprise (PostgreSQL + Redis) deployments

## Quick Start: WebSocket Streaming Chat

Experience real-time agent reasoning in 3 steps:

1. **Start the application**:
   ```bash
   python main.py
   ```

2. **Open the GUI**:
   - Navigate to http://localhost:7860
   - Click the **"⚡ Real-Time Chat"** tab

3. **Connect and Chat**:
   - Click **"Connect"** to establish WebSocket connection
   - Select an agent (e.g., "researcher")
   - Type your message and click **"Send"**
   - Watch reasoning steps appear in real-time!

**What you'll see**:
- 💭 Blue cards - Agent's thinking process
- 🔧 Orange cards - Tools being called
- 📊 Purple cards - Tool execution results
- ✅ Green cards - Final answer

For detailed documentation, see [docs/websocket-streaming-reasoning.md](docs/websocket-streaming-reasoning.md).

## HTTP Streaming API

Experience OpenAI-compatible streaming responses for API clients:

### Python SDK Usage

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="test"  # Not used for authentication
)

stream = client.chat.completions.create(
    model="researcher",
    messages=[{"role": "user", "content": "Count to 5"}],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

### cURL Usage

```bash
curl -N http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "researcher",
    "messages": [{"role": "user", "content": "Say hello"}],
    "stream": true
  }'
```

### LangChain Integration

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://localhost:8000/v1",
    model="researcher",
    streaming=True
)

response = await llm.ainvoke("Say hello")
```

**Features:**
- OpenAI-compatible SSE (Server-Sent Events) format
- Token-level or chunk-level streaming
- Compatible with OpenAI Python SDK
- Works with LangChain, LlamaIndex, and more

## Dual SDK Architecture

The system supports **both Qwen Agent SDK and Claude Agent SDK** simultaneously, allowing you to choose the best SDK for each agent's requirements.

### SDK Comparison

| Feature | Qwen SDK | Claude SDK |
|---------|-----------|-------------|
| **Multi-LLM Support** | ✅ OpenAI, DeepSeek, GLM, etc. | ❌ Claude models only |
| **Computer Use** | ❌ | ✅ Direct browser/system control |
| **Extended Thinking** | ❌ | ✅ Deep reasoning mode |
| **MCP Integration** | ✅ | ✅ |
| **Function Calling** | ✅ | ✅ Native support |
| **Streaming** | ✅ | ✅ Native support |

### When to Use Each SDK

**Use Qwen SDK for:**
- Multi-LLM deployments (cost optimization)
- Agents using non-Claude models (GPT-4, DeepSeek, GLM)
- Simple query-response tasks
- High-volume automated tasks

**Use Claude SDK for:**
- Computer Use tasks (web automation, form filling, data entry)
- Complex reasoning requiring Extended Thinking
- Tasks benefiting from Claude's native tool calling
- Agents that need browser interaction capabilities

### Configuration

Configure SDK selection in `config/agents.yaml`:

```yaml
agents:
  # Qwen SDK agent (default)
  - name: "researcher"
    llm_model: "glm-4.7"
    sdk: "qwen"  # Optional - auto-detected from model name
    mcp_servers: ["filesystem", "web-search"]
    enabled: true

  # Claude SDK agent with Computer Use
  - name: "browser_assistant"
    llm_model: "claude-3-5-sonnet-20241022"
    sdk: "claude"  # Required for Claude-specific features
    computer_use_enabled: true
    extended_thinking_enabled: true
    mcp_servers: ["filesystem"]
    enabled: false  # Set to true when ANTHROPIC_API_KEY is configured
```

### Claude SDK Setup

To use Claude SDK features (Computer Use, Extended Thinking):

1. **Install the Claude SDK**:
   ```bash
   pip install anthropic
   ```

2. **Set your API key**:
   ```bash
   export ANTHROPIC_API_KEY=your_key_here
   ```

3. **Add a Claude provider to `config/llm.yaml`**:
   ```yaml
   providers:
     claude:
       api_key: "${ANTHROPIC_API_KEY}"
       base_url: https://api.anthropic.com/v1
       description: Anthropic Claude - Computer Use & Extended Thinking
   ```

4. **Enable a Claude agent** in `config/agents.yaml`

For detailed documentation, see [docs/DUAL_SDK_ARCHITECTURE.md](docs/DUAL_SDK_ARCHITECTURE.md).

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     AInTandem Agent MCP Scheduler               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Gradio    │  │   FastAPI   │  │     CLI     │              │
│  │     GUI     │  │     API     │  │  Interface  │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                     │
│         └────────────────┴────────────────┘                     │
│                          │                                      │
│         ┌────────────────┴────────────────┐                     │
│         │         Core Components          │                    │
│         ├──────────────────────────────────┤                    │
│         │  AgentManager │  TaskScheduler   │                    │
│         │  MCPBridge    │  SandboxManager  │                    │
│         │  ConfigManager│  SecurityPolicy  │                    │
│         └──────────────────────────────────┘                    │
│                          │                                      │
│         ┌────────────────┴────────────────┐                     │
│         │            Agents               │                     │
│         ├─────────────────────────────────┤                     │
│         │  Researcher  │  Developer       │                     │
│         │  Writer      │  Analyst         │                     │
│         └─────────────────────────────────┘                     │
│                          │                                      │
│         ┌────────────────┴────────────────┐                     │
│         │          MCP Servers            │                     │
│         ├─────────────────────────────────┤                     │
│         │  Filesystem  │  Web-Search      │                     │
│         │  GitHub      │  PostgreSQL      │                     │
│         │  Google-Maps │  Puppeteer       │                     │
│         └─────────────────────────────────┘                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.10+
- pip or uv
- Node.js (for MCP servers)

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd agent-infra

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. Copy example configuration:
```bash
cp .env.example .env
```

2. Edit `.env` with your API keys:
```bash
# LLM Provider (OpenAI-compatible)
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1

# Or for DeepSeek
DEEPSEEK_API_KEY=your_deepseek_key
```

3. Review configuration files in `config/` directory:
   - `config/llm.yaml` - LLM provider settings
   - `config/agents.yaml` - Agent definitions
   - `config/mcp_servers.yaml` - MCP server configurations
   - `config/app.yaml` - Application settings
   - `config/storage.yaml` - Storage and cache configuration

### Storage Configuration

The system supports two deployment editions with different storage backends:

#### Personal Edition (SQLite)

Single-container deployment with embedded SQLite database:

```yaml
# config/storage.yaml
storage:
  type: sqlite
  sqlite:
    path: "./storage/data.db"
    enable_wal: true

cache:
  type: memory
  max_size: 1000
  default_ttl: 300
```

**Features**:
- No external dependencies
- Easy backup (single file)
- Suitable for personal use and testing

#### Enterprise Edition (PostgreSQL + Redis)

Multi-instance deployment with production-grade storage:

```yaml
# config/storage.yaml
storage:
  type: postgresql
  postgresql:
    host: "${DB_HOST}"
    port: 5432
    database: qwen_agent
    user: "${DB_USER}"
    password: "${DB_PASSWORD}"
    pool_size: 20

cache:
  type: redis
  redis:
    host: "${REDIS_HOST}"
    port: 6379
    password: "${REDIS_PASSWORD}"
```

**Features**:
- Horizontal scaling support
- Connection pooling
- Distributed caching
- Suitable for production and multi-user environments

#### File-based Storage (Legacy)

For backward compatibility, the system supports file-based storage:

```yaml
storage:
  type: file
cache:
  type: none
```

This uses JSON files in `storage/tasks/` for persistence.

### Running the Application

```bash
# Start all services (API + GUI)
python main.py

# Or start individual components
python -m api.openapi_server     # API server on :8000
python -m gui.app                # GUI on :7860
```

### Access Points

- **Gradio GUI**: http://localhost:7860
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Configuration

### LLM Configuration (`config/llm.yaml`)

```yaml
llm:
  provider: "openai_compatible"
  base_url: "https://api.openai.com/v1"
  api_key: "${OPENAI_API_KEY}"
  default_model: "gpt-4"
  models:
    - name: "gpt-4"
      provider: "openai"
    - name: "qwen-turbo"
      provider: "dashscope"
```

### Agent Configuration (`config/agents.yaml`)

```yaml
agents:
  - name: "researcher"
    role: "Research Assistant"
    description: "Professional research assistant with web search capabilities"
    system_prompt: |
      You are a professional research assistant. Help users find and analyze information.
    mcp_servers: ["filesystem", "web-search"]
    llm_model: "gpt-4"
    enabled: true

  - name: "developer"
    role: "Code Assistant"
    description: "Programming assistant with code execution capabilities"
    system_prompt: |
      You are a programming assistant. Help users write, debug, and optimize code.
    mcp_servers: ["filesystem", "github"]
    llm_model: "gpt-4"
    enabled: true
```

### MCP Server Configuration (`config/mcp_servers.yaml`)

The system supports MCP servers via two transport types:

- **stdio**: Standard input/output (default, for local MCP servers)
- **sse**: Server-Sent Events (for remote/streaming MCP servers)

For detailed MCP server configuration, see [docs/MCP_SERVER_CONFIGURATION.md](docs/MCP_SERVER_CONFIGURATION.md).

**Quick Example**:
```yaml
mcp_servers:
  # Local stdio server
  - name: "filesystem"
    transport: "stdio"
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "${AGENT_ROOT_PATH}"]
    enabled: true

  # Remote SSE server (streaming support)
  - name: "remote-mcp-server"
    transport: "sse"
    sse:
      url: "https://api.example.com/mcp/sse"
      headers:
        Authorization: "Bearer ${MCP_SERVER_TOKEN}"
    enabled: false
```

**Available Official Servers**:
- `@modelcontextprotocol/server-filesystem` - File system access
- `@modelcontextprotocol/server-brave-search` - Web search
- `mcp-server-github` - GitHub integration
- `mcp-server-postgres` - PostgreSQL database
- `@modelcontextprotocol/server-google-maps` - Google Maps services
- `@modelcontextprotocol/server-puppeteer` - Web automation

## API Usage

### Chat Completions (Non-Streaming)

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "researcher",
    "messages": [
      {"role": "user", "content": "Search for recent AI papers"}
    ],
    "temperature": 0.7
  }'
```

### Chat Completions (Streaming)

```bash
curl -N http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "researcher",
    "messages": [
      {"role": "user", "content": "Count to 5"}
    ],
    "stream": true
  }'
```

**Response Format (SSE):**
```
data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"researcher","choices":[{"delta":{"content":"1"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"researcher","choices":[{"delta":{"content":", 2"},"finish_reason":null}]}

data: {"id":"chatcmpl-xxx","object":"chat.completion.chunk","created":1234567890,"model":"researcher","choices":[{"delta":{},"finish_reason":"stop"}]}
```

### Function Calling (Create Scheduled Task)

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "researcher",
    "messages": [
      {"role": "user", "content": "Schedule a daily report at 9 AM"}
    ],
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "create_scheduled_task",
          "arguments": "{\"name\": \"Daily Report\", \"agent_name\": \"analyst\", \"task_prompt\": \"Generate daily report\", \"schedule_type\": \"cron\", \"schedule_value\": \"0 9 * * *\", \"repeat\": true}"
        }
      }
    ]
  }'
```

### Available Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/chat/completions` | POST | Chat completions (OpenAI-compatible) |
| `/v1/agents` | GET | List all agents |
| `/v1/agents/{name}` | GET | Get agent details |
| `/v1/tasks` | GET | List all tasks |
| `/v1/tasks/{id}` | GET | Get task details |
| `/v1/tasks/{id}/enable` | POST | Enable task |
| `/v1/tasks/{id}/disable` | POST | Disable task |
| `/v1/tasks/{id}` | DELETE | Cancel task |
| `/sse/tools/call` | POST | Stream MCP tool execution (SSE) |
| `/sse/tools/call/by-name` | POST | Stream tool by full name (SSE) |
| `/sse/tools` | GET | List tools with streaming support |
| `/sse/servers` | GET | List MCP servers with transport info |
| `/ws/chat/{session_id}` | WebSocket | Real-time agent chat with reasoning |

## Task Scheduling

### Schedule Types

1. **Cron**: Unix cron expression
   ```python
   schedule_type = "cron"
   schedule_value = "0 9 * * *"  # Daily at 9 AM
   ```

2. **Interval**: Seconds between runs
   ```python
   schedule_type = "interval"
   schedule_value = "300"  # Every 5 minutes
   ```

3. **Once**: Specific datetime (ISO format)
   ```python
   schedule_type = "once"
   schedule_value = "2026-01-06T20:00:00"
   ```

### GUI Task Creation

1. Navigate to "Tasks" tab in Gradio GUI
2. Fill in task details:
   - Task name
   - Select agent
   - Task prompt
   - Schedule type and value
   - Repeat setting
3. Click "Create Task"

## Sandbox & Security

### Sandbox Configuration

The sandbox provides execution isolation with resource limits:

```python
from core.sandbox import SandboxConfig, SandboxManager

config = SandboxConfig(
    enabled=True,
    max_memory_mb=512,
    max_cpu_time=30,
    max_wall_time=60,
    network_access=True,
)
```

### Security Policies

```python
from core.security import SecurityPolicy, SecurityValidator

policy = SecurityPolicy(
    allow_command_execution=False,
    allow_file_write=True,
    allow_network_access=True,
    blocked_domains=["malware.com"],
)

validator = SecurityValidator(policy)

# Validate input
valid, error = validator.validate_input(user_input)
if not valid:
    print(f"Blocked: {error}")
```

### Protected Paths

The following paths are automatically protected:
- `/etc/passwd`, `/etc/shadow`, `/etc/sudoers`
- `~/.ssh`, `~/.gnupg`
- `.env`, `.aws/credentials`
- Files containing: `secret`, `password`, `token`

## Development

### Running Tests

```bash
# Unit tests
pytest tests/

# Integration tests
python tests/test_integration.py

# Specific module tests
python tests/test_config.py
python tests/test_agent_manager.py
python tests/test_task_scheduler.py
python tests/test_sandbox.py
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

## Project Structure

```
agent-infra/
├── config/                 # Configuration files
│   ├── llm.yaml           # LLM provider settings
│   ├── agents.yaml        # Agent definitions
│   ├── mcp_servers.yaml   # MCP server configs
│   ├── app.yaml           # Application settings
│   └── storage.yaml       # Storage & cache configuration
├── docs/                  # Documentation
│   ├── MCP_SERVER_CONFIGURATION.md  # MCP server configuration guide
│   └── MCP_TROUBLESHOOTING.md  # MCP server troubleshooting guide
├── src/
│   ├── core/              # Core components
│   │   ├── config.py      # Configuration management
│   │   ├── agent_manager.py  # Agent lifecycle (with SDK factory)
│   │   ├── agent_adapter.py  # Unified agent adapter interface
│   │   ├── qwen_agent_adapter.py  # Qwen SDK adapter
│   │   ├── claude_agent_adapter.py # Claude SDK adapter (Computer Use)
│   │   ├── task_scheduler.py  # Task scheduling
│   │   ├── mcp_bridge.py  # MCP integration (stdio + SSE)
│   │   ├── mcp_stdio_client.py  # MCP stdio client
│   │   ├── mcp_sse_client.py    # MCP SSE client (streaming)
│   │   ├── mcp_tool_converter.py  # MCP tool format converter
│   │   ├── sandbox.py     # Sandbox environment
│   │   ├── resource_limiter.py  # Resource limits
│   │   ├── security.py    # Security policies
│   │   └── storage_helpers.py  # Storage adapter helpers
│   ├── storage/           # Storage Adapter Layer
│   │   ├── base_adapter.py      # Storage adapter interface
│   │   ├── base_cache.py        # Cache adapter interface
│   │   ├── base_vector_store.py # Vector store interface (RAG)
│   │   ├── factory.py           # Adapter factory
│   │   ├── config.py            # Storage configuration models
│   │   ├── sqlite_adapter.py     # SQLite implementation
│   │   ├── postgres_adapter.py   # PostgreSQL implementation
│   │   └── redis_cache.py        # Cache implementations
│   ├── agents/            # Agent implementations
│   │   └── base_agent.py  # Base agent class
│   ├── api/               # REST API
│   │   ├── openapi_server.py  # FastAPI server
│   │   ├── sse_endpoints.py    # SSE endpoints for streaming
│   │   └── websocket_endpoints.py  # WebSocket endpoints
│   └── gui/               # Web interface
│       └── app.py         # Gradio GUI
├── storage/               # Local storage (legacy)
│   ├── tasks/             # Task persistence
│   └── logs/              # Application logs
├── tests/                 # Test suite
│   ├── test_*.py          # Unit tests
│   ├── test_storage_adapters.py  # Storage layer tests
│   └── test_integration.py # Integration tests
├── worklogs/              # Development logs
│   ├── storage-adapter-layer/  # Storage adapter implementation
│   │   └── *.md          # Phase reports
│   └── sse-mcp-transport/  # SSE transport implementation
│       └── IMPLEMENTATION.md  # Implementation report
├── plans/                 # Implementation plans
│   └── storage-adapter-layer.md  # Storage adapter plan
├── main.py                # Application entry point
├── requirements.txt       # Python dependencies
├── pyproject.toml        # Project metadata
└── README.md             # This file
```

## Troubleshooting

### MCP Server Issues

If you encounter problems with MCP server connections, see [docs/MCP_TROUBLESHOOTING.md](docs/MCP_TROUBLESHOOTING.md) for:
- Connection timeout issues
- SDK version compatibility
- Server-specific problems
- Common error messages and solutions

## Dependencies

### Core Dependencies

- `qwen-agent` - Qwen Agent SDK
- `fastapi` - REST API framework
- `gradio` - Web UI framework
- `apscheduler` - Task scheduling
- `pydantic` - Data validation
- `loguru` - Logging

### MCP Dependencies

- `mcp==1.8.1` - Model Context Protocol SDK
  - **Important**: Version 1.9.0+ has known issues with `stdio_client` (BrokenResourceError, session initialization hangs)
  - See: [Issue #1452](https://github.com/modelcontextprotocol/python-sdk/issues/1452), [Issue #1564](https://github.com/modelcontextprotocol/python-sdk/issues/1564)
  - Use v1.8.1 for stable stdio transport communication
- `anyio` - Async IO

### Storage Dependencies

**Personal Edition (SQLite)**:
- `aiosqlite` - Async SQLite adapter

**Enterprise Edition (PostgreSQL + Redis)**:
- `sqlalchemy` - SQL ORM and toolkit
- `asyncpg` - Async PostgreSQL driver
- `redis` - Redis client for distributed caching

### Utility Dependencies

- `psutil` - Resource monitoring
- `pyyaml` - YAML configuration
- `python-dotenv` - Environment variables

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- Qwen Agent SDK for the agent framework
- Model Context Protocol for server integration
- FastAPI and Gradio for the web interface
- APScheduler for task scheduling
