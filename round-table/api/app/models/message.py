"""Message-related Pydantic models"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MessageStatus(BaseModel):
    """Message delivery status"""
    status: str = "pending"
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    failed_at: datetime | None = None
    error_message: str | None = None


class AgentMessage(BaseModel):
    """Full message entity"""
    message_id: str
    from_sandbox_id: str
    to_sandbox_id: str | None = None
    workspace_id: str
    content: dict[str, Any]
    message_type: str = "request"
    status: MessageStatus
    created_at: str | None = None
    updated_at: str | None = None


class SendMessageRequest(BaseModel):
    """Message sending request"""
    to_sandbox_id: str
    content: dict[str, Any]
    message_type: str = Field(default="request", pattern="^(request|response|notification|command)$")


class BroadcastMessageRequest(BaseModel):
    """Broadcast message request"""
    content: dict[str, Any]
    message_type: str = Field(default="notification")
    exclude_sender: bool = True
