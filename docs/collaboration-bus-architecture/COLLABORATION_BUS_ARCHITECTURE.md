# Collaboration Bus Architecture

## Overview

This document defines the architecture for the **Collaboration Bus** - the core communication infrastructure that enables cross-container agent collaboration in the AInTandem platform. The Collaboration Bus allows agents running in isolated containers to communicate, coordinate, and collaborate with each other.

## Vision: A Coworking Space Built for AI

AInTandem is a co-creation space where humans and AI can seamlessly share knowledge and experience. The Collaboration Bus is the nervous system that enables AI agents to work together as true coworkers.

## Product Strategy

### Edition Comparison

| Feature | Community Edition (Free) | Enterprise Edition |
|---------|-------------------------|-------------------|
| **Deployment** | Docker Compose (Single Machine) | Docker Swarm / Kubernetes |
| **Communication** | Same-machine containers | Cross-machine containers |
| **Message Bus** | Redis (Standalone) | Redis Cluster / NATS |
| **Storage** | SQLite | PostgreSQL + Redis |
| **Authentication** | Local users | SSO / LDAP |
| **Monitoring** | Basic logging | Full monitoring + Audit |
| **Support** | Community documentation | Enterprise SLA |
| **Sandbox Limit** | Limited (e.g., 5 containers) | Unlimited |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AInTandem Platform                              │
│                    "A Coworking Space Built for AI"                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    AInTandem Desktop                            │   │
│  │  (GUI for Workspace/Sandbox/Agent Management)                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│         ┌────────────────────┼────────────────────┐                    │
│         │                    │                    │                    │
│         ▼                    ▼                    ▼                    │
│  ┌──────────┐        ┌──────────┐        ┌──────────┐                │
│  │ Community│        │ Enterprise│        │ Enterprise│                │
│  │  (Free)  │        │  Single   │        │Distributed│                │
│  │          │        │  Machine  │        │            │                │
│  └──────────┘        └──────────┘        └──────────┘                │
│         │                    │                    │                    │
│         ▼                    ▼                    ▼                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Container-Based Sandboxes                    │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐             │   │
│  │  │Container│  │Container│  │Container│  │Container│             │   │
│  │  │  Agent  │  │  Agent  │  │  Agent  │  │  Agent  │             │   │
│  │  │   Team  │  │   Team  │  │   Team  │  │   Team  │             │   │
│  │  │    A    │  │    B    │  │    C    │  │    D    │             │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘             │   │
│  │       │            │            │            │                   │   │
│  └───────┼────────────┼────────────┼────────────┼───────────────────┘   │
│          │            │            │            │                      │
│          └────────────┼────────────┼────────────┘                      │
│                       │            │                                   │
│                       ▼            ▼                                   │
│              ┌───────────────────────────────┐                        │
│              │   Collaboration Bus           │                        │
│              │  (Cross-container Agent Comm) │                        │
│              └───────────────────────────────┘                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Detailed Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AInTandem Infrastructure                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   AInTandem Desktop                      │  │
│  │              (Electron/Tauri GUI Application)             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                   │
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              AInTandem Core Services                      │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │  │
│  │  │ Workspace    │  │   Sandbox    │  │ Collaboration│  │  │
│  │  │  Manager     │  │   Manager    │  │    Bus API   │  │  │
│  │  │  (REST API)  │  │ (REST API)   │  │  (REST/WS)    │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                   │
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │               Collaboration Message Bus                   │  │
│  │          (Redis/NATS/RabbitMQ - Pluggable)               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                   │
│         ┌───────────────────┼───────────────────┐              │
│         │                   │                   │              │
│         ▼                   ▼                   ▼              │
│  ┌─────────┐          ┌─────────┐          ┌─────────┐         │
│  │ Docker  │          │ Docker  │          │ Docker  │         │
│  │Container│          │Container│          │Container│         │
│  │  Agent  │          │  Agent  │          │  Agent  │         │
│  │  Team A │          │  Team B │          │  Team C │         │
│  └─────────┘          └─────────┘          └─────────┘         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Collaboration Bus Service (Microservice)

