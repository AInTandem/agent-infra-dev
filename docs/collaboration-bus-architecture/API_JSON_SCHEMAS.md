# AInTandem API - JSON Schemas Definition

## Document Purpose

This document defines the JSON schemas for all AInTandem API entities. These schemas ensure type safety, enable validation, and serve as the foundation for Python and TypeScript SDK code generation.

## Schema Version

- **Schema Version**: 1.0.0
- **JSON Schema Draft**: 2020-12
- **Naming Convention**: camelCase for JSON, PascalCase for types

---

## Core Schemas

### 1. Common Schemas

#### SuccessResponse
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/success.json",
  "title": "SuccessResponse",
  "description": "Standard success response wrapper",
  "type": "object",
  "required": ["success", "data"],
  "properties": {
    "success": {
      "type": "boolean",
      "const": true
    },
    "data": {
      "description": "Response data (varies by endpoint)"
    },
    "meta": {
      "$ref": "https://api.aintandem.com/schemas/v1/metadata.json"
    }
  }
}
```

#### ErrorResponse
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/error.json",
  "title": "ErrorResponse",
  "description": "Standard error response wrapper",
  "type": "object",
  "required": ["success", "error"],
  "properties": {
    "success": {
      "type": "boolean",
      "const": false
    },
    "error": {
      "$ref": "https://api.aintandem.com/schemas/v1/error_detail.json"
    },
    "meta": {
      "$ref": "https://api.aintandem.com/schemas/v1/metadata.json"
    }
  }
}
```

#### Metadata
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/metadata.json",
  "title": "Metadata",
  "description": "Response metadata",
  "type": "object",
  "required": ["request_id", "timestamp"],
  "properties": {
    "request_id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique request identifier for tracing"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "Response timestamp in ISO 8601 format"
    },
    "version": {
      "type": "string",
      "description": "API version"
    }
  }
}
```

#### ErrorDetail
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/error_detail.json",
  "title": "ErrorDetail",
  "description": "Detailed error information",
  "type": "object",
  "required": ["code", "message"],
  "properties": {
    "code": {
      "type": "string",
      "description": "Machine-readable error code",
      "enum": [
        "AUTHENTICATION_FAILED",
        "AUTHORIZATION_FAILED",
        "RESOURCE_NOT_FOUND",
        "RESOURCE_ALREADY_EXISTS",
        "VALIDATION_ERROR",
        "RATE_LIMIT_EXCEEDED",
        "SANDBOX_NOT_READY",
        "MESSAGE_DELIVERY_FAILED",
        "COLLABORATION_FAILED",
        "CONFIGURATION_INVALID",
        "RESOURCE_EXHAUSTED"
      ]
    },
    "message": {
      "type": "string",
      "description": "Human-readable error message"
    },
    "details": {
      "type": "object",
      "description": "Additional error context"
    },
    "field": {
      "type": "string",
      "description": "Field that caused the error (for validation errors)"
    }
  }
}
```

#### PaginationMeta
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/pagination_meta.json",
  "title": "PaginationMeta",
  "description": "Pagination metadata",
  "type": "object",
  "required": ["total", "page", "per_page", "total_pages"],
  "properties": {
    "total": {
      "type": "integer",
      "minimum": 0
    },
    "page": {
      "type": "integer",
      "minimum": 1
    },
    "per_page": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100
    },
    "total_pages": {
      "type": "integer",
      "minimum": 0
    },
    "has_next": {
      "type": "boolean"
    },
    "has_prev": {
      "type": "boolean"
    }
  }
}
```

---

### 2. Authentication Schemas

#### RegisterRequest
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/register_request.json",
  "title": "RegisterRequest",
  "type": "object",
  "required": ["email", "password", "name"],
  "properties": {
    "email": {
      "type": "string",
      "format": "email"
    },
    "password": {
      "type": "string",
      "minLength": 8,
      "description": "Password must be at least 8 characters"
    },
    "name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100
    },
    "organization": {
      "type": "string",
      "maxLength": 100
    }
  }
}
```

