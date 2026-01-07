"""
Agent Manager implementation.

Manages multiple agent instances with MCP tool integration.
"""

import asyncio
import hashlib
from typing import Any, Dict, List, Optional

from loguru import logger

from agents.base_agent import BaseAgent
from core.config import AgentConfig, ConfigManager
from core.mcp_bridge import MCPBridge


class AgentManager:
    """
    Manager for multiple AI agents.

    Handles:
    - Agent creation from configuration
    - MCP tool assignment
    - Agent lifecycle management
    - Agent lookup and routing
    - Response caching (optional)
    """

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        mcp_bridge: Optional[MCPBridge] = None,
        cache_adapter: Optional[Any] = None,
    ):
        """
        Initialize the AgentManager.

        Args:
            config_manager: Configuration manager instance
            mcp_bridge: MCP Bridge for tool integration
            cache_adapter: Optional CacheAdapter for response caching
        """
        self.config_manager = config_manager or ConfigManager()
        self.mcp_bridge = mcp_bridge
        self.cache_adapter = cache_adapter

        self._agents: Dict[str, BaseAgent] = {}
        self._llm_registry: Dict[str, Any] = {}
        self._is_initialized = False

        # Cache configuration
        self._cache_ttl = 600  # 10 minutes default TTL
        self._use_cache = cache_adapter is not None

    async def initialize(
        self,
        mcp_bridge: Optional[MCPBridge] = None,
    ) -> None:
        """
        Initialize the AgentManager.

        Loads agent configurations and creates agent instances.

        Args:
            mcp_bridge: Optional MCP Bridge instance
        """
        if self._is_initialized:
            logger.warning("AgentManager already initialized")
            return

        logger.info("Initializing AgentManager...")

        # Set MCP Bridge if provided
        if mcp_bridge:
            self.mcp_bridge = mcp_bridge

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

    async def _create_agent(self, config: AgentConfig) -> BaseAgent:
        """
        Create an agent from configuration.

        Args:
            config: Agent configuration

        Returns:
            Created BaseAgent instance
        """
        logger.info(f"Creating agent: {config.name}")

        # Get tools for this agent
        tools = []
        if self.mcp_bridge and config.mcp_servers:
            tools = self.mcp_bridge.get_tools_for_agent(config.mcp_servers)
            logger.debug(f"[{config.name}] Loaded {len(tools)} tools from {config.mcp_servers}")

        # Get LLM instance
        llm = self._get_llm_for_agent(config)

        # Create the agent
        agent = BaseAgent(
            config=config,
            llm=llm,
            tools=tools,
        )

        # Store the agent
        self._agents[config.name] = agent

        logger.info(f"[{config.name}] Agent created with {len(tools)} tools")
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

        # For now, return None to use Qwen Agent's default
        # In production, you would create proper LLM instances here
        # based on the model_name and configuration

        llm_config = self.config_manager.llm

        # Check if we have an OpenAI-compatible LLM
        if llm_config.provider == "openai_compatible":
            # Import Qwen Agent's OpenAI-compatible LLM
            try:
                from qwen_agent.llm.schema import DEFAULT_MODEL
                from qwen_agent.llm.base import BaseChatModel

                # For simplicity, we'll let Qwen Agent use defaults
                # In production, you would configure the LLM properly
                logger.debug(f"[{config.name}] Using OpenAI-compatible LLM: {model_name}")
                return None  # Let Qwen Agent use default

            except ImportError:
                logger.warning(f"Failed to import OpenAI-compatible LLM, using default")

        return None

    async def create_agent(
        self,
        name: str,
        role: str,
        system_prompt: str,
        mcp_servers: Optional[List[str]] = None,
        llm_model: Optional[str] = None,
        description: str = "",
    ) -> BaseAgent:
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
            Created BaseAgent instance
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

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """
        Get an agent by name.

        Args:
            name: Agent name

        Returns:
            BaseAgent instance or None
        """
        return self._agents.get(name)

    def list_agents(self) -> List[str]:
        """Get list of all agent names."""
        return list(self._agents.keys())

    def get_all_agents(self) -> Dict[str, BaseAgent]:
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
            return agent.to_dict()
        return None

    def get_all_agent_info(self) -> List[Dict[str, Any]]:
        """Get information about all agents."""
        return [agent.to_dict() for agent in self._agents.values()]

    async def reload_agent(self, name: str) -> Optional[BaseAgent]:
        """
        Reload an agent from configuration.

        Args:
            name: Agent name

        Returns:
            Reloaded BaseAgent instance or None
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
    mcp_bridge: Optional[MCPBridge] = None,
    cache_adapter: Optional[Any] = None,
    force_refresh: bool = False
) -> AgentManager:
    """
    Get the global agent manager instance.

    Args:
        config_manager: Optional configuration manager
        mcp_bridge: Optional MCP Bridge
        cache_adapter: Optional CacheAdapter for response caching
        force_refresh: Force re-initialization

    Returns:
        AgentManager instance
    """
    global _agent_manager

    if _agent_manager is None or force_refresh:
        _agent_manager = AgentManager(config_manager, cache_adapter=cache_adapter)
        await _agent_manager.initialize(mcp_bridge)

    return _agent_manager
