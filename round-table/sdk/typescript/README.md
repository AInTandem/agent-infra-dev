# Round Table TypeScript SDK

A TypeScript SDK for interacting with the Round Table Collaboration Bus API.

## Installation

```bash
npm install @roundtable/sdk
```

## Quick Start

```typescript
import { RoundTableClient } from '@roundtable/sdk';

async function main() {
  // Initialize the client
  const client = new RoundTableClient({
    apiKey: 'your-api-key'
  });

  try {
    // Create a workspace
    const workspace = await client.workspaces.create({
      name: 'My Workspace',
      description: 'A workspace for my agents'
    });
    console.log(`Created workspace: ${workspace.workspace_id}`);

    // Create a sandbox (agent container)
    const sandbox = await client.sandboxes.create(workspace.workspace_id, {
      name: 'Research Agent',
      agent_config: {
        primary_agent: 'researcher',
        model: 'gpt-4'
      }
    });
    console.log(`Created sandbox: ${sandbox.sandbox_id}`);

    // Start the sandbox
    const started = await client.sandboxes.start(sandbox.sandbox_id);
    console.log(`Sandbox status: ${started.status}`);

  } finally {
    await client.close();
  }
}

main();
```

## Configuration

### Using API Key Directly

```typescript
import { RoundTableClient } from '@roundtable/sdk';

const client = new RoundTableClient({
  apiKey: 'your-api-key',
  baseURL: 'http://localhost:8000/api/v1'
});
```

### Using Configuration Object

```typescript
import { RoundTableClient, RoundTableConfig } from '@roundtable/sdk';

const config = new RoundTableConfig({
  apiKey: 'your-api-key',
  baseURL: 'https://api.roundtable.example.com/api/v1',
  timeout: 60000,
  maxRetries: 3
});
const client = new RoundTableClient(config);
```

### Using Environment Variables

```typescript
import { RoundTableConfig } from '@roundtable/sdk';

const config = RoundTableConfig.fromEnv();
const client = new RoundTableClient(config);
```

Required environment variables:
- `ROUNDTABLE_API_KEY`: Your API key

Optional environment variables:
- `ROUNDTABLE_BASE_URL`: Base URL (default: `http://localhost:8000/api/v1`)
- `ROUNDTABLE_TIMEOUT`: Request timeout in milliseconds (default: `30000`)
- `ROUNDTABLE_MAX_RETRIES`: Maximum number of retries (default: `3`)
- `ROUNDTABLE_VERIFY_SSL`: Verify SSL certificates (default: `true`)

## Workspaces

### List Workspaces

```typescript
const workspaces = await client.workspaces.list({ offset: 0, limit: 100 });
for (const workspace of workspaces.workspaces) {
  console.log(`${workspace.name}: ${workspace.workspace_id}`);
}
```

### Create Workspace

```typescript
const workspace = await client.workspaces.create({
  name: 'My Workspace',
  description: 'Optional description',
  settings: {
    max_sandboxes: 20,
    auto_cleanup: true,
    retention_days: 30,
    collaboration_policy: {}
  }
});
```

### Get Workspace

```typescript
const workspace = await client.workspaces.get('workspace_id');
```

### Update Workspace

```typescript
const workspace = await client.workspaces.update('workspace_id', {
  name: 'Updated Name',
  description: 'Updated description'
});
```

### Delete Workspace

```typescript
await client.workspaces.delete('workspace_id');
```

## Sandboxes

### List Sandboxes

```typescript
const sandboxes = await client.sandboxes.list('workspace_id');
for (const sandbox of sandboxes.sandboxes) {
  console.log(`${sandbox.name}: ${sandbox.status}`);
}
```

### Create Sandbox

```typescript
const sandbox = await client.sandboxes.create('workspace_id', {
  name: 'My Agent',
  agent_config: {
    primary_agent: 'researcher',
    model: 'gpt-4',
    max_tokens: 4000,
    temperature: 0.7,
    tools: ['search', 'calculator'],
    system_prompt: 'You are a helpful research assistant.',
    extra_config: {}
  }
});
```

### Start Sandbox

```typescript
const sandbox = await client.sandboxes.start('sandbox_id');
```

### Stop Sandbox

