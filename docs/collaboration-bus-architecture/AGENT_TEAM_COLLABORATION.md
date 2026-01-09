# Agent Team Collaboration Architecture

## Overview

This document describes the architecture for a multi-agent collaboration system where agents work in isolated sandboxes and coordinate with each other through a collaboration bus. This design enables two primary collaboration modes:

- **Mode 1**: One developer working with multiple agent teams
- **Mode 2**: Multiple developers, each with their own agent teams, working together

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Agent Team Collaboration Platform                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    Collaboration Bus (Message Queue)             │  │
│  │  - Pub/Sub Messaging  - Agent Discovery  - Coordination          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              │         │                                 │
│           ┌──────────────────┘         └──────────────────┐              │
│           ▼                                                    ▼          │
│  ┌────────────────────┐                            ┌────────────────────┐│
│  │   Mode 1:          │                            │   Mode 2:          ││
│  │  1 Developer +     │                            │  Multiple Teams    ││
│  │  Multiple Agents   │                            │  + Their Agents    ││
│  └────────────────────┘                            └────────────────────┘│
│           │                                                    │          │
│  ┌────────┴────────┐                              ┌─────────┴──────────┐ │
│  ▼                 ▼                              ▼                     ▼ │
│ ┌──────┐        ┌──────┐        ┌──────┐       ┌──────┐          ┌──────┐│
│ │Sandbox│       │Sandbox│       │Sandbox│       │Sandbox│          │Sandbox││
│ │  1   │        │  2   │  ...  │  N   │       │  1   │    ...   │  N   ││
│ └──────┘        └──────┘        └──────┘       └──────┘          └──────┘│
│    │               │               │               │                  │    │
│    ▼               ▼               ▼               ▼                  ▼    │
│ ┌──────┐        ┌──────┐        ┌──────┐       ┌──────┐          ┌──────┐│
│ │Agent │        │Agent │        │Agent │       │Agent │          │Agent ││
│ │ Team │        │ Team │        │ Team │       │ Team │          │ Team ││
│ │  A   │        │  B   │        │  C   │       │  A   │          │  B   ││
│ └──────┘        └──────┘        └──────┘       └──────┘          └──────┘│
│    │               │               │               │                  │    │
│  Sub-agents      Sub-agents      Sub-agents      Sub-agents        Sub-agents│
│  (optional)      (optional)      (optional)      (optional)        (optional)│
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Key Design Principles

### 1. Sandbox Isolation

Each agent team operates in its own isolated sandbox:
- **Process isolation**: Separate execution context
- **Resource limits**: Memory, CPU, time constraints
- **File system isolation**: Separate working directories
- **Network control**: Configurable network access

### 2. Communication Protocol

Agents communicate through a standardized message protocol:
- **Typed messages**: request, response, notification, command
- **Addressing**: Source/destination with optional broadcast
- **Priority**: Message prioritization (0-9)
- **Reliability**: Acknowledgment and timeout handling

### 3. Collaboration Modes

- **Peer-to-peer**: Direct agent-to-agent communication
- **Broadcast**: One-to-all messaging
- **Orchestrated**: Coordinated by a leader agent
- **Swarm**: Consensus-based collaboration

## Core Components

### AgentMessage

```python
@dataclass
class AgentMessage:
    """Message protocol for inter-agent communication"""
    message_id: str
    from_sandbox: str           # Source sandbox ID
    to_sandbox: str             # Target sandbox ID (or "broadcast")
    from_agent: str             # Source agent name
    to_agent: str               # Target agent name (or "any")
    message_type: MessageType   # request, response, notification, command
    content: Dict[str, Any]
    timestamp: float
    priority: int = 5           # 0-9, 9 = highest
    requires_response: bool = False
    correlation_id: Optional[str] = None  # For request-response tracking
```

### CollaborationBus

```python
class CollaborationBus:
    """
    Message bus for cross-sandbox agent communication.

    Features:
    - Pub/sub messaging with topic routing
    - Message persistence and replay
    - Agent discovery and registry
    - Dead letter queue for failed messages
    """

    async def send_message(self, message: AgentMessage) -> str:
        """Send a message to another sandbox"""
        pass

    async def broadcast(self, from_sandbox: str, message: AgentMessage):
        """Broadcast a message to all sandboxes"""
        pass

    async def subscribe(self, sandbox_id: str, handler: MessageHandler):
        """Subscribe to messages for this sandbox"""
        pass

    async def register_agent(self, sandbox_id: str, agent_info: AgentInfo):
        """Register an agent for discovery"""
        pass

    async def discover_agents(self, query: AgentQuery) -> List[AgentInfo]:
        """Discover agents by capability"""
        pass
```

