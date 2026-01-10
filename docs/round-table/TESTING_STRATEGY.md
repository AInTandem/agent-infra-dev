# Round Table - Testing Strategy

## Challenge: Testing AI Agent Systems

Traditional testing approaches fail with AI Agent systems because AI responses are **non-deterministic**:

```
Traditional:  input → [system] → expected_output  ✅ Predictable
AI Agent:     input → [AI]    → ???               ❌ Unpredictable
```

### The Three "Dings" We Lack

| Aspect | Traditional Systems | AI Agent Systems |
|--------|-------------------|------------------|
| **定性 (Qualitative)** | Fixed output types | Variable response types |
| **定向 (Directional)** | Predictable behavior | Emergent behavior |
| **定量 (Quantitative)** | Exact values | Probabilistic outcomes |

---

## Solution: Layered Testing Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                    ROUND TABLE TESTING PYRAMID                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                    ▲                                             │
│                   ╱ ╲                                            │
│                  ╱   ╲          AI Agent Behavior Testing        │
│                 ╱─────╲         (Property-Based, Simulation)     │
│                ╱       ╲                                       │
│               ╱─────────╲      Agent Interaction Testing         │
│              ╱___________╲     (Contract-Based, Mock Agents)     │
│             ╱             ╲                                    │
│            ╱_______________╲   Infrastructure Testing            │
│                                (Unit, Integration, E2E)          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Infrastructure Testing (Deterministic)

**Goal**: Verify the collaboration bus infrastructure works correctly

**Scope**:
- API Server endpoints
- Message Bus (Redis/NATS) operations
- Storage layer (SQLite/PostgreSQL)
- Authentication & Authorization
- WebSocket connections

**Testing Approach**: Traditional testing methods work here

### 1.1 Unit Tests

```python
# Example: Testing message queue operations
def test_enqueue_message():
    """Test that messages are correctly queued"""
    queue = MessageQueue(redis_client)
    message = AgentMessage(
        from_agent="agent_1",
        to_agent="agent_2",
        content={"task": "hello"}
    )

    message_id = await queue.enqueue(message)

    assert message_id is not None
    assert await queue.size("agent_2") == 1

def test_message_routing():
    """Test that messages are routed correctly"""
    router = MessageRouter(redis_client)

    # Subscribe agent_2 to "research" channel
    await router.subscribe("agent_2", ["research"])

    # Publish message
    await router.publish("research", message)

    # Verify routing
    queued_for = await router.get_recipients("research")
    assert "agent_2" in queued_for
```

### 1.2 Integration Tests

```python
# Example: Testing API → Message Bus integration
async def test_api_sends_message_to_bus():
    """Test that API calls correctly publish to message bus"""
    # Setup
    api_client = APIClient(base_url="http://localhost:8000")
    test_message = {
        "from_sandbox": "sb_abc123def4",
        "to_sandbox": "sb_xyz789ghi1",
        "content": {"type": "greeting", "text": "hello"}
    }

    # Execute
    response = await api_client.post("/api/v1/messages", json=test_message)

    # Verify
    assert response.status_code == 202
    assert await message_bus.exists("sb_xyz789ghi1")
```

### 1.3 Contract Tests

```python
# Example: Testing API contract compliance
def test_api_response_format():
    """Test that all responses follow the standard format"""
    response = client.get("/api/v1/workspaces")

    # Verify standard wrapper
    assert "success" in response.json()
    assert "data" in response.json()
    assert "meta" in response.json()
    assert response.json()["meta"]["request_id"] is not None
```

---

## Layer 2: Agent Interaction Testing (Semi-Deterministic)

**Goal**: Verify agents can interact through the bus correctly

**Strategy**: Use **Mock Agents** with deterministic behavior

### 2.1 Mock Agent Framework

```python
class MockAgent:
    """
    A mock agent that behaves deterministically for testing
    """
    def __init__(self, agent_id: str, behavior: dict):
        self.agent_id = agent_id
        self.behavior = behavior  # Predefined responses

    async def send_message(self, to_agent: str, content: dict):
        """Send message through Round Table"""
        await round_table_client.send_message(
            from_agent=self.agent_id,
            to_agent=to_agent,
            content=content
        )

    async def handle_message(self, message: AgentMessage):
        """Handle incoming message with deterministic response"""
        response_type = self.behavior.get(message.type)
        return {
            "from_agent": self.agent_id,
            "content": response_type
        }
```

### 2.2 Interaction Scenarios

```python
async def test_two_agent_communication():
    """Test that two agents can exchange messages"""
    # Create mock agents
    agent_a = MockAgent("agent_a", {
        "request": {"status": "acknowledged", "data": "processing"}
    })
    agent_b = MockAgent("agent_b", {
        "response": {"status": "completed", "result": "42"}
    })

    # Register agents
    await round_table.register(agent_a)
    await round_table.register(agent_b)

    # Test communication
    await agent_a.send_message("agent_b", {"type": "request"})

    # Verify
    messages = await agent_b.get_messages()
    assert len(messages) == 1
    assert messages[0].content["type"] == "request"
```

