// Copyright (c) 2025 AInTandem
// SPDX-License-Identifier: MIT

import { AxiosInstance } from 'axios';
import {
  AgentMessage,
  MessageCreateRequest,
  MessageListResponse,
  BroadcastRequest,
} from './types';

/**
 * Client for message operations
 *
 * Provides methods for sending messages between agents and broadcasting.
 */
export class MessageClient {
  constructor(private readonly httpClient: AxiosInstance) {}

  /**
   * Send a message from one sandbox to another
   *
   * @param fromSandboxId - Sender sandbox ID
   * @param request - Message creation request
   * @returns Sent message
   */
  async send(fromSandboxId: string, request: MessageCreateRequest): Promise<AgentMessage> {
    const response = await this.httpClient.post(
      `/sandboxes/${fromSandboxId}/messages`,
      request
    );
    return response.data.data;
  }

  /**
   * Get messages for a sandbox
   *
   * @param sandboxId - Sandbox ID
   * @param params - Pagination parameters
   * @returns Message list response
   */
  async getMessages(
    sandboxId: string,
    params?: { offset?: number; limit?: number }
  ): Promise<MessageListResponse> {
    const response = await this.httpClient.get(`/sandboxes/${sandboxId}/messages`, {
      params: {
        offset: params?.offset ?? 0,
        limit: params?.limit ?? 100,
      },
    });

    return response.data.data;
  }

  /**
   * Get message by ID
   *
   * @param messageId - Message ID
   * @returns Message details
   */
  async get(messageId: string): Promise<AgentMessage> {
    const response = await this.httpClient.get(`/messages/${messageId}`);
    return response.data.data;
  }

  /**
   * Broadcast a message to all sandboxes in a workspace
   *
   * @param workspaceId - Workspace ID
   * @param request - Broadcast request
   * @returns Broadcast response data
   */
  async broadcast(workspaceId: string, request: BroadcastRequest): Promise<{
    broadcast_to: number;
    workspace_id: string;
  }> {
    const response = await this.httpClient.post(
      `/workspaces/${workspaceId}/broadcast`,
      request
    );
    return response.data.data;
  }
}
