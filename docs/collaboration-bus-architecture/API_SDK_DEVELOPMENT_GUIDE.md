# AInTandem API - SDK Development Guide

## Document Purpose

This document explains how the API specifications and schemas defined in this directory are used to develop both Python and TypeScript SDKs for the AInTandem platform.

---

## Document Structure

The API documentation consists of the following files:

```
docs/
├── API_USE_CASES_AND_SCENARIOS.md     # Use cases and user scenarios
├── API_ENDPOINTS_SPECIFICATION.md      # RESTful API endpoints
├── API_JSON_SCHEMAS.md                 # JSON schema definitions
├── openapi.yaml                         # OpenAPI 3.1 specification
└── API_SDK_DEVELOPMENT_GUIDE.md        # This file
```

---

## SDK Development Approach

### 1. Code Generation from OpenAPI Specification

The OpenAPI specification (`openapi.yaml`) can be used with various code generation tools:

#### Python SDK
```bash
# Generate Python client using openapi-generator
openapi-generator-cli generate \
  -i docs/openapi.yaml \
  -g python \
  -o sdk/python/ \
  --package-name aintandem

# Or using datamodel-code-generator for Pydantic models
datamodel-codegen \
  --input docs/openapi.yaml \
  --output sdk/python/models/ \
  --output-model-type pydantic_v2.BaseModel
```

#### TypeScript SDK
```bash
# Generate TypeScript client using openapi-generator
openapi-generator-cli generate \
  -i docs/openapi.yaml \
  -g typescript-fetch \
  -o sdk/typescript/ \
  --package-name @aintandem/sdk

# Or using typescript-fetch for React Query integration
openapi-generator-cli generate \
  -i docs/openapi.yaml \
  -g typescript-axios \
  -o sdk/typescript-axios/
```

### 2. Manual SDK Development

For better developer experience, manual SDK development is recommended:

#### Python SDK Structure
```
sdk/python/
├── aintandem/
│   ├── __init__.py
│   ├── client.py              # Main client class
│   ├── auth.py                # Authentication
│   ├── workspaces/            # Workspace operations
│   │   ├── __init__.py
│   │   ├── client.py
│   │   └── models.py
│   ├── sandboxes/             # Sandbox operations
│   │   ├── __init__.py
│   │   ├── client.py
│   │   └── models.py
│   ├── messages/              # Messaging operations
│   │   ├── __init__.py
│   │   ├── client.py
│   │   └── models.py
│   ├── collaboration/         # Collaboration operations
│   │   ├── __init__.py
│   │   ├── client.py
│   │   └── models.py
│   └── models/                # Shared models
│       ├── __init__.py
│       ├── base.py
│       ├── workspace.py
│       ├── sandbox.py
│       ├── message.py
│       └── collaboration.py
├── tests/
├── examples/
├── setup.py
└── pyproject.toml
```

#### TypeScript SDK Structure
```
sdk/typescript/
├── src/
│   ├── index.ts
│   ├── client.ts              # Main client class
│   ├── auth.ts                # Authentication
│   ├── workspaces/            # Workspace operations
│   │   ├── index.ts
│   │   ├── client.ts
│   │   └── types.ts
│   ├── sandboxes/             # Sandbox operations
│   │   ├── index.ts
│   │   ├── client.ts
│   │   └── types.ts
│   ├── messages/              # Messaging operations
│   │   ├── index.ts
│   │   ├── client.ts
│   │   └── types.ts
│   ├── collaboration/         # Collaboration operations
│   │   ├── index.ts
│   │   ├── client.ts
│   │   └── types.ts
│   └── types/                 # Shared types
│       ├── index.ts
│       ├── workspace.ts
│       ├── sandbox.ts
│       ├── message.ts
│       └── collaboration.ts
├── tests/
├── examples/
├── package.json
└── tsconfig.json
```

---

## Python SDK Implementation

### Core Client Class

