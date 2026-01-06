#!/usr/bin/env python3
"""
Test script for configuration system.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import (
    ConfigManager,
    AppConfig,
    LLMConfig,
    AgentConfig,
    MCPServerConfig,
    substitute_env,
    substitute_env_recursive,
)


def test_env_substitution():
    """Test environment variable substitution."""
    import os

    # Set test environment variables
    os.environ["TEST_VAR"] = "test_value"
    os.environ["TEST_NESTED"] = "nested_value"

    # Test basic substitution
    assert substitute_env("${TEST_VAR}") == "test_value"
    assert substitute_env("$TEST_VAR") == "test_value"
    assert substitute_env("prefix_${TEST_VAR}_suffix") == "prefix_test_value_suffix"

    # Test recursive substitution
    data = {
        "key1": "${TEST_VAR}",
        "key2": ["$TEST_VAR", "${TEST_NESTED}"],
        "key3": {"nested": "$TEST_NESTED"}
    }
    result = substitute_env_recursive(data)
    assert result["key1"] == "test_value"
    assert result["key2"][0] == "test_value"
    assert result["key2"][1] == "nested_value"
    assert result["key3"]["nested"] == "nested_value"

    # Clean up
    del os.environ["TEST_VAR"]
    del os.environ["TEST_NESTED"]

    print("✓ Environment variable substitution tests passed")


def test_config_manager():
    """Test configuration manager."""
    config = ConfigManager()

    # Load all configurations
    config.load_all()

    # Test app config
    app_cfg = config.app
    assert isinstance(app_cfg, AppConfig)
    assert app_cfg.name == "Qwen Agent MCP Scheduler"
    print(f"✓ App config loaded: {app_cfg.name} v{app_cfg.version}")

    # Test LLM config
    llm_cfg = config.llm
    assert isinstance(llm_cfg, LLMConfig)
    assert llm_cfg.provider == "openai_compatible"
    print(f"✓ LLM config loaded: {llm_cfg.provider}, model: {llm_cfg.default_model}")

    # Test agents
    agents = config.agents
    assert len(agents) > 0
    assert "researcher" in agents
    assert "developer" in agents
    print(f"✓ Agent configs loaded: {list(agents.keys())}")

    # Test MCP servers
    mcp_servers = config.mcp_servers
    assert len(mcp_servers) > 0
    assert "filesystem" in mcp_servers
    assert "web-search" in mcp_servers
    print(f"✓ MCP server configs loaded: {list(mcp_servers.keys())}")

    # Test enabled agents
    enabled_agents = config.get_enabled_agents()
    print(f"✓ Enabled agents: {[name for name, cfg in enabled_agents.items() if cfg.enabled]}")

    # Test enabled MCP servers
    enabled_servers = config.get_enabled_mcp_servers()
    print(f"✓ Enabled MCP servers: {[name for name, cfg in enabled_servers.items() if cfg.enabled]}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Configuration System Tests")
    print("=" * 60)
    print()

    test_env_substitution()
    print()
    test_config_manager()

    print()
    print("=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    main()
