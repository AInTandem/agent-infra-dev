# AInTandem API - RESTful Endpoints Specification

## Document Purpose

This document defines the RESTful API endpoints for the AInTandem platform. This specification serves as the foundation for both Python and TypeScript SDK implementations.

## Base URL

```
Community Edition:  http://localhost:8000/api/v1
Enterprise Edition:  https://api.aintandem.com/api/v1
```

## API Versioning

- **Current Version**: v1
- **Version Format**: `/api/v{version}`
- **Backward Compatibility**: Maintained within major versions
- **Deprecation Policy**: 6-month notice for breaking changes

## Common Headers

```http
Authorization: Bearer {jwt_token}
Content-Type: application/json
Accept: application/json
X-Request-ID: {uuid}
X-Client-Version: {sdk_version}
```

## Common Response Format

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2025-01-10T15:30:00Z",
    "version": "1.0.0"
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested resource was not found",
    "details": { ... }
  },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2025-01-10T15:30:00Z"
  }
}
```

---

## API Endpoints

### 1. Authentication

#### POST /auth/register
Register a new user account.

**Request**:
```json
{
  "email": "user@example.com",
  "password": "secure_password",
  "name": "John Doe",
  "organization": "Example Corp"
}
```

**Response**: 201 Created
```json
{
  "success": true,
  "data": {
    "user_id": "usr_1234567890",
    "email": "user@example.com",
    "name": "John Doe",
    "created_at": "2025-01-10T15:30:00Z"
  }
}
```

#### POST /auth/login
Authenticate and receive access token.

**Request**:
```json
{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Response**: 200 OK
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 3600,
    "user": {
      "user_id": "usr_1234567890",
      "email": "user@example.com",
      "name": "John Doe"
    }
  }
}
```

#### POST /auth/refresh
Refresh access token using refresh token.

**Request**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response**: 200 OK
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "expires_in": 3600
  }
}
```

#### POST /auth/logout
Invalidate current session.

**Response**: 204 No Content

---

### 2. Workspaces

#### GET /workspaces
List all workspaces accessible to the user.

**Query Parameters**:
- `page` (integer, default: 1)
- `per_page` (integer, default: 20, max: 100)
- `sort` (string, default: "created_at")
- `order` (string, enum: "asc", "desc", default: "desc")
- `search` (string, optional)

**Response**: 200 OK
```json
{
  "success": true,
  "data": [
    {
      "workspace_id": "ws_1234567890",
      "name": "E-commerce Development",
      "description": "AI agents for e-commerce platform",
      "owner_id": "usr_1234567890",
      "settings": {
        "max_sandboxes": 10,
        "default_llm_provider": "qwen"
      },
      "sandbox_count": 4,
      "created_at": "2025-01-10T10:00:00Z",
      "updated_at": "2025-01-10T15:30:00Z"
    }
  ],
  "meta": {
    "total": 1,
    "page": 1,
    "per_page": 20,
    "total_pages": 1
  }
}
```

#### POST /workspaces
Create a new workspace.

**Request**:
```json
{
  "name": "E-commerce Development",
  "description": "AI agents for e-commerce platform",
  "settings": {
    "max_sandboxes": 10,
    "default_llm_provider": "qwen",
    "collaboration_policy": "allow_list"
  }
}
```

**Response**: 201 Created
```json
{
  "success": true,
  "data": {
    "workspace_id": "ws_1234567890",
    "name": "E-commerce Development",
    "description": "AI agents for e-commerce platform",
    "owner_id": "usr_1234567890",
    "settings": { ... },
    "created_at": "2025-01-10T15:30:00Z"
  }
}
```

#### GET /workspaces/{workspace_id}
Get workspace details.

