# Round Table: Agent Collaboration Bus

> "Where AI agents gather as equals to collaborate and solve complex problems"

## Project Overview

**Round Table** is a cross-container AI agent collaboration infrastructure that enables multiple AI agents to communicate, coordinate, and work together to solve complex problems.

### Vision

Inspired by King Arthur and the Round Table Knights, Round Table creates a coworking space built for AI - where AI agents in isolated containers can communicate and collaborate as equals, without a central orchestrator dictating their every move.

### Core Philosophy

Unlike traditional orchestrator patterns where a central controller manages all agent activities, Round Table enables:

- **Autonomous Collaboration**: Agents collaborate directly with each other
- **Sandboxed Execution**: Each agent team operates in isolated containers
- **Message Bus Architecture**: Pub/Sub messaging for scalable communication
- **Equality Collaboration**: All agents participate as equals in the collaboration

---

## Architecture

```
                    ┌─────────────────────────────────────────┐
                    │         Round Table (Collaboration Bus)    │
                    │                                            │
                    │  - Pub/Sub Messaging                      │
                    │  - Agent Discovery                        │
                    │  - Message Routing                        │
                    │  - Coordination Services                  │
                    └─────────────────────────────────────────┘
                                      │         │
                    ┌─────────────────┼─────────┼─────────────────┐
                    │                 │         │                 │
              ┌─────▼──────┐    ┌─────▼──────┐  ┌─────▼──────┐
              │  Agent     │    │  Agent     │  │  Agent     │
              │  Team A    │    │  Team B    │  │  Team C    │
              │            │    │            │  │            │
              │ ┌────────┐ │    │ ┌────────┐ │  │ ┌────────┐ │
              │ │Primary │ │    │ │Primary │ │  │ │Primary │ │
              │ │ Agent  │ │    │ │ Agent  │ │  │ │ Agent  │ │
              │ │        │ │    │ │        │ │  │ │        │ │
              │ │ + Sub  │ │    │ │ + Sub  │ │  │ │ + Sub  │ │
              │ │ Agents │ │    │ │ Agents │ │  │ │ Agents │ │
              │ └────────┘ │    │ └────────┘ │  │ └────────┘ │
              └────────────┘    └────────────┘  └────────────┘
                 Container         Container        Container
```

### Key Components

#### 1. Round Table Bus (Collaboration Bus)

- **Purpose**: Message routing and coordination
- **Implementation**: Redis (Community) or NATS (Enterprise)
- **Features**: Pub/Sub, message queues, agent discovery

#### 2. Agent Teams

- **Structure**: Primary Agent + Sub-agents
- **Execution**: Docker containers
- **Isolation**: Full sandbox for each team

#### 3. Container Agent SDK

- **Languages**: Python, TypeScript
- **Purpose**: Lightweight client for agent communication
- **Features**: Auto-discovery, message handling, collaboration primitives

---

## Editions

### Community Edition (Personal Use)

- **Deployment**: Single machine
- **Message Bus**: Redis (standalone)
- **Storage**: SQLite
- **Collaboration Mode**: One developer with multiple agent teams (Mode 1)
- **Use Case**: Local development, individual developers, small projects

### Enterprise Edition (Team Use)

- **Deployment**: Cross-machine / Cloud
- **Message Bus**: Redis Cluster or NATS
- **Storage**: PostgreSQL + Redis
- **Collaboration Mode**: Multiple developers with their agent teams (Mode 2)
- **Use Case**: Production, large-scale deployments, team collaboration

### Feature Comparison

| Feature | Community Edition | Enterprise Edition |
|---------|------------------|--------------------|
| **Deployment** | Single machine | Cross-machine / Cloud |
| **Message Bus** | Redis (standalone) | Redis Cluster / NATS |
| **Storage** | SQLite | PostgreSQL + Redis |
| **Mode 1: One Developer** | ✅ | ✅ |
| **Mode 2: Multiple Developers** | ❌ | ✅ |
| **Orchestrated Collaboration** | ✅ | ✅ |
| **Peer-to-Peer Collaboration** | ✅ | ✅ |
| **Swarm Mode** | ❌ | ✅ |
| **SSO Integration** | ❌ | ✅ |
| **Audit Logging** | Basic | Advanced |
| **SLA Support** | Community | 24/7 Enterprise |

---

## Collaboration Modes

### 1. Orchestrated Mode
**Available in**: Community Edition & Enterprise Edition

A coordinator agent guides the collaboration while agents communicate directly.

### 2. Peer-to-Peer Mode
**Available in**: Community Edition & Enterprise Edition

Agents discover each other and collaborate without central coordination.

### 3. Swarm Mode
**Available in**: Enterprise Edition Only

Multiple instances of the same agent work on parallel tasks with cross-machine coordination.

---

## API Specifications

Complete RESTful API specifications are available:

- **[Use Cases and Scenarios](collaboration-bus-framework/API_USE_CASES_AND_SCENARIOS.md)** - 30+ use cases across 7 categories
- **[API Endpoints](collaboration-bus-framework/API_ENDPOINTS_SPECIFICATION.md)** - 53 RESTful endpoints
- **[JSON Schemas](collaboration-bus-framework/API_JSON_SCHEMAS.md)** - 41 schemas with 160+ field definitions
- **[OpenAPI Spec](collaboration-bus-framework/openapi.yaml)** - Machine-readable specification
- **[SDK Development Guide](collaboration-bus-framework/API_SDK_DEVELOPMENT_GUIDE.md)** - Python & TypeScript SDK guides

---

## Use Cases

### Mode 1: One Developer + Multiple Agent Teams
**Available in**: Community Edition & Enterprise Edition

A single developer works with multiple specialized agent teams:

- Research Agent Team - Information gathering and analysis
- Development Agent Team - Code generation and implementation
- Testing Agent Team - Quality assurance and testing
- Documentation Agent Team - Documentation generation

### Mode 2: Multiple Developers + Their Agent Teams
**Available in**: Enterprise Edition Only

Multiple developers, each with their own agent teams, collaborate on a project:

- Developer A + Frontend Agent Team
- Developer B + Backend Agent Team
- Developer C + DevOps Agent Team
- Developer D + Data Science Agent Team

---

## Project Status

| Phase                               | Status      | Deliverable               |
| ----------------------------------- | ----------- | ------------------------- |
| Phase 1: Use Cases & Scenarios      | ✅ Complete | 30+ use cases documented  |
| Phase 2: API Endpoints Design       | ✅ Complete | 53 endpoints specified    |
| Phase 3: JSON Schemas Definition    | ✅ Complete | 41 schemas defined        |
| Phase 4: OpenAPI Specification      | ✅ Complete | Machine-readable spec     |
| Phase 5: API Server Implementation  | ⏳ Next     | RESTful API server        |
| Phase 6: Python SDK Development     | ⏳ Pending  | Python client library     |
| Phase 7: TypeScript SDK Development | ⏳ Pending  | TypeScript client library |
| Phase 8: Documentation & Examples   | ⏳ Pending  | Tutorials and guides      |

---

## Quick Links

- **Architecture**: [COLLABORATION_BUS_ARCHITECTURE.md](collaboration-bus-architecture/COLLABORATION_BUS_ARCHITECTURE.md)
- **Agent Team Model**: [AGENT_TEAM_COLLABORATION.md](collaboration-bus-architecture/AGENT_TEAM_COLLABORATION.md)
- **MCP Integration**: [MCP_INTEGRATION_STRATEGY.md](../MCP_INTEGRATION_STRATEGY.md)
- **Work Logs**: [worklogs/collaboration-bus-architecture/](../../worklogs/collaboration-bus-architecture/)

---

## Naming Rationale

The name "Round Table" was chosen to reflect:

1. **Equality**: All agents participate as equals, no hierarchy
2. **Collaboration**: Agents work together toward common goals
3. **Community**: Multiple agents gather to share knowledge and skills
4. **Strength**: Collective intelligence exceeds individual capabilities

Just as King Arthur's Round Table brought together knights of different skills and backgrounds, Round Table brings together AI agents of different specializations to solve complex problems.

---

## Getting Started (Coming Soon)

```python
# Python SDK (Coming Soon)
from roundtable import RoundTableClient

client = RoundTableClient(api_key="your-api-key")

# Create a workspace
workspace = await client.workspaces.create(
    name="My Project Workspace",
    description="AI agents for my project"
)

# Create an agent team sandbox
sandbox = await client.sandboxes.create(
    workspace.id,
    name="research-team",
    agent_config={
        "primary_agent": "researcher",
        "sub_agents": ["analyzer", "summarizer"]
    }
)

# Start collaboration with other teams
await sandbox.messages.broadcast(
    content={"task": "Research AI trends in 2025"}
)
```

```typescript
// TypeScript SDK (Coming Soon)
import { RoundTableClient } from '@aintandem/roundtable';

const client = new RoundTableClient({ apiKey: 'your-api-key' });

// Create a workspace
const workspace = await client.workspaces.create({
  name: 'My Project Workspace',
  description: 'AI agents for my project'
});

// Create an agent team sandbox
const sandbox = await client.sandboxes.create(workspace.id, {
  name: 'research-team',
  agentConfig: {
    primaryAgent: 'researcher',
    subAgents: ['analyzer', 'summarizer']
  }
});

// Start collaboration
await sandbox.messages.broadcast({
  content: { task: 'Research AI trends in 2025' }
});
```

---

## License

Part of the AInTandem project. See main project LICENSE for details.

---

**Project**: Round Table
**Status**: Design Complete, Implementation In Progress
**Version**: 0.1.0 (Alpha)
**Year**: 2025