#### LoginRequest
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/login_request.json",
  "title": "LoginRequest",
  "type": "object",
  "required": ["email", "password"],
  "properties": {
    "email": {
      "type": "string",
      "format": "email"
    },
    "password": {
      "type": "string"
    }
  }
}
```

#### AuthResponse
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/auth_response.json",
  "title": "AuthResponse",
  "type": "object",
  "required": ["access_token", "refresh_token", "token_type", "expires_in", "user"],
  "properties": {
    "access_token": {
      "type": "string",
      "description": "JWT access token"
    },
    "refresh_token": {
      "type": "string",
      "description": "JWT refresh token"
    },
    "token_type": {
      "type": "string",
      "const": "Bearer"
    },
    "expires_in": {
      "type": "integer",
      "description": "Token expiration in seconds"
    },
    "user": {
      "$ref": "https://api.aintandem.com/schemas/v1/user.json"
    }
  }
}
```

#### User
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/user.json",
  "title": "User",
  "type": "object",
  "required": ["user_id", "email", "name"],
  "properties": {
    "user_id": {
      "type": "string",
      "pattern": "^usr_[a-z0-9]{10}$"
    },
    "email": {
      "type": "string",
      "format": "email"
    },
    "name": {
      "type": "string"
    },
    "organization": {
      "type": "string"
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    }
  }
}
```

---

### 3. Workspace Schemas

#### Workspace
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/workspace.json",
  "title": "Workspace",
  "type": "object",
  "required": ["workspace_id", "name", "owner_id", "settings", "created_at"],
  "properties": {
    "workspace_id": {
      "type": "string",
      "pattern": "^ws_[a-z0-9]{10}$"
    },
    "name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100
    },
    "description": {
      "type": "string",
      "maxLength": 500
    },
    "owner_id": {
      "type": "string",
      "pattern": "^usr_[a-z0-9]{10}$"
    },
    "settings": {
      "$ref": "https://api.aintandem.com/schemas/v1/workspace_settings.json"
    },
    "sandbox_count": {
      "type": "integer",
      "minimum": 0
    },
    "sandboxes": {
      "type": "array",
      "items": {
        "$ref": "https://api.aintandem.com/schemas/v1/sandbox_summary.json"
      }
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "updated_at": {
      "type": "string",
      "format": "date-time"
    }
  }
}
```

#### WorkspaceCreateRequest
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/workspace_create_request.json",
  "title": "WorkspaceCreateRequest",
  "type": "object",
  "required": ["name"],
  "properties": {
    "name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100
    },
    "description": {
      "type": "string",
      "maxLength": 500
    },
    "settings": {
      "$ref": "https://api.aintandem.com/schemas/v1/workspace_settings.json"
    }
  }
}
```

#### WorkspaceUpdateRequest
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/workspace_update_request.json",
  "title": "WorkspaceUpdateRequest",
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100
    },
    "description": {
      "type": "string",
      "maxLength": 500
    },
    "settings": {
      "$ref": "https://api.aintandem.com/schemas/v1/workspace_settings.json"
    }
  }
}
```