**Response**: 200 OK
```json
{
  "success": true,
  "data": {
    "workspace_id": "ws_1234567890",
    "name": "E-commerce Development",
    "description": "AI agents for e-commerce platform",
    "owner_id": "usr_1234567890",
    "settings": { ... },
    "sandbox_count": 4,
    "sandboxes": [
      {
        "sandbox_id": "sb_1234567890",
        "name": "frontend-team",
        "status": "running"
      }
    ],
    "created_at": "2025-01-10T10:00:00Z",
    "updated_at": "2025-01-10T15:30:00Z"
  }
}
```

#### PUT /workspaces/{workspace_id}
Update workspace configuration.

**Request**:
```json
{
  "name": "E-commerce Development (Updated)",
  "description": "AI agents for e-commerce platform",
  "settings": {
    "max_sandboxes": 20
  }
}
```

**Response**: 200 OK
```json
{
  "success": true,
  "data": {
    "workspace_id": "ws_1234567890",
    "name": "E-commerce Development (Updated)",
    "updated_at": "2025-01-10T16:00:00Z"
  }
}
```

#### DELETE /workspaces/{workspace_id}
Delete a workspace and all its resources.

**Response**: 204 No Content

---

### 3. Sandboxes

#### GET /workspaces/{workspace_id}/sandboxes
List all sandboxes in a workspace.

**Query Parameters**:
- `status` (string, enum: "running", "stopped", "error", optional)
- `page`, `per_page`, `sort`, `order`, `search`

**Response**: 200 OK
```json
{
  "success": true,
  "data": [
    {
      "sandbox_id": "sb_1234567890",
      "name": "frontend-team",
      "workspace_id": "ws_1234567890",
      "status": "running",
      "agent_config": { ... },
      "resources": {
        "memory_mb": 512,
        "cpu_cores": 1
      },
      "health": {
        "status": "healthy",
        "last_heartbeat": "2025-01-10T15:30:00Z"
      },
      "created_at": "2025-01-10T10:00:00Z"
    }
  ],
  "meta": {
    "total": 4,
    "page": 1,
    "per_page": 20
  }
}
```

#### POST /workspaces/{workspace_id}/sandboxes
Create a new sandbox.

**Request**:
```json
{
  "name": "frontend-team",
  "agent_config": {
    "primary_agent": {
      "name": "frontend-architect",
      "role": "Frontend Architect",
      "system_prompt": "Expert in React, TypeScript..."
    },
    "sub_agents": [
      {
        "name": "react-expert",
        "role": "React Specialist"
      }
    ]
  },
  "resources": {
    "memory_mb": 512,
    "cpu_cores": 1,
    "timeout_seconds": 300
  },
  "mcp_servers": ["filesystem", "web-search"],
  "environment_variables": {
    "NODE_ENV": "development"
  }
}
```

**Response**: 201 Created
```json
{
  "success": true,
  "data": {
    "sandbox_id": "sb_1234567890",
    "name": "frontend-team",
    "status": "provisioning",
    "connection_details": {
      "collaboration_bus_url": "ws://localhost:8001/ws/sandboxes/sb_1234567890",
      "api_endpoint": "http://localhost:8000/api/v1/sandboxes/sb_1234567890"
    },
    "created_at": "2025-01-10T15:30:00Z"
  }
}
```

#### GET /sandboxes/{sandbox_id}
Get sandbox details.

**Response**: 200 OK
```json
{
  "success": true,
  "data": {
    "sandbox_id": "sb_1234567890",
    "name": "frontend-team",
    "workspace_id": "ws_1234567890",
    "status": "running",
    "agent_config": { ... },
    "resources": { ... },
    "health": { ... },
    "metrics": {
      "cpu_usage_percent": 25.5,
      "memory_usage_mb": 256,
      "message_count": 150,
      "uptime_seconds": 3600
    },
    "created_at": "2025-01-10T10:00:00Z",
    "started_at": "2025-01-10T10:05:00Z"
  }
}
```

#### POST /sandboxes/{sandbox_id}/start
Start a stopped sandbox.

**Response**: 202 Accepted
```json
{
  "success": true,
  "data": {
    "sandbox_id": "sb_1234567890",
    "status": "starting",
    "estimated_ready_seconds": 10
  }
}
```

