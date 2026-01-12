#!/usr/bin/env python3
"""
Tests for configuration validation functions.

Tests the enhanced validation functionality added in Phase 5.
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import (
    AgentConfig,
    LLMConfig,
    LLMProviderConfig,
    LLMModelConfig,
    MCPServerConfig,
    validate_agent_config,
    validate_agent_mcp_compatibility,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_llm_config():
    """Create a sample LLM configuration."""
    return LLMConfig(
        default_model="claude-3-5-sonnet-20241022",
        providers={
            "claude": LLMProviderConfig(
                description="Anthropic Claude",
                api_key="${ANTHROPIC_API_KEY}",
                base_url="https://api.anthropic.com",
                sdk="claude",
                supports_mcp=True,
                supports_computer_use=True,
            ),
            "openai": LLMProviderConfig(
                description="OpenAI GPT",
                api_key="${OPENAI_API_KEY}",
                base_url="https://api.openai.com/v1",
                sdk="openai",
                supports_mcp=False,
                supports_computer_use=False,
            ),
            "qwen": LLMProviderConfig(
                description="Qwen",
                api_key="${DASHSCOPE_API_KEY}",
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
                name="gpt-4o",
                provider="openai",
                supports_mcp=False,
            ),
            LLMModelConfig(
                name="qwen-max",
                provider="qwen",
                supports_mcp=False,
            ),
        ],
    )


@pytest.fixture
def sample_mcp_configs():
    """Create sample MCP server configurations."""
    return {
        "native_server": MCPServerConfig(
            name="native_server",
            description="Native MCP server",
            transport="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            enabled=True,
            function_call_wrapper=False,  # Native MCP only
        ),
        "wrapper_server": MCPServerConfig(
            name="wrapper_server",
            description="Function call wrapper server",
            transport="stdio",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            enabled=True,
            function_call_wrapper=True,  # Function call wrapper
        ),
    }


# ============================================================================
# Test validate_agent_mcp_compatibility
# ============================================================================

def test_validate_mcp_native_with_native_server(sample_llm_config, sample_mcp_configs):
    """Test that native MCP model with native MCP server is valid."""
    agent_config = AgentConfig(
        name="test_agent",
        role="assistant",
        description="Test agent",
        system_prompt="You are a helpful assistant.",
        llm_model="claude-3-5-sonnet-20241022",  # Native MCP
        mcp_servers=["native_server"],  # Native server
        enabled=True,
    )

    # Should not raise
    validate_agent_mcp_compatibility(agent_config, sample_llm_config, sample_mcp_configs)


def test_validate_mcp_native_with_wrapper_server(sample_llm_config, sample_mcp_configs):
    """Test that native MCP model with wrapper server logs warning (not an error)."""
    agent_config = AgentConfig(
        name="test_agent",
        role="assistant",
        description="Test agent",
        system_prompt="You are a helpful assistant.",
        llm_model="claude-3-5-sonnet-20241022",  # Native MCP
        mcp_servers=["wrapper_server"],  # Wrapper server (should warn, not error)
        enabled=True,
    )

    # Should not raise (logs warning instead)
    validate_agent_mcp_compatibility(agent_config, sample_llm_config, sample_mcp_configs)


def test_validate_non_mcp_with_native_server_raises(sample_llm_config, sample_mcp_configs):
    """Test that non-MCP model with native MCP server raises error."""
    agent_config = AgentConfig(
        name="test_agent",
        role="assistant",
        description="Test agent",
        system_prompt="You are a helpful assistant.",
        llm_model="qwen-max",  # No native MCP
        mcp_servers=["native_server"],  # Native server (incompatible!)
        enabled=True,
    )

    # Should raise ValueError
    with pytest.raises(ValueError, match="does not support native MCP"):
        validate_agent_mcp_compatibility(agent_config, sample_llm_config, sample_mcp_configs)


def test_validate_non_mcp_with_wrapper_server(sample_llm_config, sample_mcp_configs):
    """Test that non-MCP model with wrapper server is valid."""
    agent_config = AgentConfig(
        name="test_agent",
        role="assistant",
        description="Test agent",
        system_prompt="You are a helpful assistant.",
        llm_model="qwen-max",  # No native MCP
        mcp_servers=["wrapper_server"],  # Wrapper server (compatible)
        enabled=True,
    )

    # Should not raise
    validate_agent_mcp_compatibility(agent_config, sample_llm_config, sample_mcp_configs)


# ============================================================================
# Test validate_agent_config
# ============================================================================

def test_validate_agent_config_valid(sample_llm_config, sample_mcp_configs):
    """Test validation with valid configuration."""
    agent_config = AgentConfig(
        name="test_agent",
        role="assistant",
        description="Test agent",
        system_prompt="You are a helpful assistant.",
        llm_model="claude-3-5-sonnet-20241022",
        mcp_servers=["native_server"],
        enabled=True,
    )

    warnings = validate_agent_config(agent_config, sample_llm_config, sample_mcp_configs)
    assert isinstance(warnings, list)
    # No warnings expected for valid config


def test_validate_agent_config_missing_model(sample_llm_config, sample_mcp_configs):
    """Test validation with non-existent model."""
    agent_config = AgentConfig(
        name="test_agent",
        role="assistant",
        description="Test agent",
        system_prompt="You are a helpful assistant.",
        llm_model="non-existent-model",
        mcp_servers=[],
        enabled=True,
    )

    with pytest.raises(ValueError, match="not found in LLM configuration"):
        validate_agent_config(agent_config, sample_llm_config, sample_mcp_configs)


def test_validate_agent_config_duplicate_servers(sample_llm_config, sample_mcp_configs):
    """Test validation detects duplicate MCP servers."""
    agent_config = AgentConfig(
        name="test_agent",
        role="assistant",
        description="Test agent",
        system_prompt="You are a helpful assistant.",
        llm_model="claude-3-5-sonnet-20241022",
        mcp_servers=["native_server", "native_server"],  # Duplicate
        enabled=True,
    )

    warnings = validate_agent_config(agent_config, sample_llm_config, sample_mcp_configs)
    assert len(warnings) > 0
    assert any("duplicate" in w.lower() for w in warnings)


def test_validate_agent_config_computer_use_with_non_claude(sample_llm_config, sample_mcp_configs):
    """Test that Computer Use with non-Claude SDK raises error."""
    # Add computer_use_enabled attribute dynamically
    agent_config = AgentConfig(
        name="test_agent",
        role="assistant",
        description="Test agent",
        system_prompt="You are a helpful assistant.",
        llm_model="qwen-max",  # Non-Claude
        mcp_servers=[],
        enabled=True,
    )
    # Add computer_use_enabled dynamically for testing
    setattr(agent_config, 'computer_use_enabled', True)

    with pytest.raises(ValueError, match="Computer Use.*only supported with Claude SDK"):
        validate_agent_config(agent_config, sample_llm_config, sample_mcp_configs)


def test_validate_agent_config_extended_thinking_with_non_claude(sample_llm_config, sample_mcp_configs):
    """Test that Extended Thinking with non-Claude SDK produces warning."""
    agent_config = AgentConfig(
        name="test_agent",
        role="assistant",
        description="Test agent",
        system_prompt="You are a helpful assistant.",
        llm_model="qwen-max",  # Non-Claude
        mcp_servers=[],
        enabled=True,
    )
    # Add extended_thinking_enabled dynamically for testing
    setattr(agent_config, 'extended_thinking_enabled', True)

    warnings = validate_agent_config(agent_config, sample_llm_config, sample_mcp_configs)
    assert len(warnings) > 0
    assert any("extended thinking" in w.lower() for w in warnings)


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