### 2.3 Contract-Based Testing

```python
# Define agent interaction contracts
class AgentContract:
    """
    Defines the contract agents must follow
    """
    @staticmethod
    def validate_message(message: AgentMessage) -> bool:
        """Validate message structure"""
        return (
            hasattr(message, 'from_agent') and
            hasattr(message, 'to_agent') and
            hasattr(message, 'content') and
            isinstance(message.content, dict)
        )

    @staticmethod
    def validate_response_time(response_time: float) -> bool:
        """Validate response time SLA"""
        return response_time < 5.0  # 5 seconds

# Test contract compliance
def test_agent_follows_contract():
    """Test that agents follow interaction contracts"""
    message = AgentMessage(
        from_agent="agent_1",
        to_agent="agent_2",
        content={"task": "test"}
    )

    assert AgentContract.validate_message(message)
```

---

## Layer 3: AI Agent Behavior Testing (Non-Deterministic)

**Goal**: Verify AI agents can collaborate effectively despite non-deterministic responses

**Strategy**: Focus on **properties** and **behaviors**, not exact outputs

### 3.1 Property-Based Testing

Instead of testing exact outputs, test **properties** that should always hold:

```python
# Using hypothesis for property-based testing
from hypothesis import given, strategies as st

@given(st.text(min_size=1))
async def test_message_delivery_property(task_description: str):
    """
    Property: All messages from Agent A should reach Agent B
    regardless of task content
    """
    agent_a = await create_test_agent("researcher")
    agent_b = await create_test_agent("developer")

    # Send any task
    await agent_a.send_to(agent_b, {"task": task_description})

    # Property: Agent B should receive exactly one message
    messages = await agent_b.get_messages()
    assert len(messages) == 1

    # Property: Message should contain required fields
    assert "from_agent" in messages[0]
    assert "content" in messages[0]
```

### 3.2 Invariant Testing

Test **invariants** - properties that should never change:

```python
async def test_system_invariants():
    """
    Invariants that should always hold:
    1. Total messages = sum of messages in all agent queues
    2. No message exists in system without a sender
    3. All registered agents are discoverable
    """
    # Register agents
    agents = [create_agent(f"agent_{i}") for i in range(5)]
    for agent in agents:
        await round_table.register(agent)

    # Send messages
    for i, agent in enumerate(agents):
        if i < len(agents) - 1:
            await agent.send_to(agents[i+1], {"test": i})

    # Verify invariants
    total_messages = await round_table.total_messages()
    sum_queue_sizes = sum([await a.queue_size() for a in agents])

    assert total_messages == sum_queue_sizes  # Invariant 1
```

### 3.3 Simulation Testing

Create realistic scenarios and observe system behavior:

```python
async def test_collaboration_scenario():
    """
    Simulate a realistic collaboration scenario:
    Researcher → Developer → Tester → Documentation
    """
    # Create agents
    researcher = create_ai_agent("researcher", model="gpt-4")
    developer = create_ai_agent("developer", model="gpt-4")
    tester = create_ai_agent("tester", model="gpt-4")
    docs = create_ai_agent("docs", model="gpt-4")

    # Register all
    for agent in [researcher, developer, tester, docs]:
        await round_table.register(agent)

    # Start collaboration
    await researcher.broadcast({
        "type": "task",
        "topic": "Build a REST API for task management"
    })

    # Let collaboration run
    await asyncio.sleep(30)

    # Verify properties (not exact messages)
    assert await developer.message_count() > 0
    assert await tester.message_count() > 0
    assert await docs.message_count() > 0

    # Verify collaboration happened
    participants = await round_table.get_participants()
    assert len(participants) >= 4
```

### 3.4 Oracle-Based Testing

Use a **deterministic reference implementation** as oracle:

```python
class DeterministicOrcale:
    """
    A simple, deterministic implementation that we trust
    """
    def handle_task(self, task: dict) -> dict:
        # Simple, predictable logic
        if task["type"] == "add":
            return {"result": task["a"] + task["b"]}
        elif task["type"] == "multiply":
            return {"result": task["a"] * task["b"]}

async def test_ai_agent_oracle():
    """
    Compare AI agent behavior against deterministic oracle
    """
    oracle = DeterministicOrcale()
    ai_agent = create_ai_agent("calculator", model="gpt-4")

    # Test cases
    tasks = [
        {"type": "add", "a": 2, "b": 3},
        {"type": "multiply", "a": 4, "b": 5}
    ]

    for task in tasks:
        # Get oracle result (deterministic)
        oracle_result = oracle.handle_task(task)

        # Get AI agent result (may vary in format, but should have same meaning)
        ai_response = await ai_agent.handle(task)

        # Property: Both should have correct answer
        assert oracle_result["result"] == extract_number(ai_response)
```

