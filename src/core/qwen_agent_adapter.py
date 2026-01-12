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
Qwen Agent SDK Adapter.

Wraps the existing BaseAgent class to conform to the IAgentAdapter interface.
"""

from typing import Any, AsyncIterator, Dict, List, Optional

from loguru import logger

from agents.base_agent import BaseAgent
from core.agent_adapter import IAgentAdapter, AgentSDKType, ReasoningStep


class QwenAgentAdapter(IAgentAdapter):
    """
    Adapter for Qwen Agent SDK.

    Wraps the existing BaseAgent class which extends Qwen Agent's Assistant.
    This provides backward compatibility while conforming to the unified interface.
    """

    def __init__(
        self,
        config: Any,
        llm: Any = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        mcp_bridge: Any = None
    ):
        """
        Initialize the Qwen Agent adapter.

        Args:
            config: Agent configuration
            llm: LLM instance
            tools: List of tools from MCP Bridge
            mcp_bridge: MCP Bridge instance (unused in Qwen, kept for interface)
        """
        self._config = config
        self._agent = BaseAgent(
            config=config,
            llm=llm,
            tools=tools or []
        )
        logger.info(f"[{config.name}] Created QwenAgentAdapter")

    async def run_async(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        **kwargs
    ) -> List[Any]:
        """Run the agent asynchronously."""
        return await self._agent.run_async(prompt, session_id=session_id, **kwargs)

    async def run_with_reasoning(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        max_iterations: int = 20,
        **kwargs
    ) -> List[ReasoningStep]:
        """
        Run the agent with continuous reasoning.

        Converts BaseAgent's reasoning steps to the unified ReasoningStep format.
        """
        raw_steps = await self._agent.run_with_reasoning(
            prompt,
            session_id=session_id,
            max_iterations=max_iterations,
            **kwargs
        )

        # Convert to ReasoningStep format
        reasoning_steps = []
        for step in raw_steps:
            reasoning_steps.append(ReasoningStep(
                type=step.get("type", "thought"),
                content=step.get("content", ""),
                tool_name=step.get("tool_name"),
                iteration=step.get("iteration"),
                timestamp=step.get("timestamp"),
                metadata={"sdk": "qwen"}
            ))

        return reasoning_steps

    async def run_with_reasoning_stream(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        max_iterations: int = 20,
        **kwargs
    ) -> AsyncIterator[ReasoningStep]:
        """Run the agent with continuous reasoning - streaming."""
        async for step in self._agent.run_with_reasoning_stream(
            prompt,
            session_id=session_id,
            max_iterations=max_iterations,
            **kwargs
        ):
            yield ReasoningStep(
                type=step.get("type", "thought"),
                content=step.get("content", ""),
                tool_name=step.get("tool_name"),
                iteration=step.get("iteration"),
                timestamp=step.get("timestamp"),
                metadata={"sdk": "qwen"}
            )

    async def run_async_stream(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Run the agent with streaming output.

        Since Qwen Agent SDK may not have native token-level streaming,
        this implementation uses a fallback strategy that yields
        the complete response at the end, but maintains the async
        iterator interface for compatibility.

        Future enhancement: Hook into LLM callbacks for true streaming.
        """
        logger.debug(f"[{self.name}] Running agent with streaming (fallback mode)")

        # Run the agent and get the complete response
        response = await self.run_async(prompt, session_id=session_id, **kwargs)

        # Extract and yield content chunks
        for msg in response:
            if isinstance(msg, dict):
                content = msg.get("content", "")
            elif hasattr(msg, "content"):
                content = msg.content or ""
            else:
                content = str(msg)

            if content:
                # For a better streaming experience, split by sentences
                # This gives a pseudo-streaming effect
                chunks = self._split_content_for_streaming(content)
                for chunk in chunks:
                    yield chunk

    def _split_content_for_streaming(self, content: str) -> List[str]:
        """
        Split content into smaller chunks for pseudo-streaming effect.

        Splits by sentence boundaries to provide more granular updates
        while keeping content coherent.
        """
        import re

        # Split by sentence-ending punctuation followed by space or end
        # This preserves paragraph structure
        chunks = re.split(r'([.!?。！？]\s+|$)', content)

        # Re-attach punctuation to the chunks
        result = []
        current = ""
        for i, chunk in enumerate(chunks):
            if chunk:
                current += chunk
                # If we hit a sentence ending or the last chunk, yield it
                if i < len(chunks) - 1 and re.match(r'[.!?。！？]\s*$', chunk):
                    result.append(current)
                    current = ""
                elif i == len(chunks) - 1:
                    result.append(current)

        return [c for c in result if c.strip()]

    def get_history(self) -> List[Dict[str, str]]:
        """Get the current message history."""
        return self._agent.get_history_dict()

    def clear_history(self) -> None:
        """Clear the message history."""
        self._agent.clear_history()

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        return self._agent.get_stats()

    def get_sdk_type(self) -> AgentSDKType:
        """Get the SDK type."""
        return AgentSDKType.QWEN

    @property
    def supports_computer_use(self) -> bool:
        """Qwen SDK does not support Computer Use."""
        return False

    @property
    def supports_extended_thinking(self) -> bool:
        """Qwen SDK does not support Extended Thinking."""
        return False

    async def use_mcp_session(self, session: Any) -> None:
        """
        Qwen Agent SDK does not support native MCP.

        This method is called by AgentManager but should not be used
        for Qwen-based agents. Tools should be provided via the
        function call wrapper instead.
        """
        logger.warning(
            f"[{self.name}] Qwen Agent SDK does not support native MCP. "
            f"Use MCPFunctionCallWrapper instead to provide tools in function call format."
        )

    @property
    def name(self) -> str:
        """Get agent name."""
        return self._agent.name

    @property
    def role(self) -> str:
        """Get agent role."""
        return self._agent.role

    @property
    def description(self) -> str:
        """Get agent description."""
        return self._agent.description

    def chat(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Chat interface compatible with Gradio ChatInterface."""
        return self._agent.chat(message, history, **kwargs)

    def __repr__(self) -> str:
        """String representation."""
        return f"QwenAgentAdapter(name={self.name}, sdk=qwen)"


__all__ = ["QwenAgentAdapter"]