#### POST /sandboxes/{sandbox_id}/stop
Stop a running sandbox.

**Response**: 202 Accepted
```json
{
  "success": true,
  "data": {
    "sandbox_id": "sb_1234567890",
    "status": "stopping"
  }
}
```

#### POST /sandboxes/{sandbox_id}/restart
Restart a sandbox.

**Response**: 202 Accepted

#### GET /sandboxes/{sandbox_id}/logs
Get sandbox logs.

**Query Parameters**:
- `limit` (integer, default: 100, max: 1000)
- `since` (ISO 8601 timestamp, optional)
- `level` (string, enum: "debug", "info", "warn", "error", optional)

**Response**: 200 OK
```json
{
  "success": true,
  "data": {
    "sandbox_id": "sb_1234567890",
    "logs": [
      {
        "timestamp": "2025-01-10T15:30:00Z",
        "level": "info",
        "message": "Agent started successfully"
      },
      {
        "timestamp": "2025-01-10T15:30:05Z",
        "level": "info",
        "message": "Connected to collaboration bus"
      }
    ],
    "meta": {
      "total": 2,
      "since": "2025-01-10T15:00:00Z"
    }
  }
}
```

#### GET /sandboxes/{sandbox_id}/status
Get sandbox status and health.

**Response**: 200 OK
```json
{
  "success": true,
  "data": {
    "sandbox_id": "sb_1234567890",
    "status": "running",
    "health": {
      "status": "healthy",
      "last_heartbeat": "2025-01-10T15:30:00Z",
      "uptime_seconds": 3600
    },
    "resources": {
      "memory_mb": {
        "allocated": 512,
        "used": 256,
        "percentage": 50
      },
      "cpu_cores": {
        "allocated": 1,
        "used": 0.25
      }
    },
    "connections": {
      "collaboration_bus": "connected",
      "mcp_servers": {
        "filesystem": "connected",
        "web-search": "connected"
      }
    }
  }
}
```

#### DELETE /sandboxes/{sandbox_id}
Delete a sandbox.

**Response**: 204 No Content

---

### 4. Agent Communication

#### POST /sandboxes/{sandbox_id}/messages
Send a message from this sandbox to another.

**Request**:
```json
{
  "to_sandbox": "sb_0987654321",
  "to_agent": "backend-architect",
  "message_type": "request",
  "content": {
    "task": "Design user authentication API",
    "context": "Frontend needs OAuth2.0 integration"
  },
  "priority": 7,
  "requires_response": true,
  "timeout": 30
}
```

**Response**: 202 Accepted
```json
{
  "success": true,
  "data": {
    "message_id": "msg_1234567890",
    "status": "queued",
    "timestamp": "2025-01-10T15:30:00Z"
  }
}
```

#### POST /workspaces/{workspace_id}/broadcast
Broadcast a message to all sandboxes in workspace.

**Request**:
```json
{
  "from_sandbox": "sb_1234567890",
  "message_type": "notification",
  "content": {
    "event": "deployment_completed",
    "version": "v2.5.0"
  },
  "priority": 5
}
```

**Response**: 202 Accepted
```json
{
  "success": true,
  "data": {
    "broadcast_id": "bc_1234567890",
    "recipients": ["sb_1234567890", "sb_0987654321", "sb_5555555555"],
    "timestamp": "2025-01-10T15:30:00Z"
  }
}
```

#### GET /sandboxes/{sandbox_id}/messages
Get messages sent to/from this sandbox.

**Query Parameters**:
- `direction` (string, enum: "sent", "received", "both", default: "both")
- `limit` (integer, default: 50)
- `since` (ISO 8601 timestamp, optional)

**Response**: 200 OK
```json
{
  "success": true,
  "data": {
    "messages": [
      {
        "message_id": "msg_1234567890",
        "from_sandbox": "sb_1234567890",
        "from_agent": "frontend-architect",
        "to_sandbox": "sb_0987654321",
        "to_agent": "backend-architect",
        "message_type": "request",
        "content": { ... },
        "status": "delivered",
        "timestamp": "2025-01-10T15:30:00Z"
      }
    ],
    "meta": {
      "total": 50,
      "since": "2025-01-10T15:00:00Z"
    }
  }
}
```