#### WorkspaceSettings
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/workspace_settings.json",
  "title": "WorkspaceSettings",
  "type": "object",
  "properties": {
    "max_sandboxes": {
      "type": "integer",
      "minimum": 1,
      "maximum": 1000,
      "default": 10
    },
    "default_llm_provider": {
      "type": "string",
      "enum": ["qwen", "glm", "claude", "openai"],
      "default": "qwen"
    },
    "collaboration_policy": {
      "type": "string",
      "enum": ["allow_all", "allow_list", "deny_list"],
      "default": "allow_all"
    },
    "resource_defaults": {
      "type": "object",
      "properties": {
        "memory_mb": {
          "type": "integer",
          "default": 512
        },
        "cpu_cores": {
          "type": "number",
          "default": 1
        },
        "timeout_seconds": {
          "type": "integer",
          "default": 300
        }
      }
    }
  }
}
```

---

### 4. Sandbox Schemas

#### Sandbox
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/sandbox.json",
  "title": "Sandbox",
  "type": "object",
  "required": ["sandbox_id", "name", "workspace_id", "status", "agent_config", "resources", "created_at"],
  "properties": {
    "sandbox_id": {
      "type": "string",
      "pattern": "^sb_[a-z0-9]{10}$"
    },
    "name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100
    },
    "workspace_id": {
      "type": "string",
      "pattern": "^ws_[a-z0-9]{10}$"
    },
    "status": {
      "type": "string",
      "enum": ["provisioning", "running", "stopped", "error", "stopping", "starting"]
    },
    "agent_config": {
      "$ref": "https://api.aintandem.com/schemas/v1/agent_config.json"
    },
    "resources": {
      "$ref": "https://api.aintandem.com/schemas/v1/resource_limits.json"
    },
    "health": {
      "$ref": "https://api.aintandem.com/schemas/v1/health_status.json"
    },
    "connection_details": {
      "$ref": "https://api.aintandem.com/schemas/v1/connection_details.json"
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "started_at": {
      "type": "string",
      "format": "date-time"
    }
  }
}
```

#### SandboxSummary
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/sandbox_summary.json",
  "title": "SandboxSummary",
  "type": "object",
  "required": ["sandbox_id", "name", "status"],
  "properties": {
    "sandbox_id": {
      "type": "string"
    },
    "name": {
      "type": "string"
    },
    "status": {
      "type": "string"
    }
  }
}
```

#### SandboxCreateRequest
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/sandbox_create_request.json",
  "title": "SandboxCreateRequest",
  "type": "object",
  "required": ["name", "agent_config"],
  "properties": {
    "name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100
    },
    "agent_config": {
      "$ref": "https://api.aintandem.com/schemas/v1/agent_config.json"
    },
    "resources": {
      "$ref": "https://api.aintandem.com/schemas/v1/resource_limits.json"
    },
    "mcp_servers": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "environment_variables": {
      "type": "object",
      "additionalProperties": {
        "type": "string"
      }
    }
  }
}
```

#### AgentConfig
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/agent_config.json",
  "title": "AgentConfig",
  "type": "object",
  "required": ["primary_agent"],
  "properties": {
    "primary_agent": {
      "$ref": "https://api.aintandem.com/schemas/v1/agent_definition.json"
    },
    "sub_agents": {
      "type": "array",
      "items": {
        "$ref": "https://api.aintandem.com/schemas/v1/agent_definition.json"
      }
    },
    "llm_provider": {
      "type": "string",
      "enum": ["qwen", "glm", "claude", "openai"]
    },
    "llm_model": {
      "type": "string"
    },
    "llm_parameters": {
      "type": "object",
      "properties": {
        "temperature": {
          "type": "number",
          "minimum": 0,
          "maximum": 2
        },
        "max_tokens": {
          "type": "integer",
          "minimum": 1
        },
        "top_p": {
          "type": "number",
          "minimum": 0,
          "maximum": 1
        }
      }
    }
  }
}
```

#### AgentDefinition
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/agent_definition.json",
  "title": "AgentDefinition",
  "type": "object",
  "required": ["name", "role"],
  "properties": {
    "name": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100
    },
    "role": {
      "type": "string",
      "minLength": 1,
      "maxLength": 100
    },
    "description": {
      "type": "string",
      "maxLength": 500
    },
    "system_prompt": {
      "type": "string",
      "maxLength": 10000
    },
    "capabilities": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  }
}
```

