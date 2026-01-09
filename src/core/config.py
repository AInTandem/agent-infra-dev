# Copyright (c) 2025 AInTandem
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Configuration management with Pydantic models.

Provides type-safe configuration loading with environment variable substitution.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger
from pydantic import BaseModel, Field, field_validator


def substitute_env(value: str) -> str:
    """
    Substitute environment variables in string values.

    Supports ${VAR_NAME} and $VAR_NAME syntax.

    Args:
        value: String potentially containing environment variable references

    Returns:
        String with environment variables replaced
    """
    if not isinstance(value, str):
        return value

    # Match ${VAR_NAME} or $VAR_NAME
    pattern = r'\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)'

    def replacer(match):
        var_name = match.group(1) or match.group(2)
        return os.environ.get(var_name, match.group(0))

    return re.sub(pattern, replacer, value)


def substitute_env_with_tracking(value: str) -> Tuple[str, List[Tuple[str, str]]]:
    """
    Substitute environment variables in string values and track substitutions.

    Args:
        value: String value potentially containing environment variables

    Returns:
        Tuple of (substituted_value, list of (var_name, var_value) substitutions)
    """
    substitutions = []

    def replacer(match: re.Match) -> str:
        var_name = match.group(1) or match.group(2)
        var_value = os.environ.get(var_name, match.group(0))
        substitutions.append((var_name, var_value))
        return var_value

    pattern = r'\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}|\$([a-zA-Z_][a-zA-Z0-9_]*)'
    result = re.sub(pattern, replacer, value)
    return result, substitutions


