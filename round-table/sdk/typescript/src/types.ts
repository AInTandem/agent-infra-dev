// Copyright (c) 2025 AInTandem
// SPDX-License-Identifier: MIT

/**
 * Type definitions for Round Table SDK
 */

/**
 * Workspace settings configuration
 */
export interface WorkspaceSettings {
  max_sandboxes: number;
  auto_cleanup: boolean;
  retention_days: number;
  collaboration_policy: Record<string, unknown>;
}

/**
 * Workspace model
 */
export interface Workspace {
  workspace_id: string;
  user_id: string;
  name: string;
  description?: string;
  settings: WorkspaceSettings;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

/**
 * Lightweight workspace reference
 */
export interface WorkspaceSummary {
  workspace_id: string;
  name: string;
  description?: string;
  sandbox_count: number;
  created_at?: string;
}

/**
 * Workspace creation request
 */
export interface WorkspaceCreateRequest {
  name: string;
  description?: string;
  settings?: WorkspaceSettings;
}

/**
 * Workspace update request
 */
export interface WorkspaceUpdateRequest {
  name?: string;
  description?: string;
  settings?: WorkspaceSettings;
  is_active?: boolean;
}

/**
 * Workspace list response
 */
export interface WorkspaceListResponse {
  workspaces: WorkspaceSummary[];
  count: number;
  offset: number;
  limit: number;
}

/**
 * Agent configuration
 */
export interface AgentConfig {
  primary_agent: string;
  model: string;
  max_tokens?: number;
  temperature?: number;
  system_prompt?: string;
  tools: string[];
  extra_config: Record<string, unknown>;
}

/**
 * Resource limits for sandbox
 */
export interface ResourceLimits {
  max_memory_mb?: number;
  max_cpu_cores?: number;
  max_disk_gb?: number;
  max_execution_time_seconds?: number;
}

/**
 * Sandbox model
 */
export interface Sandbox {
  sandbox_id: string;
  workspace_id: string;
  name: string;
  status: string;
  agent_config: AgentConfig;
  connection_details?: Record<string, unknown>;
  container_id?: string;
  created_at?: string;
  updated_at?: string;
}

/**
 * Sandbox creation request
 */
export interface SandboxCreateRequest {
  name: string;
  agent_config: AgentConfig;
  description?: string;
}

/**
 * Sandbox update request
 */
export interface SandboxUpdateRequest {
  name?: string;
  agent_config?: AgentConfig;
}

/**
 * Sandbox list response
 */
export interface SandboxListResponse {
  sandboxes: Sandbox[];
  count: number;
  offset: number;
  limit: number;
}

/**
 * Sandbox status information
 */
export interface SandboxStatus {
  sandbox_id: string;
  status: string;
  container_status?: string;
  last_heartbeat?: string;
  uptime_seconds?: number;
}

/**
 * Sandbox metrics
 */
export interface SandboxMetrics {
  sandbox_id: string;
  metrics: Record<string, unknown>;
  timestamp: string;
}

/**
 * Agent message
 */
export interface AgentMessage {
  message_id: string;
  from_sandbox_id: string;
  to_sandbox_id: string;
  workspace_id: string;
  content: Record<string, unknown>;
  message_type: string;
  status: string;
  created_at?: string;
  updated_at?: string;
}

/**
 * Message creation request
 */
export interface MessageCreateRequest {
  to_sandbox_id: string;
  content: Record<string, unknown>;
  message_type?: string;
}

/**
 * Broadcast request
 */
export interface BroadcastRequest {
  content: Record<string, unknown>;
  message_type?: string;
}

/**
 * Message list response
 */
export interface MessageListResponse {
  messages: AgentMessage[];
  count: number;
  offset: number;
  limit: number;
}

/**
 * Collaboration mode configuration
 */
export interface CollaborationMode {
  mode: 'orchestrated' | 'peer_to_peer' | 'broadcast';
  max_duration_seconds?: number;
  allow_parallel_tasks: boolean;
  require_consensus: boolean;
}

/**
 * Collaboration configuration
 */
export interface CollaborationConfig {
  timeout: number;
  max_iterations: number;
  terminate_on_completion: boolean;
  save_history: boolean;
  extra_params: Record<string, unknown>;
}

/**
 * Collaboration model
 */
export interface Collaboration {
  collaboration_id: string;
  workspace_id: string;
  task: string;
  mode: string;
  participants: string[];
  status: string;
  config: CollaborationConfig;
  result?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
}

/**
 * Collaboration orchestration request
 */
export interface OrchestrateCollaborationRequest {
  task: string;
  mode?: string;
  participants: string[];
  config?: CollaborationConfig;
}

/**
 * Agent information for discovery
 */
export interface AgentInfo {
  sandbox_id: string;
  name: string;
  primary_agent: string;
  model: string;
  status: string;
  capabilities: string[];
}

/**
 * Agent list response
 */
export interface AgentListResponse {
  workspace_id: string;
  count: number;
  agents: AgentInfo[];
}

/**
 * System health status
 */
export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  database: 'connected' | 'disconnected';
  message_bus: 'connected' | 'disconnected';
  timestamp: string;
}

/**
 * System information
 */
export interface SystemInfo {
  name: string;
  version: string;
  description: string;
  environment: string;
  python_version: string;
  platform: string;
  authenticated: boolean;
  user_id?: string;
  email?: string;
}

/**
 * Aggregate metrics for workspace
 */
export interface AggregateMetrics {
  workspace_id: string;
  sandboxes: Record<string, unknown>;
  messages: Record<string, unknown>;
  collaborations: Record<string, unknown>;
  timestamp: string;
}

/**
 * API response wrapper
 */
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  status_code?: number;
}

/**
 * Pagination parameters
 */
export interface PaginationParams {
  offset?: number;
  limit?: number;
}