```python
# aintandem/client.py
from typing import Optional
import httpx
from pydantic import BaseModel

from aintandem.auth import AuthManager
from aintandem.workspaces import WorkspaceClient
from aintandem.sandboxes import SandboxClient

class AInTandemClient:
    """
    Main AInTandem SDK client.

    Example:
        ```python
        import asyncio
        from aintandem import AInTandemClient

        async def main():
            client = AInTandemClient(api_key="your_api_key")

            # Create workspace
            workspace = await client.workspaces.create(
                name="My Workspace",
                description="AI agents for my project"
            )

            # Create sandbox
            sandbox = await client.sandboxes.create(
                workspace.id,
                name="my-sandbox",
                agent_config={...}
            )

            # Send message
            await sandbox.messages.send(
                to="other-sandbox",
                content={"task": "Help me with X"}
            )
        ```
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.aintandem.com/api/v1",
        timeout: int = 30
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout

        self._http_client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout
        )

        # Initialize sub-clients
        self.auth = AuthManager(self._http_client)
        self.workspaces = WorkspaceClient(self._http_client)
        self.sandboxes = SandboxClient(self._http_client)
        # ... other sub-clients

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """Close the HTTP client."""
        await self._http_client.aclose()
```

### Workspace Client

```python
# aintandem/workspaces/client.py
from typing import List, Optional
from ..models.workspace import Workspace, WorkspaceCreateRequest
from ..models.base import SuccessResponse

class WorkspaceClient:
    """Client for workspace operations."""

    def __init__(self, http_client: httpx.AsyncClient):
        self._client = http_client

    async def create(
        self,
        name: str,
        description: Optional[str] = None,
        settings: Optional[dict] = None
    ) -> Workspace:
        """Create a new workspace."""
        request = WorkspaceCreateRequest(
            name=name,
            description=description,
            settings=settings
        )

        response = await self._client.post(
            "/workspaces",
            json=request.dict(exclude_none=True)
        )
        response.raise_for_status()

        data = SuccessResponse[Workspace](**response.json())
        return Workspace(**data.data)

    async def get(self, workspace_id: str) -> Workspace:
        """Get workspace details."""
        response = await self._client.get(f"/workspaces/{workspace_id}")
        response.raise_for_status()

        data = SuccessResponse[Workspace](**response.json())
        return Workspace(**data.data)

    async def list(
        self,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None
    ) -> List[Workspace]:
        """List workspaces."""
        params = {"page": page, "per_page": per_page}
        if search:
            params["search"] = search

        response = await self._client.get("/workspaces", params=params)
        response.raise_for_status()

        data = SuccessResponse[List[Workspace]](**response.json())
        return [Workspace(**item) for item in data.data]

    # ... other methods
```

### Pydantic Models

```python
# aintandem/models/workspace.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class WorkspaceSettings(BaseModel):
    """Workspace settings."""
    max_sandboxes: int = Field(default=10, ge=1, le=1000)
    default_llm_provider: str = Field(default="qwen")
    collaboration_policy: str = Field(default="allow_all")

class Workspace(BaseModel):
    """Workspace model."""
    workspace_id: str = Field(..., pattern=r"^ws_[a-z0-9]{10}$")
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    owner_id: str = Field(..., pattern=r"^usr_[a-z0-9]{10}$")
    settings: WorkspaceSettings
    sandbox_count: int = Field(default=0, ge=0)
    created_at: datetime
    updated_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

---

## TypeScript SDK Implementation

### Core Client Class

```typescript
// src/client.ts
import { AuthManager } from './auth';
import { WorkspaceClient } from './workspaces';
import { SandboxClient } from './sandboxes';
import { HttpClient } from './http-client';

export interface AInTandemClientConfig {
  apiKey: string;
  baseUrl?: string;
  timeout?: number;
}

export class AInTandemClient {
  /**
   * Main AInTandem SDK client.
   *
   * @example
   * ```typescript
   * import { AInTandemClient } from '@aintandem/sdk';
   *
   * const client = new AInTandemClient({
   *   apiKey: 'your_api_key'
   * });
   *
   * // Create workspace
   * const workspace = await client.workspaces.create({
   *   name: 'My Workspace',
   *   description: 'AI agents for my project'
   * });
   *
   * // Create sandbox
   * const sandbox = await client.sandboxes.create(workspace.id, {
   *   name: 'my-sandbox',
   *   agentConfig: {...}
   * });
   *
   * // Send message
   * await sandbox.messages.send('other-sandbox', {
   *   task: 'Help me with X'
   * });
   * ```
   */

  public readonly auth: AuthManager;
  public readonly workspaces: WorkspaceClient;
  public readonly sandboxes: SandboxClient;
  // ... other sub-clients