#### ResourceLimits
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/resource_limits.json",
  "title": "ResourceLimits",
  "type": "object",
  "properties": {
    "memory_mb": {
      "type": "integer",
      "minimum": 128,
      "maximum": 16384,
      "default": 512
    },
    "cpu_cores": {
      "type": "number",
      "minimum": 0.1,
      "maximum": 16,
      "default": 1
    },
    "timeout_seconds": {
      "type": "integer",
      "minimum": 30,
      "maximum": 3600,
      "default": 300
    },
    "max_processes": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100,
      "default": 10
    }
  }
}
```

#### HealthStatus
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/health_status.json",
  "title": "HealthStatus",
  "type": "object",
  "required": ["status", "last_heartbeat"],
  "properties": {
    "status": {
      "type": "string",
      "enum": ["healthy", "unhealthy", "unknown"]
    },
    "last_heartbeat": {
      "type": "string",
      "format": "date-time"
    },
    "uptime_seconds": {
      "type": "integer",
      "minimum": 0
    },
    "restart_count": {
      "type": "integer",
      "minimum": 0
    }
  }
}
```

#### ConnectionDetails
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/connection_details.json",
  "title": "ConnectionDetails",
  "type": "object",
  "properties": {
    "collaboration_bus_url": {
      "type": "string",
      "format": "uri"
    },
    "api_endpoint": {
      "type": "string",
      "format": "uri"
    },
    "websocket_url": {
      "type": "string",
      "format": "uri"
    }
  }
}
```

---

### 5. Message Schemas

#### AgentMessage
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/agent_message.json",
  "title": "AgentMessage",
  "type": "object",
  "required": ["message_id", "from_sandbox", "message_type", "content", "timestamp"],
  "properties": {
    "message_id": {
      "type": "string",
      "pattern": "^msg_[a-z0-9]{10}$"
    },
    "correlation_id": {
      "type": "string",
      "description": "For request-response tracking"
    },
    "from_sandbox": {
      "type": "string",
      "pattern": "^sb_[a-z0-9]{10}$"
    },
    "to_sandbox": {
      "type": "string",
      "pattern": "^sb_[a-z0-9]{10}$"
    },
    "from_agent": {
      "type": "string"
    },
    "to_agent": {
      "type": "string"
    },
    "message_type": {
      "type": "string",
      "enum": ["request", "response", "notification", "command"]
    },
    "content": {
      "type": "object",
      "description": "Message content (flexible structure)"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    },
    "priority": {
      "type": "integer",
      "minimum": 0,
      "maximum": 9,
      "default": 5
    },
    "requires_response": {
      "type": "boolean",
      "default": false
    },
    "timeout": {
      "type": "integer",
      "minimum": 1,
      "maximum": 300,
      "description": "Response timeout in seconds"
    },
    "ttl": {
      "type": "integer",
      "minimum": 1,
      "description": "Message time-to-live in seconds"
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    }
  }
}
```

#### SendMessageRequest
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/send_message_request.json",
  "title": "SendMessageRequest",
  "type": "object",
  "required": ["to_sandbox", "message_type", "content"],
  "properties": {
    "to_sandbox": {
      "type": "string"
    },
    "to_agent": {
      "type": "string"
    },
    "message_type": {
      "type": "string",
      "enum": ["request", "response", "notification", "command"]
    },
    "content": {
      "type": "object"
    },
    "priority": {
      "type": "integer",
      "minimum": 0,
      "maximum": 9
    },
    "requires_response": {
      "type": "boolean"
    },
    "timeout": {
      "type": "integer",
      "minimum": 1,
      "maximum": 300
    }
  }
}
```

#### BroadcastMessageRequest
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/broadcast_request.json",
  "title": "BroadcastMessageRequest",
  "type": "object",
  "required": ["from_sandbox", "message_type", "content"],
  "properties": {
    "from_sandbox": {
      "type": "string"
    },
    "message_type": {
      "type": "string",
      "enum": ["notification", "command"]
    },
    "content": {
      "type": "object"
    },
    "priority": {
      "type": "integer",
      "minimum": 0,
      "maximum": 9
    },
    "exclude_self": {
      "type": "boolean",
      "default": true
    }
  }
}
```

