# Claude Code Integration Plan

## Project Overview

**Project**: Round Table - Claude Code Integration
**Objective**: Integrate Claude Code as a collaborative agent in the Round Table ecosystem
**Benefits**:
- Enable Claude Code to collaborate with other AI agents across different machines
- Allow Claude Code to receive and process tasks from other agents
- Enable multi-agent workflows for complex development tasks
- Leverage Claude Code's powerful coding capabilities in agent swarms

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Claude Code Environment                      │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                 Claude Code Plugin                         │  │
│  │  - SessionStart Hook: Register agent                      │  │
│  │  - SessionEnd Hook: Cleanup resources                     │  │
│  │  - Agent Handlers: Process incoming messages              │  │
│  └───────────────┬───────────────────────────┬───────────────┘  │
│                  │                           │                   │
│                  │                           │                   │
│  ┌───────────────▼───────────────┐  ┌───────▼───────────────┐  │
│  │   Round Table Client          │  │   Claude Code Tools   │  │
│  │   - WebSocket connection      │  │   - Read, Write, Edit │  │
│  │   - Message routing           │  │   - Bash, Task, etc.  │  │
│  │   - Agent registration        │  └───────────────────────┘  │
│  └───────────────┬───────────────┘                              │
│                  │                                              │
└──────────────────┼──────────────────────────────────────────────┘
                   │
                   │ WebSocket + REST
                   │
┌──────────────────▼──────────────────────────────────────────────┐
│                    Round Table API Server                        │
│  - Workspace management                                         │
│  - Agent discovery & registration                               │
│  - Message routing & delivery                                   │
└──────────────────┬──────────────────────────────────────────────┘
                   │
      ┌────────────┼────────────┐
      │            │            │
┌─────▼─────┐ ┌───▼────┐ ┌────▼─────┐
│  Agent A  │ │Agent B │ │ Agent C  │
│ (Python)  │ │(Node)  │ │ (Other)  │
└───────────┘ └────────┘ └──────────┘
```

---

## Integration Components

### 1. Round Table Client Wrapper

A TypeScript client that connects Claude Code to Round Table API.

**Location**: `integrations/claude-code/src/client/`

```typescript
interface RoundTableClientConfig {
  baseUrl: string;          // Round Table API URL
  apiKey?: string;          // Optional API key
  workspaceId?: string;     // Existing workspace ID
  autoConnect?: boolean;    // Auto-connect on init
}

class RoundTableClient {
  // Connect to Round Table server
  async connect(): Promise<void>

  // Register Claude Code as an agent
  async registerAgent(config: AgentConfig): Promise<Sandbox>

  // Subscribe to message topics
  async subscribe(topics: string[]): Promise<void>

  // Send message to another agent
  async sendTo(agentId: string, content: MessageContent): Promise<void>

  // Broadcast message to workspace
  async broadcast(content: MessageContent): Promise<void>

  // Get pending messages
  async getMessages(): Promise<Message[]>

  // Disconnect and cleanup
  async disconnect(): Promise<void>
}
```

### 2. Claude Code Agent Handlers

Handlers that process incoming messages from other agents.

**Location**: `integrations/claude-code/src/handlers/`

| Handler | Description | Input | Output |
|---------|-------------|-------|--------|
| `CodeGenerationHandler` | Generate or modify code | File path, requirements | Generated code |
| `CodeReviewHandler` | Review code for issues | File path, code | Review report |
| `TestExecutionHandler` | Run tests and report | Test command, files | Test results |
| `RefactoringHandler` | Refactor code | File, requirements | Refactored code |
| `DocumentationHandler` | Generate docs | Files, format | Documentation |
| `DebugHandler` | Debug issues | Error context, files | Fix suggestions |
| `FileOperationHandler` | File operations | Operation, path, content | Success/failure |

### 3. Claude Code Hooks

Lifecycle hooks for agent registration and cleanup.

**Location**: `integrations/claude-code/hooks/`

| Hook | Trigger | Action |
|------|---------|--------|
| `SessionStart` | Claude Code starts | Register agent, connect WebSocket |
| `SessionEnd` | Claude Code exits | Unregister agent, cleanup |
| `PreToolUse` | Before tool execution | Log to Round Table |
| `PostToolUse` | After tool execution | Report result |
| `UserPromptSubmit` | User submits prompt | Broadcast if collaborative |

### 4. Plugin Configuration

**Location**: `integrations/claude-code/plugin.json`

```json
{
  "name": "round-table-integration",
  "version": "0.1.0",
  "description": "Integrate Claude Code with Round Table agent collaboration bus",
  "author": "Round Table Team",
  "permissions": [
    "network",
    "file:read",
    "file:write"
  ],
  "settings": {
    "roundTableUrl": {
      "type": "string",
      "default": "http://localhost:8000",
      "description": "Round Table API server URL"
    },
    "workspaceId": {
      "type": "string",
      "description": "Workspace ID to join (optional, creates new if not specified)"
    },
    "agentName": {
      "type": "string",
      "default": "claude-code",
      "description": "Agent name for identification"
    },
    "autoConnect": {
      "type": "boolean",
      "default": true,
      "description": "Automatically connect on startup"
    }
  },
  "hooks": {
    "SessionStart": "./dist/hooks/session-start.js",
    "SessionEnd": "./dist/hooks/session-end.js"
  },
  "skills": [
    {
      "name": "collaborate-with-agents",
      "description": "Collaborate with other AI agents via Round Table"
    }
  ]
}
```

---

## Message Protocol

### Claude Code → Other Agents

```typescript
interface ClaudeCodeMessage {
  message_id: string;
  from_agent: string;      // "claude-code-{id}"
  to_agent?: string;       // Specific agent (optional)
  workspace_id: string;
  content: {
    type: MessageType;
    action: string;
    parameters: Record<string, any>;
  };
  message_type: "request" | "response" | "notification";
  timestamp: string;
}

