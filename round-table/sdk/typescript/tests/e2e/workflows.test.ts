// Copyright (c) 2025 AInTandem
// SPDX-License-Identifier: MIT

/**
 * End-to-End workflow tests for Round Table TypeScript SDK
 *
 * These tests demonstrate real-world usage patterns and complete workflows.
 */

import { describe, test, expect, beforeAll } from '@jest/globals';
import { RoundTableClient } from '../src/client';
import {
  Workspace,
  Sandbox,
  Collaboration,
  NotFoundError,
  ValidationError,
} from '../src/types';

// Test configuration
const TEST_API_KEY = process.env.ROUND_TABLE_API_KEY || 'test-api-key';
const TEST_BASE_URL = process.env.ROUND_TABLE_BASE_URL || 'http://localhost:8000/api/v1';

describe('TypeScript SDK E2E Workflows', () => {
  let client: RoundTableClient;

  beforeAll(() => {
    client = new RoundTableClient({
      apiKey: TEST_API_KEY,
      baseURL: TEST_BASE_URL,
    });
  });

  describe('Complete Collaboration Workflow', () => {
    test('should execute full collaboration workflow', async () => {
      // Step 1: Create workspace
      const workspace = await client.workspaces.create({
        name: 'ts-sdk-test-project',
        description: 'E2E test for TypeScript SDK',
      });
      expect(workspace.workspace_id).toMatch(/^ws_/);
      expect(workspace.name).toBe('ts-sdk-test-project');

      // Step 2: Create researcher sandbox
      const researcher = await client.sandboxes.create(
        workspace.workspace_id,
        {
          name: 'researcher',
          description: 'Research specialist',
          agent_config: {
            primary_agent: 'researcher',
            model: 'gpt-4',
            temperature: 0.7,
          },
        }
      );
      expect(researcher.sandbox_id).toMatch(/^sb_/);

      // Step 3: Create developer sandbox
      const developer = await client.sandboxes.create(
        workspace.workspace_id,
        {
          name: 'developer',
          description: 'Development specialist',
          agent_config: {
            primary_agent: 'developer',
            model: 'gpt-4',
            temperature: 0.5,
          },
        }
      );
      expect(developer.sandbox_id).toMatch(/^sb_/);

      // Step 4: Start researcher sandbox
      const startedResearcher = await client.sandboxes.start(
        researcher.sandbox_id
      );
      expect(['running', 'starting']).toContain(startedResearcher.status);

      // Step 5: Discover agents
      const agents = await client.collaborations.discoverAgents(
        workspace.workspace_id
      );
      expect(agents.count).toBeGreaterThanOrEqual(1);
      expect(agents.agents.length).toBeGreaterThanOrEqual(1);

      // Step 6: Orchestrate collaboration
      const collaboration = await client.collaborations.orchestrate(
        workspace.workspace_id,
        {
          task: 'Implement a user authentication system',
          mode: 'orchestrated',
          participants: [researcher.sandbox_id, developer.sandbox_id],
          config: {
            max_duration: 300,
            timeout: 30,
          },
        }
      );
      expect(collaboration.collaboration_id).toMatch(/^collab_/);
      expect(['pending', 'in_progress']).toContain(collaboration.status);

      // Step 7: Check collaboration status
      const status = await client.collaborations.getCollaboration(
        collaboration.collaboration_id
      );
      expect(status.collaboration_id).toBe(collaboration.collaboration_id);

      // Step 8: Send message between sandboxes
      const message = await client.messages.send({
        from_sandbox_id: researcher.sandbox_id,
        to_sandbox_id: developer.sandbox_id,
        content: {
          type: 'task_update',
          message: 'Starting research phase',
        },
      });
      expect(message.message_id).toMatch(/^msg_/);

      // Step 9: Get messages
      const messages = await client.messages.list(developer.sandbox_id);
      expect(messages.messages.length).toBeGreaterThanOrEqual(1);

      // Step 10: Cleanup
      await client.sandboxes.stop(researcher.sandbox_id);
      await client.sandboxes.delete(researcher.sandbox_id);
      await client.workspaces.delete(workspace.workspace_id);
    });
  });

  describe('Workspace Lifecycle', () => {
    test('should manage workspace lifecycle', async () => {
      // Create
      const workspace = await client.workspaces.create({
        name: 'lifecycle-test',
        description: 'Testing workspace lifecycle',
      });
      const workspaceId = workspace.workspace_id;

      // Read
      const fetched = await client.workspaces.get(workspaceId);
      expect(fetched.workspace_id).toBe(workspaceId);
      expect(fetched.name).toBe('lifecycle-test');

      // Update
      const updated = await client.workspaces.update(workspaceId, {
        name: 'lifecycle-test-updated',
        description: 'Updated description',
      });
      expect(updated.name).toBe('lifecycle-test-updated');

      // List
      const workspaces = await client.workspaces.list();
      expect(workspaces.workspaces.length).toBeGreaterThanOrEqual(1);

      // Delete
      await client.workspaces.delete(workspaceId);

      // Verify deletion
      await expect(client.workspaces.get(workspaceId)).rejects.toThrow(
        NotFoundError
      );
    });
  });

  describe('Sandbox Lifecycle', () => {
    test('should manage sandbox lifecycle', async () => {
      // Create workspace first
      const workspace = await client.workspaces.create({
        name: 'sandbox-lifecycle-test',
      });

      // Create sandbox
      const sandbox = await client.sandboxes.create(
        workspace.workspace_id,
        {
          name: 'test-agent',
          agent_config: {
            primary_agent: 'tester',
            model: 'gpt-4',
          },
        }
      );
      const sandboxId = sandbox.sandbox_id;

      // Get sandbox details
      const fetched = await client.sandboxes.get(sandboxId);
      expect(fetched.sandbox_id).toBe(sandboxId);

      // Start sandbox
      const started = await client.sandboxes.start(sandboxId);
      expect(['running', 'starting']).toContain(started.status);

      // Get status
      const status = await client.sandboxes.status(sandboxId);
      expect(['running', 'starting']).toContain(status.status);

      // Get metrics
      const metrics = await client.sandboxes.metrics(sandboxId);
      expect(metrics.sandbox_id).toBe(sandboxId);

      // Stop sandbox
      const stopped = await client.sandboxes.stop(sandboxId);
      expect(stopped.status).toBe('stopped');

      // Delete sandbox
      await client.sandboxes.delete(sandboxId);

      // Verify deletion
      await expect(client.sandboxes.get(sandboxId)).rejects.toThrow(
        NotFoundError
      );

      // Cleanup workspace
      await client.workspaces.delete(workspace.workspace_id);
    });
  });

  describe('Message Workflow', () => {
    test('should handle message sending and receiving', async () => {
      // Setup workspace and sandboxes
      const workspace = await client.workspaces.create({
        name: 'message-test',
      });

      const sender = await client.sandboxes.create(
        workspace.workspace_id,
        {
          name: 'sender',
          agent_config: {
            primary_agent: 'agent1',
            model: 'gpt-4',
          },
        }
      );

      const receiver = await client.sandboxes.create(
        workspace.workspace_id,
        {
          name: 'receiver',
          agent_config: {
            primary_agent: 'agent2',
            model: 'gpt-4',
          },
        }
      );

      // Send message
      const message = await client.messages.send({
        from_sandbox_id: sender.sandbox_id,
        to_sandbox_id: receiver.sandbox_id,
        content: {
          type: 'request',
          action: 'process_data',
          data: { key: 'value' },
        },
      });
      expect(message.message_id).toMatch(/^msg_/);

      // Get message details
      const fetched = await client.messages.get(message.message_id);
      expect(fetched.message_id).toBe(message.message_id);

      // List messages for receiver
      const messages = await client.messages.list(receiver.sandbox_id);
      expect(messages.messages.length).toBeGreaterThanOrEqual(1);

      // Broadcast message
      const broadcast = await client.messages.broadcast({
        workspace_id: workspace.workspace_id,
        from_sandbox_id: sender.sandbox_id,
        content: {
          type: 'announcement',
          message: 'Hello everyone!',
        },
      });
      expect(broadcast.message_id).toMatch(/^msg_/);

      // Cleanup
      await client.sandboxes.delete(sender.sandbox_id);
      await client.sandboxes.delete(receiver.sandbox_id);
      await client.workspaces.delete(workspace.workspace_id);
    });
  });

  describe('Error Handling', () => {
    test('should handle not found errors', async () => {
      await expect(client.workspaces.get('ws_nonexistent')).rejects.toThrow(
        NotFoundError
      );
      await expect(client.sandboxes.get('sb_nonexistent')).rejects.toThrow(
        NotFoundError
      );
    });

    test('should handle validation errors', async () => {
      await expect(
        client.workspaces.create({
          name: '', // Empty name should fail
        })
      ).rejects.toThrow(ValidationError);
    });
  });

  describe('Configuration Management', () => {
    test('should manage workspace configuration', async () => {
      // Create workspace
      const workspace = await client.workspaces.create({
        name: 'config-test',
      });

      // Get initial configuration
      const config = await client.workspaces.getConfig(
        workspace.workspace_id
      );
      expect(config.config).toBeDefined();

      // Update configuration
      const updated = await client.workspaces.updateConfig(
        workspace.workspace_id,
        {
          max_sandboxes: 10,
          max_agents_per_sandbox: 5,
        }
      );
      expect(updated.config.max_sandboxes).toBe(10);

      // Verify update
      const verified = await client.workspaces.getConfig(
        workspace.workspace_id
      );
      expect(verified.config.max_sandboxes).toBe(10);

      // Cleanup
      await client.workspaces.delete(workspace.workspace_id);
    });
  });

  describe('System Monitoring', () => {
    test('should monitor system health and metrics', async () => {
      // Health check would be implemented if endpoint exists
      // For now, test system info

      // Create workspace for metrics
      const workspace = await client.workspaces.create({
        name: 'metrics-test',
      });

      // Create sandbox to generate activity
      const sandbox = await client.sandboxes.create(
        workspace.workspace_id,
        {
          name: 'metrics-agent',
          agent_config: {
            primary_agent: 'agent',
            model: 'gpt-4',
          },
        }
      );

      // Get aggregate metrics (if endpoint exists)
      // const metrics = await client.workspaces.getMetrics(
      //   workspace.workspace_id
      // );
      // expect(metrics.workspace_id).toBe(workspace.workspace_id);

      // Cleanup
      await client.sandboxes.delete(sandbox.sandbox_id);
      await client.workspaces.delete(workspace.workspace_id);
    });
  });
});
