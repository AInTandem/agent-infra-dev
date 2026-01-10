# Round Table - Standard MVP Implementation Plan

## Project Overview

**Project**: Round Table - Agent Collaboration Bus
**MVP Scope**: Community Edition (Personal Use)
**Objective**: Build a complete, production-ready collaboration bus for AI agents

### MVP Deliverables

| Component | Description |
|-----------|-------------|
| **API Server** | Complete RESTful API + WebSocket support |
| **Python SDK** | Full-featured Python client library |
| **TypeScript SDK** | Full-featured TypeScript client library |
| **Tests** | Comprehensive test suite (infrastructure + agent interaction) |
| **Documentation** | API docs, SDK guides, examples |
| **Docker Setup** | Complete containerization for easy deployment |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Round Table MVP                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    FastAPI REST API                         │   │
│  │  - JWT Authentication                                        │   │
│  │  - Request Validation                                        │   │
│  │  - Rate Limiting                                             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                 │                                   │
│  ┌──────────────────────────────┼───────────────────────────────┐  │
│  │                              │                               │  │
│  │  ┌───────────────────────────▼──────────────────────────┐   │  │
│  │  │         Collaboration Bus Service                      │   │  │
│  │  │  - Agent Discovery                                     │   │  │
│  │  │  - Message Routing                                     │   │  │
│  │  │  - Workspace Management                                │   │  │
│  │  │  - Sandbox Lifecycle                                   │   │  │
│  │  └──────────────────────────┬──────────────────────────┘   │  │
│  │                             │                              │  │
│  │  ┌──────────────────────────▼──────────────────────────┐   │  │
│  │  │              Message Bus Layer                        │   │  │
│  │  │  - Redis (Pub/Sub, Queues)                            │   │  │
│  │  │  - WebSocket Management                               │   │  │
│  │  └──────────────────────────┬──────────────────────────┘   │  │
│  │                             │                              │  │
│  │  ┌──────────────────────────▼──────────────────────────┐   │  │
│  │  │              Storage Layer                            │   │  │
│  │  │  - SQLite (workspaces, sandboxes, users)              │   │  │
│  │  └──────────────────────────────────────────────────────┘   │  │
│  │                                                               │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

SDK Clients:
┌──────────────┐    ┌──────────────────┐
│ Python SDK   │    │ TypeScript SDK   │
│ - Pydantic   │    │ - Zod            │
│ - httpx      │    │ - axios          │
│ - websockets │    │ - ws-client      │
└──────────────┘    └──────────────────┘
```

---

## Implementation Phases

### Phase 1: Project Foundation (Week 1)

**Objective**: Set up project structure, development environment, and CI/CD

#### 1.1 Project Setup
- [ ] Create monorepo structure
- [ ] Set up Python virtual environment
- [ ] Initialize Node.js for TypeScript SDK
- [ ] Configure development tools (pre-commit, linting, formatting)
- [ ] Set up Docker Compose for local development

**Deliverables**:
```
round-table/
├── api/                    # Python API Server
│   ├── app/
│   ├── tests/
│   └── Dockerfile
├── sdk/
│   ├── python/             # Python SDK
│   │   ├── src/
│   │   ├── tests/
│   │   └── pyproject.toml
│   └── typescript/         # TypeScript SDK
│       ├── src/
│       ├── tests/
│       └── package.json
├── docker/
│   ├── docker-compose.yml
│   └── redis.conf
├── scripts/
│   └── dev.sh
├── .github/
│   └── workflows/
│       └── ci.yml
├── pyproject.toml
├── package.json
└── README.md
```

#### 1.2 CI/CD Pipeline
- [ ] Configure GitHub Actions workflow
- [ ] Set up automated testing on PR
- [ ] Configure code coverage reporting
- [ ] Add automated linting checks

#### 1.3 Testing Framework Setup
- [ ] pytest configuration with async support
- [ ] pytest-cov for coverage
- [ ] pytest-mock for mocking
- [ ] hypothesis for property-based testing
- [ ] Test database setup (SQLite in-memory)

**Testing Goals**:
- Infrastructure tests can run locally
- CI runs full test suite in < 5 minutes
- Coverage reporting for API server

---

### Phase 2: Storage Layer & Data Models (Week 2)

**Objective**: Implement database schema and core data models

#### 2.1 Database Schema
- [ ] Design SQLite schema for:
  - Users (authentication)
  - Workspaces
  - Sandboxes
  - Messages (audit log)
- [ ] Create migration system
- [ ] Implement seed data for testing

**Schema Files**:
```
api/app/db/
├── __init__.py
├── base.py           # Base database class
├── models.py         # SQLAlchemy models
├── schemas.py        # Pydantic schemas (from API spec)
└── migrations/       # Alembic migrations
```

#### 2.2 Pydantic Models
- [ ] Implement all 41 JSON schemas as Pydantic models
- [ ] Add validation logic
- [ ] Create factory classes for testing

**Models File**:
```
api/app/models/
├── __init__.py
├── auth.py           # User, AuthResponse
├── workspace.py      # Workspace, WorkspaceCreateRequest
├── sandbox.py        # Sandbox, AgentConfig, ResourceLimits
├── message.py        # AgentMessage, MessageStatus
├── collaboration.py  # Collaboration, OrchestrateCollaborationRequest
└── common.py         # SuccessResponse, ErrorResponse, Metadata
```

#### 2.3 Storage Service
- [ ] Implement database operations
- [ ] Add transaction management
- [ ] Implement repository pattern

**Tests** (Layer 1: Infrastructure):
```python
# api/tests/test_storage_layer.py
async def test_create_workspace():
    """Test workspace creation in database"""
    repo = WorkspaceRepository(db_session)
    workspace = await repo.create(WorkspaceCreateRequest(name="test"))

    assert workspace.workspace_id.startswith("ws_")
    assert workspace.name == "test"
    assert workspace.created_at is not None