type MessageType =
  | "code_generation"
  | "code_review"
  | "test_execution"
  | "refactoring"
  | "documentation"
  | "debug"
  | "file_operation"
  | "status_update";
```

### Other Agents → Claude Code

```typescript
interface AgentRequest {
  message_id: string;
  from_agent: string;
  content: {
    type: MessageType;
    action: string;
    parameters: {
      // Common parameters
      task?: string;
      files?: string[];
      requirements?: string;

      // Specific parameters
      file_path?: string;       // For file operations
      code?: string;            // For code review
      test_command?: string;    // For test execution
    };
  };
}
```

---

## Implementation Phases

### Phase 1: Foundation Setup

**Objective**: Set up the plugin structure and basic connectivity

#### Tasks

1. **Project Structure**
   - [ ] Create `integrations/claude-code/` directory
   - [ ] Initialize Node.js project with TypeScript
   - [ ] Set up build system (esbuild or webpack)
   - [ ] Configure TypeScript for Claude Code plugin API

2. **Dependencies**
   - [ ] Install Round Table TypeScript SDK
   - [ ] Install Claude Code plugin types
   - [ ] Install WebSocket client library
   - [ ] Install development dependencies

3. **Basic Plugin**
   - [ ] Create `plugin.json` manifest
   - [ ] Implement `plugin-main.ts` entry point
   - [ ] Set up basic error handling
   - [ ] Add logging system

**Deliverables**:
```
integrations/claude-code/
├── plugin.json
├── package.json
├── tsconfig.json
├── src/
│   ├── main.ts
│   ├── config.ts
│   └── utils/
│       ├── logger.ts
│       └── errors.ts
└── dist/
```

---

### Phase 2: Round Table Client

**Objective**: Implement the Round Table client wrapper

#### Tasks

1. **Client Core**
   - [ ] Implement connection management
   - [ ] Implement agent registration
   - [ ] Implement WebSocket subscription
   - [ ] Implement reconnection logic

2. **Message Operations**
   - [ ] Implement send message
   - [ ] Implement broadcast
   - [ ] Implement message queue
   - [ ] Implement message handler registration

3. **Lifecycle Management**
   - [ ] Implement connect/disconnect
   - [ ] Implement health checks
   - [ ] Implement graceful shutdown

**Files**:
```
src/client/
├── index.ts              # Main client class
├── connection.ts         # Connection management
├── messages.ts           # Message operations
├── websocket.ts          # WebSocket handling
└── types.ts              # Type definitions
```

---

### Phase 3: Claude Code Hooks

**Objective**: Implement lifecycle hooks for agent registration

#### Tasks

1. **SessionStart Hook**
   - [ ] Load plugin configuration
   - [ ] Initialize Round Table client
   - [ ] Register Claude Code as agent
   - [ ] Subscribe to message topics
   - [ ] Start message polling

2. **SessionEnd Hook**
   - [ ] Unsubscribe from topics
   - [ ] Unregister agent
   - [ ] Close connections
   - [ ] Cleanup resources

3. **Tool Use Hooks (Optional)**
   - [ ] Log tool use to Round Table
   - [ ] Enable agent monitoring
   - [ ] Track collaborative sessions

**Files**:
```
src/hooks/
├── session-start.ts
├── session-end.ts
└── tool-monitor.ts       # Optional
```

---

### Phase 4: Message Handlers

**Objective**: Implement handlers for processing incoming messages

#### Tasks

1. **Handler Framework**
   - [ ] Create base handler interface
   - [ ] Implement handler registry
   - [ ] Implement message routing
   - [ ] Add error handling

2. **Core Handlers**
   - [ ] CodeGenerationHandler
   - [ ] CodeReviewHandler
   - [ ] TestExecutionHandler
   - [ ] FileOperationHandler

3. **Advanced Handlers**
   - [ ] RefactoringHandler
   - [ ] DocumentationHandler
   - [ ] DebugHandler

**Files**:
```
src/handlers/
├── index.ts              # Handler registry
├── base.ts               # Base handler interface
├── code-generation.ts
├── code-review.ts
├── test-execution.ts
├── refactoring.ts
├── documentation.ts
├── debug.ts
└── file-operation.ts
```

---

### Phase 5: Skills and Agents

**Objective**: Create Claude Code skills for agent collaboration

#### Tasks

1. **Collaboration Skill**
   - [ ] Create skill definition
   - [ ] Implement agent discovery
   - [ ] Implement task delegation
   - [ ] Implement result aggregation

2. **Agent Definition**
   - [ ] Define Claude Code agent capabilities
   - [ ] Specify supported message types
   - [ ] Document agent behavior

**Files**:
```
src/agents/
├── claude-code-agent.ts
└── capabilities.ts

