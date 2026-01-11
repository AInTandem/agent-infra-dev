# TypeScript SDK Quick Start

The Round Table TypeScript SDK provides a type-safe interface for interacting with the Round Table API.

## Installation

```bash
npm install @roundtable/sdk
```

Or install from source:

```bash
cd sdk/typescript
npm install
npm build
npm link
```

## Configuration

### Using API Key

```typescript
import { RoundTableClient } from '@roundtable/sdk';

const client = new RoundTableClient({
  apiKey: 'your-api-key',
  baseURL: 'http://localhost:8000/api/v1'
});
```

### Using Environment Variables

```bash
export ROUND_TABLE_API_KEY="your-api-key"
export ROUND_TABLE_BASE_URL="http://localhost:8000/api/v1"
```

```typescript
const client = new RoundTableClient({
  apiKey: process.env.ROUND_TABLE_API_KEY!,
  baseURL: process.env.ROUND_TABLE_BASE_URL
});
```

## Basic Usage

### Cleanup Pattern

Always close the client when done:

```typescript
const client = new RoundTableClient({ apiKey: 'your-api-key' });
try {
  // Your code here
} finally {
  await client.close();
}
```

## Workspaces

### Create a Workspace

```typescript
const workspace = await client.workspaces.create({
  name: 'My Project',
  description: 'A workspace for my agents'
});
console.log(`Created workspace: ${workspace.workspace_id}`);
```

### List Workspaces

```typescript
const workspaces = await client.workspaces.list({ limit: 50 });
for (const ws of workspaces.workspaces) {
  console.log(`${ws.name}: ${ws.workspace_id}`);
}
```

### Get Workspace Details

```typescript
const workspace = await client.workspaces.get('ws_abc123');
console.log(`Workspace: ${workspace.name}`);
console.log(`Status: ${workspace.status}`);
console.log(`Created: ${workspace.created_at}`);
```

### Update Workspace

```typescript
const updated = await client.workspaces.update('ws_abc123', {
  name: 'Updated Name',
  description: 'New description'
});
```

### Delete Workspace

```typescript
await client.workspaces.delete('ws_abc123');
```

## Sandboxes

### Create a Sandbox

```typescript
const sandbox = await client.sandboxes.create('ws_abc123', {
  name: 'Research Agent',
  description: 'Research specialist',
  agent_config: {
    primary_agent: 'researcher',
    model: 'gpt-4',
    temperature: 0.7,
    max_tokens: 2000
  }
});
console.log(`Created sandbox: ${sandbox.sandbox_id}`);
```

### List Sandboxes

```typescript
const sandboxes = await client.sandboxes.list('ws_abc123', { limit: 50 });
for (const sb of sandboxes.sandboxes) {
  console.log(`${sb.name}: ${sb.status}`);
}
```

### Start a Sandbox

```typescript
const started = await client.sandboxes.start('sb_xyz789');
console.log(`Status: ${started.status}`);
```

### Stop a Sandbox

```typescript
const stopped = await client.sandboxes.stop('sb_xyz789');
console.log(`Status: ${stopped.status}`);
```

### Get Sandbox Status

```typescript
const status = await client.sandboxes.status('sb_xyz789');
console.log(`Status: ${status.status}`);
console.log(`Uptime: ${status.uptime}`);
```

### Get Sandbox Metrics

```typescript
const metrics = await client.sandboxes.metrics('sb_xyz789');
console.log(`Messages sent: ${metrics.messages_sent}`);
console.log(`Messages received: ${metrics.messages_received}`);
```

### Delete Sandbox

```typescript
await client.sandboxes.delete('sb_xyz789');
```

## Messages

### Send a Message

```typescript
const message = await client.messages.send({
  from_sandbox_id: 'sb_xyz789',
  to_sandbox_id: 'sb_def456',
  content: {
    type: 'request',
    action: 'analyze',
    data: { key: 'value' }
  }
});
console.log(`Message sent: ${message.message_id}`);
```

### Get Messages

```typescript
const messages = await client.messages.list('sb_xyz789', { limit: 100 });
for (const msg of messages.messages) {
  console.log(`From: ${msg.from_sandbox_id}`);
  console.log(`Content: ${msg.content}`);
}
```

### Get Message Details

```typescript
const message = await client.messages.get('msg_abc123');
console.log(`Status: ${message.status}`);
console.log(`Content: ${message.content}`);
```