async def test_workspace_constraints():
    """Test workspace constraints (property-based)"""
    @given(st.text(min_size=1, max_size=100))
    async def test_name_validation(name):
        workspace = WorkspaceCreateRequest(name=name)
        assert len(workspace.name) == len(name)
```

**Deliverables**:
- Working SQLite database with migrations
- All Pydantic models implemented
- Storage service with 80%+ test coverage
- Repository pattern for data access

---

### Phase 3: Message Bus Layer (Week 3)

**Objective**: Implement Redis-based message bus

#### 3.1 Redis Integration
- [ ] Configure Redis connection pooling
- [ ] Implement Pub/Sub operations
- [ ] Implement message queues
- [ ] Add connection health checks

**Files**:
```
api/app/message_bus/
├── __init__.py
├── client.py          # Redis client management
├── pubsub.py          # Pub/Sub operations
├── queue.py           # Message queue operations
└── health.py          # Health checks
```

#### 3.2 Message Routing
- [ ] Implement topic-based routing
- [ ] Add direct message support
- [ ] Implement broadcast functionality
- [ ] Add message acknowledgment

**Implementation**:
```python
# api/app/message_bus/router.py
class MessageRouter:
    async def publish(self, topic: str, message: AgentMessage):
        """Publish message to topic"""

    async def subscribe(self, agent_id: str, topics: List[str]):
        """Subscribe agent to topics"""

    async def send_direct(self, from_agent: str, to_agent: str, message: dict):
        """Send direct message to specific agent"""
```

#### 3.3 WebSocket Support
- [ ] WebSocket connection manager
- [ ] Topic subscription over WebSocket
- [ ] Message streaming to clients
- [ ] Connection lifecycle management

**Files**:
```
api/app/websocket/
├── __init__.py
├── manager.py         # Connection manager
├── handler.py         # Message handler
└── routes.py          # WebSocket routes
```

**Tests** (Layer 1: Infrastructure):
```python
# api/tests/test_message_bus.py
async def test_message_routing():
    """Test message is routed to correct subscribers"""
    router = MessageRouter(redis_client)

    # Subscribe agent_2 to "research" topic
    await router.subscribe("agent_2", ["research"])

    # Publish message
    msg = AgentMessage(from_agent="agent_1", content={"task": "test"})
    await router.publish("research", msg)

    # Verify agent_2 received message
    messages = await router.get_pending("agent_2")
    assert len(messages) == 1
    assert messages[0].from_agent == "agent_1"