skills/
└── collaborate-with-agents.md
```

---

### Phase 6: Testing

**Objective**: Comprehensive testing of integration

#### Tasks

1. **Unit Tests**
   - [ ] Test client operations
   - [ ] Test message handlers
   - [ ] Test hook execution
   - [ ] Test error handling

2. **Integration Tests**
   - [ ] Test agent registration
   - [ ] Test message flow
   - [ ] Test collaboration scenarios
   - [ ] Test reconnection logic

3. **E2E Tests**
   - [ ] Test complete workflow
   - [ ] Test multi-agent collaboration
   - [ ] Test error recovery

**Files**:
```
tests/
├── unit/
│   ├── client.test.ts
│   ├── handlers.test.ts
│   └── hooks.test.ts
├── integration/
│   ├── agent-registration.test.ts
│   └── message-flow.test.ts
└── e2e/
    └── collaboration.test.ts
```

---

### Phase 7: Documentation

**Objective**: Complete documentation for users and developers

#### Tasks

1. **User Documentation**
   - [ ] Installation guide
   - [ ] Configuration guide
   - [ ] Usage examples
   - [ ] Troubleshooting

2. **Developer Documentation**
   - [ ] Architecture overview
   - [ ] API reference
   - [ ] Handler development guide
   - [ ] Contributing guidelines

3. **Examples**
   - [ ] Simple collaboration example
   - [ ] Multi-agent workflow example
   - [ ] Custom handler example

**Files**:
```
docs/
├── README.md
├── installation.md
├── configuration.md
├── usage.md
├── api-reference.md
├── examples/
│   ├── simple-collaboration.md
│   ├── multi-agent-workflow.md
│   └── custom-handler.md
└── troubleshooting.md
```

---

## Directory Structure

```
round-table/
├── api/                          # Existing API server
├── sdk/
│   ├── python/                   # Existing Python SDK
│   └── typescript/               # Existing TypeScript SDK
├── integrations/
│   └── claude-code/              # 🆕 Claude Code Integration
│       ├── plugin.json           # Plugin manifest
│       ├── package.json          # NPM dependencies
│       ├── tsconfig.json         # TypeScript config
│       ├── README.md             # Plugin README
│       ├── src/
│       │   ├── main.ts           # Entry point
│       │   ├── config.ts         # Configuration management
│       │   ├── client/           # Round Table client
│       │   │   ├── index.ts
│       │   │   ├── connection.ts
│       │   │   ├── messages.ts
│       │   │   ├── websocket.ts
│       │   │   └── types.ts
│       │   ├── handlers/         # Message handlers
│       │   │   ├── index.ts
│       │   │   ├── base.ts
│       │   │   ├── code-generation.ts
│       │   │   ├── code-review.ts
│       │   │   ├── test-execution.ts
│       │   │   ├── refactoring.ts
│       │   │   ├── documentation.ts
│       │   │   ├── debug.ts
│       │   │   └── file-operation.ts
│       │   ├── hooks/            # Claude Code hooks
│       │   │   ├── session-start.ts
│       │   │   ├── session-end.ts
│       │   │   └── tool-monitor.ts
│       │   ├── agents/           # Agent definitions
│       │   │   ├── claude-code-agent.ts
│       │   │   └── capabilities.ts
│       │   └── utils/
│       │       ├── logger.ts
│       │       ├── errors.ts
│       │       └── validation.ts
│       ├── skills/               # Claude Code skills
│       │   └── collaborate-with-agents.md
│       ├── tests/
│       │   ├── unit/
│       │   ├── integration/
│       │   └── e2e/
│       ├── docs/
│       │   ├── installation.md
│       │   ├── configuration.md
│       │   ├── usage.md
│       │   ├── api-reference.md
│       │   └── examples/
│       ├── dist/                 # Compiled output
│       └── scripts/
│           ├── build.ts
│           └── dev.ts
├── docker/
├── docs/
├── plans/
│   ├── round-table-mvp.md        # Existing MVP plan
│   └── claude-code-integration.md # This file
└── worklogs/
    └── claude-code-integration/
        ├── phase-1.md
        ├── phase-2.md
        └── ...
