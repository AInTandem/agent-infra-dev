# Round Table Python SDK

A Python SDK for interacting with the Round Table Collaboration Bus API.

## Installation

```bash
pip install roundtable-sdk
```

## Quick Start

```python
import asyncio
from roundtable import RoundTableClient

async def main():
    # Initialize the client
    async with RoundTableClient(api_key="your-api-key") as client:
        # Create a workspace
        workspace = await client.workspaces.create(
            name="My Workspace",
            description="A workspace for my agents"
        )
        print(f"Created workspace: {workspace.workspace_id}")

        # Create a sandbox (agent container)
        sandbox = await client.sandboxes.create(
            workspace_id=workspace.workspace_id,
            name="Research Agent",
            agent_config={
                "primary_agent": "researcher",
                "model": "gpt-4"
            }
        )
        print(f"Created sandbox: {sandbox.sandbox_id}")

        # Start the sandbox
        started = await client.sandboxes.start(sandbox.sandbox_id)
        print(f"Sandbox status: {started.status}")

asyncio.run(main())
```

## Configuration

You can configure the SDK in several ways:

### Using API Key Directly

```python
from roundtable import RoundTableClient

client = RoundTableClient(
    api_key="your-api-key",
    base_url="http://localhost:8000/api/v1"
)
```

### Using Configuration Object

```python
from roundtable import RoundTableClient, RoundTableConfig

config = RoundTableConfig(
    api_key="your-api-key",
    base_url="https://api.roundtable.example.com/api/v1",
    timeout=60.0,
    max_retries=3
)
client = RoundTableClient(config=config)
```

### Using Environment Variables

```python
from roundtable import RoundTableConfig

config = RoundTableConfig.from_env()
client = RoundTableClient(config=config)
```

Required environment variables:
- `ROUNDTABLE_API_KEY`: Your API key

Optional environment variables:
- `ROUNDTABLE_BASE_URL`: Base URL (default: `http://localhost:8000/api/v1`)
- `ROUNDTABLE_TIMEOUT`: Request timeout in seconds (default: `30`)
- `ROUNDTABLE_MAX_RETRIES`: Maximum number of retries (default: `3`)
- `ROUNDTABLE_VERIFY_SSL`: Verify SSL certificates (default: `true`)

## Workspaces

### List Workspaces

```python
workspaces = await client.workspaces.list(offset=0, limit=100)
for workspace in workspaces.workspaces:
    print(f"{workspace.name}: {workspace.workspace_id}")
```

### Create Workspace

```python
workspace = await client.workspaces.create(
    name="My Workspace",
    description="Optional description",
    settings={
        "max_sandboxes": 20,
        "auto_cleanup": True,
        "retention_days": 30
    }
)
```

### Get Workspace

```python
workspace = await client.workspaces.get("workspace_id")
```

### Update Workspace

```python
workspace = await client.workspaces.update(
    "workspace_id",
    name="Updated Name",
    description="Updated description"
)
```

### Delete Workspace

```python
success = await client.workspaces.delete("workspace_id")
```

## Sandboxes

### List Sandboxes

```python
sandboxes = await client.sandboxes.list("workspace_id")
for sandbox in sandboxes.sandboxes:
    print(f"{sandbox.name}: {sandbox.status}")
```

### Create Sandbox

```python
sandbox = await client.sandboxes.create(
    workspace_id="workspace_id",
    name="My Agent",
    agent_config={
        "primary_agent": "researcher",
        "model": "gpt-4",
        "max_tokens": 4000,
        "temperature": 0.7,
        "tools": ["search", "calculator"],
        "system_prompt": "You are a helpful research assistant."
    }
)
```

### Start Sandbox

```python
sandbox = await client.sandboxes.start("sandbox_id")
```

### Stop Sandbox

```python
sandbox = await client.sandboxes.stop("sandbox_id")
```

### Get Sandbox Status

```python
status = await client.sandboxes.status("sandbox_id")
print(f"Status: {status.status}")
print(f"Uptime: {status.uptime_seconds}s")
```

### Delete Sandbox

```python
success = await client.sandboxes.delete("sandbox_id")
```

## Messages

### Send Message

```python
message = await client.messages.send(
    from_sandbox_id="sender_id",
    to_sandbox_id="recipient_id",
    content={
        "type": "request",
        "action": "analyze",
        "data": {"text": "Analyze this data"}
    },
    message_type="request"
)
```

### Get Messages

```python
messages = await client.messages.get_messages(
    "sandbox_id",
    offset=0,
    limit=100
)
for message in messages.messages:
    print(f"From: {message.from_sandbox_id}, Content: {message.content}")
```

### Get Message

```python
message = await client.messages.get_message("message_id")
```

### Broadcast Message

```python
result = await client.messages.broadcast(
    workspace_id="workspace_id",
    content={
        "type": "announcement",
        "message": "Important update!"
    },
    message_type="notification"
)
print(f"Broadcast to {result['broadcast_to']} agents")
```

## Collaborations

### Orchestrate Collaboration

```python
collab = await client.collaborations.orchestrate(
    workspace_id="workspace_id",
    task="Analyze research data and create summary",
    participants=["sandbox_1", "sandbox_2"],
    mode="orchestrated",
    config={
        "timeout": 600,
        "max_iterations": 20,
        "terminate_on_completion": True
    }
)
print(f"Collaboration ID: {collab.collaboration_id}")
```

### Get Collaboration

```python
collab = await client.collaborations.get_collaboration("collaboration_id")
print(f"Status: {collab.status}")
if collab.result:
    print(f"Result: {collab.result}")
```

### Discover Agents

```python
agents = await client.collaborations.discover_agents("workspace_id")
for agent in agents.agents:
    print(f"{agent.name}: {agent.primary_agent} ({agent.status})")
    print(f"  Capabilities: {', '.join(agent.capabilities)}")
```

## Error Handling

The SDK provides specific exceptions for different error scenarios:

```python
from roundtable import RoundTableClient
from roundtable.exceptions import (
    AuthenticationError,
    NotFoundError,
    ValidationError,
    RateLimitError
)

async def safe_operation():
    try:
        workspace = await client.workspaces.create(name="Test")
    except AuthenticationError:
        print("Invalid API key")
    except NotFoundError:
        print("Resource not found")
    except ValidationError as e:
        print(f"Invalid input: {e.message}")
    except RateLimitError as e:
        print(f"Rate limited, retry after {e.retry_after}s")
    except Exception as e:
        print(f"Unexpected error: {e}")
```

## Testing

The SDK includes a comprehensive test suite:

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=roundtable tests/
```

## Development

### Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"
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

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- GitHub: https://github.com/aintandem/round-table
- Documentation: https://github.com/aintandem/round-table/docs