async def test_pubsub_invariant():
    """Test invariant: message count = sum of queue sizes"""
    router = MessageRouter(redis_client)

    initial_count = await router.total_messages()
    await router.publish("test", AgentMessage(...))

    final_count = await router.total_messages()
    assert final_count == initial_count + 1
```

**Deliverables**:
- Working Redis message bus
- Pub/Sub and direct messaging
- WebSocket support
- 80%+ test coverage

---

### Phase 4: Authentication & Authorization (Week 4)

**Objective**: Implement JWT-based authentication

#### 4.1 JWT Implementation
- [ ] JWT token generation
- [ ] Token validation middleware
- [ ] Refresh token handling
- [ ] Password hashing (bcrypt)

**Files**:
```
api/app/auth/
├── __init__.py
├── jwt.py             # JWT operations
├── middleware.py      # Auth middleware
├── dependencies.py    # FastAPI dependencies
└── routes.py          # Auth endpoints
```

#### 4.2 User Management
- [ ] User registration
- [ ] User login
- [ ] Token refresh
- [ ] Logout/invalidation

**Tests** (Layer 1: Infrastructure):
```python
# api/tests/test_auth.py
async def test_user_registration():
    """Test user registration"""
    response = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "securepass123"
    })

    assert response.status_code == 201
    assert "access_token" in response.json()["data"]

async def test_jwt_validation():
    """Test JWT validation middleware"""
    # Create user and get token
    token = await create_test_user()

    # Access protected endpoint
    response = await client.get(
        "/api/v1/workspaces",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200

async def test_token_refresh():
    """Test token refresh flow"""
    refresh_token = await login_and_get_refresh_token()

    response = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token
    })

    assert response.status_code == 200
    assert "access_token" in response.json()["data"]
```

**Deliverables**:
- Complete authentication system
- JWT middleware
- User registration/login
- 90%+ test coverage

---

### Phase 5: Core API Endpoints (Week 5-6)

**Objective**: Implement all RESTful API endpoints

#### 5.1 Workspace Endpoints
- [ ] GET /workspaces - List workspaces
- [ ] POST /workspaces - Create workspace
- [ ] GET /workspaces/{id} - Get workspace details
- [ ] PUT /workspaces/{id} - Update workspace
- [ ] DELETE /workspaces/{id} - Delete workspace

**Files**:
```
api/app/api/
├── __init__.py
├── dependencies.py   # Common dependencies
├── workspaces.py     # Workspace endpoints
├── sandboxes.py      # Sandbox endpoints
├── messages.py       # Message endpoints
├── collaborations.py # Collaboration endpoints
└── system.py         # System endpoints
```

#### 5.2 Sandbox Endpoints
- [ ] GET /workspaces/{workspace_id}/sandboxes - List sandboxes
- [ ] POST /workspaces/{workspace_id}/sandboxes - Create sandbox
- [ ] GET /sandboxes/{id} - Get sandbox details
- [ ] POST /sandboxes/{id}/start - Start sandbox
- [ ] POST /sandboxes/{id}/stop - Stop sandbox
- [ ] DELETE /sandboxes/{id} - Delete sandbox
- [ ] GET /sandboxes/{id}/status - Get status
- [ ] GET /sandboxes/{id}/logs - Get logs

#### 5.3 Message Endpoints
- [ ] POST /sandboxes/{id}/messages - Send message
- [ ] GET /sandboxes/{id}/messages - Get messages
- [ ] POST /workspaces/{id}/broadcast - Broadcast message
- [ ] GET /messages/{id} - Get message details

#### 5.4 Collaboration Endpoints
- [ ] POST /workspaces/{id}/collaboration/orchestrate - Orchestrate task
- [ ] GET /collaborations/{id} - Get collaboration status
- [ ] GET /workspaces/{id}/agents/discover - Discover agents

#### 5.5 Configuration & Monitoring
- [ ] GET/PUT /workspaces/{id}/config - Workspace config
- [ ] GET/PUT /sandboxes/{id}/config - Sandbox config
- [ ] GET /sandboxes/{id}/metrics - Sandbox metrics
- [ ] GET /workspaces/{id}/metrics/aggregate - Aggregate metrics
- [ ] GET /system/health - Health check
- [ ] GET /system/info - System info

**Tests** (Layer 1: Infrastructure):
```python
# api/tests/test_api_endpoints.py
async def test_create_sandbox_workflow():
    """Test complete sandbox creation workflow"""
    # Create workspace
    workspace = await client.post("/api/v1/workspaces", json={
        "name": "test-workspace"
    })
    workspace_id = workspace.json()["data"]["workspace_id"]

    # Create sandbox
    sandbox = await client.post(
        f"/api/v1/workspaces/{workspace_id}/sandboxes",
        json={
            "name": "test-sandbox",
            "agent_config": {
                "primary_agent": "researcher",
                "model": "gpt-4"
            }
        }
    )

    assert sandbox.status_code == 201
    assert sandbox.json()["data"]["status"] == "provisioning"