```

---

## Usage Example

### Basic Usage

```markdown
# In Claude Code, after plugin installation:

> /collaborate with research-agent on data analysis

# Claude Code will:
1. Connect to Round Table
2. Register as an agent
3. Send task to research-agent
4. Receive analysis results
5. Generate code based on analysis
```

### Multi-Agent Workflow

```markdown
> Create a REST API with the help of agent team

# Agents involved:
- claude-code: Code generation and implementation
- research-agent: API design research
- test-agent: Test generation and execution
- doc-agent: Documentation generation

# Workflow:
1. Research agent proposes API design
2. Claude Code implements endpoints
3. Test agent generates and runs tests
4. Doc agent generates API documentation
5. All agents collaborate through Round Table
```

---

## Configuration Example

**File**: `~/.claude/plugins/round-table-integration/.local.md`

```yaml
---
roundTableUrl: "http://localhost:8000"
workspaceId: "ws_dev_team_123"
agentName: "claude-code-primary"
autoConnect: true

# Subscriptions
topics:
  - code-review
  - testing
  - documentation

# Capabilities
capabilities:
  - code-generation
  - code-review
  - refactoring
  - testing
  - debugging

# Collaboration settings
collaboration:
  autoAcceptTasks: false
  maxConcurrentTasks: 3
  taskTimeout: 300  # seconds
---

# Claude Code Round Table Integration

This plugin enables Claude Code to collaborate with other AI agents through the Round Table infrastructure.

## Features

- **Agent Registration**: Automatically register as an agent on startup
- **Message Handling**: Process requests from other agents
- **Task Collaboration**: Work with multiple agents on complex tasks
- **Status Broadcasting**: Share progress with the team

## Configuration

Edit the frontmatter above to customize:
- `roundTableUrl`: Your Round Table server URL
- `workspaceId`: Workspace to join (creates new if not specified)
- `agentName`: Name for this agent instance
- `autoConnect`: Automatically connect on startup
```

---

## Success Criteria

Integration is complete when:

- [ ] Plugin can be installed in Claude Code
- [ ] Agent successfully registers on startup
- [ ] Can receive and process messages from other agents
- [ ] Can send messages to other agents
- [ ] All core handlers implemented and tested
- [ ] WebSocket connection stable with reconnection
- [ ] Comprehensive test coverage (80%+)
- [ ] Complete documentation with examples
- [ ] E2E tests demonstrate multi-agent collaboration
- [ ] Performance: <100ms message processing latency

---

## Next Steps

After integration complete:

1. **Advanced Features**
   - Task scheduling and queuing
   - Result caching
   - Agent capability negotiation
   - Collaborative debugging

2. **Monitoring**
   - Integration with Round Table metrics
   - Performance monitoring
   - Collaboration analytics

3. **Community**
   - Publish to Claude Code plugin marketplace
   - Share example workflows
   - Create handler templates

---

**Document**: Claude Code Integration Plan
**Version**: 1.0
**Date**: 2025-01-11
**Status**: Ready for Implementation
**Dependencies**: Round Table MVP (Phases 1-10)
