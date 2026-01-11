# Python SDK Quick Start

The Round Table Python SDK provides a convenient interface for interacting with the Round Table API.

## Installation

```bash
pip install roundtable-sdk
```

Or install from source:

```bash
cd sdk/python
pip install -e .
```

## Configuration

### Using API Key

```python
from roundtable import RoundTableClient

client = RoundTableClient(
    api_key="your-api-key",
    base_url="http://localhost:8000/api/v1"
)
```

### Using Environment Variables

```bash
export ROUND_TABLE_API_KEY="your-api-key"
export ROUND_TABLE_BASE_URL="http://localhost:8000/api/v1"
```

```python
import os
from roundtable import RoundTableClient

client = RoundTableClient(
    api_key=os.getenv("ROUND_TABLE_API_KEY"),
    base_url=os.getenv("ROUND_TABLE_BASE_URL")
)
```

## Basic Usage

### Context Manager Pattern

Recommended for automatic cleanup:

```python
async with RoundTableClient(api_key="your-api-key") as client:
    # Your code here
    pass  # Client automatically closed
```

### Manual Cleanup

```python
client = RoundTableClient(api_key="your-api-key")
try:
    # Your code here
    pass
finally:
    await client.close()
```

## Workspaces

### Create a Workspace

```python
workspace = await client.workspaces.create(
    name="My Project",
    description="A workspace for my agents"
)
print(f"Created workspace: {workspace.workspace_id}")
```

### List Workspaces

```python
workspaces = await client.workspaces.list(limit=50)
for ws in workspaces.workspaces:
    print(f"{ws.name}: {ws.workspace_id}")
```

### Get Workspace Details

```python
workspace = await client.workspaces.get("ws_abc123")
print(f"Workspace: {workspace.name}")
print(f"Status: {workspace.status}")
print(f"Created: {workspace.created_at}")
```

### Update Workspace

```python
updated = await client.workspaces.update(
    "ws_abc123",
    name="Updated Name",
    description="New description"
)
```

### Delete Workspace

```python
await client.workspaces.delete("ws_abc123")
```

## Sandboxes

### Create a Sandbox

```python
sandbox = await client.sandboxes.create(
    workspace_id="ws_abc123",
    name="Research Agent",
    description="Research specialist",
    agent_config={
        "primary_agent": "researcher",
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 2000
    }
)
print(f"Created sandbox: {sandbox.sandbox_id}")
```

### List Sandboxes

```python
sandboxes = await client.sandboxes.list(
    workspace_id="ws_abc123",
    limit=50
)
for sb in sandboxes.sandboxes:
    print(f"{sb.name}: {sb.status}")
```

### Start a Sandbox

```python
started = await client.sandboxes.start("sb_xyz789")
print(f"Status: {started.status}")
```

### Stop a Sandbox

```python
stopped = await client.sandboxes.stop("sb_xyz789")
print(f"Status: {stopped.status}")
```

### Get Sandbox Status

```python
status = await client.sandboxes.status("sb_xyz789")
print(f"Status: {status.status}")
print(f"Uptime: {status.uptime}")
```

### Get Sandbox Metrics

```python
metrics = await client.sandboxes.metrics("sb_xyz789")
print(f"Messages sent: {metrics.messages_sent}")
print(f"Messages received: {metrics.messages_received}")
```

### Delete Sandbox

```python
await client.sandboxes.delete("sb_xyz789")
```

## Messages

### Send a Message

```python
message = await client.messages.send(
    from_sandbox_id="sb_xyz789",
    to_sandbox_id="sb_def456",
    content={
        "type": "request",
        "action": "analyze",
        "data": {"key": "value"}
    }
)
print(f"Message sent: {message.message_id}")
```

### Get Messages

```python
messages = await client.messages.list(
    sandbox_id="sb_xyz789",
    limit=100
)
for msg in messages.messages:
    print(f"From: {msg.from_sandbox_id}")
    print(f"Content: {msg.content}")
```

### Get Message Details

