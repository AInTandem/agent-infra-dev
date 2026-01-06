# Qwen Agent MCP Scheduler

A comprehensive local agent infrastructure built with Qwen Agent SDK, featuring MCP server integration, task scheduling, OpenAI-compatible API, and Gradio GUI.

## Features

- **Customizable Agents**: Define agents with custom system prompts and MCP server integrations
- **MCP Server Integration**: Seamlessly integrate Model Context Protocol servers via YAML configuration
- **Task Scheduling**: Schedule automated agent tasks with Cron, Interval, and One-time scheduling
- **OpenAI-Compatible API**: REST API compatible with OpenAI's chat completions and function calling
- **Gradio GUI**: User-friendly web interface for managing agents and tasks
- **Sandbox Execution**: Isolated execution environment with resource limits and security policies

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Qwen Agent MCP Scheduler                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Gradio    │  │   FastAPI   │  │     CLI     │             │
│  │     GUI     │  │     API     │  │  Interface  │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                      │
│         └────────────────┴────────────────┘                      │
│                          │                                       │
│         ┌────────────────┴────────────────┐                      │
│         │         Core Components          │                      │
│         ├──────────────────────────────────┤                      │
│         │  AgentManager │  TaskScheduler   │                      │
│         │  MCPBridge    │  SandboxManager  │                      │
│         │  ConfigManager│  SecurityPolicy  │                      │
│         └──────────────────────────────────┘                      │
│                          │                                       │
│         ┌────────────────┴────────────────┐                      │
│         │            Agents               │                      │
│         ├──────────────────────────────────┤                      │
│         │  Researcher  │  Developer       │                      │
│         │  Writer      │  Analyst         │                      │
│         └──────────────────────────────────┘                      │
│                          │                                       │
│         ┌────────────────┴────────────────┐                      │
│         │          MCP Servers            │                      │
│         ├──────────────────────────────────┤                      │
│         │  Filesystem  │  Web-Search      │                      │
│         │  GitHub      │  PostgreSQL       │                      │
│         │  Google-Maps │  Puppeteer       │                      │
│         └──────────────────────────────────┘                      │
│                                                                   │
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

```yaml
mcp_servers:
  - name: "filesystem"
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"]
    env: {}
    description: "File system access"
    enabled: true

  - name: "web-search"
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-brave-search"]
    env:
      BRAVE_API_KEY: "${BRAVE_API_KEY}"
    description: "Web search via Brave Search API"
    enabled: true
```

## API Usage

### Chat Completions

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
│   └── app.yaml           # Application settings
├── src/
│   ├── core/              # Core components
│   │   ├── config.py      # Configuration management
│   │   ├── agent_manager.py  # Agent lifecycle
│   │   ├── task_scheduler.py  # Task scheduling
│   │   ├── mcp_bridge.py  # MCP integration
│   │   ├── sandbox.py     # Sandbox environment
│   │   ├── resource_limiter.py  # Resource limits
│   │   └── security.py    # Security policies
│   ├── agents/            # Agent implementations
│   │   └── base_agent.py  # Base agent class
│   ├── api/               # REST API
│   │   └── openapi_server.py  # FastAPI server
│   └── gui/               # Web interface
│       └── app.py         # Gradio GUI
├── storage/               # Local storage
│   ├── tasks/             # Task persistence
│   └── logs/              # Application logs
├── tests/                 # Test suite
│   ├── test_*.py          # Unit tests
│   └── test_integration.py # Integration tests
├── worklogs/              # Development logs
│   └── qwen-agent-mcp-scheduler/
│       └── phase-*.md     # Phase reports
├── main.py                # Application entry point
├── requirements.txt       # Python dependencies
├── pyproject.toml        # Project metadata
└── README.md             # This file
```

## Dependencies

### Core Dependencies

- `qwen-agent` - Qwen Agent SDK
- `fastapi` - REST API framework
- `gradio` - Web UI framework
- `apscheduler` - Task scheduling
- `pydantic` - Data validation
- `loguru` - Logging

### MCP Dependencies

- `mcp` - Model Context Protocol SDK
- `anyio` - Async IO

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
