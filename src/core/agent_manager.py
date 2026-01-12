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
Agent Manager implementation.

Manages multiple agent instances with MCP tool integration.
Supports dual SDK architecture (Qwen Agent SDK and Claude Agent SDK).
"""

import asyncio
import hashlib
from typing import Any, Dict, List, Optional

from loguru import logger

from core.agent_adapter import AgentAdapterFactory, IAgentAdapter
from core.config import AgentConfig, ConfigManager, validate_agent_mcp_compatibility
from core.mcp_manager import MCPManager


class AgentManager:
    """
    Manager for multiple AI agents.

    Handles:
    - Agent creation from configuration
    - MCP tool assignment via MCPManager (native MCP or function call wrapper)
    - Agent lifecycle management
    - Agent lookup and routing
    - Response caching (optional)
    - MCP compatibility validation
    """

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        mcp_manager: Optional[MCPManager] = None,
        cache_adapter: Optional[Any] = None,
    ):
        """
        Initialize the AgentManager.

        Args:
            config_manager: Configuration manager instance
            mcp_manager: MCP Manager for tool integration (native MCP or function call wrapper)
            cache_adapter: Optional CacheAdapter for response caching
        """
        self.config_manager = config_manager or ConfigManager()
        self.mcp_manager = mcp_manager
        self.cache_adapter = cache_adapter

        self._agents: Dict[str, IAgentAdapter] = {}  # Changed from BaseAgent to IAgentAdapter
        self._llm_registry: Dict[str, Any] = {}
        self._is_initialized = False

        # Cache configuration
        self._cache_ttl = 600  # 10 minutes default TTL
        self._use_cache = cache_adapter is not None

    async def initialize(
        self,
        mcp_manager: Optional[MCPManager] = None,
    ) -> None:
        """
        Initialize the AgentManager.

        Loads agent configurations and creates agent instances.

        Args:
            mcp_manager: Optional MCP Manager instance
        """
        if self._is_initialized:
            logger.warning("AgentManager already initialized")
            return

        logger.info("Initializing AgentManager...")

        # Set MCP Manager if provided
        if mcp_manager:
            self.mcp_manager = mcp_manager

        # Get agent configurations
        agent_configs = self.config_manager.get_enabled_agents()

        if not agent_configs:
            logger.warning("No enabled agents found in configuration")
            self._is_initialized = True
            return

        # Create agents
        created_count = 0
        for name, config in agent_configs.items():
            try:
                await self._create_agent(config)
                created_count += 1
            except Exception as e:
                logger.error(f"Failed to create agent {name}: {e}")

        self._is_initialized = True
        logger.info(f"AgentManager initialized with {created_count}/{len(agent_configs)} agents")

    async def _create_agent(self, config: AgentConfig) -> IAgentAdapter:
        """
        Create an agent from configuration using AgentAdapterFactory.

        The factory automatically selects the appropriate SDK (Qwen or Claude)
        based on the agent's configuration.

        For agents with native MCP support, this method also:
        - Validates agent-MCP compatibility
        - Passes MCP sessions directly to the agent

        Args:
            config: Agent configuration

        Returns:
            Created IAgentAdapter instance (Qwen or Claude)
        """
        logger.info(f"Creating agent: {config.name}")

        # Get LLM configuration
        llm_config = self.config_manager.llm

        # Validate agent-MCP compatibility if MCP servers are configured
        if config.mcp_servers and self.mcp_manager:
            try:
                # Get all MCP server configurations
                mcp_configs = {}
                for server_name in config.mcp_servers:
                    server_config = self.config_manager.get_mcp_server(server_name)
                    if server_config:
                        mcp_configs[server_name] = server_config

                validate_agent_mcp_compatibility(config, llm_config, mcp_configs)
                logger.debug(f"[{config.name}] MCP compatibility validated")
            except ValueError as e:
                logger.error(f"[{config.name}] MCP compatibility check failed: {e}")
                raise

        # Get tools for this agent (format depends on LLM MCP support)
        tools = []
        if self.mcp_manager and config.mcp_servers:
            tools = self.mcp_manager.get_tools_for_agent(config, llm_config)
            logger.debug(f"[{config.name}] Loaded {len(tools)} tools from {config.mcp_servers}")

        # Get LLM instance
        llm = self._get_llm_for_agent(config)

        # Use AgentAdapterFactory to create the appropriate adapter
        agent = AgentAdapterFactory.create_adapter(
            config=config,
            llm=llm,
            tools=tools,
            mcp_bridge=None  # No longer using old MCPBridge
        )

        # For native MCP models, pass MCP sessions directly to the agent
        if config.mcp_servers and self.mcp_manager:
            llm_supports_mcp = llm_config.get_model_mcp_support(config.llm_model)
            if llm_supports_mcp:
                logger.debug(f"[{config.name}] LLM supports native MCP, passing sessions")
                for server_name in config.mcp_servers:
                    session = await self.mcp_manager.get_mcp_session(server_name, config)
                    if session:
                        await agent.use_mcp_session(session)
                        logger.debug(
                            f"[{config.name}] Passed MCP session for '{server_name}'"
                        )

        # Store the agent
        self._agents[config.name] = agent

        sdk_type = agent.get_sdk_type()
        logger.info(f"[{config.name}] {sdk_type.value.upper()} agent created with {len(tools)} tools")
        return agent

    def _get_llm_for_agent(self, config: AgentConfig) -> Optional[Any]:
        """
        Get or create LLM instance for an agent.

        Args:
            config: Agent configuration

        Returns:
            LLM instance or None (will use default)
        """
        model_name = config.llm_model
        llm_config = self.config_manager.llm

        try:
            from qwen_agent.llm.oai import TextChatAtOAI

            # Find the model configuration
            model_config = None
            for model in llm_config.models:
                if model.name == model_name:
                    model_config = model
                    break

            if not model_config:
                logger.warning(f"[{config.name}] Model '{model_name}' not found in LLM config, using default")
                return None

            # Get provider configuration
            provider_name = model_config.provider
            provider_config = llm_config.providers.get(provider_name)

            if not provider_config:
                logger.warning(f"[{config.name}] Provider '{provider_name}' not found for model '{model_name}'")
                return None

            # Use model's override settings if available, otherwise use provider's settings
            api_key = model_config.api_key if model_config.api_key else provider_config.api_key
            base_url = model_config.base_url if model_config.base_url else provider_config.base_url

            # Handle environment variable substitution
            if api_key and api_key.startswith("${"):
                import os
                env_var = api_key[2:-1]  # Remove ${ and }
                api_key = os.environ.get(env_var, "")
                if not api_key:
                    logger.warning(f"[{config.name}] Environment variable {env_var} not set")
                    return None

            if not api_key:
                logger.warning(f"[{config.name}] No API key found for model '{model_name}'")
                return None

            if not base_url:
                logger.warning(f"[{config.name}] No base URL found for model '{model_name}'")
                return None

            logger.debug(f"[{config.name}] Using LLM: {model_name} via provider '{provider_name}'")

            # Create OpenAI-compatible client
            llm_cfg = {
                "model": model_name,
                "api_key": api_key,
                "base_url": base_url,
                "generate_config": llm_config.generation.dict() if hasattr(llm_config, 'generation') else {}
            }
            llm = TextChatAtOAI(cfg=llm_cfg)
            return llm

        except ImportError as e:
            logger.warning(f"[{config.name}] Failed to import LLM modules: {e}")
            return None
        except Exception as e:
            logger.warning(f"[{config.name}] Error configuring LLM: {e}")
            return None

        return None

    async def create_agent(
        self,
        name: str,
        role: str,
        system_prompt: str,
        mcp_servers: Optional[List[str]] = None,
        llm_model: Optional[str] = None,
        description: str = "",
    ) -> IAgentAdapter:
        """
        Dynamically create a new agent.

        Args:
            name: Agent name
            role: Agent role
            system_prompt: System prompt for the agent
            mcp_servers: List of MCP server names
            llm_model: LLM model name
            description: Agent description

        Returns:
            Created IAgentAdapter instance (Qwen or Claude)
        """
        logger.info(f"Creating agent dynamically: {name}")

        # Get default LLM model from config if not specified
        if not llm_model:
            llm_model = self.config_manager.llm.default_model

        # Create AgentConfig
        config = AgentConfig(
            name=name,
            role=role,
            description=description,
            system_prompt=system_prompt,
            mcp_servers=mcp_servers or [],
            llm_model=llm_model,
            enabled=True,
        )

        # Create the agent
        agent = await self._create_agent(config)

        return agent

    async def remove_agent(self, name: str) -> bool:
        """
        Remove an agent.

        Args:
            name: Agent name

        Returns:
            True if removed successfully
        """
        if name not in self._agents:
            logger.warning(f"Agent {name} not found")
            return False

        del self._agents[name]
        logger.info(f"Agent {name} removed")
        return True

    def get_agent(self, name: str) -> Optional[IAgentAdapter]:
        """
        Get an agent by name.

        Args:
            name: Agent name

        Returns:
            IAgentAdapter instance or None
        """
        return self._agents.get(name)

    def list_agents(self) -> List[str]:
        """Get list of all agent names."""
        return list(self._agents.keys())

    def get_all_agents(self) -> Dict[str, IAgentAdapter]:
        """Get all agents."""
        return self._agents.copy()

    def get_agent_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about an agent.

        Args:
            name: Agent name

        Returns:
            Agent information dictionary or None
        """
        agent = self._agents.get(name)
        if agent:
            return agent.to_dict() if hasattr(agent, 'to_dict') else agent.get_stats()
        return None

    def get_all_agent_info(self) -> List[Dict[str, Any]]:
        """Get information about all agents."""
        return [
            agent.to_dict() if hasattr(agent, 'to_dict') else agent.get_stats()
            for agent in self._agents.values()
        ]

    async def reload_agent(self, name: str) -> Optional[IAgentAdapter]:
        """
        Reload an agent from configuration.

        Args:
            name: Agent name

        Returns:
            Reloaded IAgentAdapter instance or None
        """
        config = self.config_manager.get_agent(name)
        if not config:
            logger.error(f"Agent {name} not found in configuration")
            return None

        # Remove existing agent
        if name in self._agents:
            del self._agents[name]

        # Create new agent
        return await self._create_agent(config)

    async def reload_all(self) -> int:
        """
        Reload all agents from configuration.

        Returns:
            Number of successfully reloaded agents
        """
        logger.info("Reloading all agents...")

        # Clear existing agents
        self._agents.clear()

        # Reload configuration
        self.config_manager.reload()

        # Recreate agents
        agent_configs = self.config_manager.get_enabled_agents()
        reloaded_count = 0

        for name, config in agent_configs.items():
            try:
                await self._create_agent(config)
                reloaded_count += 1
            except Exception as e:
                logger.error(f"Failed to reload agent {name}: {e}")

        logger.info(f"Reloaded {reloaded_count}/{len(agent_configs)} agents")
        return reloaded_count

    async def run_agent(
        self,
        name: str,
        prompt: str,
        use_cache: Optional[bool] = None,
        **kwargs
    ) -> List[Any]:
        """
        Run an agent with a prompt.

        Args:
            name: Agent name
            prompt: User prompt
            use_cache: Whether to use response cache (default: auto-detect)
            **kwargs: Additional arguments

        Returns:
            Agent response messages
        """
        agent = self.get_agent(name)
        if not agent:
            raise ValueError(f"Agent {name} not found")

        # Check cache if enabled
        if use_cache is None:
            use_cache = self._use_cache

        if use_cache and self.cache_adapter:
            # Generate cache key
            cache_key = self._generate_cache_key(name, prompt, kwargs)

            # Try to get from cache
            cached_response = await self.cache_adapter.get(cache_key)
            if cached_response is not None:
                logger.debug(f"[{name}] Cache hit for key: {cache_key[:16]}...")
                return cached_response

            logger.debug(f"[{name}] Cache miss for key: {cache_key[:16]}...")

        # Run the agent
        response = await agent.run_async(prompt, **kwargs)

        # Store in cache if enabled
        if use_cache and self.cache_adapter:
            cache_key = self._generate_cache_key(name, prompt, kwargs)
            from datetime import timedelta
            await self.cache_adapter.set(cache_key, response, timedelta(seconds=self._cache_ttl))
            logger.debug(f"[{name}] Cached response with key: {cache_key[:16]}...")

        return response

    def _generate_cache_key(self, agent_name: str, prompt: str, kwargs: Dict[str, Any]) -> str:
        """
        Generate a cache key for agent response.

        Args:
            agent_name: Name of the agent
            prompt: User prompt
            kwargs: Additional arguments

        Returns:
            Cache key string
        """
        # Create a deterministic hash of the inputs
        key_data = f"{agent_name}:{prompt}:{sorted(kwargs.items())}"
        hash_obj = hashlib.sha256(key_data.encode())
        return f"agent_response:{agent_name}:{hash_obj.hexdigest()[:16]}"

    def get_agent_stats(self, name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for an agent."""
        agent = self._agents.get(name)
        if agent:
            return agent.get_stats()
        return None

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all agents."""
        return {
            name: agent.get_stats()
            for name, agent in self._agents.items()
        }

    @property
    def is_initialized(self) -> bool:
        """Check if the manager is initialized."""
        return self._is_initialized

    @property
    def agent_count(self) -> int:
        """Get the number of agents."""
        return len(self._agents)

    @property
    def has_cache(self) -> bool:
        """Check if cache is available."""
        return self._use_cache and self.cache_adapter is not None

    async def clear_agent_cache(self, agent_name: Optional[str] = None) -> int:
        """
        Clear cached responses for an agent or all agents.

        Args:
            agent_name: Optional agent name. If None, clears all agent caches.

        Returns:
            Number of cache keys cleared
        """
        if not self.cache_adapter:
            logger.warning("No cache adapter available")
            return 0

        if agent_name:
            # Clear cache for specific agent
            pattern = f"agent_response:{agent_name}:*"
            count = await self.cache_adapter.clear_pattern(pattern)
            logger.info(f"Cleared {count} cached responses for agent: {agent_name}")
        else:
            # Clear all agent caches
            pattern = "agent_response:*"
            count = await self.cache_adapter.clear_pattern(pattern)
            logger.info(f"Cleared {count} cached responses for all agents")

        return count

    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Cache statistics dictionary
        """
        if not self.cache_adapter:
            return {"enabled": False}

        # Get all agent cache keys
        pattern = "agent_response:*"
        keys = await self.cache_adapter.keys(pattern)

        # Count by agent
        agent_counts: Dict[str, int] = {}
        for key in keys:
            # Extract agent name from key: "agent_response:agent_name:hash"
            parts = key.split(":")
            if len(parts) >= 3:
                agent = parts[2]
                agent_counts[agent] = agent_counts.get(agent, 0) + 1

        return {
            "enabled": True,
            "total_entries": len(keys),
            "by_agent": agent_counts,
        }

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"AgentManager("
            f"initialized={self._is_initialized}, "
            f"agents={self.agent_count})"
        )


# Global agent manager instance
_agent_manager: Optional[AgentManager] = None


async def get_agent_manager(
    config_manager: Optional[ConfigManager] = None,
    mcp_manager: Optional[MCPManager] = None,
    cache_adapter: Optional[Any] = None,
    force_refresh: bool = False
) -> AgentManager:
    """
    Get the global agent manager instance.

    Args:
        config_manager: Optional configuration manager
        mcp_manager: Optional MCP Manager for tool integration
        cache_adapter: Optional CacheAdapter for response caching
        force_refresh: Force re-initialization

    Returns:
        AgentManager instance
    """
    global _agent_manager

    if _agent_manager is None or force_refresh:
        _agent_manager = AgentManager(config_manager, cache_adapter=cache_adapter)
        await _agent_manager.initialize(mcp_manager)

    return _agent_manager