async def test_message_sending():
    """Test sending message between sandboxes"""
    # Create two sandboxes
    sandbox_1 = await create_test_sandbox("agent_1")
    sandbox_2 = await create_test_sandbox("agent_2")

    # Send message
    response = await client.post(
        f"/api/v1/sandboxes/{sandbox_1['id']}/messages",
        json={
            "to_sandbox_id": sandbox_2['id'],
            "content": {"type": "greeting", "text": "hello"}
        }
    )

    assert response.status_code == 202

async def test_agent_discovery():
    """Test agent discovery endpoint"""
    # Register multiple agents
    for i in range(3):
        await create_test_sandbox(f"agent_{i}")

    # Discover agents
    response = await client.get("/api/v1/workspaces/ws_xxx/agents/discover")

    assert response.status_code == 200
    assert len(response.json()["data"]["agents"]) == 3
```

**Deliverables**:
- All 53 API endpoints implemented
- Request validation
- Error handling
- 80%+ test coverage

---

### Phase 6: Mock Agent Framework (Week 7)

**Objective**: Build deterministic mock agent framework for testing

#### 6.1 Mock Agent Implementation
- [ ] Base MockAgent class
- [ ] Behavior configuration system
- [ ] Message handler
- [ ] Lifecycle management

**Files**:
```
api/tests/mock_agents/
├── __init__.py
├── base.py            # MockAgent base class
├── behaviors.py       # Predefined behaviors
├── registry.py        # Agent registration helpers
└── scenarios.py       # Test scenarios
```

**Implementation**:
```python
# api/tests/mock_agents/base.py
class MockAgent:
    def __init__(self, agent_id: str, behavior: Dict[str, Any]):
        self.agent_id = agent_id
        self.behavior = behavior
        self.round_table_client = None
        self.message_history = []

    async def connect(self, api_url: str, token: str):
        """Connect to Round Table"""
        self.round_table_client = RoundTableClient(
            base_url=api_url,
            token=token
        )
        await self.round_table_client.register_agent(self.agent_id)

    async def handle_message(self, message: AgentMessage) -> Optional[Dict]:
        """Handle incoming message"""
        self.message_history.append(message)

        # Return response based on behavior
        msg_type = message.content.get("type")
        return self.behavior.get(msg_type, {})

    async def send_to(self, to_agent: str, content: dict):
        """Send message to another agent"""
        await self.round_table_client.send_message(
            from_agent=self.agent_id,
            to_agent=to_agent,
            content=content
        )
