// Copyright (c) 2025 AInTandem
// SPDX-License-Identifier: MIT

import { AxiosInstance } from 'axios';
import {
  Workspace,
  WorkspaceCreateRequest,
  WorkspaceUpdateRequest,
  WorkspaceListResponse,
  WorkspaceSettings,
} from './types';

/**
 * Client for workspace operations
 *
 * Provides methods for creating, listing, updating, and deleting workspaces.
 */
export class WorkspaceClient {
  constructor(private readonly httpClient: AxiosInstance) {}

  /**
   * List all workspaces
   *
   * @param params - Pagination parameters
   * @returns Workspace list response
   */
  async list(params?: { offset?: number; limit?: number }): Promise<WorkspaceListResponse> {
    const response = await this.httpClient.get('/workspaces', {
      params: {
        offset: params?.offset ?? 0,
        limit: params?.limit ?? 100,
      },
    });

    return response.data.data;
  }

  /**
   * Create a new workspace
   *
   * @param request - Workspace creation request
   * @returns Created workspace
   */
  async create(request: WorkspaceCreateRequest): Promise<Workspace> {
    const response = await this.httpClient.post('/workspaces', request);
    return response.data.data;
  }

  /**
   * Get workspace by ID
   *
   * @param workspaceId - Workspace ID
   * @returns Workspace details
   */
  async get(workspaceId: string): Promise<Workspace> {
    const response = await this.httpClient.get(`/workspaces/${workspaceId}`);
    return response.data.data;
  }

  /**
   * Update workspace
   *
   * @param workspaceId - Workspace ID
   * @param request - Update request
   * @returns Updated workspace
   */
  async update(workspaceId: string, request: WorkspaceUpdateRequest): Promise<Workspace> {
    const response = await this.httpClient.put(`/workspaces/${workspaceId}`, request);
    return response.data.data;
  }

  /**
   * Delete workspace
   *
   * @param workspaceId - Workspace ID
   * @returns True if deleted successfully
   */
  async delete(workspaceId: string): Promise<boolean> {
    await this.httpClient.delete(`/workspaces/${workspaceId}`);
    return true;
  }

  /**
   * Get workspace configuration
   *
   * @param workspaceId - Workspace ID
   * @returns Workspace settings
   */
  async getConfig(workspaceId: string): Promise<WorkspaceSettings> {
    const response = await this.httpClient.get(`/workspaces/${workspaceId}/config`);
    return response.data.data;
  }

  /**
   * Update workspace configuration
   *
   * @param workspaceId - Workspace ID
   * @param settings - New settings
   * @returns Updated workspace
   */
  async updateConfig(workspaceId: string, settings: WorkspaceSettings): Promise<Workspace> {
    const response = await this.httpClient.put(`/workspaces/${workspaceId}/config`, settings);
    return response.data.data;
  }
}
