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
Claude Agent SDK Adapter.

Provides integration with Claude API including:
- Computer Use capability
- Extended Thinking
- Native tool calling with MCP integration
"""

import asyncio
import json
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from loguru import logger

from core.agent_adapter import IAgentAdapter, AgentSDKType, ReasoningStep


class ClaudeAgentAdapter(IAgentAdapter):
    """
    Adapter for Claude API/SDK.

    Supports:
    - Computer Use (Claude 3.5 Sonnet)
    - Extended Thinking (Claude models with thinking)
    - MCP tool integration
    - Streaming responses
    """

    def __init__(
        self,
        config: Any,
        llm: Any = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        mcp_bridge: Any = None
    ):
        """
        Initialize the Claude Agent adapter.

        Args:
            config: Agent configuration
            llm: LLM instance (can be TextChatAtOAI configured for Claude)
            tools: List of tools from MCP Bridge
            mcp_bridge: MCP Bridge instance
        """
        self._config = config
        self._llm = llm
        self._tools = tools or []
        self._mcp_bridge = mcp_bridge

        # Parse agent properties
        self.name = config.name
        self.role = config.role
        self.description = config.description
        self.system_prompt = config.system_prompt
        self.mcp_servers = config.mcp_servers

        # Claude-specific settings
        self._computer_use_enabled = getattr(config, 'computer_use_enabled', False)
        self._extended_thinking_enabled = getattr(config, 'extended_thinking_enabled', False)

        # Message history
        self._history: List[Dict[str, Any]] = []
        self._max_history_length = 100

        # Statistics
        self._total_runs = 0

        # Initialize Claude client
        self._client = self._create_client()

        logger.info(
            f"[{self.name}] Created ClaudeAgentAdapter "
            f"(computer_use={self._computer_use_enabled}, "
            f"extended_thinking={self._extended_thinking_enabled})"
        )

    def _create_client(self) -> Any:
        """
        Create or get the Claude API client.

        Uses the provided LLM (TextChatAtOAI configured for Claude)
        or creates a new Anthropic client.
        """
        # If LLM is already configured, use it
        if self._llm:
            logger.debug(f"[{self.name}] Using provided LLM client")
            return self._llm

        # Otherwise, create Anthropic client directly
        try:
            from anthropic import Anthropic

            # Get API key from config or environment
            api_key = getattr(self._config, 'anthropic_api_key', None)
            if not api_key:
                import os
                api_key = os.environ.get("ANTHROPIC_API_KEY")

            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in config or environment")

            client = Anthropic(api_key=api_key)
            logger.debug(f"[{self.name}] Created Anthropic client")
            return client

        except ImportError:
            logger.warning(f"[{self.name}] anthropic package not installed")
            raise ImportError(
                "anthropic package required for Claude SDK. "
                "Install with: pip install anthropic"
            )

    def _convert_mcp_tools_to_claude_format(self) -> List[Dict[str, Any]]:
        """
        Convert MCP tools to Claude tool format.

        Claude's tool format:
        {
            "name": "tool_name",
            "description": "Tool description",
            "input_schema": {
                "type": "object",
                "properties": {...},
                "required": [...]
            }
        }
        """
        claude_tools = []

        for tool in self._tools:
            claude_tool = {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["parameters"]
            }
            claude_tools.append(claude_tool)

        logger.debug(f"[{self.name}] Converted {len(claude_tools)} MCP tools to Claude format")
        return claude_tools

    async def run_async(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        **kwargs
    ) -> List[Any]:
        """
        Run the agent asynchronously.

        For Computer Use, this will handle the tool execution loop.
        """
        logger.info(f"[{self.name}] Running Claude agent: {prompt[:50]}...")
        self._total_runs += 1

        # Add user message to history
        self._history.append({"role": "user", "content": prompt})

        try:
            # Prepare tools for Claude
            tools = self._convert_mcp_tools_to_claude_format() if self._tools else None

            # Prepare messages
            messages = [{"role": "user", "content": prompt}]
            if self._extended_thinking_enabled:
                # Add thinking prefix for extended thinking
                messages.insert(0, {
                    "role": "user",
                    "content": "Please think through this step by step before responding."
                })

            # Check if using TextChatAtOAI (Qwen's LLM wrapper) or native Anthropic client
            if hasattr(self._client, 'chat') or hasattr(self._client, 'generate'):
                # Using Qwen's LLM wrapper configured for Claude API
                return await self._run_via_qwen_llm(messages, tools, **kwargs)
            else:
                # Using native Anthropic client
                return await self._run_via_anthropic(messages, tools, **kwargs)

        except Exception as e:
            logger.error(f"[{self.name}] Error running agent: {e}")
            raise

    async def _run_via_qwen_llm(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        **kwargs
    ) -> List[Any]:
        """Run using Qwen's LLM wrapper (TextChatAtOAI) configured for Claude."""
        # Convert messages to Qwen format
        from qwen_agent.llm.schema import Message

        qwen_messages = []
        for msg in messages:
            qwen_messages.append(Message(
                role=msg["role"],
                content=msg["content"]
            ))

        # Run in thread since LLM call is synchronous
        response = await asyncio.to_thread(
            self._client.chat,
            messages=qwen_messages,
            functions=tools,
            **kwargs
        )

        # Convert response to list
        if isinstance(response, list):
            # Add to history
            for msg in response:
                if isinstance(msg, dict):
                    self._history.append(msg)
                elif hasattr(msg, 'role'):
                    self._history.append({
                        "role": msg.role,
                        "content": msg.content or ""
                    })
            return response
        else:
            return [response]

    async def _run_via_anthropic(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]],
        **kwargs
    ) -> List[Any]:
        """Run using native Anthropic client (for Computer Use)."""
        # Get model name
        model = getattr(self._config, 'llm_model', 'claude-3-5-sonnet-20241022')

        # Build API call parameters
        api_params = {
            "model": model,
            "messages": messages,
            "max_tokens": kwargs.get('max_tokens', 8192),
            "temperature": kwargs.get('temperature', 0.7),
        }

        # Add system prompt
        if self.system_prompt:
            api_params["system"] = self.system_prompt

        # Add tools (including Computer Use)
        if tools or self._computer_use_enabled:
            all_tools = []

            # Add MCP tools
            if tools:
                all_tools.extend(tools)

            # Add Computer Use tool if enabled
            if self._computer_use_enabled:
                all_tools.append({
                    "type": "computer_20241022",
                    "name": "computer",
                    "description": "Computer use tool for interacting with the system",
                    "display_size_px": kwargs.get('display_size', [1024, 768]),
                })

            if all_tools:
                api_params["tools"] = all_tools

        # Run in thread since Anthropic client is synchronous
        response = await asyncio.to_thread(
            self._client.messages.create,
            **api_params
        )

        # Process response
        result_messages = []

        for block in response.content:
            if block.type == "text":
                result_messages.append({
                    "role": "assistant",
                    "content": block.text
                })
                self._history.append({
                    "role": "assistant",
                    "content": block.text
                })
            elif block.type == "tool_use":
                # Execute tool and add result
                tool_result = await self._execute_tool(block)
                result_messages.append({
                    "role": "assistant",
                    "content": f"Tool use: {block.name}",
                    "tool_use": block.model_dump()
                })
                result_messages.append({
                    "role": "tool_result",
                    "content": tool_result
                })
                # Add to history
                self._history.append({"role": "assistant", "content": block.input})
                self._history.append({
                    "role": "user",
                    "content": json.dumps({
                        "tool_use_id": block.id,
                        "result": tool_result
                    })
                })

        return result_messages

    async def _execute_tool(self, tool_use_block: Any) -> str:
        """
        Execute a tool called by Claude.

        Handles both MCP tools and Computer Use.
        """
        tool_name = tool_use_block.name
        tool_input = tool_use_block.input

        logger.info(f"[{self.name}] Executing tool: {tool_name}")

        if tool_name == "computer":
            # Computer Use - execute browser/controller action
            return await self._execute_computer_use(tool_input)
        else:
            # MCP tool - find and execute via MCP Bridge
            return await self._execute_mcp_tool(tool_name, tool_input)

    async def _execute_computer_use(self, tool_input: Dict[str, Any]) -> str:
        """
        Execute Computer Use action.

        This requires a browser automation framework or screenshot service.
        Implementation depends on your environment.
        """
        action = tool_input.get("action", "")

        # This is a placeholder - actual implementation would:
        # 1. Take screenshot
        # 2. Execute browser action
        # 3. Return result
        logger.warning(f"[{self.name}] Computer Use not fully implemented: {action}")

        return f"Computer Use executed: {action}"

    async def _execute_mcp_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """Execute an MCP tool via MCP Bridge."""
        if not self._mcp_bridge:
            return f"Error: MCP Bridge not available for tool {tool_name}"

        # Find the tool in our tool list
        tool = None
        for t in self._tools:
            if t["name"] == tool_name:
                tool = t
                break

        if not tool:
            return f"Error: Tool {tool_name} not found"

        # Execute the tool function
        try:
            if asyncio.iscoroutinefunction(tool["function"]):
                result = await tool["function"](**tool_input)
            else:
                result = tool["function"](**tool_input)

            # Extract content from result
            if isinstance(result, dict):
                return result.get("content", str(result))
            return str(result)

        except Exception as e:
            logger.error(f"[{self.name}] Error executing MCP tool {tool_name}: {e}")
            return f"Error: {str(e)}"

    async def run_with_reasoning(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        max_iterations: int = 20,
        **kwargs
    ) -> List[ReasoningStep]:
        """
        Run the agent with continuous reasoning.

        Claude has native reasoning support through Extended Thinking.
        """
        logger.info(f"[{self.name}] Running with reasoning: {prompt[:50]}...")
        self._total_runs += 1

        reasoning_steps = []
        iteration = 0

        # Build messages
        messages = [{"role": "user", "content": prompt}]
        if self._extended_thinking_enabled:
            messages.insert(0, {
                "role": "user",
                "content": "Think step by step before responding."
            })

        # Get tools
        tools = self._convert_mcp_tools_to_claude_format() if self._tools else None

        try:
            while iteration < max_iterations:
                iteration += 1

                # Run Claude
                if hasattr(self._client, 'messages'):
                    response = await asyncio.to_thread(
                        self._client.messages.create,
                        model=getattr(self._config, 'llm_model', 'claude-3-5-sonnet-20241022'),
                        messages=messages,
                        system=self.system_prompt,
                        tools=tools,
                        max_tokens=8192
                    )

                    # Process response
                    tool_used = False
                    for block in response.content:
                        if block.type == "text":
                            reasoning_steps.append(ReasoningStep(
                                type="thought",
                                content=block.text,
                                iteration=iteration,
                                timestamp=time.time(),
                                metadata={"sdk": "claude"}
                            ))

                        elif block.type == "tool_use":
                            tool_used = True
                            reasoning_steps.append(ReasoningStep(
                                type="tool_use",
                                tool_name=block.name,
                                content=str(block.input),
                                iteration=iteration,
                                timestamp=time.time(),
                                metadata={"sdk": "claude"}
                            ))

                            # Execute tool
                            result = await self._execute_tool(block)
                            reasoning_steps.append(ReasoningStep(
                                type="tool_result",
                                tool_name=block.name,
                                content=str(result)[:500],
                                iteration=iteration,
                                timestamp=time.time(),
                                metadata={"sdk": "claude"}
                            ))

                            # Add to messages for next iteration
                            messages.append({"role": "assistant", "content": block.input})
                            messages.append({
                                "role": "user",
                                "content": json.dumps({
                                    "tool_use_id": block.id,
                                    "result": result
                                })
                            })

                    # If no tool used, we're done
                    if not tool_used:
                        # Mark last thought as final answer
                        if reasoning_steps:
                            reasoning_steps[-1].type = "final_answer"
                        break

                else:
                    # Using Qwen LLM wrapper
                    break

            logger.info(f"[{self.name}] Reasoning completed: {len(reasoning_steps)} steps")
            return reasoning_steps

        except Exception as e:
            logger.error(f"[{self.name}] Error in reasoning: {e}")
            reasoning_steps.append(ReasoningStep(
                type="error",
                content=str(e),
                iteration=iteration,
                timestamp=time.time(),
                metadata={"sdk": "claude"}
            ))
            return reasoning_steps

    async def run_with_reasoning_stream(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        max_iterations: int = 20,
        **kwargs
    ) -> AsyncIterator[ReasoningStep]:
        """
        Run the agent with continuous reasoning - streaming version.

        Yields reasoning steps as they are generated.
        """
        # For now, delegate to non-streaming version
        # Streaming with Claude API requires handling Server-Sent Events
        steps = await self.run_with_reasoning(
            prompt,
            session_id=session_id,
            max_iterations=max_iterations,
            **kwargs
        )

        for step in steps:
            yield step

    def get_history(self) -> List[Dict[str, str]]:
        """Get the current message history."""
        return [
            {k: v for k, v in msg.items() if k != "metadata"}
            for msg in self._history
        ]

    def clear_history(self) -> None:
        """Clear the message history."""
        self._history.clear()
        logger.info(f"[{self.name}] History cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        return {
            "name": self.name,
            "role": self.role,
            "sdk": "claude",
            "total_runs": self._total_runs,
            "history_length": len(self._history),
            "tool_count": len(self._tools),
            "mcp_servers": self.mcp_servers,
            "computer_use_enabled": self._computer_use_enabled,
            "extended_thinking_enabled": self._extended_thinking_enabled,
        }

    def get_sdk_type(self) -> AgentSDKType:
        """Get the SDK type."""
        return AgentSDKType.CLAUDE

    @property
    def supports_computer_use(self) -> bool:
        """Check if Computer Use is enabled."""
        return self._computer_use_enabled

    @property
    def supports_extended_thinking(self) -> bool:
        """Check if Extended Thinking is enabled."""
        return self._extended_thinking_enabled

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"ClaudeAgentAdapter(name={self.name}, sdk=claude, "
            f"computer_use={self._computer_use_enabled})"
        )


__all__ = ["ClaudeAgentAdapter"]