---

## Layer 4: Golden Master Testing

For complex scenarios, use **Golden Master** approach:

### 4.1 Record & Replay

```python
# Step 1: Record successful interactions
async def record_successful_collaboration():
    """Record a successful collaboration as golden master"""
    interactions = await capture_collaboration(
        agents=[researcher, developer, tester],
        task="Build a todo list API"
    )

    # Save as golden master
    save_golden_master("todo_api_collaboration.json", interactions)

# Step 2: Compare future runs against golden master
async def test_against_golden_master():
    """Test that system produces equivalent behavior"""
    current = await capture_collaboration(
        agents=[researcher, developer, tester],
        task="Build a todo list API"
    )

    golden = load_golden_master("todo_api_collaboration.json")

    # Compare properties, not exact messages
    assert len(current) == len(golden)
    assert current.task_completion_time < golden.task_completion_time * 1.2
    assert current.success_rate >= golden.success_rate
```

---

## Test Categories Summary

| Layer | Focus | Determinism | Testing Method |
|-------|-------|-------------|----------------|
| **Infrastructure** | API, Message Bus, Storage | ✅ Deterministic | Unit, Integration, E2E |
| **Agent Interaction** | Agent-to-agent communication | 🟡 Semi-deterministic | Mock Agents, Contracts |
| **AI Behavior** | AI agent collaboration | ❌ Non-deterministic | Property-Based, Invariants, Simulation |
| **Golden Master** | Complex scenarios | 🟡 Semi-deterministic | Record & Replay |

---

## Coverage Metrics

### Traditional Coverage (for Infrastructure)

- Line coverage: > 80%
- Branch coverage: > 70%
- Function coverage: > 90%

### AI System Coverage (for Agent Behavior)

- **Property Coverage**: Percentage of invariants tested
- **Scenario Coverage**: Number of collaboration scenarios tested
- **Agent Type Coverage**: Different agent types and models tested
- **Failure Mode Coverage**: Edge cases and error scenarios

---

## Continuous Testing Strategy

### 1. Fast Feedback Loop (Infrastructure)

```yaml
# On every commit
- Run unit tests (< 30 seconds)
- Run contract tests (< 1 minute)
- Run smoke tests (< 2 minutes)
```

### 2. Comprehensive Testing (Daily)

```yaml
# Daily CI/CD
- Run full integration suite (< 10 minutes)
- Run mock agent scenarios (< 15 minutes)
- Run property-based tests (< 20 minutes)
```

### 3. Deep Testing (Weekly)

```yaml
# Weekly
- Run simulation tests (< 1 hour)
- Run golden master comparisons (< 30 minutes)
- Run chaos engineering tests (< 1 hour)
```

---

## Implementation Roadmap

### Phase 1: Infrastructure Tests (Week 1-2)
- [ ] Unit tests for all core components
- [ ] Integration tests for API endpoints
- [ ] Contract tests for API compliance

### Phase 2: Mock Agent Framework (Week 3-4)
- [ ] Implement MockAgent class
- [ ] Create test scenarios with mock agents
- [ ] Test agent discovery and registration

### Phase 3: Property-Based Testing (Week 5-6)
- [ ] Identify system invariants
- [ ] Implement property tests
- [ ] Create simulation scenarios

### Phase 4: Golden Master (Week 7-8)
- [ ] Record golden master scenarios
- [ ] Implement comparison logic
- [ ] Set up regression detection

---

## Tools & Frameworks

### Testing Frameworks

| Purpose | Tool |
|---------|------|
| Unit/Integration Tests | pytest, unittest |
| Property-Based Testing | Hypothesis, QuickCheck |
| Mock Agents | Custom framework, pytest-mock |
| Contract Testing | Pact, JSON Schema validation |
| Load Testing | Locust, k6 |
| Chaos Engineering | Chaos Monkey, Toxiproxy |

### AI Testing Tools

| Purpose | Tool |
|---------|------|
| Response Validation | JSON Schema, Pydantic |
| Behavior Analysis | Custom metrics, observability |
| Simulation | Deterministic mocks, record/replay |

---

## Conclusion

Testing AI Agent systems requires a **paradigm shift**:

1. **Don't test exact outputs** - Test properties and invariants
2. **Don't rely on determinism** - Embrace and test for non-determinism
3. **Don't test in isolation** - Test interactions and emergent behavior
4. **Don't forget the basics** - Infrastructure still needs traditional testing

The key is **layered testing**: each layer uses appropriate methods for its level of determinism.

---

**Document**: Round Table Testing Strategy
**Version**: 1.0
**Date**: 2025-01-11
**Status**: Draft for Review