```

#### 6.2 Predefined Behaviors
- [ ] Echo Agent - Echoes received messages
- [ ] Calculator Agent - Performs calculations
- [ ] Researcher Agent - Simulates research tasks
- [ ] Developer Agent - Simulates development tasks

**Tests** (Layer 2: Agent Interaction):
```python
# api/tests/test_agent_interactions.py
async def test_two_agent_communication():
    """Test communication between two mock agents"""
    # Create mock agents
    agent_a = MockAgent("agent_a", {
        "request": {"status": "acknowledged"}
    })
    agent_b = MockAgent("agent_b", {
        "response": {"result": "42"}
    })

    # Connect to Round Table
    await agent_a.connect(api_url, token)
    await agent_b.connect(api_url, token)

    # Send message
    await agent_a.send_to("agent_b", {"type": "request"})

    # Verify agent_b received
    messages = await agent_b.get_messages()
    assert len(messages) == 1
    assert messages[0].content["type"] == "request"

async def test_multi_agent_collaboration():
    """Test three-agent collaboration"""
    researcher = MockAgent("researcher", {
        "task": {"status": "researching"}
    })
    developer = MockAgent("developer", {
        "research": {"status": "implementing"}
    })
    tester = MockAgent("tester", {
        "implementation": {"status": "testing"}
    })

    # Connect all
    for agent in [researcher, developer, tester]:
        await agent.connect(api_url, token)

    # Start collaboration
    await researcher.send_to("developer", {"type": "task"})

    # Let it run
    await asyncio.sleep(1)

    # Verify messages were exchanged
    assert len(researcher.message_history) > 0
    assert len(developer.message_history) > 0
    assert len(tester.message_history) > 0
```

**Deliverables**:
- Mock agent framework
- 4 predefined agent behaviors
- Agent interaction test suite
- 70%+ test coverage

---

### Phase 7: Python SDK (Week 8-9)

**Objective**: Build complete Python SDK

#### 7.1 SDK Structure
- [ ] Client initialization
- [ ] Workspace operations
- [ ] Sandbox operations
- [ ] Message operations
- [ ] Collaboration operations
- [ ] WebSocket support

**Files**:
```
sdk/python/src/
├── roundtable/
│   ├── __init__.py
│   ├── client.py         # Main client
│   ├── config.py         # Configuration
│   ├── workspaces.py     # Workspace client
│   ├── sandboxes.py      # Sandbox client
│   ├── messages.py       # Message client
│   ├── collaborations.py # Collaboration client
│   ├── websocket.py      # WebSocket client
│   ├── models.py         # Pydantic models
│   └── exceptions.py     # Custom exceptions
```

**Implementation**:
```python
# sdk/python/src/roundtable/client.py
class RoundTableClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8000/api/v1"
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.http_client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"}
        )

    @property
    def workspaces(self) -> WorkspaceClient:
        return WorkspaceClient(self.http_client)

    @property
    def sandboxes(self) -> SandboxClient:
        return SandboxClient(self.http_client)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def close(self):
        await self.http_client.aclose()
```

#### 7.2 SDK Tests
- [ ] Unit tests for all operations
- [ ] Integration tests against mock server
- [ ] Example usage tests

**Tests**:
```python
# sdk/python/tests/test_sdk.py
async def test_sdk_workspace_operations():
    """Test SDK workspace operations"""
    async with RoundTableClient(api_key="test-key") as client:
        # Create workspace
        workspace = await client.workspaces.create(
            name="test-workspace",
            description="Test workspace"
        )

        assert workspace.workspace_id.startswith("ws_")

        # List workspaces
        workspaces = await client.workspaces.list()
        assert len(workspaces) > 0

        # Get workspace
        fetched = await client.workspaces.get(workspace.workspace_id)
        assert fetched.name == "test-workspace"

async def test_sdk_sandbox_lifecycle():
    """Test sandbox lifecycle through SDK"""
    async with RoundTableClient(api_key="test-key") as client:
        # Create workspace
        workspace = await client.workspaces.create(name="test")

        # Create sandbox
        sandbox = await client.sandboxes.create(
            workspace_id=workspace.workspace_id,
            name="test-sandbox",
            agent_config={"primary_agent": "researcher"}
        )

        # Start sandbox
        await sandbox.start()
        assert (await sandbox.status()).status == "running"

        # Stop sandbox
        await sandbox.stop()
        assert (await sandbox.status()).status == "stopped"