def substitute_env_recursive(data: Any) -> Any:
    """
    Recursively substitute environment variables in data structures.

    Args:
        data: Any data structure (dict, list, str, etc.)

    Returns:
        Data with environment variables substituted
    """
    if isinstance(data, dict):
        return {k: substitute_env_recursive(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [substitute_env_recursive(item) for item in data]
    elif isinstance(data, str):
        return substitute_env(data)
    else:
        return data


def substitute_env_recursive_with_tracking(data: Any, path: str = "") -> Tuple[Any, List[Tuple[str, str, str]]]:
    """
    Recursively substitute environment variables with tracking.

    Args:
        data: Any data structure (dict, list, str, etc.)
        path: Current path in the data structure (for logging)

    Returns:
        Tuple of (substituted_data, list of (path, var_name, var_value) substitutions)
    """
    all_substitutions = []

    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            new_path = f"{path}.{key}" if path else key
            new_value, subs = substitute_env_recursive_with_tracking(value, new_path)
            result[key] = new_value
            all_substitutions.extend(subs)
        return result, all_substitutions

    elif isinstance(data, list):
        result = []
        for i, item in enumerate(data):
            new_path = f"{path}[{i}]"
            new_value, subs = substitute_env_recursive_with_tracking(item, new_path)
            result.append(new_value)
            all_substitutions.extend(subs)
        return result, all_substitutions

    elif isinstance(data, str):
        substituted, subs = substitute_env_with_tracking(data)
        for var_name, var_value in subs:
            all_substitutions.append((path, var_name, var_value))
        return substituted, all_substitutions

    else:
        return data, all_substitutions


# ============================================================================
# LLM Configuration Models
# ============================================================================

class LLMProviderConfig(BaseModel):
    """Configuration for an LLM provider."""
    description: str = ""
    api_key: str = ""
    base_url: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMProviderConfig":
        """Create LLMProviderConfig from dictionary with env var substitution."""
        data = substitute_env_recursive(data)
        return cls(**data)


class LLMModelConfig(BaseModel):
    """Configuration for a specific LLM model."""
    name: str
    provider: str
    description: str = ""
    max_tokens: int = 4096
    supports_streaming: bool = True
    supports_function_calling: bool = True
    # Optional override fields
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class LLMGenerationConfig(BaseModel):
    """LLM generation parameters."""
    temperature: float = 0.7
    top_p: float = 0.9
    max_retries: int = 3
    timeout: int = 60

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if not 0 <= v <= 2:
            raise ValueError("temperature must be between 0 and 2")
        return v


class LLMConfig(BaseModel):
    """LLM configuration with provider-model hierarchy."""
    providers: Dict[str, LLMProviderConfig] = Field(default_factory=dict)
    default_model: str = "Qwen/Qwen3-7B-Instruct"
    models: List[LLMModelConfig] = Field(default_factory=list)
    generation: LLMGenerationConfig = Field(default_factory=LLMGenerationConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMConfig":
        """Create LLMConfig from dictionary with env var substitution."""
        data = substitute_env_recursive(data)

        # Handle providers dict
        providers_data = data.get("providers", {})
        providers = {}
        for provider_name, provider_config in providers_data.items():
            providers[provider_name] = LLMProviderConfig.from_dict(provider_config)

        # Handle models list
        models_data = data.get("models", [])
        models = [LLMModelConfig(**model) for model in models_data]

        # Handle generation config
        generation_data = data.get("generation", {})
        generation = LLMGenerationConfig(**generation_data) if generation_data else LLMGenerationConfig()

        return cls(
            providers=providers,
            default_model=data.get("default_model", "Qwen/Qwen3-7B-Instruct"),
            models=models,
            generation=generation,
        )


# ============================================================================
# MCP Server Configuration Models
# ============================================================================

class HealthCheckConfig(BaseModel):
    """Health check configuration for MCP servers."""
    enabled: bool = True
    interval: int = 60  # seconds


class MCPSSEConfig(BaseModel):
    """Configuration for SSE transport."""
    url: str
    headers: Dict[str, str] = Field(default_factory=dict)


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server."""
    name: str
    description: str = ""
    transport: str = Field(default="stdio", pattern="^(stdio|sse)$")
    # Stdio transport fields
    command: Optional[str] = None
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    # SSE transport fields
    sse: Optional[MCPSSEConfig] = None
    # Common fields
    timeout: int = 30
    enabled: bool = True
    health_check: HealthCheckConfig = Field(default_factory=HealthCheckConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPServerConfig":
        """Create MCPServerConfig from dictionary with env var substitution."""
        server_name = data.get("name", "unknown")

        # Use tracking version to log environment variable substitutions
        substituted_data, substitutions = substitute_env_recursive_with_tracking(data)

        if substitutions:
            logger.debug(f"[MCP Server: {server_name}] Environment variable substitutions:")
            for path, var_name, var_value in substitutions:
                # Mask sensitive values
                display_value = "***" if any(keyword in var_name.upper() for keyword in ["KEY", "TOKEN", "PASSWORD", "SECRET"]) else var_value
                logger.debug(f"  {path} → ${{{var_name}}} = \"{display_value}\"")
        else:
            logger.debug(f"[MCP Server: {server_name}] No environment variables to substitute")

        # Create the config instance
        config = cls(**substituted_data)

        # Display the actual command that will be executed
        command_parts = [config.command] + config.args
        # Mask sensitive values in args for display
        display_parts = []
        for part in command_parts:
            # Check if this part is a sensitive value (contains actual sensitive data)
            is_sensitive = False
            for path, var_name, var_value in substitutions:
                if part == var_value and any(keyword in var_name.upper() for keyword in ["KEY", "TOKEN", "PASSWORD", "SECRET"]):
                    is_sensitive = True
                    break
            display_parts.append("***" if is_sensitive else part)

        logger.debug(f"[MCP Server: {server_name}] Command: {' '.join(display_parts)}")

        return config


# ============================================================================
# Agent Configuration Models
# ============================================================================

class AgentConfig(BaseModel):
    """Configuration for a single agent."""
    name: str
    role: str
    description: str = ""
    system_prompt: str
    mcp_servers: List[str] = Field(default_factory=list)
    llm_model: str
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentConfig":
        """Create AgentConfig from dictionary."""
        return cls(**data)


# ============================================================================
# Application Configuration Models
# ============================================================================

class ServerConfig(BaseModel):
    """Server configuration."""
    host: str = "0.0.0.0"
    api_port: int = 8000
    gui_port: int = 7860
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:7860"])


class StorageConfig(BaseModel):
    """Storage configuration."""
    base_dir: str = "./storage"
    tasks_dir: str = "./storage/tasks"
    logs_dir: str = "./storage/logs"
    max_log_size: int = 10485760  # 10MB
    log_rotation: int = 5


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    format: str = "rich"
    console: bool = True
    file: bool = True


class SchedulerConfig(BaseModel):
    """Task scheduler configuration."""
    enabled: bool = True
    timezone: str = "Asia/Shanghai"
    max_concurrent_tasks: int = 5
    task_persistence: bool = True


class SandboxConfig(BaseModel):
    """Sandbox configuration."""
    enabled: bool = False
    isolation_level: str = "basic"
    allowed_paths: List[str] = Field(default_factory=lambda: ["./storage", "./config"])
    blocked_commands: List[str] = Field(default_factory=lambda: ["rm -rf", "dd", "mkfs"])


class AgentSystemConfig(BaseModel):
    """Agent system configuration."""
    max_history_length: int = 100
    history_ttl: int = 86400  # 24 hours
    default_timeout: int = 300  # 5 minutes
    enable_streaming: bool = True


class AppConfig(BaseModel):
    """Main application configuration."""
    name: str = "AInTandem Agent MCP Scheduler"
    version: str = "0.1.0"
    debug: bool = False
    server: ServerConfig = Field(default_factory=ServerConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)
    agent: AgentSystemConfig = Field(default_factory=AgentSystemConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        """Create AppConfig from dictionary."""
        return cls(**data)


# ============================================================================
# Configuration Manager
# ============================================================================

class ConfigManager:
    """
    Central configuration manager.

    Loads and manages all configuration files with environment variable substitution.
    """

    def __init__(self, config_dir: str = "config"):
        """
        Initialize the configuration manager.

        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self._app_config: Optional[AppConfig] = None
        self._llm_config: Optional[LLMConfig] = None
        self._agents: Dict[str, AgentConfig] = {}
        self._mcp_servers: Dict[str, MCPServerConfig] = {}
        self._storage_config: Optional[Dict[str, Any]] = None

    def load_all(self) -> None:
        """Load all configuration files."""
        self.load_app_config()
        self.load_llm_config()
        self.load_agents()
        self.load_mcp_servers()
        self.load_storage_config()

    def load_app_config(self) -> AppConfig:
        """Load application configuration from app.yaml."""
        import yaml

        config_file = self.config_dir / "app.yaml"
        if not config_file.exists():
            # Return default config if file doesn't exist
            self._app_config = AppConfig()
            return self._app_config

        with open(config_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        self._app_config = AppConfig.from_dict(data.get("app", data))
        return self._app_config

    def load_llm_config(self) -> LLMConfig:
        """Load LLM configuration from llm.yaml."""
        import yaml

        config_file = self.config_dir / "llm.yaml"
        if not config_file.exists():
            # Return default config
            self._llm_config = LLMConfig()
            return self._llm_config

        with open(config_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        self._llm_config = LLMConfig.from_dict(data.get("llm", data))
        return self._llm_config

    def load_agents(self) -> Dict[str, AgentConfig]:
        """Load agent configurations from agents.yaml."""
        import yaml

        config_file = self.config_dir / "agents.yaml"
        if not config_file.exists():
            return self._agents

        with open(config_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        agents_data = data.get("agents", [])
        for agent_data in agents_data:
            config = AgentConfig.from_dict(agent_data)
            self._agents[config.name] = config

        return self._agents

    def load_mcp_servers(self) -> Dict[str, MCPServerConfig]:
        """Load MCP server configurations from mcp_servers.yaml."""
        import yaml

        config_file = self.config_dir / "mcp_servers.yaml"
        if not config_file.exists():
            return self._mcp_servers

        with open(config_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        servers_data = data.get("mcp_servers", [])
        for server_data in servers_data:
            config = MCPServerConfig.from_dict(server_data)
            self._mcp_servers[config.name] = config

        return self._mcp_servers

    def load_storage_config(self) -> Dict[str, Any]:
        """Load storage configuration from storage.yaml."""
        import yaml

        config_file = self.config_dir / "storage.yaml"
        if not config_file.exists():
            # Return default config (file-based storage)
            self._storage_config = {
                "storage": {
                    "type": "file"
                }
            }
            return self._storage_config

        with open(config_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # Substitute environment variables
        data = substitute_env_recursive(data)

        self._storage_config = data
        return self._storage_config

    # ========================================================================
    # Getter methods
    # ========================================================================

    @property
    def app(self) -> AppConfig:
        """Get application configuration."""
        if self._app_config is None:
            self.load_app_config()
        return self._app_config

    @property
    def llm(self) -> LLMConfig:
        """Get LLM configuration."""
        if self._llm_config is None:
            self.load_llm_config()
        return self._llm_config

    @property
    def agents(self) -> Dict[str, AgentConfig]:
        """Get all agent configurations."""
        if not self._agents:
            self.load_agents()
        return self._agents

    @property
    def mcp_servers(self) -> Dict[str, MCPServerConfig]:
        """Get all MCP server configurations."""
        if not self._mcp_servers:
            self.load_mcp_servers()
        return self._mcp_servers

    @property
    def storage(self) -> Dict[str, Any]:
        """Get storage configuration."""
        if self._storage_config is None:
            self.load_storage_config()
        return self._storage_config

    def get_agent(self, name: str) -> Optional[AgentConfig]:
        """Get a specific agent configuration by name."""
        return self._agents.get(name)

    def get_mcp_server(self, name: str) -> Optional[MCPServerConfig]:
        """Get a specific MCP server configuration by name."""
        return self._mcp_servers.get(name)

    def get_enabled_agents(self) -> Dict[str, AgentConfig]:
        """Get all enabled agent configurations."""
        return {name: cfg for name, cfg in self._agents.items() if cfg.enabled}

    def get_enabled_mcp_servers(self) -> Dict[str, MCPServerConfig]:
        """Get all enabled MCP server configurations."""
        return {name: cfg for name, cfg in self._mcp_servers.items() if cfg.enabled}

    def reload(self) -> None:
        """Reload all configuration files."""
        self._app_config = None
        self._llm_config = None
        self._agents.clear()
        self._mcp_servers.clear()
        self._storage_config = None
        self.load_all()


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config(config_dir: str = "config") -> ConfigManager:
    """
    Get the global configuration manager instance.

    Args:
        config_dir: Directory containing configuration files

    Returns:
        ConfigManager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_dir)
        _config_manager.load_all()
    return _config_manager