The Collaboration Bus is deployed as an independent microservice that handles all inter-container communication.

```python
class CollaborationBusService:
    """
    Cross-container Agent Communication Service

    Deployment:
    - Community: Single-machine Redis
    - Enterprise: Redis Cluster or NATS
    """

    # REST API endpoints
    POST   /api/v1/messages              # Send message to specific container
    POST   /api/v1/broadcast             # Broadcast to all containers
    GET    /api/v1/messages/{id}         # Get message by ID
    GET    /api/v1/sandboxes             # List registered sandboxes
    POST   /api/v1/sandboxes/register    # Register a new sandbox
    DELETE /api/v1/sandboxes/{id}        # Unregister a sandbox

    # WebSocket endpoints
    WS     /ws/sandboxes/{sandbox_id}    # Subscribe to messages for a sandbox
    WS     /ws/broadcast                # Subscribe to broadcast messages
    WS     /ws/events                   # Subscribe to system events
```

**Key Features:**
- Message routing and delivery
- Pub/sub messaging with topic support
- Agent discovery and registry
- Dead letter queue for failed messages
- Message persistence and replay
- Health monitoring and metrics

### 2. Container Agent SDK (Lightweight Client)

The SDK is installed in each container and provides a simple interface for agents to communicate.

```python
from aintandem_agent_sdk import ContainerAgent

class ContainerAgent:
    """
    In-container Agent Client

    Responsibilities:
    - Register with Collaboration Bus
    - Send/receive messages
    - Collaborate with other containers
    - Handle reconnection and error recovery
    """

    def __init__(
        self,
        sandbox_id: str,
        collaboration_bus_url: str,  # "http://bus-service:8000"
        agent: BaseAgent,
        config: ContainerAgentConfig = None
    ):
        self.sandbox_id = sandbox_id
        self.bus_url = collaboration_bus_url
        self.agent = agent
        self.config = config or ContainerAgentConfig()

    async def start(self):
        """Start and register with the bus"""
        await self.register()
        asyncio.create_task(self._message_loop())
        asyncio.create_task(self._heartbeat_loop())

    async def send_message(
        self,
        target_sandbox: str,
        content: Dict[str, Any],
        message_type: MessageType = MessageType.REQUEST
    ) -> str:
        """Send a message to another container"""
        pass

    async def broadcast(self, content: Dict[str, Any]):
        """Broadcast a message to all containers"""
        pass

    async def collaborate_with(
        self,
        target_sandbox: str,
        task: str,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """Initiate collaboration with another container"""
        pass
```

### 3. AInTandem Core API (Unified Entry Point)

The Core API provides unified management for workspaces, sandboxes, and agents.

```python
class AInTandemCoreAPI:
    """
    Core Service API

    Provides:
    - Workspace management
    - Sandbox management
    - Agent management
    - Collaboration Bus management
    """

    # Workspace endpoints
    POST   /api/v1/workspaces                    # Create workspace
    GET    /api/v1/workspaces                    # List workspaces
    GET    /api/v1/workspaces/{id}               # Get workspace details
    PUT    /api/v1/workspaces/{id}               # Update workspace
    DELETE /api/v1/workspaces/{id}               # Delete workspace

    # Sandbox endpoints
    POST   /api/v1/sandboxes                     # Create sandbox container
    GET    /api/v1/sandboxes                     # List sandboxes
    GET    /api/v1/sandboxes/{id}                # Get sandbox details
    GET    /api/v1/sandboxes/{id}/status         # Get sandbox status
    GET    /api/v1/sandboxes/{id}/logs           # Get sandbox logs
    POST   /api/v1/sandboxes/{id}/start          # Start sandbox
    POST   /api/v1/sandboxes/{id}/stop           # Stop sandbox
    DELETE /api/v1/sandboxes/{id}                # Delete sandbox

    # Collaboration endpoints
    GET    /api/v1/collaboration/status          # Get bus status
    GET    /api/v1/collaboration/sandboxes       # Get registered sandboxes
    POST   /api/v1/collaboration/disconnect      # Force disconnect sandbox
```

