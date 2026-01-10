# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""Unit tests for repository pattern"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, AsyncSessionTransaction
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, User, Workspace, Sandbox, Message
from app.repositories import (
    UserRepository,
    WorkspaceRepository,
    SandboxRepository,
    MessageRepository
)
from app.models.auth import RegisterRequest
from app.models.workspace import WorkspaceCreateRequest
from app.models.sandbox import SandboxCreateRequest, AgentConfig


# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def engine():
    """Create test database engine"""
    from sqlalchemy.ext.asyncio import async_engine_from_config
    
    engine = async_engine_from_config(
        {"sqlalchemy.url": TEST_DATABASE_URL},
        prefix="sqlalchemy.",
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def session(engine):
    """Create test database session"""
    async_session_factory = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_factory() as session:
        yield session
        await session.rollback()


class TestUserRepository:
    """Test User repository"""
    
    @pytest.mark.asyncio
    async def test_create_user(self, session):
        """Test creating a user"""
        repo = UserRepository(session)
        
        user_in = RegisterRequest(
            email="test@example.com",
            password="hashedpassword",
            full_name="Test User"
        )
        
        user = await repo.create_user(user_in, "hashedpassword")
        
        assert user.user_id.startswith("usr_")
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.is_active is True
    
    @pytest.mark.asyncio
    async def test_get_by_email(self, session):
        """Test getting user by email"""
        repo = UserRepository(session)
        
        # Create user
        user_in = RegisterRequest(
            email="findme@example.com",
            password="hashedpassword"
        )
        await repo.create_user(user_in, "hashedpassword")
        
        # Find by email
        found = await repo.get_by_email("findme@example.com")
        
        assert found is not None
        assert found.email == "findme@example.com"
    
    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, session):
        """Test getting non-existent user"""
        repo = UserRepository(session)
        
        found = await repo.get_by_email("nonexistent@example.com")
        
        assert found is None


class TestWorkspaceRepository:
    """Test Workspace repository"""
    
    @pytest.mark.asyncio
    async def test_create_workspace(self, session):
        """Test creating a workspace"""
        repo = WorkspaceRepository(session)
        
        ws_in = WorkspaceCreateRequest(
            name="Test Workspace",
            description="A test workspace"
        )
        
        workspace = await repo.create_workspace(ws_in, "usr_test123")
        
        assert workspace.workspace_id.startswith("ws_")
        assert workspace.name == "Test Workspace"
        assert workspace.user_id == "usr_test123"
        assert workspace.is_active is True
    
    @pytest.mark.asyncio
    async def test_list_by_user(self, session):
        """Test listing workspaces by user"""
        repo = WorkspaceRepository(session)
        
        # Create workspaces
        for i in range(3):
            ws_in = WorkspaceCreateRequest(name=f"Workspace {i}")
            await repo.create_workspace(ws_in, "usr_test123")
        
        # List workspaces
        workspaces = await repo.get_by_user("usr_test123")
        
        assert len(workspaces) == 3
        assert all(ws.user_id == "usr_test123" for ws in workspaces)


class TestSandboxRepository:
    """Test Sandbox repository"""
    
    @pytest.mark.asyncio
    async def test_create_sandbox(self, session):
        """Test creating a sandbox"""
        repo = SandboxRepository(session)
        
        sb_in = SandboxCreateRequest(
            name="test-sandbox",
            agent_config=AgentConfig(primary_agent="researcher")
        )
        
        sandbox = await repo.create_sandbox(sb_in, "ws_test123")
        
        assert sandbox.sandbox_id.startswith("sb_")
        assert sandbox.name == "test-sandbox"
        assert sandbox.workspace_id == "ws_test123"
        assert sandbox.status == "provisioning"
    
    @pytest.mark.asyncio
    async def test_update_status(self, session):
        """Test updating sandbox status"""
        repo = SandboxRepository(session)
        
        # Create sandbox
        sb_in = SandboxCreateRequest(
            name="test-sandbox",
            agent_config=AgentConfig(primary_agent="agent")
        )
        sandbox = await repo.create_sandbox(sb_in, "ws_test123")
        
        # Update status
        updated = await repo.update_status(sandbox.sandbox_id, "running")
        
        assert updated is not None
        assert updated.status == "running"


class TestMessageRepository:
    """Test Message repository"""
    
    @pytest.mark.asyncio
    async def test_create_message(self, session):
        """Test creating a message"""
        repo = MessageRepository(session)
        
        message = await repo.create_message(
            from_sandbox_id="sb_sender",
            to_sandbox_id="sb_receiver",
            workspace_id="ws_test",
            content={"type": "greeting", "text": "hello"},
            message_type="request"
        )
        
        assert message.message_id.startswith("msg_")
        assert message.from_sandbox_id == "sb_sender"
        assert message.to_sandbox_id == "sb_receiver"
        assert message.status == "pending"
    
    @pytest.mark.asyncio
    async def test_update_message_status(self, session):
        """Test updating message status"""
        repo = MessageRepository(session)
        
        # Create message
        message = await repo.create_message(
            from_sandbox_id="sb_sender",
            to_sandbox_id="sb_receiver",
            workspace_id="ws_test",
            content={"text": "test"}
        )
        
        # Update status
        updated = await repo.update_status(message.message_id, "delivered")
        
        assert updated is not None
        assert updated.status == "delivered"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