```

**Deliverables**:
- Complete Python SDK
- Async interface
- Type hints throughout
- 80%+ test coverage
- Example scripts

---

### Phase 8: TypeScript SDK (Week 10-11)

**Objective**: Build complete TypeScript SDK

#### 8.1 SDK Structure
- [ ] Client initialization
- [ ] All API operations
- [ ] Type definitions
- [ ] WebSocket support

**Files**:
```
sdk/typescript/src/
├── index.ts
├── client.ts          # Main client
├── workspaces.ts      # Workspace client
├── sandboxes.ts       # Sandbox client
├── messages.ts        # Message client
├── collaborations.ts  # Collaboration client
├── websocket.ts       # WebSocket client
├── models.ts          # TypeScript interfaces
├── types.ts           # Common types
└── errors.ts          # Error classes
```

**Implementation**:
```typescript
// sdk/typescript/src/client.ts
export class RoundTableClient {
  private httpClient: AxiosInstance;
  private wsClient?: WebSocketClient;

  constructor(config: RoundTableConfig) {
    this.httpClient = axios.create({
      baseURL: config.baseURL || 'http://localhost:8000/api/v1',
      headers: {
        'Authorization': `Bearer ${config.apiKey}`
      }
    });
  }

  get workspaces(): WorkspaceClient {
    return new WorkspaceClient(this.httpClient);
  }

  get sandboxes(): SandboxClient {
    return new SandboxClient(this.httpClient);
  }

  async close(): Promise<void> {
    if (this.wsClient) {
      await this.wsClient.close();
    }
  }
}
```

#### 8.2 SDK Tests
- [ ] Jest test suite
- [ ] Type checking
- [ ] Integration tests

**Deliverables**:
- Complete TypeScript SDK
- Full type definitions
- 80%+ test coverage
- Example scripts

---

### Phase 9: Property-Based Testing (Week 12)

**Objective**: Add property-based tests for system invariants

#### 9.1 Identify Invariants
- [ ] Message delivery invariants
- [ ] Agent registration invariants
- [ ] Workspace state invariants

**Tests** (Layer 3: AI Behavior):
```python
# api/tests/test_properties.py
@given(st.text(min_size=1, max_size=50))
async def test_any_message_can_be_sent(message_content: str):
    """
    Property: Any valid message can be sent and received
    """
    agent_a = await create_mock_agent("agent_a")
    agent_b = await create_mock_agent("agent_b")

    await agent_a.send_to("agent_b", {"text": message_content})

    messages = await agent_b.get_messages()
    assert len(messages) == 1
    assert messages[0].content["text"] == message_content

@given(st.lists(st.text(min_size=1)))
async def test_multiple_agents_message_routing(agent_ids: List[str]):
    """
    Property: Messages are routed to all subscribed agents
    """
    topic = "test-topic"
    router = MessageRouter(redis_client)

    # Subscribe all agents
    for agent_id in agent_ids:
        await router.subscribe(agent_id, [topic])

    # Publish message
    await router.publish(topic, AgentMessage(...))

    # Verify all agents received
    for agent_id in agent_ids:
        messages = await router.get_pending(agent_id)
        assert len(messages) == 1
```

**Deliverables**:
- Property-based test suite
- Hypothesis tests for invariants
- Coverage for edge cases

---

### Phase 10: Integration & Documentation (Week 13-14)

**Objective**: Integrate all components and create documentation

#### 10.1 End-to-End Tests
- [ ] Complete workflow tests
- [ ] Multi-agent collaboration scenarios
- [ ] Error scenario tests

**Tests**:
```python
# api/tests/test_e2e.py
async def test_complete_collaboration_workflow():
    """
    E2E Test: Researcher → Developer → Tester → Documentation
    """
    async with RoundTableClient(api_key="test") as client:
        # Create workspace
        workspace = await client.workspaces.create(name="project-x")

        # Create agent teams
        researcher = await client.sandboxes.create(
            workspace.workspace_id,
            agent_config={"primary_agent": "researcher"}
        )
        developer = await client.sandboxes.create(
            workspace.workspace_id,
            agent_config={"primary_agent": "developer"}
        )

        # Start collaboration
        collaboration = await client.collaborations.orchestrate(
            workspace.workspace_id,
            task="Build a REST API",
            participants=[researcher.sandbox_id, developer.sandbox_id]
        )

        # Verify collaboration
        status = await client.collaborations.get_status(
            collaboration.collaboration_id
        )
        assert status.status in ["in_progress", "completed"]