  private readonly httpClient: HttpClient;

  constructor(config: AInTandemClientConfig) {
    const {
      apiKey,
      baseUrl = 'https://api.aintandem.com/api/v1',
      timeout = 30000
    } = config;

    this.httpClient = new HttpClient({
      baseUrl,
      apiKey,
      timeout
    });

    // Initialize sub-clients
    this.auth = new AuthManager(this.httpClient);
    this.workspaces = new WorkspaceClient(this.httpClient);
    this.sandboxes = new SandboxClient(this.httpClient);
    // ... other sub-clients
  }

  async close(): Promise<void> {
    await this.httpClient.close();
  }
}
```

### Workspace Client

```typescript
// src/workspaces/client.ts
import { HttpClient } from '../http-client';
import {
  Workspace,
  WorkspaceCreateRequest,
  WorkspaceUpdateRequest,
  PaginatedResponse
} from './types';

export class WorkspaceClient {
  /** Client for workspace operations. */

  constructor(private readonly httpClient: HttpClient) {}

  /**
   * Create a new workspace.
   */
  async create(request: WorkspaceCreateRequest): Promise<Workspace> {
    const response = await this.httpClient.post<Workspace>(
      '/workspaces',
      request
    );
    return Workspace.fromJSON(response.data);
  }

  /**
   * Get workspace details.
   */
  async get(workspaceId: string): Promise<Workspace> {
    const response = await this.httpClient.get<Workspace>(
      `/workspaces/${workspaceId}`
    );
    return Workspace.fromJSON(response.data);
  }

  /**
   * List workspaces.
   */
  async list(options?: {
    page?: number;
    perPage?: number;
    search?: string;
  }): Promise<PaginatedResponse<Workspace>> {
    const response = await this.httpClient.get<{ data: Workspace[], meta: any }>(
      '/workspaces',
      options
    );
    return {
      data: response.data.map(item => Workspace.fromJSON(item)),
      meta: response.meta
    };
  }

  // ... other methods
}
```

### TypeScript Interfaces

```typescript
// src/workspaces/types.ts
export interface WorkspaceSettings {
  maxSandboxes?: number;
  defaultLlmProvider?: 'qwen' | 'glm' | 'claude' | 'openai';
  collaborationPolicy?: 'allow_all' | 'allow_list' | 'deny_list';
}

export interface Workspace {
  workspaceId: string;
  name: string;
  description?: string;
  ownerId: string;
  settings: WorkspaceSettings;
  sandboxCount: number;
  createdAt: string;
  updatedAt: string;

  // Static method for JSON parsing
  static fromJSON(data: any): Workspace {
    return {
      ...data,
      createdAt: new Date(data.createdAt),
      updatedAt: new Date(data.updatedAt)
    };
  }
}

export interface WorkspaceCreateRequest {
  name: string;
  description?: string;
  settings?: WorkspaceSettings;
}

export interface WorkspaceUpdateRequest {
  name?: string;
  description?: string;
  settings?: WorkspaceSettings;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: {
    total: number;
    page: number;
    perPage: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}
```

---

## SDK Features

### 1. Type Safety

Both SDKs provide full type safety:
- **Python**: Type hints + Pydantic validation
- **TypeScript**: Full TypeScript definitions

### 2. Error Handling

```python
# Python
try:
    workspace = await client.workspaces.get("ws_invalid")
except AInTandemNotFoundError as e:
    print(f"Workspace not found: {e.message}")
except AInTandemAPIError as e:
    print(f"API error: {e.message}")
```

```typescript
// TypeScript
try {
  const workspace = await client.workspaces.get('ws_invalid');
} catch (error) {
  if (error instanceof NotFoundError) {
    console.log(`Workspace not found: ${error.message}`);
  } else if (error instanceof APIError) {
    console.log(`API error: ${error.message}`);
  }
}
```

### 3. Retry Logic

```python
# Python - Automatic retry with exponential backoff
@retry(max_attempts=3, backoff_factor=2)
async def create_sandbox(...):
    ...
```

```typescript
// TypeScript - Automatic retry with exponential backoff
import { retry } from '@aintandem/sdk';

@retry({ maxAttempts: 3, backoffFactor: 2 })
async createSandbox(...) {
  ...
}
```

### 4. Logging

```python
# Python
import logging
from aintandem import AInTandemClient

logging.basicConfig(level=logging.DEBUG)
client = AInTandemClient(api_key="...", log_level=logging.DEBUG)
```

```typescript
// TypeScript
import { AInTandemClient } from '@aintandem/sdk';

const client = new AInTandemClient({
  apiKey: '...',
  logLevel: 'debug'
});
```

---

## Testing Strategy

### Python Tests

```python
# tests/test_workspaces.py
import pytest
from aintandem import AInTandemClient
from aintandem.models import Workspace

@pytest.mark.asyncio
async def test_create_workspace():
    client = AInTandemClient(api_key="test_key")
    workspace = await client.workspaces.create(
        name="Test Workspace"
    )