#### GET /messages/{message_id}
Get message details.

**Response**: 200 OK
```json
{
  "success": true,
  "data": {
    "message_id": "msg_1234567890",
    "from_sandbox": "sb_1234567890",
    "to_sandbox": "sb_0987654321",
    "message_type": "request",
    "content": { ... },
    "status": "delivered",
    "response": {
      "message_id": "msg_0987654321",
      "content": { ... }
    },
    "timestamp": "2025-01-10T15:30:00Z",
    "delivered_at": "2025-01-10T15:30:01Z",
    "responded_at": "2025-01-10T15:30:05Z"
  }
}
```

#### POST /messages/{message_id}/retry
Retry a failed message delivery.

**Response**: 202 Accepted

---

### 5. Collaboration

#### POST /workspaces/{workspace_id}/collaboration/orchestrate
Orchestrate a multi-agent collaboration task.

**Request**:
```json
{
  "task": "Implement user authentication feature",
  "participants": ["frontend-team", "backend-team", "security-team"],
  "collaboration_mode": "orchestrated",
  "orchestrator": "project-manager",
  "timeout": 300,
  "deliverables": [
    "frontend_components",
    "backend_api",
    "security_review"
  ]
}
```

**Response**: 202 Accepted
```json
{
  "success": true,
  "data": {
    "collaboration_id": "col_1234567890",
    "status": "initializing",
    "participants": ["sb_1234567890", "sb_0987654321", "sb_5555555555"],
    "estimated_duration_seconds": 300
  }
}
```

#### GET /collaborations/{collaboration_id}
Get collaboration status and progress.

**Response**: 200 OK
```json
{
  "success": true,
  "data": {
    "collaboration_id": "col_1234567890",
    "status": "in_progress",
    "progress": {
      "percentage": 45,
      "current_step": "backend_api_design",
      "completed_steps": ["task_breakdown", "frontend_analysis"],
      "remaining_steps": ["backend_implementation", "integration", "testing"]
    },
    "participants": [
      {
        "sandbox_id": "sb_1234567890",
        "status": "active",
        "messages_exchanged": 15
      }
    ],
    "messages": [
      {
        "from": "sb_1234567890",
        "to": "sb_0987654321",
        "content": "..."
      }
    ],
    "started_at": "2025-01-10T15:00:00Z",
    "estimated_completion": "2025-01-10T15:30:00Z"
  }
}
```

#### GET /workspaces/{workspace_id}/agents/discover
Discover agents by capability.

**Query Parameters**:
- `capability` (string, optional)
- `role` (string, optional)
- `sandbox_id` (string, optional)

**Response**: 200 OK
```json
{
  "success": true,
  "data": {
    "agents": [
      {
        "sandbox_id": "sb_0987654321",
        "agent_name": "backend-architect",
        "role": "Backend Architect",
        "capabilities": ["api_design", "database_optimization"],
        "status": "available",
        "metrics": {
          "messages_processed": 250,
          "avg_response_time_ms": 150
        }
      }
    ]
  }
}
```

---

### 6. Configuration

#### GET /workspaces/{workspace_id}/config
Get workspace configuration.

**Response**: 200 OK
```json
{
  "success": true,
  "data": {
    "workspace_id": "ws_1234567890",
    "settings": {
      "max_sandboxes": 10,
      "default_llm_provider": "qwen"
    },
    "llm_providers": [
      {
        "name": "qwen",
        "models": ["qwen-plus", "qwen-max"],
        "default_model": "qwen-plus"
      }
    ],
    "mcp_servers": [
      {
        "name": "filesystem",
        "status": "enabled"
      }
    ],
    "collaboration_policy": {
      "mode": "allow_list",
      "rules": [ ... ]
    }
  }
}
```

