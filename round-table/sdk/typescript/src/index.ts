// Copyright (c) 2025 AInTandem
// SPDX-License-Identifier: MIT

/**
 * Round Table TypeScript SDK
 *
 * A TypeScript SDK for interacting with the Round Table Collaboration Bus API.
 */

// Main client
export { RoundTableClient } from './client';

// Configuration
export { RoundTableConfig, type RoundTableConfigOptions } from './config';

// Errors
export {
  RoundTableError,
  AuthenticationError,
  ForbiddenError,
  NotFoundError,
  BadRequestError,
  ValidationError,
  ConflictError,
  RateLimitError,
  ServerError,
  ConnectionError,
  raiseForStatus,
} from './errors';

// Types
export type {
  // Workspace types
  WorkspaceSettings,
  Workspace,
  WorkspaceSummary,
  WorkspaceCreateRequest,
  WorkspaceUpdateRequest,
  WorkspaceListResponse,

  // Sandbox types
  AgentConfig,
  ResourceLimits,
  Sandbox,
  SandboxCreateRequest,
  SandboxUpdateRequest,
  SandboxListResponse,
  SandboxStatus,
  SandboxMetrics,

  // Message types
  AgentMessage,
  MessageCreateRequest,
  BroadcastRequest,
  MessageListResponse,

  // Collaboration types
  CollaborationMode,
  CollaborationConfig,
  Collaboration,
  OrchestrateCollaborationRequest,
  AgentInfo,
  AgentListResponse,

  // System types
  SystemHealth,
  SystemInfo,
  AggregateMetrics,

  // Common types
  ApiResponse,
  PaginationParams,
} from './types';

// Resource clients
export { WorkspaceClient } from './workspaces';
export { SandboxClient } from './sandboxes';
export { MessageClient } from './messages';
export { CollaborationClient } from './collaborations';
