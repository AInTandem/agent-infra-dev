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
Dual SDK Agent Architecture

Provides a unified interface for both Qwen Agent SDK and Claude Agent SDK,
allowing agents to choose the appropriate SDK based on their requirements.
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field


class AgentSDKType(str, Enum):
    """Supported Agent SDK types."""
    QWEN = "qwen"
    CLAUDE = "claude"


class ReasoningStep(BaseModel):
    """
    Represents a single step in the agent's reasoning process.

    Attributes:
        type: Step type (thought, tool_use, tool_result, final_answer, error)
        content: The content of the step
        tool_name: Tool name (for tool_use/tool_result steps)
        iteration: Iteration number
        timestamp: Unix timestamp when the step was generated
        metadata: Additional metadata (SDK-specific)
    """
    type: str
    content: str
    tool_name: Optional[str] = None
    iteration: Optional[int] = None
    timestamp: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class IAgentAdapter(ABC):
    """
    Unified interface for Agent adapters.

    All agent adapters must implement this interface, ensuring
    consistent behavior regardless of the underlying SDK.
    """

    @abstractmethod
    async def run_async(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        **kwargs
    ) -> List[Any]:
        """
        Run the agent asynchronously with a prompt.

        Args:
            prompt: User prompt
            session_id: Optional session ID for multi-turn conversations
            **kwargs: Additional arguments for the agent

        Returns:
            List of response messages (SDK-agnostic format)
        """
        pass

    @abstractmethod
    async def run_with_reasoning(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        max_iterations: int = 20,
        **kwargs
    ) -> List[ReasoningStep]:
        """
        Run the agent with continuous reasoning (multi-step tool use).

        Args:
            prompt: User prompt
            session_id: Optional session ID
            max_iterations: Maximum reasoning iterations
            **kwargs: Additional arguments

        Returns:
            List of reasoning steps
        """
        pass

    @abstractmethod
    async def run_with_reasoning_stream(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        max_iterations: int = 20,
        **kwargs
    ) -> AsyncIterator[ReasoningStep]:
        """
        Run the agent with continuous reasoning - streaming version.

        Args:
            prompt: User prompt
            session_id: Optional session ID
            max_iterations: Maximum reasoning iterations
            **kwargs: Additional arguments

        Yields:
            ReasoningStep objects as they are generated
        """
        pass

    @abstractmethod
    def get_history(self) -> List[Dict[str, str]]:
        """Get the current message history."""
        pass

    @abstractmethod
    def clear_history(self) -> None:
        """Clear the message history."""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        pass

    @abstractmethod
    def get_sdk_type(self) -> AgentSDKType:
        """Get the SDK type used by this adapter."""
        pass

    @property
    @abstractmethod
    def supports_computer_use(self) -> bool:
        """Check if this adapter supports Computer Use (Claude SDK only)."""
        pass

    @property
    @abstractmethod
    def supports_extended_thinking(self) -> bool:
        """Check if this adapter supports Extended Thinking (Claude SDK only)."""
        pass


class AgentAdapterFactory:
    """
    Factory for creating agent adapters based on SDK type.

    This factory determines which SDK to use based on:
    1. Agent configuration (sdk field)
    2. Model requirements (e.g., Computer Use requires Claude SDK)
    3. Default fallback
    """

    @staticmethod
    def create_adapter(
        config: Any,
        llm: Any = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        mcp_bridge: Any = None
    ) -> IAgentAdapter:
        """
        Create an agent adapter based on configuration.

        Args:
            config: Agent configuration (AgentConfig or similar)
            llm: LLM instance
            tools: List of tools from MCP Bridge
            mcp_bridge: MCP Bridge instance

        Returns:
            IAgentAdapter instance (Qwen or Claude)
        """
        # Get SDK type from config
        sdk_type = getattr(config, 'sdk', None)

        # Auto-detect SDK based on model if not specified
        if not sdk_type:
            model_name = getattr(config, 'llm_model', '')
            if 'claude' in model_name.lower():
                sdk_type = AgentSDKType.CLAUDE
            else:
                sdk_type = AgentSDKType.QWEN

        # Check for Computer Use requirement
        requires_computer_use = getattr(config, 'computer_use_enabled', False)
        if requires_computer_use and sdk_type != AgentSDKType.CLAUDE:
            from loguru import logger
            logger.warning(
                f"[{config.name}] Computer Use requested but SDK is '{sdk_type}'. "
                f"Computer Use requires Claude SDK. Switching to Claude SDK."
            )
            sdk_type = AgentSDKType.CLAUDE

        # Import adapters
        if sdk_type == AgentSDKType.CLAUDE:
            from .claude_agent_adapter import ClaudeAgentAdapter
            return ClaudeAgentAdapter(
                config=config,
                llm=llm,
                tools=tools,
                mcp_bridge=mcp_bridge
            )
        else:  # Default to Qwen
            from .qwen_agent_adapter import QwenAgentAdapter
            return QwenAgentAdapter(
                config=config,
                llm=llm,
                tools=tools,
                mcp_bridge=mcp_bridge
            )


__all__ = [
    "AgentSDKType",
    "IAgentAdapter",
    "AgentAdapterFactory",
    "ReasoningStep",
]