### AgentSandbox

```python
class AgentSandbox:
    """
    Isolated sandbox containing a primary agent and optional sub-agents.

    Each sandbox can:
    - Host a primary agent and multiple sub-agents
    - Communicate with other sandboxes via CollaborationBus
    - Delegate tasks to sub-agents
    - Maintain its own context and memory
    """

    def __init__(
        self,
        sandbox_id: str,
        owner_id: str,               # Developer/team ID
        primary_agent: BaseAgent,
        sub_agents: List[BaseAgent] = None,
        collaboration_bus: CollaborationBus = None,
        config: SandboxConfig = None
    ):
        self.sandbox_id = sandbox_id
        self.owner_id = owner_id
        self.primary_agent = primary_agent
        self.sub_agents = sub_agents or []
        self.collaboration_bus = collaboration_bus
        self.config = config or SandboxConfig()

        # Message handlers registry
        self.message_handlers: Dict[str, Callable] = {}

        # Subscribe to cross-sandbox messages
        if collaboration_bus:
            asyncio.create_task(
                collaboration_bus.subscribe(sandbox_id, self._handle_incoming_message)
            )

    async def delegate_to_sub_agent(
        self,
        task: str,
        sub_agent_name: str,
        context: Dict[str, Any] = None
    ) -> Any:
        """Delegate a task to a specific sub-agent"""
        pass

    async def collaborate_with_sandbox(
        self,
        target_sandbox: str,
        request: Dict[str, Any],
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Collaborate with an agent in another sandbox"""
        pass

    async def broadcast_to_all(
        self,
        message: Dict[str, Any],
        exclude_self: bool = True
    ):
        """Broadcast a message to all sandboxes"""
        pass

    async def _handle_incoming_message(self, message: AgentMessage):
        """Handle incoming message from collaboration bus"""
        pass
```

## Collaboration Modes

### Mode 1: Single Developer + Multiple Agents

```python
class SingleDeveloperWorkspace:
    """
    Workspace for a single developer with multiple agent sandboxes.

    Usage:
    - Create multiple specialized agent teams
    - Coordinate them for complex tasks
    - Maintain full control over all agents
    """

    def __init__(self, developer_id: str):
        self.developer_id = developer_id
        self.sandboxes: Dict[str, AgentSandbox] = {}
        self.collaboration_bus = CollaborationBus()

    async def create_sandbox(
        self,
        agent_config: AgentConfig,
        sub_agent_configs: List[AgentConfig] = None,
        sandbox_config: SandboxConfig = None
    ) -> AgentSandbox:
        """Create a new agent sandbox for this developer"""
        sandbox_id = f"{self.developer_id}_{uuid.uuid4().hex[:8]}"

        primary_agent = await self._create_agent(agent_config)
        sub_agents = [
            await self._create_agent(cfg)
            for cfg in (sub_agent_configs or [])
        ]

        sandbox = AgentSandbox(
            sandbox_id=sandbox_id,
            owner_id=self.developer_id,
            primary_agent=primary_agent,
            sub_agents=sub_agents,
            collaboration_bus=self.collaboration_bus,
            config=sandbox_config
        )

        self.sandboxes[sandbox_id] = sandbox
        return sandbox

    async def coordinate_collaboration(
        self,
        task: str,
        participants: List[str],
        collaboration_mode: str = "orchestrated"
    ) -> Dict[str, Any]:
        """Coordinate multiple sandboxes to complete a task"""
        pass

    async def get_all_agent_statuses(self) -> Dict[str, Any]:
        """Get status of all agent sandboxes"""
        pass
```

### Mode 2: Multiple Teams + Their Agents

