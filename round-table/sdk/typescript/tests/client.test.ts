// Copyright (c) 2025 AInTandem
// SPDX-License-Identifier: MIT

import { RoundTableClient, RoundTableConfig } from '../src';

describe('RoundTableClient', () => {
  let client: RoundTableClient;

  beforeEach(() => {
    client = new RoundTableClient({ apiKey: 'test-key' });
  });

  afterEach(async () => {
    await client.close();
  });

  describe('initialization', () => {
    test('should initialize with API key', () => {
      expect(client.config.apiKey).toBe('test-key');
      expect(client.config.baseURL).toContain('localhost:8000');
    });

    test('should initialize with config object', () => {
      const config = new RoundTableConfig({
        apiKey: 'test-key',
        baseURL: 'http://example.com/api/v1',
      });
      const customClient = new RoundTableClient(config);

      expect(customClient.config.apiKey).toBe('test-key');
      expect(customClient.config.baseURL).toContain('example.com');
    });

    test('should normalize base URL', () => {
      const customClient = new RoundTableClient({
        apiKey: 'test-key',
        baseURL: 'http://example.com',
      });

      expect(customClient.config.baseURL).toBe('http://example.com/api/v1');
    });

    test('should support string API key', () => {
      const stringClient = new RoundTableClient('test-key');
      expect(stringClient.config.apiKey).toBe('test-key');
    });
  });

  describe('resource clients', () => {
    test('should provide workspaces client', () => {
      expect(client.workspaces).toBeDefined();
      expect(client.workspaces).toBeInstanceOf(Object);
    });

    test('should provide sandboxes client', () => {
      expect(client.sandboxes).toBeDefined();
      expect(client.sandboxes).toBeInstanceOf(Object);
    });

    test('should provide messages client', () => {
      expect(client.messages).toBeDefined();
      expect(client.messages).toBeInstanceOf(Object);
    });

    test('should provide collaborations client', () => {
      expect(client.collaborations).toBeDefined();
      expect(client.collaborations).toBeInstanceOf(Object);
    });

    test('should reuse client instances', () => {
      const workspaces1 = client.workspaces;
      const workspaces2 = client.workspaces;

      expect(workspaces1).toBe(workspaces2);
    });
  });

  describe('cleanup', () => {
    test('should close client', async () => {
      await expect(client.close()).resolves.not.toThrow();
    });
  });
});
