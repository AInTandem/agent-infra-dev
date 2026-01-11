# API Overview

The Round Table API provides a comprehensive RESTful interface for managing AI agent collaborations.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Most endpoints require authentication using a Bearer token:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:8000/api/v1/workspaces
```

## Response Format

All API responses follow this structure:

### Success Response

```json
{
  "success": true,
  "data": { ... },
  "message": "Operation successful"
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": { ... }
  }
}
```

## Core Concepts

### Workspaces

Workspaces are isolated environments where agent teams collaborate. Each workspace:
- Has a unique ID (prefixed with `ws_`)
- Contains multiple sandboxes
- Has configurable limits and settings
- Maintains aggregate metrics

### Sandboxes

Sandboxes are agent containers that:
- Represent individual AI agents
- Have configurable agent behavior
- Can be started, stopped, and monitored
- Send and receive messages

### Messages

Messages are the primary communication mechanism:
- Direct: Point-to-point between sandboxes
- Broadcast: Sent to all agents in a workspace
- Persistent: Stored in the audit log

### Collaborations

Collaborations coordinate multi-agent workflows:
- Orchestrated: Central coordinator manages the workflow
- Peer-to-Peer: Agents communicate directly
- Broadcast: Messages sent to all participants

## Common Operations

### Creating a Workspace

```bash
curl -X POST http://localhost:8000/api/v1/workspaces \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "name": "Project X",
    "description": "Research and development workspace"
  }'
```

Response:
```json
{
  "success": true,
  "data": {
    "workspace_id": "ws_abc123",
    "name": "Project X",
    "description": "Research and development workspace",
    "created_at": "2025-01-11T10:00:00Z",
    "status": "active"
  }
}
```

### Creating a Sandbox

```bash
curl -X POST http://localhost:8000/api/v1/workspaces/ws_abc123/sandboxes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "name": "Research Agent",
    "description": "Specialist in data research",
    "agent_config": {
      "primary_agent": "researcher",
      "model": "gpt-4",
      "temperature": 0.7,
      "max_tokens": 2000
    }
  }'
```

### Starting a Sandbox

```bash
curl -X POST http://localhost:8000/api/v1/sandboxes/sb_xyz789/start \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Sending Messages

```bash
curl -X POST http://localhost:8000/api/v1/sandboxes/sb_xyz789/messages \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "to_sandbox_id": "sb_def456",
    "content": {
      "type": "request",
      "action": "analyze_data",
      "parameters": {
        "dataset": "sales_2024"
      }
    }
  }'
```

### Orchestrating Collaboration

```bash
curl -X POST http://localhost:8000/api/v1/workspaces/ws_abc123/collaboration/orchestrate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "task": "Analyze Q4 sales data and create presentation",
    "mode": "orchestrated",
    "participants": ["sb_xyz789", "sb_def456"],
    "config": {
      "max_duration": 300,
      "timeout": 30,
      "max_rounds": 10
    }
  }'
```

## Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `AUTHENTICATION_ERROR` | 401 | Invalid or missing API key |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 422 | Invalid request data |
| `CONFLICT` | 409 | Resource already exists |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

## Rate Limiting

API requests are rate limited to:
- 100 requests per minute per IP
- 1000 requests per hour per API key

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1704960000
```

## Pagination

List endpoints support pagination:

```bash
curl "http://localhost:8000/api/v1/workspaces?offset=0&limit=50"
```

Response includes pagination metadata:
```json
{
  "success": true,
  "data": {
    "workspaces": [...],
    "count": 150,
    "offset": 0,
    "limit": 50
  }
}
```

## Versioning

The API is versioned using URL paths. The current version is `v1`.

## Webhooks

Webhooks are planned for future releases to enable real-time notifications.

## SDK Support

Official SDKs are available:
- [Python SDK](../sdk/python-quickstart.md)
- [TypeScript SDK](../sdk/typescript-quickstart.md)