#### PUT /workspaces/{workspace_id}/config
Update workspace configuration.

**Request**:
```json
{
  "settings": {
    "max_sandboxes": 20
  },
  "llm_providers": [
    {
      "name": "claude",
      "api_key": "${ANTHROPIC_API_KEY}",
      "models": ["claude-3-5-sonnet-20241022"],
      "default_model": "claude-3-5-sonnet-20241022"
    }
  ]
}
```

**Response**: 200 OK

#### GET /sandboxes/{sandbox_id}/config
Get sandbox configuration.

**Response**: 200 OK

#### PUT /sandboxes/{sandbox_id}/config
Update sandbox configuration.

**Request**:
```json
{
  "resources": {
    "memory_mb": 1024,
    "cpu_cores": 2
  },
  "environment_variables": {
    "NODE_ENV": "production"
  }
}
```

**Response**: 200 OK

---

### 7. Monitoring

#### GET /sandboxes/{sandbox_id}/metrics
Get sandbox metrics.

**Response**: 200 OK
```json
{
  "success": true,
  "data": {
    "sandbox_id": "sb_1234567890",
    "timestamp": "2025-01-10T15:30:00Z",
    "resources": {
      "cpu_usage_percent": 25.5,
      "memory_usage_mb": 256,
      "memory_usage_percent": 50.0,
      "disk_usage_mb": 512,
      "network_in_bytes": 1024000,
      "network_out_bytes": 2048000
    },
    "messaging": {
      "messages_sent": 150,
      "messages_received": 145,
      "messages_failed": 0,
      "avg_response_time_ms": 120
    },
    "health": {
      "status": "healthy",
      "uptime_seconds": 3600,
      "restart_count": 0
    }
  }
}
```

#### GET /workspaces/{workspace_id}/metrics/aggregate
Get aggregated metrics for all sandboxes.

**Query Parameters**:
- `since` (ISO 8601 timestamp)
- `granularity` (string, enum: "minute", "hour", "day")

**Response**: 200 OK
```json
{
  "success": true,
  "data": {
    "workspace_id": "ws_1234567890",
    "period": {
      "start": "2025-01-10T00:00:00Z",
      "end": "2025-01-10T15:30:00Z",
      "granularity": "hour"
    },
    "summary": {
      "total_sandboxes": 4,
      "active_sandboxes": 4,
      "total_messages": 1250,
      "avg_cpu_usage": 30.5,
      "avg_memory_usage": 65.2
    },
    "by_sandbox": [ ... ]
  }
}
```

---

### 8. System

#### GET /system/health
Health check endpoint.