    assert isinstance(workspace, Workspace)
    assert workspace.name == "Test Workspace"
    assert workspace.workspace_id.startswith("ws_")
```

### TypeScript Tests

```typescript
// tests/workspaces.test.ts
import { AInTandemClient } from '@aintandem/sdk';

describe('WorkspaceClient', () => {
  let client: AInTandemClient;

  beforeEach(() => {
    client = new AInTandemClient({ apiKey: 'test_key' });
  });

  afterEach(async () => {
    await client.close();
  });

  it('should create a workspace', async () => {
    const workspace = await client.workspaces.create({
      name: 'Test Workspace'
    });

    expect(workspace.name).toBe('Test Workspace');
    expect(workspace.workspaceId).toMatch(/^ws_[a-z0-9]{10}$/);
  });
});
```

---

## Documentation Generation

### Python Documentation

Use the OpenAPI spec to generate documentation:

```bash
# Generate documentation with Sphinx
sphinx-apidoc -o docs sdk/python/aintandem

# Or use mkdocs with mkdocstrings
mkdocs serve
```

### TypeScript Documentation

Use TypeDoc to generate API documentation:

```bash
# Generate documentation
typedoc --out docs src/

# Or use API Extractor for better docs
api-extractor run --local
```

---

## Versioning Strategy

### Semantic Versioning

SDK versions follow semantic versioning and align with API versions:

```
API Version    SDK Version
------------    -----------
v1.0.0        1.0.0
v1.1.0        1.1.0
v1.2.0        1.2.0
v2.0.0        2.0.0 (breaking changes)
```

### Deprecation Policy

- Deprecated features are marked for 6 months
- Follow semver for breaking changes
- Maintain backward compatibility within major versions

---

## Release Process

### 1. Update OpenAPI Specification

Make changes to `openapi.yaml` following API changes.

### 2. Regenerate Types

```bash
# Python
datamodel-codegen --input docs/openapi.yaml --output sdk/python/models/

# TypeScript
openapi-generator-cli generate -i docs/openapi.yaml -g typescript-axios -o sdk/typescript/
```

### 3. Update SDK Code

Manually update SDK code for new features and bug fixes.

### 4. Update Tests

Add tests for new functionality.

### 5. Update Documentation

Update SDK documentation and examples.

### 6. Release

```bash
# Python
git tag sdk-python-v1.0.0
git push origin sdk-python-v1.0.0

# TypeScript
npm version 1.0.0
npm publish
```

---

## Best Practices

### 1. Consistent Naming

- Use camelCase for JSON
- Use camelCase for TypeScript
- Use snake_case for Python

### 2. Error Handling

- Always provide clear error messages
- Include error codes for programmatic handling
- Provide examples in documentation

### 3. Testing

- Write tests for all public APIs
- Use mocking for external dependencies
- Test error cases

### 4. Documentation

- Provide clear examples
- Document all parameters
- Include common use cases

### 5. Performance

- Use connection pooling
- Implement retry logic
- Cache frequently accessed data

---

## Next Steps

1. ✅ Use cases and scenarios defined
2. ✅ RESTful API endpoints designed
3. ✅ JSON schemas defined
4. ✅ OpenAPI specification created
5. ⏳ Generate initial SDK code
6. ⏳ Implement core SDK functionality
7. ⏳ Write comprehensive tests
8. ⏳ Create examples and tutorials

---

## References

- [OpenAPI Specification](https://swagger.io/specification/)
- [OpenAPI Generator](https://openapi-generator.tech)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)

---

**Document Version**: 1.0
**Last Updated:** 2025-01-10
**Status:** SDK Development Guide
