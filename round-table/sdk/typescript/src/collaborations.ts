// Copyright (c) 2025 AInTandem
// SPDX-License-Identifier: MIT

import { AxiosInstance } from 'axios';
import {
  Collaboration,
  OrchestrateCollaborationRequest,
  AgentListResponse,
} from './types';

/**
 * Client for collaboration operations
 *
 * Provides methods for orchestrating multi-agent collaborations.
 */
export class CollaborationClient {
  constructor(private readonly httpClient: AxiosInstance) {}

  /**
   * Orchestrate a collaboration task
   *
   * @param workspaceId - Workspace ID
   * @param request - Collaboration orchestration request
   * @returns Created collaboration
   */
  async orchestrate(
    workspaceId: string,
    request: OrchestrateCollaborationRequest
  ): Promise<Collaboration> {
    const response = await this.httpClient.post(
      `/collaborations/workspaces/${workspaceId}/collaboration/orchestrate`,
      request
    );
    return response.data.data;
  }

  /**
   * Get collaboration status
   *
   * @param collaborationId - Collaboration ID
   * @returns Collaboration details
   */
  async getCollaboration(collaborationId: string): Promise<Collaboration> {
    const response = await this.httpClient.get(
      `/collaborations/collaborations/${collaborationId}`
    );
    return response.data.data;
  }

  /**
   * Discover agents in a workspace
   *
   * @param workspaceId - Workspace ID
   * @returns Agent list response
   */
  async discoverAgents(workspaceId: string): Promise<AgentListResponse> {
    const response = await this.httpClient.get(
      `/collaborations/workspaces/${workspaceId}/agents/discover`
    );
    return response.data.data;
  }
}