```python
class MultiTeamCollaborationSpace:
    """
    Collaboration space for multiple teams/developers.

    Each team has their own agent teams and can collaborate
    with other teams under controlled access.
    """

    def __init__(self):
        self.teams: Dict[str, SingleDeveloperWorkspace] = {}
        self.collaboration_bus = CollaborationBus()
        self.access_policies: Dict[str, AccessPolicy] = {}

    async def create_team(
        self,
        team_id: str,
        access_policy: AccessPolicy = None
    ) -> SingleDeveloperWorkspace:
        """Create a new team workspace"""
        team = SingleDeveloperWorkspace(team_id)
        team.collaboration_bus = self.collaboration_bus

        if access_policy:
            self.access_policies[team_id] = access_policy

        self.teams[team_id] = team
        return team

    async def cross_team_collaboration(
        self,
        initiator_team: str,
        target_teams: List[str],
        task: Dict[str, Any],
        collaboration_mode: str = "peer_to_peer"
    ) -> Dict[str, Any]:
        """Facilitate cross-team collaboration"""
        pass

    async def enforce_access_policy(
        self,
        from_team: str,
        to_team: str,
        action: str
    ) -> bool:
        """Check if cross-team access is allowed"""
        pass
```

## Use Cases

### Use Case 1: Software Development Team

```python
# Create development team workspace
dev_workspace = await collaboration_space.create_team("dev-team-alpha")

# Frontend team sandbox
frontend_sandbox = await dev_workspace.create_sandbox(
    agent_config=AgentConfig(
        name="frontend-architect",
        role="Frontend Architect",
        system_prompt="Expert in frontend architecture, React, TypeScript...",
    ),
    sub_agent_configs=[
        AgentConfig(name="react-expert", role="React Specialist"),
        AgentConfig(name="css-specialist", role="CSS Specialist"),
        AgentConfig(name="accessibility-auditor", role="Accessibility Auditor")
    ]
)

# Backend team sandbox
backend_sandbox = await dev_workspace.create_sandbox(
    agent_config=AgentConfig(
        name="backend-architect",
        role="Backend Architect",
        system_prompt="Expert in backend architecture, APIs, databases...",
    ),
    sub_agent_configs=[
        AgentConfig(name="api-designer", role="API Designer"),
        AgentConfig(name="db-optimizer", role="Database Optimizer"),
        AgentConfig(name="security-reviewer", role="Security Reviewer")
    ]
)

# Cross-sandbox collaboration: Design authentication feature
await frontend_sandbox.collaborate_with_sandbox(
    target_sandbox="backend_sandbox",
    request={
        "task": "Design user authentication API",
        "context": "Frontend needs OAuth2.0 integration",
        "required_outputs": ["API specification", "Data model", "Security considerations"]
    }
)
```

### Use Case 2: Marketing Campaign Planning

```python
# Marketing team workspace
marketing_workspace = await collaboration_space.create_team("marketing-team")

# Strategy team
strategy_sandbox = await marketing_workspace.create_sandbox(
    agent_config=AgentConfig(
        name="strategy-director",
        role="Strategy Director",
        system_prompt="Expert in marketing strategy and planning...",
    ),
    sub_agent_configs=[
        AgentConfig(name="seo-specialist", role="SEO Specialist"),
        AgentConfig(name="analyst", role="Data Analyst")
    ]
)

# Creative team
creative_sandbox = await marketing_workspace.create_sandbox(
    agent_config=AgentConfig(
        name="creative-director",
        role="Creative Director",
        system_prompt="Expert in creative direction and brand strategy...",
    ),
    sub_agent_configs=[
        AgentConfig(name="copywriter", role="Copywriter"),
        AgentConfig(name="visual-designer", role="Visual Designer"),
        AgentConfig(name="video-producer", role="Video Producer")
    ]
)

# Joint campaign planning
result = await strategy_sandbox.primary_agent.coordinate_with(
    target_sandbox=creative_sandbox,
    task="Plan 2025 Spring Product Launch Campaign",
    collaboration_mode="swarm"  # Consensus-based collaboration
)
```

### Use Case 3: Multi-Organization Project

```python
# Create multi-team collaboration space
project_space = MultiTeamCollaborationSpace()

# Company A team
company_a = await project_space.create_team(
    "company-a",
    access_policy=AccessPolicy(
        can collaborate_with=["company-b"],
        can_share_resources=["documents", "code"]
    )
)

# Company B team
company_b = await project_space.create_team(
    "company-b",
    access_policy=AccessPolicy(
        can_collaborate_with=["company-a"],
        can_share_resources=["documents"]
    )
)

# Cross-company collaboration
await project_space.cross_team_collaboration(
    initiator_team="company-a",
    target_teams=["company-b"],
    task={
        "project": "Joint API Integration",
        "deliverables": ["API spec", "Implementation guide"]
    }
)
```