#### MessageStatus
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/message_status.json",
  "title": "MessageStatus",
  "type": "string",
  "enum": ["queued", "sent", "delivered", "failed", "timeout"]
}
```

---

### 6. Collaboration Schemas

#### Collaboration
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/collaboration.json",
  "title": "Collaboration",
  "type": "object",
  "required": ["collaboration_id", "workspace_id", "status", "created_at"],
  "properties": {
    "collaboration_id": {
      "type": "string",
      "pattern": "^col_[a-z0-9]{10}$"
    },
    "workspace_id": {
      "type": "string"
    },
    "task": {
      "type": "string"
    },
    "status": {
      "type": "string",
      "enum": ["initializing", "in_progress", "completed", "failed", "cancelled"]
    },
    "collaboration_mode": {
      "type": "string",
      "enum": ["orchestrated", "peer_to_peer", "swarm"]
    },
    "orchestrator": {
      "type": "string"
    },
    "participants": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "progress": {
      "$ref": "https://api.aintandem.com/schemas/v1/collaboration_progress.json"
    },
    "messages": {
      "type": "array",
      "items": {
        "$ref": "https://api.aintandem.com/schemas/v1/agent_message.json"
      }
    },
    "deliverables": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "result": {
      "type": "object"
    },
    "error": {
      "type": "string"
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "started_at": {
      "type": "string",
      "format": "date-time"
    },
    "completed_at": {
      "type": "string",
      "format": "date-time"
    },
    "estimated_completion": {
      "type": "string",
      "format": "date-time"
    }
  }
}
```

#### OrchestrateCollaborationRequest
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/orchestrate_collaboration_request.json",
  "title": "OrchestrateCollaborationRequest",
  "type": "object",
  "required": ["task", "participants", "collaboration_mode"],
  "properties": {
    "task": {
      "type": "string",
      "minLength": 1
    },
    "participants": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "minItems": 2
    },
    "collaboration_mode": {
      "type": "string",
      "enum": ["orchestrated", "peer_to_peer", "swarm"]
    },
    "orchestrator": {
      "type": "string"
    },
    "timeout": {
      "type": "integer",
      "minimum": 30,
      "maximum": 3600
    },
    "deliverables": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  }
}
```

#### CollaborationProgress
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/collaboration_progress.json",
  "title": "CollaborationProgress",
  "type": "object",
  "properties": {
    "percentage": {
      "type": "number",
      "minimum": 0,
      "maximum": 100
    },
    "current_step": {
      "type": "string"
    },
    "completed_steps": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "remaining_steps": {
      "type": "array",
      "items": {
        "type": "string"
      }
    }
  }
}
```

---

### 7. Metrics Schemas

#### SandboxMetrics
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/sandbox_metrics.json",
  "title": "SandboxMetrics",
  "type": "object",
  "required": ["sandbox_id", "timestamp"],
  "properties": {
    "sandbox_id": {
      "type": "string"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    },
    "resources": {
      "$ref": "https://api.aintandem.com/schemas/v1/resource_metrics.json"
    },
    "messaging": {
      "$ref": "https://api.aintandem.com/schemas/v1/messaging_metrics.json"
    },
    "health": {
      "$ref": "https://api.aintandem.com/schemas/v1/health_metrics.json"
    }
  }
}
```

#### ResourceMetrics
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/resource_metrics.json",
  "title": "ResourceMetrics",
  "type": "object",
  "properties": {
    "cpu_usage_percent": {
      "type": "number",
      "minimum": 0,
      "maximum": 100
    },
    "memory_usage_mb": {
      "type": "integer",
      "minimum": 0
    },
    "memory_usage_percent": {
      "type": "number",
      "minimum": 0,
      "maximum": 100
    },
    "disk_usage_mb": {
      "type": "integer",
      "minimum": 0
    },
    "network_in_bytes": {
      "type": "integer",
      "minimum": 0
    },
    "network_out_bytes": {
      "type": "integer",
      "minimum": 0
    }
  }
}
```

