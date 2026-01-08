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
Configuration Editor for AInTandem Agent MCP Scheduler.

Provides GUI for editing all configuration files with both form-based
and YAML editor modes.
"""

import copy
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr
from loguru import logger
import yaml


class ConfigEditor:
    """
    Configuration editor with dual-mode editing (Form and YAML).

    Features:
    - Form-based editing for all configurations
    - YAML editor mode for advanced users
    - Batch save functionality
    - Configuration validation
    - Auto-backup before save
    - Restart prompt after save
    """

    def __init__(self, config_manager, config_dir: str = "config"):
        """
        Initialize the configuration editor.

        Args:
            config_manager: ConfigManager instance
            config_dir: Configuration directory path
        """
        self.config_manager = config_manager
        self.config_dir = Path(config_dir)

        # Track pending changes
        self._pending_changes: Dict[str, Dict] = {}
        self._original_configs: Dict[str, Any] = {}

        # Load current configurations
        self._load_all_configs()

        # Backup directory
        self.backup_dir = self.config_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)

    def _load_all_configs(self):
        """Load all configuration files."""
        self.configs = {
            "llm": self._load_yaml("llm.yaml"),
            "agents": self._load_yaml("agents.yaml"),
            "mcp_servers": self._load_yaml("mcp_servers.yaml"),
            "storage": self._load_yaml("storage.yaml"),
            "app": self._load_yaml("app.yaml"),
        }
        # Store originals for change tracking
        self._original_configs = {
            k: copy.deepcopy(v) for k, v in self.configs.items()
        }

    def _load_yaml(self, filename: str) -> Dict:
        """Load YAML configuration file."""
        filepath = self.config_dir / filename
        if not filepath.exists():
            return {}

        with open(filepath, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _save_yaml(self, filename: str, data: Dict):
        """Save YAML configuration file."""
        filepath = self.config_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    def _backup_config(self, filename: str):
        """Create backup of configuration file."""
        filepath = self.config_dir / filename
        if filepath.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"{filename}.{timestamp}.bak"
            shutil.copy2(filepath, backup_path)
            logger.info(f"Backed up {filename} to {backup_path}")

    # ============================================================================
    # LLM Configuration
    # ============================================================================

    # ------------------------------------------------------------------------
    # Provider Management
    # ------------------------------------------------------------------------

    def get_llm_providers_list(self) -> List[List]:
        """Get LLM providers list for dataframe display."""
        llm_config = self.configs.get("llm", {}).get("llm", {})
        providers = llm_config.get("providers", {})

        return [
            [
                provider_name,
                provider_config.get("description", ""),
                "✅" if provider_config.get("api_key") else "❌",
                provider_config.get("base_url", ""),
            ]
            for provider_name, provider_config in providers.items()
        ]

    def get_llm_provider_names(self) -> List[str]:
        """Get list of LLM provider names."""
        llm_config = self.configs.get("llm", {}).get("llm", {})
        providers = llm_config.get("providers", {})
        return list(providers.keys())

    def get_llm_provider_config(self, provider_name: str) -> Dict:
        """Get LLM provider configuration for editing."""
        llm_config = self.configs.get("llm", {}).get("llm", {})
        providers = llm_config.get("providers", {})
        return providers.get(provider_name, {})

    def update_llm_provider(
        self,
        name: str,
        description: str,
        api_key: str,
        base_url: str,
    ) -> str:
        """Update or add LLM provider."""
        llm_config = self.configs.get("llm", {})
        if "llm" not in llm_config:
            llm_config["llm"] = {}
        if "providers" not in llm_config["llm"]:
            llm_config["llm"]["providers"] = {}

        provider_config = {
            "description": description,
            "api_key": api_key,
            "base_url": base_url,
        }

        llm_config["llm"]["providers"][name] = provider_config
        self.configs["llm"] = llm_config
        self._pending_changes["llm"] = llm_config

        return f"✅ Provider '{name}' 已更新（尚未儲存）"

    def delete_llm_provider(self, provider_name: str) -> str:
        """Delete LLM provider."""
        llm_config = self.configs.get("llm", {})
        if "llm" not in llm_config:
            llm_config["llm"] = {}

        providers = llm_config["llm"].get("providers", {})

        # Check if any model is using this provider
        models = llm_config["llm"].get("models", [])
        models_using_provider = [m for m in models if m.get("provider") == provider_name]
        if models_using_provider:
            return f"❌ 無法刪除 provider '{provider_name}'，有 {len(models_using_provider)} 個模型正在使用"

        if provider_name not in providers:
            return f"❌ Provider '{provider_name}' 不存在"

        del providers[provider_name]
        llm_config["llm"]["providers"] = providers
        self.configs["llm"] = llm_config
        self._pending_changes["llm"] = llm_config

        return f"✅ Provider '{provider_name}' 已刪除（尚未儲存）"

    # ------------------------------------------------------------------------
    # Model Management
    # ------------------------------------------------------------------------

    def get_llm_models_list(self) -> List[List]:
        """Get LLM models list for dataframe display."""
        llm_config = self.configs.get("llm", {}).get("llm", {})
        models = llm_config.get("models", [])
        default_model = llm_config.get("default_model", "")

        return [
            [
                "⭐" if model.get("name") == default_model else "",
                model.get("name", ""),
                model.get("provider", ""),
                model.get("description", ""),
                model.get("max_tokens", 4096),
                "🔑" if model.get("api_key") else "",
                "🔗" if model.get("base_url") else "",
                "✅" if model.get("supports_function_calling", False) else "❌",
                "✅" if model.get("supports_streaming", False) else "❌",
            ]
            for model in models
        ]

    def get_llm_model_names(self) -> List[str]:
        """Get list of LLM model names."""
        llm_config = self.configs.get("llm", {}).get("llm", {})
        models = llm_config.get("models", [])
        return [model.get("name", "") for model in models]

    def get_llm_model_names_with_provider(self) -> List[str]:
        """Get list of LLM model names with provider info."""
        llm_config = self.configs.get("llm", {}).get("llm", {})
        models = llm_config.get("models", [])
        return [f"{model.get('name', '')} / {model.get('provider', '')}" for model in models]

    def get_llm_model_config(self, model_name: str) -> Dict:
        """Get LLM model configuration for editing."""
        llm_config = self.configs.get("llm", {}).get("llm", {})
        models = llm_config.get("models", [])
        for model in models:
            if model.get("name") == model_name:
                return model
        return {}

    def get_llm_default_model(self) -> str:
        """Get current default model name."""
        llm_config = self.configs.get("llm", {}).get("llm", {})
        return llm_config.get("default_model", "")

    def get_llm_config_state(self) -> Dict:
        """Get current LLM configuration state for form."""
        llm_config = self.configs.get("llm", {}).get("llm", {})
        return {
            "llm_default_model": llm_config.get("default_model", "gpt-4o"),
            "llm_temperature": llm_config.get("generation", {}).get("temperature", 0.7),
            "llm_top_p": llm_config.get("generation", {}).get("top_p", 0.9),
            "llm_max_retries": llm_config.get("generation", {}).get("max_retries", 3),
            "llm_timeout": llm_config.get("generation", {}).get("timeout", 60),
        }

    def update_llm_generation_config(
        self,
        default_model: str,
        temperature: float,
        top_p: float,
        max_retries: int,
        timeout: int,
    ) -> Tuple[str, str]:
        """Update LLM generation configuration."""
        llm_config = self.configs.get("llm", {})
        if "llm" not in llm_config:
            llm_config["llm"] = {}

        llm_config["llm"]["default_model"] = default_model
        llm_config["llm"]["generation"] = {
            "temperature": temperature,
            "top_p": top_p,
            "max_retries": max_retries,
            "timeout": timeout,
        }

        self.configs["llm"] = llm_config
        self._pending_changes["llm"] = llm_config

        yaml_preview = yaml.dump(llm_config, default_flow_style=False, allow_unicode=True)
        return "✅ Generation 配置已更新（尚未儲存）", yaml_preview

    def add_llm_model(
        self,
        name: str,
        provider: str,
        description: str,
        max_tokens: int,
        supports_function_calling: bool,
        supports_streaming: bool,
        api_key: str,
        base_url: str,
    ) -> str:
        """Add new LLM model."""
        llm_config = self.configs.get("llm", {})
        if "llm" not in llm_config:
            llm_config["llm"] = {}

        models_list = llm_config.get("llm", {}).get("models", [])

        # Check if model already exists
        for model in models_list:
            if model.get("name") == name:
                return f"❌ Model '{name}' 已存在"

        new_model = {
            "name": name,
            "provider": provider,
            "description": description,
            "max_tokens": max_tokens,
            "supports_function_calling": supports_function_calling,
            "supports_streaming": supports_streaming,
        }

        # Add optional fields
        if api_key:
            new_model["api_key"] = api_key
        if base_url:
            new_model["base_url"] = base_url

        models_list.append(new_model)
        llm_config["llm"]["models"] = models_list
        self.configs["llm"] = llm_config
        self._pending_changes["llm"] = llm_config

        return f"✅ Model '{name}' 已新增（尚未儲存）"

    def update_llm_model(
        self,
        old_name: str,
        name: str,
        provider: str,
        description: str,
        max_tokens: int,
        supports_function_calling: bool,
        supports_streaming: bool,
        api_key: str,
        base_url: str,
    ) -> str:
        """Update existing LLM model."""
        llm_config = self.configs.get("llm", {})
        if "llm" not in llm_config:
            llm_config["llm"] = {}

        models_list = llm_config.get("llm", {}).get("models", [])

        for i, model in enumerate(models_list):
            if model.get("name") == old_name:
                updated_model = {
                    "name": name,
                    "provider": provider,
                    "description": description,
                    "max_tokens": max_tokens,
                    "supports_function_calling": supports_function_calling,
                    "supports_streaming": supports_streaming,
                }

                # Preserve optional fields if provided
                if api_key:
                    updated_model["api_key"] = api_key
                elif "api_key" in model:
                    updated_model["api_key"] = model["api_key"]

                if base_url:
                    updated_model["base_url"] = base_url
                elif "base_url" in model:
                    updated_model["base_url"] = model["base_url"]

                models_list[i] = updated_model
                break

        llm_config["llm"]["models"] = models_list
        self.configs["llm"] = llm_config
        self._pending_changes["llm"] = llm_config

        return f"✅ Model '{old_name}' 已更新為 '{name}'（尚未儲存）"

    def delete_llm_model(self, model_name: str) -> str:
        """Delete LLM model."""
        llm_config = self.configs.get("llm", {})
        if "llm" not in llm_config:
            llm_config["llm"] = {}

        models_list = llm_config.get("llm", {}).get("models", [])

        # Check if it's the default model
        default_model = llm_config.get("llm", {}).get("default_model", "")
        if model_name == default_model:
            return f"❌ 無法刪除預設模型 '{model_name}'，請先更換預設模型"

        models_list = [model for model in models_list if model.get("name") != model_name]
        llm_config["llm"]["models"] = models_list
        self.configs["llm"] = llm_config
        self._pending_changes["llm"] = llm_config

        return f"✅ Model '{model_name}' 已刪除（尚未儲存）"

    def set_default_model(self, model_name: str) -> str:
        """Set default LLM model."""
        llm_config = self.configs.get("llm", {})
        if "llm" not in llm_config:
            llm_config["llm"] = {}

        # Verify model exists
        models_list = llm_config.get("llm", {}).get("models", [])
        model_names = [m.get("name") for m in models_list]
        if model_name not in model_names:
            return f"❌ Model '{model_name}' 不存在"

        llm_config["llm"]["default_model"] = model_name
        self.configs["llm"] = llm_config
        self._pending_changes["llm"] = llm_config

        return f"✅ 已將 '{model_name}' 設為預設模型（尚未儲存）"

    def get_llm_yaml(self) -> str:
        """Get LLM configuration as YAML."""
        return yaml.dump(self.configs.get("llm", {}), default_flow_style=False, allow_unicode=True)

    def update_llm_from_yaml(self, yaml_content: str) -> str:
        """Update LLM configuration from YAML content."""
        try:
            new_config = yaml.safe_load(yaml_content)
            if not new_config or "llm" not in new_config:
                return "❌ YAML 格式錯誤：缺少 'llm' 區塊"

            self.configs["llm"] = new_config
            self._pending_changes["llm"] = new_config
            return "✅ LLM 配置已從 YAML 更新（尚未儲存）"
        except Exception as e:
            return f"❌ YAML 解析錯誤：{str(e)}"

    # ============================================================================
    # Agents Configuration
    # ============================================================================

    def get_agents_list(self) -> List[List]:
        """Get agents list for dataframe display."""
        agents = self.configs.get("agents", {}).get("agents", [])
        return [
            [
                agent.get("name", ""),
                agent.get("role", ""),
                agent.get("llm_model", ""),
                "✅" if agent.get("enabled", True) else "❌",
                ", ".join(agent.get("mcp_servers", [])),
            ]
            for agent in agents
        ]

    def get_agent_names(self) -> List[str]:
        """Get list of agent names."""
        agents = self.configs.get("agents", {}).get("agents", [])
        return [agent.get("name", "") for agent in agents]

    def get_agent_config(self, agent_name: str) -> Dict:
        """Get agent configuration for editing."""
        agents = self.configs.get("agents", {}).get("agents", [])
        for agent in agents:
            if agent.get("name") == agent_name:
                return agent
        return {}

    def add_agent(
        self,
        name: str,
        role: str,
        description: str,
        system_prompt: str,
        llm_model: str,
        mcp_servers: List[str],
        enabled: bool,
    ) -> str:
        """Add new agent."""
        agents_config = self.configs.get("agents", {})
        agents_list = agents_config.get("agents", [])

        # Check if agent already exists
        for agent in agents_list:
            if agent.get("name") == name:
                return f"❌ Agent '{name}' 已存在"

        new_agent = {
            "name": name,
            "role": role,
            "description": description,
            "system_prompt": system_prompt,
            "mcp_servers": mcp_servers,
            "llm_model": llm_model,
            "enabled": enabled,
        }

        agents_list.append(new_agent)
        agents_config["agents"] = agents_list
        self.configs["agents"] = agents_config
        self._pending_changes["agents"] = agents_config

        return f"✅ Agent '{name}' 已新增（尚未儲存）"

    def update_agent(
        self,
        old_name: str,
        name: str,
        role: str,
        description: str,
        system_prompt: str,
        llm_model: str,
        mcp_servers: List[str],
        enabled: bool,
    ) -> str:
        """Update existing agent."""
        agents_config = self.configs.get("agents", {})
        agents_list = agents_config.get("agents", [])

        for i, agent in enumerate(agents_list):
            if agent.get("name") == old_name:
                agents_list[i] = {
                    "name": name,
                    "role": role,
                    "description": description,
                    "system_prompt": system_prompt,
                    "mcp_servers": mcp_servers,
                    "llm_model": llm_model,
                    "enabled": enabled,
                }
                break

        agents_config["agents"] = agents_list
        self.configs["agents"] = agents_config
        self._pending_changes["agents"] = agents_config

        return f"✅ Agent '{old_name}' 已更新為 '{name}'（尚未儲存）"

    def delete_agent(self, agent_name: str) -> str:
        """Delete agent."""
        agents_config = self.configs.get("agents", {})
        agents_list = agents_config.get("agents", [])

        agents_list = [agent for agent in agents_list if agent.get("name") != agent_name]
        agents_config["agents"] = agents_list
        self.configs["agents"] = agents_config
        self._pending_changes["agents"] = agents_config

        return f"✅ Agent '{agent_name}' 已刪除（尚未儲存）"

    def get_agents_yaml(self) -> str:
        """Get agents configuration as YAML."""
        return yaml.dump(self.configs.get("agents", {}), default_flow_style=False, allow_unicode=True)

    def update_agents_from_yaml(self, yaml_content: str) -> str:
        """Update agents configuration from YAML content."""
        try:
            new_config = yaml.safe_load(yaml_content)
            if not new_config or "agents" not in new_config:
                return "❌ YAML 格式錯誤：缺少 'agents' 區塊"

            self.configs["agents"] = new_config
            self._pending_changes["agents"] = new_config
            return "✅ Agents 配置已從 YAML 更新（尚未儲存）"
        except Exception as e:
            return f"❌ YAML 解析錯誤：{str(e)}"

    # ============================================================================
    # MCP Servers Configuration
    # ============================================================================

    def get_mcp_servers_list(self) -> List[List]:
        """Get MCP servers list for dataframe display."""
        servers = self.configs.get("mcp_servers", {}).get("mcp_servers", [])
        return [
            [
                server.get("name", ""),
                server.get("description", ""),
                server.get("command", ""),
                "✅" if server.get("enabled", True) else "❌",
            ]
            for server in servers
        ]

    def get_mcp_server_names(self) -> List[str]:
        """Get list of MCP server names."""
        servers = self.configs.get("mcp_servers", {}).get("mcp_servers", [])
        return [server.get("name", "") for server in servers]

    def get_mcp_server_config(self, server_name: str) -> Dict:
        """Get MCP server configuration for editing."""
        servers = self.configs.get("mcp_servers", {}).get("mcp_servers", [])
        for server in servers:
            if server.get("name") == server_name:
                return server
        return {}

    def add_mcp_server(
        self,
        name: str,
        description: str,
        command: str,
        args: str,
        env: str,
        timeout: int,
        enabled: bool,
        health_check_enabled: bool,
        health_check_interval: int,
    ) -> str:
        """Add new MCP server."""
        mcp_config = self.configs.get("mcp_servers", {})
        servers_list = mcp_config.get("mcp_servers", [])

        # Check if server already exists
        for server in servers_list:
            if server.get("name") == name:
                return f"❌ MCP Server '{name}' 已存在"

        # Parse args and env
        try:
            args_list = [arg.strip() for arg in args.split("\n") if arg.strip()] if args else []
            env_dict = {}
            if env:
                for line in env.split("\n"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        env_dict[key.strip()] = value.strip()
        except Exception as e:
            return f"❌ 參數格式錯誤：{str(e)}"

        new_server = {
            "name": name,
            "description": description,
            "command": command,
            "args": args_list,
            "env": env_dict,
            "timeout": timeout,
            "enabled": enabled,
            "health_check": {
                "enabled": health_check_enabled,
                "interval": health_check_interval,
            },
        }

        servers_list.append(new_server)
        mcp_config["mcp_servers"] = servers_list
        self.configs["mcp_servers"] = mcp_config
        self._pending_changes["mcp_servers"] = mcp_config

        return f"✅ MCP Server '{name}' 已新增（尚未儲存）"

    def update_mcp_server(
        self,
        old_name: str,
        name: str,
        description: str,
        command: str,
        args: str,
        env: str,
        timeout: int,
        enabled: bool,
        health_check_enabled: bool,
        health_check_interval: int,
    ) -> str:
        """Update existing MCP server."""
        mcp_config = self.configs.get("mcp_servers", {})
        servers_list = mcp_config.get("mcp_servers", [])

        # Parse args and env
        try:
            args_list = [arg.strip() for arg in args.split("\n") if arg.strip()] if args else []
            env_dict = {}
            if env:
                for line in env.split("\n"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        env_dict[key.strip()] = value.strip()
        except Exception as e:
            return f"❌ 參數格式錯誤：{str(e)}"

        for i, server in enumerate(servers_list):
            if server.get("name") == old_name:
                servers_list[i] = {
                    "name": name,
                    "description": description,
                    "command": command,
                    "args": args_list,
                    "env": env_dict,
                    "timeout": timeout,
                    "enabled": enabled,
                    "health_check": {
                        "enabled": health_check_enabled,
                        "interval": health_check_interval,
                    },
                }
                break

        mcp_config["mcp_servers"] = servers_list
        self.configs["mcp_servers"] = mcp_config
        self._pending_changes["mcp_servers"] = mcp_config

        return f"✅ MCP Server '{old_name}' 已更新為 '{name}'（尚未儲存）"

    def delete_mcp_server(self, server_name: str) -> str:
        """Delete MCP server."""
        mcp_config = self.configs.get("mcp_servers", {})
        servers_list = mcp_config.get("mcp_servers", [])

        servers_list = [server for server in servers_list if server.get("name") != server_name]
        mcp_config["mcp_servers"] = servers_list
        self.configs["mcp_servers"] = mcp_config
        self._pending_changes["mcp_servers"] = mcp_config

        return f"✅ MCP Server '{server_name}' 已刪除（尚未儲存）"

    def get_mcp_servers_yaml(self) -> str:
        """Get MCP servers configuration as YAML."""
        return yaml.dump(self.configs.get("mcp_servers", {}), default_flow_style=False, allow_unicode=True)

    def update_mcp_servers_from_yaml(self, yaml_content: str) -> str:
        """Update MCP servers configuration from YAML content."""
        try:
            new_config = yaml.safe_load(yaml_content)
            if not new_config or "mcp_servers" not in new_config:
                return "❌ YAML 格式錯誤：缺少 'mcp_servers' 區塊"

            self.configs["mcp_servers"] = new_config
            self._pending_changes["mcp_servers"] = new_config
            return "✅ MCP Servers 配置已從 YAML 更新（尚未儲存）"
        except Exception as e:
            return f"❌ YAML 解析錯誤：{str(e)}"

    # ============================================================================
    # Storage Configuration
    # ============================================================================

    def get_storage_config_state(self) -> Dict:
        """Get current storage configuration state for form."""
        storage_config = self.configs.get("storage", {})
        storage_type = storage_config.get("storage", {}).get("type", "sqlite")

        return {
            "storage_type": storage_type,
            "sqlite_path": storage_config.get("storage", {}).get("sqlite", {}).get("path", "./storage/data.db"),
            "sqlite_pool_size": storage_config.get("storage", {}).get("sqlite", {}).get("pool_size", 5),
            "sqlite_enable_wal": storage_config.get("storage", {}).get("sqlite", {}).get("enable_wal", True),
            "postgres_host": storage_config.get("storage", {}).get("postgresql", {}).get("host", ""),
            "postgres_port": storage_config.get("storage", {}).get("postgresql", {}).get("port", 5432),
            "postgres_database": storage_config.get("storage", {}).get("postgresql", {}).get("database", ""),
            "postgres_user": storage_config.get("storage", {}).get("postgresql", {}).get("user", ""),
            "cache_type": storage_config.get("cache", {}).get("type", "none"),
            "redis_host": storage_config.get("cache", {}).get("redis", {}).get("host", ""),
            "redis_port": storage_config.get("cache", {}).get("redis", {}).get("port", 6379),
        }

    def update_storage_config(
        self,
        storage_type: str,
        sqlite_path: str,
        sqlite_pool_size: int,
        sqlite_enable_wal: bool,
        postgres_host: str,
        postgres_port: int,
        postgres_database: str,
        postgres_user: str,
        cache_type: str,
        redis_host: str,
        redis_port: int,
    ) -> Tuple[str, str]:
        """Update storage configuration."""
        new_config = {"storage": {}, "cache": {}, "vector_store": {"type": "none"}}

        # Storage configuration
        new_config["storage"]["type"] = storage_type

        if storage_type == "sqlite":
            new_config["storage"]["sqlite"] = {
                "path": sqlite_path,
                "pool_size": sqlite_pool_size,
                "enable_wal": sqlite_enable_wal,
                "journal_mode": "WAL" if sqlite_enable_wal else "DELETE",
            }
        elif storage_type == "postgresql":
            new_config["storage"]["postgresql"] = {
                "host": postgres_host or "${DB_HOST}",
                "port": postgres_port,
                "database": postgres_database or "qwen_agent",
                "user": postgres_user or "${DB_USER}",
                "password": "${DB_PASSWORD}",
                "pool_size": 20,
            }

        # Cache configuration
        new_config["cache"]["type"] = cache_type
        if cache_type == "redis":
            new_config["cache"]["redis"] = {
                "host": redis_host or "${REDIS_HOST}",
                "port": redis_port,
                "db": 0,
            }

        self.configs["storage"] = new_config
        self._pending_changes["storage"] = new_config

        yaml_preview = yaml.dump(new_config, default_flow_style=False, allow_unicode=True)
        return "✅ Storage 配置已更新（尚未儲存）", yaml_preview

    def get_storage_yaml(self) -> str:
        """Get storage configuration as YAML."""
        return yaml.dump(self.configs.get("storage", {}), default_flow_style=False, allow_unicode=True)

    def update_storage_from_yaml(self, yaml_content: str) -> str:
        """Update storage configuration from YAML content."""
        try:
            new_config = yaml.safe_load(yaml_content)
            if not new_config:
                return "❌ YAML 格式錯誤：空配置"

            self.configs["storage"] = new_config
            self._pending_changes["storage"] = new_config
            return "✅ Storage 配置已從 YAML 更新（尚未儲存）"
        except Exception as e:
            return f"❌ YAML 解析錯誤：{str(e)}"

    # ============================================================================
    # App Configuration
    # ============================================================================

    def get_app_config_state(self) -> Dict:
        """Get current app configuration state for form."""
        app_config = self.configs.get("app", {})

        return {
            "app_name": app_config.get("app", {}).get("name", "AInTandem Agent MCP Scheduler"),
            "server_host": app_config.get("server", {}).get("host", "0.0.0.0"),
            "api_port": app_config.get("server", {}).get("api_port", 8000),
            "gui_port": app_config.get("server", {}).get("gui_port", 7860),
            "log_level": app_config.get("logging", {}).get("level", "INFO"),
            "scheduler_timezone": app_config.get("scheduler", {}).get("timezone", "Asia/Shanghai"),
            "max_concurrent_tasks": app_config.get("scheduler", {}).get("max_concurrent_tasks", 5),
        }

    def update_app_config(
        self,
        app_name: str,
        server_host: str,
        api_port: int,
        gui_port: int,
        log_level: str,
        scheduler_timezone: str,
        max_concurrent_tasks: int,
    ) -> Tuple[str, str]:
        """Update app configuration."""
        new_config = {
            "app": {
                "name": app_name,
                "version": "0.1.0",
                "debug": False,
            },
            "server": {
                "host": server_host,
                "api_port": api_port,
                "gui_port": gui_port,
                "cors_origins": ["http://localhost:7860", "http://127.0.0.1:7860"],
            },
            "storage": {
                "base_dir": "./storage",
                "tasks_dir": "./storage/tasks",
                "logs_dir": "./storage/logs",
            },
            "logging": {
                "level": log_level,
                "format": "rich",
                "console": True,
                "file": True,
            },
            "scheduler": {
                "enabled": True,
                "timezone": scheduler_timezone,
                "max_concurrent_tasks": max_concurrent_tasks,
                "task_persistence": True,
            },
            "sandbox": {
                "enabled": False,
                "isolation_level": "basic",
            },
            "agent": {
                "max_history_length": 100,
                "history_ttl": 86400,
                "default_timeout": 300,
                "enable_streaming": True,
            },
        }

        self.configs["app"] = new_config
        self._pending_changes["app"] = new_config

        yaml_preview = yaml.dump(new_config, default_flow_style=False, allow_unicode=True)
        return "✅ App 配置已更新（尚未儲存）", yaml_preview

    def get_app_yaml(self) -> str:
        """Get app configuration as YAML."""
        return yaml.dump(self.configs.get("app", {}), default_flow_style=False, allow_unicode=True)

    def update_app_from_yaml(self, yaml_content: str) -> str:
        """Update app configuration from YAML content."""
        try:
            new_config = yaml.safe_load(yaml_content)
            if not new_config:
                return "❌ YAML 格式錯誤：空配置"

            self.configs["app"] = new_config
            self._pending_changes["app"] = new_config
            return "✅ App 配置已從 YAML 更新（尚未儲存）"
        except Exception as e:
            return f"❌ YAML 解析錯誤：{str(e)}"

    # ============================================================================
    # Batch Operations
    # ============================================================================

    def get_pending_changes_count(self) -> int:
        """Get number of pending changes."""
        return len(self._pending_changes)

    def get_pending_changes_list(self) -> List[str]:
        """Get list of pending changes."""
        return list(self._pending_changes.keys())

    def save_all_changes(self) -> Tuple[str, str]:
        """
        Save all pending changes to files.

        Returns:
            (status_message, restart_message)
        """
        if not self._pending_changes:
            return "ℹ️ 沒有待儲存的變更", ""

        saved_files = []

        try:
            # Save each pending change
            for config_type, config_data in self._pending_changes.items():
                filename_map = {
                    "llm": "llm.yaml",
                    "agents": "agents.yaml",
                    "mcp_servers": "mcp_servers.yaml",
                    "storage": "storage.yaml",
                    "app": "app.yaml",
                }

                filename = filename_map.get(config_type)
                if filename:
                    # Backup original
                    self._backup_config(filename)

                    # Save new config
                    self._save_yaml(filename, config_data)
                    saved_files.append(filename)

            # Clear pending changes
            self._pending_changes.clear()

            # Reload configs
            self._load_all_configs()

            status = f"✅ 已儲存 {len(saved_files)} 個配置檔案：{', '.join(saved_files)}"
            restart_msg = "⚠️ 配置變更需要重啟應用才能生效。是否要重啟？"

            return status, restart_msg

        except Exception as e:
            return f"❌ 儲存失敗：{str(e)}", ""

    def discard_pending_changes(self) -> str:
        """Discard all pending changes and reload from files."""
        discarded = list(self._pending_changes.keys())
        self._pending_changes.clear()
        self._load_all_configs()

        if discarded:
            return f"✅ 已放棄 {len(discarded)} 個配置的變更：{', '.join(discarded)}"
        return "ℹ️ 沒有待放棄的變更"

    def reload_configs(self) -> str:
        """Reload all configurations from files."""
        self._load_all_configs()
        return "✅ 配置已從檔案重新載入"
