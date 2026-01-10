"""SQLAlchemy database models"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models"""
    pass


class TimestampMixin:
    """Mixin for created/updated timestamps"""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )


class User(Base, TimestampMixin):
    """User model for authentication"""
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    full_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False
    )


class Workspace(Base, TimestampMixin):
    """Workspace model"""
    __tablename__ = "workspaces"

    workspace_id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True
    )
    user_id: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    settings_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False
    )


class Sandbox(Base, TimestampMixin):
    """Sandbox model"""
    __tablename__ = "sandboxes"

    sandbox_id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="provisioning",
        nullable=False
    )
    agent_config_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    connection_details_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    container_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )


class Message(Base, TimestampMixin):
    """Message model for audit log"""
    __tablename__ = "messages"

    message_id: Mapped[str] = mapped_column(
        String(20),
        primary_key=True
    )
    from_sandbox_id: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )
    to_sandbox_id: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        index=True
    )
    workspace_id: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )
    content_json: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    message_type: Mapped[str] = mapped_column(
        String(20),
        default="request",
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False
    )
