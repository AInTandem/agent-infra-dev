"""Pydantic models for request/response validation"""

from .auth import LoginRequest, RegisterRequest, AuthResponse, User
from .common import (
    ErrorDetail,
    ErrorResponse,
    Metadata,
    PaginationMeta,
    SuccessResponse,
    generate_id,
)
from .collaboration import (
    Collaboration,
    CollaborationProgress,
    OrchestrateCollaborationRequest,
)
from .config import (
    AggregateMetrics,
    CollaborationPolicy,
    LLMProviderConfig,
    MCPServerConfig,
    WorkspaceConfig,
    WorkspaceSettings,
)
from .message import (
    AgentMessage,
    BroadcastMessageRequest,
    MessageStatus,
    SendMessageRequest,
)
from .sandbox import (
    AgentConfig,
    AgentDefinition,
    ConnectionDetails,
    HealthStatus,
    ResourceLimits,
    Sandbox,
    SandboxCreateRequest,
    SandboxSummary,
)
from .workspace import (
    Workspace,
    WorkspaceCreateRequest,
    WorkspaceUpdateRequest,
    WorkspaceSummary,
)

__all__ = [
    # Common
    "ErrorDetail",
    "ErrorResponse",
    "Metadata",
    "PaginationMeta",
    "SuccessResponse",
    "generate_id",
    # Auth
    "LoginRequest",
    "RegisterRequest",
    "AuthResponse",
    "User",
    # Workspace
    "Workspace",
    "WorkspaceCreateRequest",
    "WorkspaceUpdateRequest",
    "WorkspaceSummary",
    # Sandbox
    "AgentConfig",
    "AgentDefinition",
    "ConnectionDetails",
    "HealthStatus",
    "ResourceLimits",
    "Sandbox",
    "SandboxCreateRequest",
    "SandboxSummary",
    # Message
    "AgentMessage",
    "BroadcastMessageRequest",
    "MessageStatus",
    "SendMessageRequest",
    # Collaboration
    "Collaboration",
    "CollaborationProgress",
    "OrchestrateCollaborationRequest",
    # Config
    "AggregateMetrics",
    "CollaborationPolicy",
    "LLMProviderConfig",
    "MCPServerConfig",
    "WorkspaceConfig",
    "WorkspaceSettings",
]