#### MessagingMetrics
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/messaging_metrics.json",
  "title": "MessagingMetrics",
  "type": "object",
  "properties": {
    "messages_sent": {
      "type": "integer",
      "minimum": 0
    },
    "messages_received": {
      "type": "integer",
      "minimum": 0
    },
    "messages_failed": {
      "type": "integer",
      "minimum": 0
    },
    "avg_response_time_ms": {
      "type": "number",
      "minimum": 0
    }
  }
}
```

#### HealthMetrics
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/health_metrics.json",
  "title": "HealthMetrics",
  "type": "object",
  "properties": {
    "status": {
      "type": "string",
      "enum": ["healthy", "unhealthy", "unknown"]
    },
    "uptime_seconds": {
      "type": "integer",
      "minimum": 0
    },
    "restart_count": {
      "type": "integer",
      "minimum": 0
    }
  }
}
```

---

### 8. Configuration Schemas

#### LLMProviderConfig
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/llm_provider_config.json",
  "title": "LLMProviderConfig",
  "type": "object",
  "required": ["name", "api_key"],
  "properties": {
    "name": {
      "type": "string",
      "enum": ["qwen", "glm", "claude", "openai"]
    },
    "api_key": {
      "type": "string"
    },
    "base_url": {
      "type": "string",
      "format": "uri"
    },
    "models": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "default_model": {
      "type": "string"
    },
    "parameters": {
      "type": "object",
      "properties": {
        "temperature": {
          "type": "number",
          "minimum": 0,
          "maximum": 2
        },
        "max_tokens": {
          "type": "integer",
          "minimum": 1
        },
        "top_p": {
          "type": "number",
          "minimum": 0,
          "maximum": 1
        }
      }
    }
  }
}
```

#### MCPServerConfig
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/mcp_server_config.json",
  "title": "MCPServerConfig",
  "type": "object",
  "required": ["name", "transport"],
  "properties": {
    "name": {
      "type": "string"
    },
    "description": {
      "type": "string"
    },
    "transport": {
      "type": "string",
      "enum": ["stdio", "sse"]
    },
    "command": {
      "type": "string"
    },
    "args": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "url": {
      "type": "string",
      "format": "uri"
    },
    "env": {
      "type": "object",
      "additionalProperties": {
        "type": "string"
      }
    },
    "enabled": {
      "type": "boolean",
      "default": true
    }
  }
}
```

#### CollaborationPolicy
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/collaboration_policy.json",
  "title": "CollaborationPolicy",
  "type": "object",
  "required": ["mode"],
  "properties": {
    "mode": {
      "type": "string",
      "enum": ["allow_all", "allow_list", "deny_list"]
    },
    "rules": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["from", "to"],
        "properties": {
          "from": {
            "type": "string"
          },
          "to": {
            "oneOf": [
              { "type": "string" },
              { "type": "array", "items": { "type": "string" } }
            ]
          },
          "message_types": {
            "type": "array",
            "items": {
              "type": "string",
              "enum": ["request", "response", "notification", "command"]
            }
          },
          "approval_required": {
            "type": "boolean"
          }
        }
      }
    }
  }
}
```

---

### 9. WebSocket Schemas

#### WebSocketMessage
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/websocket_message.json",
  "title": "WebSocketMessage",
  "type": "object",
  "required": ["channel", "event", "data", "timestamp"],
  "properties": {
    "channel": {
      "type": "string",
      "enum": ["messages", "events", "logs", "metrics"]
    },
    "event": {
      "type": "string"
    },
    "data": {
      "type": "object"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    }
  }
}
```

#### WebSocketSubscribeRequest
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/websocket_subscribe_request.json",
  "title": "WebSocketSubscribeRequest",
  "type": "object",
  "required": ["action"],
  "properties": {
    "action": {
      "type": "string",
      "const": "subscribe"
    },
    "channels": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": ["messages", "events", "logs", "metrics"]
      }
    }
  }
}
```

---

### 10. Log Schemas

#### LogEntry
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/log_entry.json",
  "title": "LogEntry",
  "type": "object",
  "required": ["timestamp", "level", "message"],
  "properties": {
    "timestamp": {
      "type": "string",
      "format": "date-time"
    },
    "level": {
      "type": "string",
      "enum": ["debug", "info", "warn", "error"]
    },
    "message": {
      "type": "string"
    },
    "context": {
      "type": "object"
    }
  }
}
```

