# Round Table - Agent Collaboration Bus

Round Table is a production-ready collaboration bus for AI agents, enabling seamless multi-agent orchestration and communication.

## Overview

Round Table provides a centralized platform for managing AI agent workspaces, facilitating agent-to-agent communication, and orchestrating complex multi-agent collaborations.

### Key Features

- **Workspace Management**: Create and manage isolated environments for agent teams
- **Sandbox Control**: Deploy, start, stop, and monitor agent containers
- **Message Bus**: Reliable message passing between agents via Redis pub/sub
- **Collaboration Orchestration**: Coordinate multi-agent workflows with different modes
- **RESTful API**: Complete HTTP API with comprehensive endpoint coverage
- **SDK Support**: Official Python and TypeScript client libraries
- **WebSocket Support**: Real-time message streaming (planned)

## Quick Start

### Using Docker Compose (Recommended)

```bash
cd docker
docker-compose up -d
```

This starts:
- Redis on port 6379
- API server on port 8000

### Manual Installation

```bash
# Install dependencies
pip install -r api/requirements.txt

# Set up database
alembic upgrade head

# Start the server
uvicorn api.app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Documentation

- [API Documentation](api/overview.md)
- [Python SDK](sdk/python-quickstart.md)
- [TypeScript SDK](sdk/typescript-quickstart.md)
- [Examples](examples/)

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get access token
- `POST /api/v1/auth/refresh` - Refresh access token

### Workspaces
- `GET /api/v1/workspaces` - List workspaces
- `POST /api/v1/workspaces` - Create workspace
- `GET /api/v1/workspaces/{id}` - Get workspace details
- `PUT /api/v1/workspaces/{id}` - Update workspace
- `DELETE /api/v1/workspaces/{id}` - Delete workspace

### Sandboxes
- `GET /api/v1/workspaces/{workspace_id}/sandboxes` - List sandboxes
- `POST /api/v1/workspaces/{workspace_id}/sandboxes` - Create sandbox
- `GET /api/v1/sandboxes/{id}` - Get sandbox details
- `POST /api/v1/sandboxes/{id}/start` - Start sandbox
- `POST /api/v1/sandboxes/{id}/stop` - Stop sandbox
- `DELETE /api/v1/sandboxes/{id}` - Delete sandbox
- `GET /api/v1/sandboxes/{id}/status` - Get sandbox status
- `GET /api/v1/sandboxes/{id}/logs` - Get sandbox logs
- `GET /api/v1/sandboxes/{id}/metrics` - Get sandbox metrics

### Messages
- `POST /api/v1/sandboxes/{id}/messages` - Send message
- `GET /api/v1/sandboxes/{id}/messages` - Get messages
- `POST /api/v1/workspaces/{id}/broadcast` - Broadcast message
- `GET /api/v1/messages/{id}` - Get message details

### Collaborations
- `POST /api/v1/workspaces/{id}/collaboration/orchestrate` - Orchestrate collaboration
- `GET /api/v1/collaborations/{id}` - Get collaboration status
- `GET /api/v1/workspaces/{id}/agents/discover` - Discover agents

### System
- `GET /api/v1/system/health` - Health check
- `GET /api/v1/system/info` - System information

## SDK Usage

### Python

```python
from roundtable import RoundTableClient

async with RoundTableClient(api_key="your-api-key") as client:
    # Create workspace
    workspace = await client.workspaces.create(name="My Workspace")

    # Create sandbox
    sandbox = await client.sandboxes.create(
        workspace_id=workspace.workspace_id,
        name="Research Agent",
        agent_config={"primary_agent": "researcher", "model": "gpt-4"}
    )
```

### TypeScript

```typescript
import { RoundTableClient } from '@roundtable/sdk';

const client = new RoundTableClient({ apiKey: 'your-api-key' });

// Create workspace
const workspace = await client.workspaces.create({
  name: 'My Workspace'
});

// Create sandbox
const sandbox = await client.sandboxes.create(workspace.workspace_id, {
  name: 'Research Agent',
  agent_config: {
    primary_agent: 'researcher',
    model: 'gpt-4'
  }
});
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=api/app

# Run E2E tests (requires running server)
export RUN_E2E_TESTS=1
pytest api/tests/test_e2e.py
```

### Code Quality

```bash
# Format code
black api/app api/tests

# Lint code
ruff check api/app api/tests

# Type check
mypy api/app
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Round Table MVP                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌───────────────────────────────────────────────────┐ │
│  │              FastAPI REST API                     │ │
│  │  - JWT Authentication                              │ │
│  │  - Request Validation                              │ │
│  │  - Rate Limiting                                   │ │
│  └───────────────────────────────────────────────────┘ │
│                           │                             │
│  ┌────────────────────────┼───────────────────────────┐ │
│  │                        │                           │ │
│  │  ┌─────────────────────▼──────────────────────┐   │ │
│  │  │     Collaboration Bus Service               │   │ │
│  │  │  - Agent Discovery                          │   │ │
│  │  │  - Message Routing                          │   │ │
│  │  │  - Workspace Management                     │   │ │
│  │  │  - Sandbox Lifecycle                        │   │ │
│  │  └─────────────────────┬──────────────────────┘   │ │
│  │                        │                           │ │
│  │  ┌─────────────────────▼──────────────────────┐   │ │
│  │  │          Message Bus Layer                  │   │ │
│  │  │  - Redis (Pub/Sub, Queues)                 │   │ │
│  │  │  - WebSocket Management                    │   │ │
│  │  └─────────────────────┬──────────────────────┘   │ │
│  │                        │                           │ │
│  │  ┌─────────────────────▼──────────────────────┐   │ │
│  │  │           Storage Layer                     │   │ │
│  │  │  - SQLite (workspaces, sandboxes, users)   │   │ │
│  │  └────────────────────────────────────────────┘   │ │
│  │                                                    │ │
│  └────────────────────────────────────────────────────┘ │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## License

Copyright (c) 2025 AInTandem. SPDX-License-Identifier: MIT

## Contributing

Contributions are welcome! Please see our contributing guidelines for more information.

## Support

For issues, questions, or contributions, please visit our GitHub repository.
