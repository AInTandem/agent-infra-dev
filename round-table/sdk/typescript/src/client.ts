// Copyright (c) 2025 AInTandem
// SPDX-License-Identifier: MIT

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { RoundTableConfig, RoundTableConfigOptions } from './config';
import { raiseForStatus } from './errors';
import { ApiResponse } from './types';
import { WorkspaceClient } from './workspaces';
import { SandboxClient } from './sandboxes';
import { MessageClient } from './messages';
import { CollaborationClient } from './collaborations';

/**
 * Main Round Table client
 *
 * Provides the main entry point for interacting with the Round Table
 * Collaboration Bus API.
 *
 * @example
 * ```typescript
 * import { RoundTableClient } from '@roundtable/sdk';
 *
 * const client = new RoundTableClient({ apiKey: 'your-api-key' });
 *
 * // Create workspace
 * const workspace = await client.workspaces.create({
 *   name: 'My Workspace',
 *   description: 'A workspace for my agents'
 * });
 *
 * // Create sandbox
 * const sandbox = await client.sandboxes.create(workspace.workspace_id, {
 *   name: 'Research Agent',
 *   agent_config: {
 *     primary_agent: 'researcher',
 *     model: 'gpt-4'
 *   }
 * });
 * ```
 */
export class RoundTableClient {
  public readonly config: RoundTableConfig;
  private readonly httpClient: AxiosInstance;
  private _workspaceClient?: WorkspaceClient;
  private _sandboxClient?: SandboxClient;
  private _messageClient?: MessageClient;
  private _collaborationClient?: CollaborationClient;

  /**
   * Initialize the Round Table client
   *
   * @param options - Configuration options or API key string
   */
  constructor(options: RoundTableConfigOptions | string) {
    // Support string API key for convenience
    if (typeof options === 'string') {
      options = { apiKey: options };
    }

    this.config = new RoundTableConfig(options);

    // Create HTTP client
    this.httpClient = axios.create({
      baseURL: this.config.baseURL,
      headers: {
        'Authorization': `Bearer ${this.config.apiKey}`,
        'Content-Type': 'application/json',
        ...this.config.extraHeaders,
      },
      timeout: this.config.timeout,
    });
  }

  /**
   * Workspace operations
   */
  get workspaces(): WorkspaceClient {
    if (!this._workspaceClient) {
      this._workspaceClient = new WorkspaceClient(this.httpClient);
    }
    return this._workspaceClient;
  }

  /**
   * Sandbox operations
   */
  get sandboxes(): SandboxClient {
    if (!this._sandboxClient) {
      this._sandboxClient = new SandboxClient(this.httpClient);
    }
    return this._sandboxClient;
  }

  /**
   * Message operations
   */
  get messages(): MessageClient {
    if (!this._messageClient) {
      this._messageClient = new MessageClient(this.httpClient);
    }
    return this._messageClient;
  }

  /**
   * Collaboration operations
   */
  get collaborations(): CollaborationClient {
    if (!this._collaborationClient) {
      this._collaborationClient = new CollaborationClient(this.httpClient);
    }
    return this._collaborationClient;
  }

  /**
   * Make an HTTP request
   *
   * @param method - HTTP method
   * @param path - Request path
   * @param options - Axios request options
   * @returns Response data
   */
  async request<T>(method: string, path: string, options?: AxiosRequestConfig): Promise<T> {
    try {
      const response: AxiosResponse<ApiResponse<T>> = await this.httpClient.request<ApiResponse<T>>({
        method,
        url: path,
        ...options,
      });

      raiseForStatus(response.data);

      return response.data.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        if (error.response) {
          raiseForStatus(error.response.data as ApiResponse<unknown>);
        } else if (error.request) {
          throw new Error('No response received from server');
        }
      }
      throw error;
    }
  }

  /**
   * Close the client and clean up resources
   */
  async close(): Promise<void> {
    // Clear client references
    this._workspaceClient = undefined;
    this._sandboxClient = undefined;
    this._messageClient = undefined;
    this._collaborationClient = undefined;
  }
}

// Export all types and classes
export * from './config';
export * from './errors';
export * from './types';
export * from './workspaces';
export * from './sandboxes';
export * from './messages';
export * from './collaborations';
