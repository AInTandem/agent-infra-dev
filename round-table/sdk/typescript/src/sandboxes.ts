// Copyright (c) 2025 AInTandem
// SPDX-License-Identifier: MIT

import { AxiosInstance } from 'axios';
import {
  Sandbox,
  SandboxCreateRequest,
  SandboxUpdateRequest,
  SandboxListResponse,
  SandboxStatus,
  SandboxMetrics,
  AgentConfig,
} from './types';

/**
 * Client for sandbox operations
 *
 * Provides methods for creating, managing, and monitoring agent containers.
 */
export class SandboxClient {
  constructor(private readonly httpClient: AxiosInstance) {}

  /**
   * List all sandboxes in a workspace
   *
   * @param workspaceId - Workspace ID
   * @param params - Pagination parameters
   * @returns Sandbox list response
   */
  async list(workspaceId: string, params?: { offset?: number; limit?: number }): Promise<SandboxListResponse> {
    const response = await this.httpClient.get(`/workspaces/${workspaceId}/sandboxes`, {
      params: {
        offset: params?.offset ?? 0,
        limit: params?.limit ?? 100,
      },
    });

    return response.data.data;
  }

  /**
   * Create a new sandbox
   *
   * @param workspaceId - Workspace ID
   * @param request - Sandbox creation request
   * @returns Created sandbox
   */
  async create(workspaceId: string, request: SandboxCreateRequest): Promise<Sandbox> {
    const response = await this.httpClient.post(`/workspaces/${workspaceId}/sandboxes`, request);
    return response.data.data;
  }

  /**
   * Get sandbox by ID
   *
   * @param sandboxId - Sandbox ID
   * @returns Sandbox details
   */
  async get(sandboxId: string): Promise<Sandbox> {
    const response = await this.httpClient.get(`/sandboxes/${sandboxId}`);
    return response.data.data;
  }

  /**
   * Update sandbox
   *
   * @param sandboxId - Sandbox ID
   * @param request - Update request
   * @returns Updated sandbox
   */
  async update(sandboxId: string, request: SandboxUpdateRequest): Promise<Sandbox> {
    const response = await this.httpClient.put(`/sandboxes/${sandboxId}`, request);
    return response.data.data;
  }

  /**
   * Delete sandbox
   *
   * @param sandboxId - Sandbox ID
   * @returns True if deleted successfully
   */
  async delete(sandboxId: string): Promise<boolean> {
    await this.httpClient.delete(`/sandboxes/${sandboxId}`);
    return true;
  }

  /**
   * Start sandbox
   *
   * @param sandboxId - Sandbox ID
   * @returns Updated sandbox with running status
   */
  async start(sandboxId: string): Promise<Sandbox> {
    const response = await this.httpClient.post(`/sandboxes/${sandboxId}/start`);
    return response.data.data;
  }

  /**
   * Stop sandbox
   *
   * @param sandboxId - Sandbox ID
   * @returns Updated sandbox with stopped status
   */
  async stop(sandboxId: string): Promise<Sandbox> {
    const response = await this.httpClient.post(`/sandboxes/${sandboxId}/stop`);
    return response.data.data;
  }

  /**
   * Get sandbox status
   *
   * @param sandboxId - Sandbox ID
   * @returns Sandbox status information
   */
  async status(sandboxId: string): Promise<SandboxStatus> {
    const response = await this.httpClient.get(`/sandboxes/${sandboxId}/status`);
    return response.data.data;
  }

  /**
   * Get sandbox logs
   *
   * @param sandboxId - Sandbox ID
   * @returns List of log lines
   */
  async logs(sandboxId: string): Promise<string[]> {
    const response = await this.httpClient.get(`/sandboxes/${sandboxId}/logs`);
    return response.data.data.logs || [];
  }

  /**
   * Get sandbox metrics
   *
   * @param sandboxId - Sandbox ID
   * @returns Sandbox metrics
   */
  async metrics(sandboxId: string): Promise<SandboxMetrics> {
    const response = await this.httpClient.get(`/sandboxes/${sandboxId}/metrics`);
    return response.data.data;
  }
}