## Message Protocol

### AgentMessage Structure

```python
@dataclass
class AgentMessage:
    """Message protocol for inter-agent communication"""
    message_id: str                    # Unique message identifier
    from_sandbox: str                  # Source sandbox ID
    to_sandbox: str                    # Target sandbox ID (or "broadcast")
    from_agent: str                    # Source agent name
    to_agent: str                      # Target agent name (or "any")
    message_type: MessageType          # request, response, notification, command
    content: Dict[str, Any]            # Message content
    timestamp: float                   # Unix timestamp
    priority: int = 5                  # 0-9, 9 = highest
    requires_response: bool = False     # Whether response is required
    correlation_id: Optional[str] = None  # For request-response tracking
    ttl: Optional[int] = None          # Time to live (seconds)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata
```

### Message Types

| Type | Description | Requires ACK | Use Case |
|------|-------------|--------------|----------|
| `REQUEST` | Request assistance or resources | Yes | Agent A needs help from Agent B |
| `RESPONSE` | Response to a request | No | Agent B responds to Agent A |
| `NOTIFICATION` | Broadcast notification | No | Agent publishes update |
| `COMMAND` | Command with authorization | Yes | Admin/manager command |

## Deployment

### Community Edition (Single Machine)

```yaml
# docker-compose.yml
version: '3.8'

services:
  collaboration-bus:
    image: aintandem/collaboration-bus:latest
    ports:
      - "8001:8000"
    environment:
      - MESSAGE_BACKEND=redis
      - REDIS_URL=redis://redis:6379
      - LOG_LEVEL=INFO
      - EDITION=community
    depends_on:
      - redis
    restart: unless-stopped

  core-api:
    image: aintandem/core-api:latest
    ports:
      - "8000:8000"
    environment:
      - COLLABORATION_BUS_URL=http://collaboration-bus:8000
      - DATABASE_URL=sqlite:///data/aintandem.db
      - EDITION=community
    volumes:
      - ./data:/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  # Example agent containers
  agent-team-a:
    image: aintandem/agent-team:latest
    environment:
      - SANDBOX_ID=team-a
      - COLLABORATION_BUS_URL=http://collaboration-bus:8000
      - AGENT_CONFIG=/config/team-a.yaml
    volumes:
      - ./config/team-a.yaml:/config/team-a.yaml
    depends_on:
      - collaboration-bus
    restart: unless-stopped

  agent-team-b:
    image: aintandem/agent-team:latest
    environment:
      - SANDBOX_ID=team-b
      - COLLABORATION_BUS_URL=http://collaboration-bus:8000
      - AGENT_CONFIG=/config/team-b.yaml
    volumes:
      - ./config/team-b.yaml:/config/team-b.yaml
    depends_on:
      - collaboration-bus
    restart: unless-stopped

volumes:
  redis_data:
```

### Enterprise Edition (Distributed)

```yaml
# docker-compose.enterprise.yml
version: '3.8'

services:
  collaboration-bus:
    image: aintandem/collaboration-b:latest
    ports:
      - "8001:8000"
    environment:
      - MESSAGE_BACKEND=nats
      - NATS_URL=nats://nats:4222
      - LOG_LEVEL=INFO
      - EDITION=enterprise
      - AUTH_ENABLED=true
      - AUTH_JWT_SECRET=${JWT_SECRET}
    depends_on:
      - nats
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
    networks:
      - aintandem-net

  core-api:
    image: aintandem/core-api:latest
    ports:
      - "8000:8000"
    environment:
      - COLLABORATION_BUS_URL=http://collaboration-bus:8000
      - DATABASE_URL=postgresql://user:pass@postgres:5432/aintandem
      - REDIS_URL=redis://redis:6379
      - EDITION=enterprise
      - AUTH_ENABLED=true
      - SSO_ENABLED=true
      - SSO_URL=${SSO_URL}
    depends_on:
      - collaboration-bus
      - postgres
      - redis
    deploy:
      replicas: 2
      restart_policy:
        condition: on-failure
    networks:
      - aintandem-net

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=aintandem
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - aintandem-net

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - aintandem-net

  nats:
    image: nats:latest
    command: "-js"
    ports:
      - "4222:4222"
      - "8222:8222"
    networks:
      - aintandem-net

networks:
  aintandem-net:
    driver: overlay

volumes:
  postgres_data:
  redis_data:
```