## Configuration

### Message Types

```yaml
# config/agent_communication.yaml

message_types:
  request:
    requires_ack: true
    timeout: 30
    description: "Request assistance or resources"

  response:
    requires_ack: false
    description: "Response to a request"

  notification:
    requires_ack: false
    description: "Broadcast notification"

  command:
    requires_ack: true
    permission_level: "admin"
    description: "Command with authorization"
```

### Collaboration Modes

```yaml
collaboration_modes:
  peer_to_peer:
    routing: "direct"
    description: "Direct agent-to-agent communication"

  broadcast:
    routing: "all"
    description: "One-to-all messaging"

  orchestrated:
    routing: "coordinator"
    description: "Coordinated by leader agent"

  swarm:
    routing: "consensus"
    description: "Consensus-based collaboration"
```

### Security Settings

```yaml
security:
  authentication:
    enabled: true
    method: "jwt"

  authorization:
    sandbox_isolation: "strict"  # strict, moderate, permissive
    cross_team_access: "role_based"

  rate_limiting:
    messages_per_minute: 100
    max_concurrent_requests: 10

  audit:
    log_all_messages: true
    retention_days: 90
```

## Implementation Phases

### Phase 1: Foundation
- [ ] Extend `SandboxManager` for agent residency
- [ ] Implement `CollaborationBus` (Redis/WebSocket)
- [ ] Define `AgentMessage` protocol
- [ ] Basic sandbox-to-sandbox messaging

### Phase 2: Single Developer Mode
- [ ] Implement `SingleDeveloperWorkspace`
- [ ] Support multiple parallel sandboxes
- [ ] Implement peer-to-peer communication
- [ ] Add sub-agent delegation

### Phase 3: Multi-Team Collaboration
- [ ] Implement `MultiTeamCollaborationSpace`
- [ ] Add permission management
- [ ] Implement isolation strategies
- [ ] Cross-team collaboration modes

### Phase 4: Advanced Features
- [ ] Orchestrated collaboration mode
- [ ] Swarm consensus mechanism
- [ ] Collaboration history and audit
- [ ] Performance optimization

## Technical Considerations

### Message Bus Implementation Options

| Option | Pros | Cons | Use Case |
|--------|------|------|----------|
| **Redis** | Fast, pub/sub built-in | External dependency | Production |
| **WebSocket** | Real-time, no external deps | Scaling complexity | Development |
| **RabbitMQ** | Enterprise features | Complex setup | Large scale |
| **In-memory** | Simple, no deps | No persistence | Testing |

### Scalability

- **Horizontal scaling**: Multiple collaboration bus instances
- **Load balancing**: Distribute sandboxes across workers
- **Message partitioning**: Topic-based routing

### Security

- **Authentication**: JWT tokens for agent identity
- **Authorization**: Role-based access control
- **Encryption**: TLS for network communication
- **Audit logging**: All messages logged

### Fault Tolerance

- **Message retries**: Automatic retry with backoff
- **Dead letter queue**: Failed message handling
- **Health checks**: Sandbox heartbeat monitoring
- **Graceful degradation**: Partial functionality on failure

## Comparison with Claude Agent SDK Orchestrator

| Feature | Our Design | Claude Orchestrator |
|---------|-----------|-------------------|
| **Architecture** | Multi-sandbox with independent agents | Single orchestrator with sub-agents |
| **Isolation** | Full sandbox isolation | Shared context |
| **Scalability** | Distributed across processes/workers | Single process |
| **Multi-tenancy** | Built-in team support | Not designed for multi-team |
| **Communication** | Message bus with pub/sub | Direct function calls |
| **Fault tolerance** | Per-sandbox failure isolation | Orchestrator failure affects all |

## Related Documentation

- [MCP Integration Strategy](./MCP_INTEGRATION_STRATEGY.md)
- [MCP Server Configuration](./MCP_SERVER_CONFIGURATION.md)
- [WebSocket Streaming Reasoning](./websocket-streaming-reasoning.md)

## References

- [Qwen Agent Documentation](https://qwen.readthedocs.io/)
- [Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [Model Context Protocol](https://modelcontextprotocol.io/)

---

**Document Version:** 1.0
**Last Updated:** 2025-01-10
**Status:** Design Proposal
