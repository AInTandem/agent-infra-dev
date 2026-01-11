#!/usr/bin/env node
/**
 * Round Table - TypeScript Application Example
 *
 * This example demonstrates how to build a TypeScript application
 * using the Round Table TypeScript SDK.
 */

import { RoundTableClient } from '@roundtable/sdk';

interface AppConfig {
  apiKey: string;
  baseURL: string;
}

async function main() {
  // Configuration
  const config: AppConfig = {
    apiKey: process.env.ROUND_TABLE_API_KEY || 'demo-api-key',
    baseURL: process.env.ROUND_TABLE_BASE_URL || 'http://localhost:8000/api/v1'
  };

  const client = new RoundTableClient(config);

  try {
    console.log('='.repeat(60));
    console.log('Round Table - TypeScript Application Example');
    console.log('='.repeat(60));

    // 1. Create workspace
    console.log('\n1. Creating workspace...');
    const workspace = await client.workspaces.create({
      name: 'TypeScript Demo',
      description: 'Demonstrating TypeScript SDK'
    });
    console.log(`   ✓ Created workspace: ${workspace.workspace_id}`);

    // 2. Create sandboxes
    console.log('\n2. Creating sandboxes...');

    const researcher = await client.sandboxes.create(
      workspace.workspace_id,
      {
        name: 'Researcher',
        description: 'Research specialist',
        agent_config: {
          primary_agent: 'researcher',
          model: 'gpt-4',
          temperature: 0.7
        }
      }
    );
    console.log(`   ✓ Created researcher: ${researcher.sandbox_id}`);

    const developer = await client.sandboxes.create(
      workspace.workspace_id,
      {
        name: 'Developer',
        description: 'Development specialist',
        agent_config: {
          primary_agent: 'developer',
          model: 'gpt-4',
          temperature: 0.5
        }
      }
    );
    console.log(`   ✓ Created developer: ${developer.sandbox_id}`);

    // 3. Start sandboxes
    console.log('\n3. Starting sandboxes...');
    await client.sandboxes.start(researcher.sandbox_id);
    await client.sandboxes.start(developer.sandbox_id);
    console.log('   ✓ All sandboxes started');

    // 4. Discover agents
    console.log('\n4. Discovering agents...');
    const agents = await client.collaborations.discoverAgents(
      workspace.workspace_id
    );
    console.log(`   ✓ Found ${agents.count} agents`);

    // 5. Orchestrate collaboration
    console.log('\n5. Orchestrating collaboration...');
    const collaboration = await client.collaborations.orchestrate(
      workspace.workspace_id,
      {
        task: 'Build a TypeScript REST API',
        mode: 'orchestrated',
        participants: [researcher.sandbox_id, developer.sandbox_id],
        config: {
          max_duration: 300,
          timeout: 30
        }
      }
    );
    console.log(`   ✓ Collaboration ID: ${collaboration.collaboration_id}`);

    // 6. Send message
    console.log('\n6. Sending message...');
    const message = await client.messages.send({
      from_sandbox_id: researcher.sandbox_id,
      to_sandbox_id: developer.sandbox_id,
      content: {
        type: 'task_update',
        message: 'Starting implementation'
      }
    });
    console.log(`   ✓ Message sent: ${message.message_id}`);

    // 7. Get messages
    console.log('\n7. Getting messages...');
    const messages = await client.messages.list(developer.sandbox_id);
    console.log(`   ✓ Total messages: ${messages.messages.length}`);

    // 8. Cleanup
    console.log('\n8. Cleaning up...');
    await client.sandboxes.stop(researcher.sandbox_id);
    await client.sandboxes.stop(developer.sandbox_id);
    await client.sandboxes.delete(researcher.sandbox_id);
    await client.sandboxes.delete(developer.sandbox_id);
    await client.workspaces.delete(workspace.workspace_id);
    console.log('   ✓ Cleanup complete');

    console.log('\n' + '='.repeat(60));
    console.log('TypeScript Application Example completed!');
    console.log('='.repeat(60));

  } catch (error) {
    console.error('Error:', error);
    throw error;
  } finally {
    await client.close();
  }
}

// Run if executed directly
if (require.main === module) {
  main().catch(console.error);
}

export { main };