## Implementation Phases

### Phase 1: Core Communication Infrastructure
- [ ] Implement `CollaborationBusService` with REST API
- [ ] Implement `AgentMessage` protocol
- [ ] Implement Redis message backend
- [ ] WebSocket subscription support
- [ ] Basic sandbox registration/discovery

### Phase 2: Container Agent SDK
- [ ] Implement `ContainerAgent` SDK
- [ ] HTTP/WebSocket client implementation
- [ ] Automatic reconnection logic
- [ ] Heartbeat and health monitoring
- [ ] Error handling and retry logic

### Phase 3: Core API Integration
- [ ] Implement `AInTandemCoreAPI` endpoints
- [ ] Docker container management integration
- [ ] Workspace and sandbox lifecycle management
- [ ] Authentication and authorization
- [ ] Logging and monitoring

### Phase 4: Desktop GUI
- [ ] Workspace manager interface
- [ ] Sandbox monitor interface
- [ ] Real-time collaboration visualization
- [ ] Configuration management
- [ ] Log viewer

### Phase 5: Enterprise Features
- [ ] Multi-machine deployment support
- [ ] NATS message backend
- [ ] PostgreSQL integration
- [ ] SSO/LDAP authentication
- [ ] Advanced monitoring and alerting
- [ ] Audit logging

## Technology Stack

### Backend Services
- **API Framework**: FastAPI
- **Message Bus**: Redis (Community), NATS/RabbitMQ (Enterprise)
- **Database**: SQLite (Community), PostgreSQL (Enterprise)
- **Container Runtime**: Docker API
- **Authentication**: JWT (Community), SSO/LDAP (Enterprise)

### SDK
- **Language**: Python 3.10+
- **HTTP Client**: httpx
- **WebSocket Client**: websockets
- **Serialization**: Pydantic

### Desktop GUI
- **Framework**: Tauri or Electron
- **Frontend**: React + TypeScript
- **UI Library**: shadcn/ui

## Security Considerations

### Authentication
- JWT-based authentication for all services
- API key support for external integrations
- SSO integration for enterprise edition

### Authorization
- Role-based access control (RBAC)
- Sandbox isolation enforcement
- Cross-container access policies

### Network Security
- TLS for all network communication
- Network isolation between sandboxes
- Configurable network access policies

### Audit
- All messages logged with timestamp
- Sandbox action audit trail
- Failed authentication logging

## Performance Considerations

### Scalability
- Horizontal scaling of Collaboration Bus
- Message partitioning by topic
- Connection pooling for backend services

### Reliability
- Message persistence and replay
- Dead letter queue for failed messages
- Automatic failover for enterprise edition

### Monitoring
- Prometheus metrics export
- Health check endpoints
- Real-time message rate monitoring

## Related Documentation

- [Agent Team Collaboration](./AGENT_TEAM_COLLABORATION.md)
- [MCP Integration Strategy](./MCP_INTEGRATION_STRATEGY.md)
- [MCP Server Configuration](./MCP_SERVER_CONFIGURATION.md)

## References

- [AInTandem Official Website](https://www.aintandem.org/)
- [Docker API Documentation](https://docs.docker.com/engine/api/)
- [Redis Pub/Sub](https://redis.io/docs/manual/pubsub/)
- [NATS Documentation](https://docs.nats.io/)

---

**Document Version:** 1.0
**Last Updated:** 2025-01-10
**Status:** Architecture Design