**Response**: 200 OK
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "services": {
      "api": "healthy",
      "collaboration_bus": "healthy",
      "database": "healthy",
      "redis": "healthy"
    },
    "timestamp": "2025-01-10T15:30:00Z"
  }
}
```

#### GET /system/info
Get system information.

**Response**: 200 OK
```json
{
  "success": true,
  "data": {
    "version": "1.0.0",
    "edition": "community",
    "features": {
      "max_workspaces": 10,
      "max_sandboxes_per_workspace": 5,
      "cross_machine_deployment": false
    },
    "supported_llm_providers": ["qwen", "glm", "claude", "openai"],
    "supported_mcp_servers": ["filesystem", "web-search", "github"]
  }
}
```

---

### 9. WebSocket Endpoints

#### WS /ws/sandboxes/{sandbox_id}
WebSocket connection for real-time message streaming.

**Connection**: WebSocket
**Authentication**: Query parameter `token={jwt_token}`

**Message Format (Client → Server)**:
```json
{
  "action": "subscribe",
  "channels": ["messages", "events", "logs"]
}
```

**Message Format (Server → Client)**:
```json
{
  "channel": "messages",
  "event": "message_received",
  "data": {
    "message_id": "msg_1234567890",
    "from_sandbox": "sb_0987654321",
    "content": { ... }
  },
  "timestamp": "2025-01-10T15:30:00Z"
}
```

**Channels**:
- `messages` - Real-time messages
- `events` - Sandbox events (started, stopped, error)
- `logs` - Log stream
- `metrics` - Metrics updates

#### WS /ws/collaborations/{collaboration_id}
WebSocket connection for collaboration updates.

#### WS /ws/system
WebSocket connection for system-wide events (admin only).

---

## HTTP Status Codes

| Code | Usage |
|------|-------|
| 200 | OK - Request successful |
| 201 | Created - Resource created successfully |
| 202 | Accepted - Request accepted for processing |
| 204 | No Content - Request successful, no content returned |
| 400 | Bad Request - Invalid request parameters |
| 401 | Unauthorized - Authentication required or failed |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource not found |
| 409 | Conflict - Resource state conflict |
| 422 | Unprocessable Entity - Validation error |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Server error |
| 503 | Service Unavailable - Service temporarily unavailable |

---

## Error Codes

| Code | Description |
|------|-------------|
| `AUTHENTICATION_FAILED` | Invalid credentials |
| `AUTHORIZATION_FAILED` | Insufficient permissions |
| `RESOURCE_NOT_FOUND` | Resource does not exist |
| `RESOURCE_ALREADY_EXISTS` | Resource with same identifier exists |
| `VALIDATION_ERROR` | Request validation failed |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `SANDBOX_NOT_READY` | Sandbox is not ready |
| `MESSAGE_DELIVERY_FAILED` | Failed to deliver message |
| `COLLABORATION_FAILED` | Collaboration task failed |
| `CONFIGURATION_INVALID` | Invalid configuration |
| `RESOURCE_EXHAUSTED` | Resource limits exceeded |

---

## Rate Limiting

| Endpoint | Limit |
|----------|-------|
| Authentication | 10 requests/minute |
| Workspace operations | 100 requests/hour |
| Sandbox operations | 200 requests/hour |
| Message sending | 1000 requests/hour |
| WebSocket | 10 concurrent connections |

---

## Pagination

List endpoints use cursor-based pagination for performance.

**Request**:
```
GET /workspaces?page=2&per_page=20
```

**Response**:
```json
{
  "data": [ ... ],
  "meta": {
    "total": 100,
    "page": 2,
    "per_page": 20,
    "total_pages": 5,
    "has_next": true,
    "has_prev": true
  }
}
```

---

## SDK Design Implications

### Python SDK Structure
```python
from aintandem import AInTandemClient

client = AInTandemClient(api_key="...")

# Workspaces
workspace = await client.workspaces.create(name="My Workspace")
sandboxes = await client.workspaces.list_sandboxes(workspace.id)

# Sandboxes
sandbox = await client.sandboxes.create(workspace.id, config={...})
await sandbox.start()
status = await sandbox.get_status()

# Messages
await sandbox.send_message(to="other-sandbox", content={...})
messages = await sandbox.get_messages()

# Collaboration
collaboration = await client.collaborations.orchestrate(...)
```

### TypeScript SDK Structure
```typescript
import { AInTandemClient } from '@aintandem/sdk';

const client = new AInTandemClient({ apiKey: '...' });

// Workspaces
const workspace = await client.workspaces.create({ name: 'My Workspace' });
const sandboxes = await client.workspaces.listSandboxes(workspace.id);

// Sandboxes
const sandbox = await client.sandboxes.create(workspace.id, config);
await sandbox.start();
const status = await sandbox.getStatus();

// Messages
await sandbox.sendMessage('other-sandbox', { ... });
const messages = await sandbox.getMessages();

// Collaboration
const collaboration = await client.collaborations.orchestrate(...);
```

---

## Next Steps

1. ✅ Use cases and scenarios defined
2. ✅ RESTful API endpoints designed
3. ⏳ JSON schemas definition
4. ⏳ OpenAPI/Swagger specification

---

**Document Version**: 1.0
**Last Updated:** 2025-01-10
**Status:** API Design