```

#### 10.2 Documentation
- [ ] API reference (from OpenAPI spec)
- [ ] SDK quick start guides
- [ ] Example applications
- [ ] Deployment guide

**Files**:
```
docs/
├── round-table/
│   ├── README.md
│   ├── api/
│   │   ├── authentication.md
│   │   ├── workspaces.md
│   │   ├── sandboxes.md
│   │   └── messages.md
│   ├── sdk/
│   │   ├── python-quickstart.md
│   │   └── typescript-quickstart.md
│   └── examples/
│       ├── basic-usage.py
│       ├── multi-agent-collab.py
│       └── typescript-app.ts
```

#### 10.3 Docker Deployment
- [ ] Multi-stage Dockerfile for API
- [ ] Docker Compose for full stack
- [ ] Environment configuration
- [ ] Health check endpoints

**Deliverables**:
- Complete documentation
- Example applications
- Docker deployment
- E2E test suite

---

## Testing Integration Summary

Each phase includes appropriate testing:

| Phase | Testing Layer | Coverage Goal |
|-------|--------------|---------------|
| 1-4 | Infrastructure (Layer 1) | 80-90% |
| 5-6 | Agent Interaction (Layer 2) | 70-80% |
| 7-8 | SDK Unit/Integration | 80%+ |
| 9 | Property-Based (Layer 3) | Key invariants |
| 10 | E2E (All layers) | Core workflows |

---

## File Structure Summary

```
round-table/
├── api/                        # FastAPI Server
│   ├── app/
│   │   ├── main.py             # Application entry
│   │   ├── config.py           # Configuration
│   │   ├── db/                 # Database layer
│   │   ├── models/             # Pydantic models
│   │   ├── message_bus/        # Redis operations
│   │   ├── websocket/          # WebSocket handling
│   │   ├── auth/               # Authentication
│   │   ├── api/                # API endpoints
│   │   └── tests/              # Tests
│   ├── Dockerfile
│   └── requirements.txt
├── sdk/
│   ├── python/                 # Python SDK
│   │   ├── src/roundtable/
│   │   ├── tests/
│   │   ├── examples/
│   │   └── pyproject.toml
│   └── typescript/             # TypeScript SDK
│       ├── src/
│       ├── tests/
│       ├── examples/
│       └── package.json
├── docker/
│   ├── docker-compose.yml
│   └── redis.conf
├── scripts/
│   ├── dev.sh                  # Development environment
│   ├── test.sh                 # Run tests
│   └── build.sh                # Build all
├── docs/                       # Documentation
│   └── round-table/
├── .github/
│   └── workflows/
│       └── ci.yml
├── pyproject.toml
├── package.json
└── README.md
```

---

## Success Criteria

MVP is complete when:

- [ ] All 53 API endpoints implemented and tested
- [ ] Python SDK with 80%+ test coverage
- [ ] TypeScript SDK with 80%+ test coverage
- [ ] Mock agent framework with test scenarios
- [ ] Property-based tests for key invariants
- [ ] E2E tests for core workflows
- [ ] Complete documentation
- [ ] Docker deployment ready
- [ ] CI/CD pipeline passing
- [ ] Performance benchmarks met (<500ms for API calls, <100ms for message delivery)

---

## Next Steps After MVP

1. **Real AI Agent Integration**: Connect actual LLM agents
2. **Enterprise Features**: Multi-developer mode, SSO, advanced audit
3. **Performance Optimization**: Caching, connection pooling
4. **Monitoring**: Observability, metrics dashboard
5. **Community**: Examples, tutorials, contribution guidelines

---

**Document**: Round Table Standard MVP Implementation Plan
**Version**: 1.0
**Date**: 2025-01-11
**Estimated Duration**: 14 weeks
**Status**: Ready for Implementation