```typescript
const sandbox = await client.sandboxes.stop('sandbox_id');
```

### Get Sandbox Status

```typescript
const status = await client.sandboxes.status('sandbox_id');
console.log(`Status: ${status.status}`);
console.log(`Uptime: ${status.uptime_seconds}s`);
```

### Get Sandbox Logs

```typescript
const logs = await client.sandboxes.logs('sandbox_id');
console.log(logs.join('\n'));
```

### Get Sandbox Metrics

```typescript
const metrics = await client.sandboxes.metrics('sandbox_id');
console.log(metrics);
```

### Delete Sandbox

```typescript
await client.sandboxes.delete('sandbox_id');
```

## Messages

### Send Message

```typescript
const message = await client.messages.send('sender_id', {
  to_sandbox_id: 'recipient_id',
  content: {
    type: 'request',
    action: 'analyze',
    data: { text: 'Analyze this data' }
  },
  message_type: 'request'
});
```

### Get Messages

```typescript
const messages = await client.messages.getMessages('sandbox_id', {
  offset: 0,
  limit: 100
});
for (const message of messages.messages) {
  console.log(`From: ${message.from_sandbox_id}, Content: ${message.content}`);
}
```

### Get Message

```typescript
const message = await client.messages.get('message_id');
```

### Broadcast Message

```typescript
const result = await client.messages.broadcast('workspace_id', {
  content: {
    type: 'announcement',
    message: 'Important update!'
  },
  message_type: 'notification'
});
console.log(`Broadcast to ${result.broadcast_to} agents`);
```

## Collaborations

### Orchestrate Collaboration

```typescript
const collab = await client.collaborations.orchestrate('workspace_id', {
  task: 'Analyze research data and create summary',
  participants: ['sandbox_1', 'sandbox_2'],
  mode: 'orchestrated',
  config: {
    timeout: 600,
    max_iterations: 20,
    terminate_on_completion: true,
    save_history: true,
    extra_params: {}
  }
});
console.log(`Collaboration ID: ${collab.collaboration_id}`);
```

### Get Collaboration

```typescript
const collab = await client.collaborations.getCollaboration('collaboration_id');
console.log(`Status: ${collab.status}`);
if (collab.result) {
  console.log(`Result: ${collab.result}`);
}
```

### Discover Agents

```typescript
const agents = await client.collaborations.discoverAgents('workspace_id');
for (const agent of agents.agents) {
  console.log(`${agent.name}: ${agent.primary_agent} (${agent.status})`);
  console.log(`  Capabilities: ${agent.capabilities.join(', ')}`);
}
```

## Error Handling

The SDK provides specific exceptions for different error scenarios:

```typescript
import {
  RoundTableClient,
  AuthenticationError,
  NotFoundError,
  ValidationError,
  RateLimitError,
  RoundTableError
} from '@roundtable/sdk';

async function safeOperation() {
  try {
    const workspace = await client.workspaces.create({
      name: 'Test Workspace'
    });
  } catch (error) {
    if (error instanceof AuthenticationError) {
      console.error('Invalid API key');
    } else if (error instanceof NotFoundError) {
      console.error('Resource not found');
    } else if (error instanceof ValidationError) {
      console.error(`Invalid input: ${error.message}`);
    } else if (error instanceof RateLimitError) {
      console.error(`Rate limited, retry after ${error.retryAfter}s`);
    } else if (error instanceof RoundTableError) {
      console.error(`SDK error: ${error.message}`);
    } else {
      console.error(`Unexpected error: ${error}`);
    }
  }
}
```

## Type Safety

The SDK is fully typed with TypeScript. All types are exported for your convenience:

```typescript
import type {
  Workspace,
  Sandbox,
  AgentMessage,
  Collaboration,
  AgentConfig,
  // ... and many more
} from '@roundtable/sdk';

function processWorkspace(workspace: Workspace): string {
  return workspace.name;
}
```

## Testing

```bash
# Run tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage
```

## Development

### Setup

```bash
# Install dependencies
npm install

# Build the project
npm run build

# Run linter
npm run lint

# Format code
npm run format
```

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- GitHub: https://github.com/aintandem/round-table
- Documentation: https://github.com/aintandem/round-table/docs