### Broadcast Message

```typescript
const broadcast = await client.messages.broadcast({
  workspace_id: 'ws_abc123',
  from_sandbox_id: 'sb_xyz789',
  content: {
    type: 'announcement',
    message: 'Hello everyone!'
  }
});
```

## Collaborations

### Orchestrate Collaboration

```typescript
const collaboration = await client.collaborations.orchestrate(
  'ws_abc123',
  {
    task: 'Analyze Q4 sales data',
    participants: ['sb_xyz789', 'sb_def456'],
    mode: 'orchestrated',
    config: {
      max_duration: 300,
      timeout: 30,
      max_rounds: 10
    }
  }
);
console.log(`Collaboration ID: ${collaboration.collaboration_id}`);
```

### Get Collaboration Status

```typescript
const status = await client.collaborations.getCollaboration('collab_abc123');
console.log(`Status: ${status.status}`);
console.log(`Progress: ${status.progress}`);
```

### Discover Agents

```typescript
const agents = await client.collaborations.discoverAgents('ws_abc123');
console.log(`Found ${agents.count} agents:`);
for (const agent of agents.agents) {
  console.log(`  - ${agent.name}: ${agent.agent_type}`);
}
```

## Error Handling

```typescript
import {
  RoundTableError,
  NotFoundError,
  ValidationError,
  AuthenticationError
} from '@roundtable/sdk';

try {
  const workspace = await client.workspaces.get('ws_nonexistent');
} catch (error) {
  if (error instanceof NotFoundError) {
    console.error('Resource not found:', error.message);
  } else if (error instanceof ValidationError) {
    console.error('Invalid data:', error.message);
  } else if (error instanceof AuthenticationError) {
    console.error('Authentication failed:', error.message);
  } else if (error instanceof RoundTableError) {
    console.error('API error:', error.message);
  } else {
    console.error('Unknown error:', error);
  }
}
```

## Complete Example

```typescript
import { RoundTableClient } from '@roundtable/sdk';

async function main() {
  const client = new RoundTableClient({
    apiKey: 'your-api-key',
    baseURL: 'http://localhost:8000/api/v1'
  });

  try {
    // Create workspace
    const workspace = await client.workspaces.create({
      name: 'Demo Project',
      description: 'Demonstrating the SDK'
    });

    // Create sandboxes
    const researcher = await client.sandboxes.create(
      workspace.workspace_id,
      {
        name: 'Researcher',
        agent_config: {
          primary_agent: 'researcher',
          model: 'gpt-4'
        }
      }
    );

    const developer = await client.sandboxes.create(
      workspace.workspace_id,
      {
        name: 'Developer',
        agent_config: {
          primary_agent: 'developer',
          model: 'gpt-4'
        }
      }
    );

    // Start collaboration
    const collaboration = await client.collaborations.orchestrate(
      workspace.workspace_id,
      {
        task: 'Build a REST API',
        participants: [researcher.sandbox_id, developer.sandbox_id],
        mode: 'orchestrated'
      }
    );

    console.log(`Collaboration started: ${collaboration.collaboration_id}`);

    // Check status
    const status = await client.collaborations.getCollaboration(
      collaboration.collaboration_id
    );
    console.log(`Status: ${status.status}`);

    // Cleanup
    await client.sandboxes.delete(researcher.sandbox_id);
    await client.sandboxes.delete(developer.sandbox_id);
    await client.workspaces.delete(workspace.workspace_id);
  } finally {
    await client.close();
  }
}

main().catch(console.error);
```

## Type Definitions

The SDK includes full TypeScript type definitions:

```typescript
import type {
  Workspace,
  Sandbox,
  AgentConfig,
  Collaboration,
  AgentMessage,
  SystemHealth,
  SystemInfo
} from '@roundtable/sdk';

// Use types in your code
function processWorkspace(workspace: Workspace): void {
  // TypeScript will provide autocomplete and type checking
  console.log(workspace.name);
}
```

## Best Practices

1. **Always close the client** when done to free resources
2. **Use type assertions** for better type safety
3. **Handle errors** with specific error types
4. **Use async/await** for cleaner async code
5. **Enable strict mode** in your TypeScript configuration

## Additional Resources

- [API Reference](../api/overview.md)
- [Examples](../examples/)
- [Python SDK](python-quickstart.md)