#### LogsResponse
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://api.aintandem.com/schemas/v1/logs_response.json",
  "title": "LogsResponse",
  "type": "object",
  "required": ["sandbox_id", "logs"],
  "properties": {
    "sandbox_id": {
      "type": "string"
    },
    "logs": {
      "type": "array",
      "items": {
        "$ref": "https://api.aintandem.com/schemas/v1/log_entry.json"
      }
    },
    "meta": {
      "type": "object",
      "properties": {
        "total": {
          "type": "integer"
        },
        "since": {
          "type": "string",
          "format": "date-time"
        }
      }
    }
  }
}
```

---

## ID Patterns

All resource IDs follow these patterns:

| Resource | Pattern | Example |
|----------|---------|---------|
| User | `usr_[a-z0-9]{10}` | `usr_abc123def4` |
| Workspace | `ws_[a-z0-9]{10}` | `ws_xyz789ghi1` |
| Sandbox | `sb_[a-z0-9]{10}` | `sb_lmn456opq2` |
| Message | `msg_[a-z0-9]{10}` | `msg_rst789uvw3` |
| Collaboration | `col_[a-z0-9]{10}` | `col_bcd234efg5` |
| Broadcast | `bc_[a-z0-9]{10}` | `bc_fgh345ijk6` |

---

## Enum Values

### SandboxStatus
- `provisioning`
- `starting`
- `running`
- `stopping`
- `stopped`
- `error`

### MessageType
- `request` - Request assistance or resources
- `response` - Response to a request
- `notification` - Broadcast notification
- `command` - Command with authorization

### CollaborationMode
- `orchestrated` - Coordinated by orchestrator agent
- `peer_to_peer` - Direct agent-to-agent communication
- `swarm` - Consensus-based collaboration

### CollaborationStatus
- `initializing`
- `in_progress`
- `completed`
- `failed`
- `cancelled`

---

## Type Generation

### Python Type Hints
```python
from typing import Literal, Optional
from pydantic import BaseModel
from datetime import datetime

class User(BaseModel):
    user_id: str
    email: str
    name: str
    organization: Optional[str] = None
    created_at: datetime

class SandboxStatus(str):
    PROVISIONING = "provisioning"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
```

### TypeScript Interfaces
```typescript
export interface User {
  user_id: string;
  email: string;
  name: string;
  organization?: string;
  created_at: string;
}

export type SandboxStatus =
  | "provisioning"
  | "starting"
  | "running"
  | "stopping"
  | "stopped"
  | "error";
```

---

## Validation Examples

### Valid Workspace Creation
```json
{
  "name": "E-commerce Development",
  "description": "AI agents for e-commerce",
  "settings": {
    "max_sandboxes": 10,
    "default_llm_provider": "qwen"
  }
}
```

### Valid Message
```json
{
  "to_sandbox": "sb_abc123def4",
  "message_type": "request",
  "content": {
    "task": "Design API",
    "context": "For user authentication"
  },
  "priority": 7,
  "requires_response": true,
  "timeout": 30
}
```

### Invalid Examples
```json
// Missing required field
{
  "description": "My workspace"
}

// Invalid enum value
{
  "status": "active"  // Should be one of the defined SandboxStatus values
}

// Violates pattern
{
  "sandbox_id": "invalid-id"  // Should match sb_[a-z0-9]{10}
}
```

---

## OpenAPI Compatibility

All schemas are designed to be compatible with OpenAPI 3.1 specification and can be directly used in:
- OpenAPI/Swagger documentation
- API validation middleware
- SDK code generation
- Type-safe client libraries

---

## Next Steps

1. ✅ Use cases and scenarios defined
2. ✅ RESTful API endpoints designed
3. ✅ JSON schemas defined
4. ⏳ OpenAPI/Swagger specification generation

---

**Document Version**: 1.0.0
**Last Updated:** 2025-01-10
**Status:** Schema Definition
