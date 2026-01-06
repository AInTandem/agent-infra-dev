# Qwen Agent MCP Scheduler

A local agent infrastructure built with Qwen Agent SDK, featuring MCP server integration, task scheduling, and a Gradio-based GUI.

## Features

- **Customizable Agents**: Define agents with custom system prompts and MCP server integrations
- **MCP Server Integration**: Seamlessly integrate Model Context Protocol servers via configuration
- **Task Scheduling**: Schedule automated agent tasks with flexible scheduling options
- **OpenAI-Compatible API**: REST API compatible with OpenAI's function calling format
- **Gradio GUI**: User-friendly web interface for managing agents and tasks
- **Sandbox Execution**: Isolated execution environment for safety

## Quick Start

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

Create your configuration files in the `config/` directory:

1. **`config/llm.yaml`** - LLM provider configuration
2. **`config/agents.yaml`** - Agent definitions
3. **`config/mcp_servers.yaml`** - MCP server configurations

See the `config/` directory for examples.

### Running the Application

Start all services:

```bash
python main.py
```

Or run individual components:

```bash
# Start API server only
python -m src.api.openapi_server

# Start GUI only
python -m src.gui.app
```

## Architecture

```
agent-infra/
├── config/           # Configuration files
├── src/
│   ├── core/        # Core components (Agent Manager, MCP Bridge, Scheduler)
│   ├── api/         # OpenAI-compatible API
│   ├── agents/      # Agent implementations
│   └── gui/         # Gradio web interface
├── storage/         # Local storage (tasks, logs)
└── tests/           # Test suite
```

## Configuration

### LLM Configuration

```yaml
# config/llm.yaml
llm:
  provider: "openai_compatible"
  base_url: "https://api.deepseek.com/v1"
  api_key: "${DEEPSEEK_API_KEY}"
  default_model: "deepseek-chat"
```

### Agent Configuration

```yaml
# config/agents.yaml
agents:
  - name: "researcher"
    role: "Research Assistant"
    system_prompt: "You are a professional research assistant..."
    mcp_servers: ["filesystem", "web-search"]
    llm_model: "deepseek-chat"
```

### MCP Server Configuration

```yaml
# config/mcp_servers.yaml
mcp_servers:
  - name: "filesystem"
    command: "npx"
    args: ["-y", "@modelcontextprotocol/server-filesystem", "/allowed/path"]
    env: {}
    description: "File system access"
```

## API Usage

### Chat Completions

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "researcher",
    "messages": [{"role": "user", "content": "Search for recent AI papers"}]
  }'
```

### Create Scheduled Task

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "researcher",
    "messages": [{"role": "user", "content": "Schedule a daily report at 9 AM"}],
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "create_scheduled_task",
          "arguments": "{\"agent_name\": \"researcher\", \"task_prompt\": \"Generate daily report\", \"schedule_time\": \"0 9 * * *\", \"repeat\": true}"
        }
      }
    ]
  }'
```

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black src/
ruff check src/
```

## License

MIT License - see LICENSE file for details.
