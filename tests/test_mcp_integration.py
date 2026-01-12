#!/usr/bin/env python3
"""
End-to-end integration tests for MCP Manager refactoring.

Tests the complete flow from configuration to agent creation with MCP integration.
"""

import asyncio
import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import (
    ConfigManager,
    AgentConfig,
    LLMConfig,
    LLMProviderConfig,
    LLMModelConfig,
    MCPServerConfig,
)
from core.mcp_manager import MCPManager
from core.agent_manager import AgentManager


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def minimal_config():
    """Create minimal configuration for testing."""
    # Create LLM config
    llm_config = LLMConfig(
        default_model="claude-3-5-sonnet-20241022",
        providers={
            "claude": LLMProviderConfig(
                description="Anthropic Claude",
                api_key="test-key",
                base_url="https://api.anthropic.com",
                sdk="claude",
                supports_mcp=True,
                supports_computer_use=True,
            ),
            "qwen": LLMProviderConfig(
                description="Qwen",
                api_key="test-key",
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                sdk="qwen",
                supports_mcp=False,
                supports_computer_use=False,
            ),
        },
        models=[
            LLMModelConfig(
                name="claude-3-5-sonnet-20241022",
                provider="claude",
                supports_mcp=True,
            ),
            LLMModelConfig(
                name="qwen-max",
                provider="qwen",
                supports_mcp=False,
            ),
        ],
    )

    # Create MCP servers config
    mcp_servers_config = {
        "native_server": MCPServerConfig(
            name="native_server",
            description="Native MCP server",
            transport="stdio",
            command="echo",
            args=["test"],
            enabled=True,
            function_call_wrapper=False,
        ),
        "wrapper_server": MCPServerConfig(
            name="wrapper_server",
            description="Wrapper server",
            transport="stdio",
            command="echo",
            args=["test"],
            enabled=True,
            function_call_wrapper=True,
        ),
    }

    # Create agents config
    agents_config = {
        "claude_agent": AgentConfig(
            name="claude_agent",
            role="assistant",
            description="Claude agent",
            system_prompt="You are a helpful assistant.",
            llm_model="claude-3-5-sonnet-20241022",
            mcp_servers=["native_server"],
            enabled=True,
        ),
        "qwen_agent": AgentConfig(
            name="qwen_agent",
            role="assistant",
            description="Qwen agent",
            system_prompt="You are a helpful assistant.",
            llm_model="qwen-max",
            mcp_servers=["wrapper_server"],
            enabled=True,
        ),
    }

    # Return a simple object with the configurations
    class MinimalConfig:
        def __init__(self):
            self.llm = llm_config
            self.mcp_servers = mcp_servers_config
            self.agents = agents_config

        def get_mcp_server(self, name):
            return self.mcp_servers.get(name)

    return MinimalConfig()


# ============================================================================
# Integration Tests
# ============================================================================

def test_mcp_manager_creation(minimal_config):
    """Test MCP Manager can be created."""
    manager = MCPManager(minimal_config)

    assert manager is not None
    assert manager.config_manager == minimal_config


def test_agent_manager_creation(minimal_config):
    """Test AgentManager can be created with MCPManager."""
    # Note: Don't initialize since that requires real MCP servers
    agent_manager = AgentManager(
        config_manager=minimal_config,
        mcp_manager=None,  # Pass None for creation test
    )

    assert agent_manager is not None
    assert agent_manager.config_manager == minimal_config


def test_tool_routing_logic(minimal_config):
    """Test that tool routing logic works based on LLM MCP support."""
    # Test routing decision without actual initialization

    # Claude agent has native MCP support
    claude_agent = minimal_config.agents["claude_agent"]
    llm_supports_mcp = minimal_config.llm.get_model_mcp_support(claude_agent.llm_model)
    assert llm_supports_mcp is True

    # Qwen agent does not have native MCP support
    qwen_agent = minimal_config.agents["qwen_agent"]
    llm_supports_mcp = minimal_config.llm.get_model_mcp_support(qwen_agent.llm_model)
    assert llm_supports_mcp is False


def test_server_config_classification(minimal_config):
    """Test that servers are classified correctly."""
    # Native server (function_call_wrapper: False)
    native_server = minimal_config.mcp_servers["native_server"]
    assert native_server.function_call_wrapper is False

    # Wrapper server (function_call_wrapper: True)
    wrapper_server = minimal_config.mcp_servers["wrapper_server"]
    assert wrapper_server.function_call_wrapper is True


def test_config_structure(minimal_config):
    """Test that configuration structure is correct."""
    # Check LLM config
    assert hasattr(minimal_config, 'llm')
    assert hasattr(minimal_config.llm, 'providers')
    assert hasattr(minimal_config.llm, 'models')
    assert 'claude' in minimal_config.llm.providers
    assert 'qwen' in minimal_config.llm.providers

    # Check MCP servers config
    assert hasattr(minimal_config, 'mcp_servers')
    assert 'native_server' in minimal_config.mcp_servers
    assert 'wrapper_server' in minimal_config.mcp_servers

    # Check agents config
    assert hasattr(minimal_config, 'agents')
    assert 'claude_agent' in minimal_config.agents
    assert 'qwen_agent' in minimal_config.agents


# ============================================================================
# Validation Integration Tests
# ============================================================================

def test_validate_compatible_configurations(minimal_config):
    """Test validation of compatible configurations."""
    from core.config import validate_agent_config

    # Claude agent with native server - should be valid
    claude_agent = minimal_config.agents["claude_agent"]
    mcp_configs = {
        "native_server": minimal_config.mcp_servers["native_server"]
    }

    warnings = validate_agent_config(
        claude_agent,
        minimal_config.llm,
        mcp_configs
    )
    # Should not raise, warnings may be empty or contain info about server not being found


def test_validate_incompatible_configurations(minimal_config):
    """Test validation catches incompatible configurations."""
    from core.config import validate_agent_config

    # Create incompatible config: Qwen agent with native server
    incompatible_agent = AgentConfig(
        name="incompatible",
        role="assistant",
        description="Incompatible agent",
        system_prompt="You are a helpful assistant.",
        llm_model="qwen-max",  # No native MCP
        mcp_servers=["native_server"],  # Native server - incompatible!
        enabled=True,
    )

    mcp_configs = {
        "native_server": minimal_config.mcp_servers["native_server"]
    }

    # Should raise ValueError
    with pytest.raises(ValueError, match="does not support native MCP"):
        validate_agent_config(
            incompatible_agent,
            minimal_config.llm,
            mcp_configs
        )


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