```python
message = await client.messages.get("msg_abc123")
print(f"Status: {message.status}")
print(f"Content: {message.content}")
```

### Broadcast Message

```python
broadcast = await client.messages.broadcast(
    workspace_id="ws_abc123",
    from_sandbox_id="sb_xyz789",
    content={
        "type": "announcement",
        "message": "Hello everyone!"
    }
)
```

## Collaborations

### Orchestrate Collaboration

```python
collaboration = await client.collaborations.orchestrate(
    workspace_id="ws_abc123",
    task="Analyze Q4 sales data",
    participants=["sb_xyz789", "sb_def456"],
    mode="orchestrated",
    config={
        "max_duration": 300,
        "timeout": 30,
        "max_rounds": 10
    }
)
print(f"Collaboration ID: {collaboration.collaboration_id}")
```

### Get Collaboration Status

```python
status = await client.collaborations.get_collaboration("collab_abc123")
print(f"Status: {status.status}")
print(f"Progress: {status.progress}")
```

### Discover Agents

```python
agents = await client.collaborations.discover_agents("ws_abc123")
print(f"Found {agents.count} agents:")
for agent in agents.agents:
    print(f"  - {agent.name}: {agent.agent_type}")
```

## System Operations

### Health Check

```python
health = await client.health_check()
print(f"System status: {health.status}")
```

### System Info

```python
info = await client.system_info()
print(f"Version: {info.version}")
print(f"Environment: {info.environment}")
```

### Aggregate Metrics

```python
metrics = await client.aggregate_metrics("ws_abc123")
print(f"Total sandboxes: {metrics.total_sandboxes}")
print(f"Total messages: {metrics.total_messages}")
```

## Error Handling

```python
from roundtable.exceptions import (
    NotFoundError,
    ValidationError,
    AuthenticationError,
    RateLimitError
)

try:
    workspace = await client.workspaces.get("ws_nonexistent")
except NotFoundError as e:
    print(f"Resource not found: {e}")
except ValidationError as e:
    print(f"Invalid data: {e}")
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
except RateLimitError as e:
    print(f"Rate limit exceeded: {e}")
```

## Complete Example

```python
import asyncio
from roundtable import RoundTableClient

async def main():
    async with RoundTableClient(api_key="your-api-key") as client:
        # Create workspace
        workspace = await client.workspaces.create(
            name="Demo Project",
            description="Demonstrating the SDK"
        )

        # Create sandboxes
        researcher = await client.sandboxes.create(
            workspace_id=workspace.workspace_id,
            name="Researcher",
            agent_config={
                "primary_agent": "researcher",
                "model": "gpt-4"
            }
        )

        developer = await client.sandboxes.create(
            workspace_id=workspace.workspace_id,
            name="Developer",
            agent_config={
                "primary_agent": "developer",
                "model": "gpt-4"
            }
        )

        # Start collaboration
        collaboration = await client.collaborations.orchestrate(
            workspace_id=workspace.workspace_id,
            task="Build a REST API",
            participants=[researcher.sandbox_id, developer.sandbox_id],
            mode="orchestrated"
        )

        print(f"Collaboration started: {collaboration.collaboration_id}")

        # Check status
        status = await client.collaborations.get_collaboration(
            collaboration.collaboration_id
        )
        print(f"Status: {status.status}")

        # Cleanup
        await client.sandboxes.delete(researcher.sandbox_id)
        await client.sandboxes.delete(developer.sandbox_id)
        await client.workspaces.delete(workspace.workspace_id)

if __name__ == "__main__":
    asyncio.run(main())
```

## Best Practices

1. **Use async context managers** for automatic cleanup
2. **Handle exceptions** gracefully with specific error types
3. **Check resource status** before dependent operations
4. **Clean up resources** when done (delete sandboxes, workspaces)
5. **Use pagination** for large list operations

## Additional Resources

- [API Reference](../api/overview.md)
- [Examples](../examples/)
- [TypeScript SDK](typescript-quickstart.md)
