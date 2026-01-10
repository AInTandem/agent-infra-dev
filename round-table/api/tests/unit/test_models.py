"""Unit tests for Pydantic models"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from api.app.models.auth import RegisterRequest, LoginRequest
from api.app.models.workspace import WorkspaceCreateRequest, WorkspaceSettings
from api.app.models.sandbox import SandboxCreateRequest, AgentConfig
from api.app.models.message import SendMessageRequest
from api.app.models.common import generate_id


class TestCommonModels:
    """Test common utility functions"""
    
    def test_generate_id(self):
        """Test ID generation"""
        id1 = generate_id("usr")
        id2 = generate_id("ws")
        
        assert id1.startswith("usr_")
        assert id2.startswith("ws_")
        assert len(id1) == 14  # usr_ + 10 hex chars
        assert id1 != id2  # Unique IDs


class TestAuthModels:
    """Test authentication models"""
    
    def test_register_request_valid(self):
        """Valid registration request"""
        data = {
            "email": "test@example.com",
            "password": "securepassword123",
            "full_name": "Test User"
        }
        req = RegisterRequest(**data)
        
        assert req.email == "test@example.com"
        assert req.password == "securepassword123"
        assert req.full_name == "Test User"
    
    def test_register_request_password_too_short(self):
        """Password too short should fail"""
        with pytest.raises(ValidationError):
            RegisterRequest(email="test@example.com", password="short")
    
    def test_login_request_valid(self):
        """Valid login request"""
        data = {
            "email": "user@example.com",
            "password": "password123"
        }
        req = LoginRequest(**data)
        
        assert req.email == "user@example.com"
        assert req.password == "password123"


class TestWorkspaceModels:
    """Test workspace models"""
    
    def test_workspace_create_request_valid(self):
        """Valid workspace creation"""
        data = {
            "name": "My Workspace",
            "description": "Test workspace"
        }
        req = WorkspaceCreateRequest(**data)
        
        assert req.name == "My Workspace"
        assert req.description == "Test workspace"
    
    def test_workspace_name_too_long(self):
        """Workspace name exceeds max length"""
        with pytest.raises(ValidationError):
            WorkspaceCreateRequest(name="x" * 101)
    
    def test_workspace_settings_defaults(self):
        """Workspace settings has correct defaults"""
        settings = WorkspaceSettings()
        
        assert settings.max_sandboxes == 10
        assert settings.auto_cleanup is True
        assert settings.retention_days == 30


class TestSandboxModels:
    """Test sandbox models"""
    
    def test_sandbox_create_request_valid(self):
        """Valid sandbox creation"""
        data = {
            "name": "test-sandbox",
            "agent_config": {
                "primary_agent": "researcher",
                "model": "gpt-4"
            }
        }
        req = SandboxCreateRequest(**data)
        
        assert req.name == "test-sandbox"
        assert req.agent_config.primary_agent == "researcher"
    
    def test_agent_config_validation(self):
        """Agent config validation"""
        config = AgentConfig(
            primary_agent="agent",
            temperature=0.5,
            max_tokens=2048
        )
        
        assert config.primary_agent == "agent"
        assert config.temperature == 0.5
        assert config.max_tokens == 2048
    
    def test_agent_config_temperature_bounds(self):
        """Temperature must be between 0 and 2"""
        with pytest.raises(ValidationError):
            AgentConfig(primary_agent="agent", temperature=3.0)


class TestMessageModels:
    """Test message models"""
    
    def test_send_message_request_valid(self):
        """Valid send message request"""
        data = {
            "to_sandbox_id": "sb_1234567890",
            "content": {"type": "greeting", "text": "hello"},
            "message_type": "request"
        }
        req = SendMessageRequest(**data)
        
        assert req.to_sandbox_id == "sb_1234567890"
        assert req.content["type"] == "greeting"
        assert req.message_type == "request"
    
    def test_message_type_validation(self):
        """Message type must be valid"""
        data = {
            "to_sandbox_id": "sb_1234567890",
            "content": {"text": "hello"},
            "message_type": "invalid_type"
        }
        with pytest.raises(ValidationError):
            SendMessageRequest(**data)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
