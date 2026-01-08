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
Base Agent implementation extending Qwen Agent's Assistant.

Provides a wrapper for Qwen Agent with MCP tool integration.
"""

import functools
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Union

from loguru import logger
from qwen_agent.agents import Assistant
from qwen_agent.llm.schema import Message
from qwen_agent.llm import get_chat_model
from qwen_agent.tools.base import BaseTool

from core.config import AgentConfig


class MCPTool(BaseTool):
    """
    Wrapper for MCP tools to make them compatible with Qwen Agent.

    This class wraps MCP tool callables (from MCPBridge) into Qwen Agent's BaseTool format.
    """

    def __init__(self, name: str, description: str, parameters: Dict[str, Any], function: Any):
        """
        Initialize the MCP Tool wrapper.

        Args:
            name: Tool name (e.g., "filesystem.read_file")
            description: Tool description
            parameters: Tool parameters schema (JSON Schema format)
            function: Async callable function that executes the tool
        """
        self.name = name
        self.description = description
        self.parameters = parameters
        self._mcp_function = function

    def call(self, params: Union[str, Dict], **kwargs) -> Union[str, List, Dict]:
        """
        Call the MCP tool.

        Args:
            params: Tool parameters (can be string or dict)
            **kwargs: Additional parameters

        Returns:
            Tool execution result
        """
        # Parse params if it's a string
        if isinstance(params, str):
            import json
            # Handle empty string
            if not params.strip():
                params = {}
            else:
                try:
                    params = json.loads(params)
                except json.JSONDecodeError:
                    # If params is not JSON, treat it as a single value
                    params = {"query": params}

        # Ensure params is a dict
        if not isinstance(params, dict):
            logger.warning(f"[{self.name}] Unexpected params type: {type(params)}, converting to dict")
            params = {"value": params}

        # Merge params with kwargs
        all_params = {**params, **kwargs}

        # Call the MCP function (may be async)
        import asyncio
        try:
            if asyncio.iscoroutinefunction(self._mcp_function):
                # Run async function in event loop
                try:
                    loop = asyncio.get_running_loop()
                    # If there's already a running loop, we need to use asyncio.create_task
                    # Since call() is synchronous, we need to run the coroutine synchronously
                    # Use a simple approach - run in a new thread if needed
                    import concurrent.futures
                    import threading

                    result_holder = []
                    exception_holder = []

                    def run_coroutine():
                        try:
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            try:
                                result = new_loop.run_until_complete(self._mcp_function(**all_params))
                                result_holder.append(result)
                            finally:
                                new_loop.close()
                        except Exception as e:
                            exception_holder.append(e)

                    thread = threading.Thread(target=run_coroutine)
                    thread.start()
                    thread.join(timeout=30)  # 30 second timeout

                    if exception_holder:
                        raise exception_holder[0]
                    if not result_holder:
                        raise TimeoutError(f"Tool {self.name} timed out after 30 seconds")

                    result = result_holder[0]
                except RuntimeError:
                    # No running loop, safe to use asyncio.run
                    result = asyncio.run(self._mcp_function(**all_params))
            else:
                result = self._mcp_function(**all_params)

            # Extract content from MCP result
            if isinstance(result, dict):
                if "content" in result:
                    return result["content"]
                elif "error" in result:
                    return f"Error: {result['error']}"
                else:
                    return result
            elif isinstance(result, list):
                # Handle list of content items
                return "\n".join(
                    item.get("text", str(item)) if isinstance(item, dict) else str(item)
                    for item in result
                )
            else:
                return str(result)
        except Exception as e:
            logger.error(f"[{self.name}] Error calling tool: {e}")
            return f"Error: {str(e)}"


class BaseAgent:
    """
    Base agent class extending Qwen Agent's Assistant.

    Provides:
    - Configuration-based initialization
    - MCP tool integration
    - Message history management
    - Execution logging
    """

    def __init__(
        self,
        config: AgentConfig,
        llm: Any = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Initialize the BaseAgent.

        Args:
            config: Agent configuration
            llm: LLM instance (optional, will use default if None)
            tools: List of tools available to this agent (from MCP Bridge)
        """
        self.config = config
        self.name = config.name
        self.role = config.role
        self.description = config.description
        self.system_prompt = config.system_prompt
        self.mcp_servers = config.mcp_servers

        # Store raw tool data
        self._tools = tools or []
        self._tool_map = {tool["name"]: tool for tool in self._tools}

        # Prepare function list for Qwen Agent using MCPTool wrappers
        function_list = []
        for tool in self._tools:
            # Create MCPTool wrapper that extends BaseTool
            mcp_tool = MCPTool(
                name=tool["name"],
                description=tool["description"],
                parameters=tool["parameters"],
                function=tool["function"],
            )
            function_list.append(mcp_tool)

        # Create or use provided LLM
        if llm is None:
            # Create default LLM using model name from config
            llm = get_chat_model({"model": self.config.llm_model})

        # Create Qwen Agent Assistant
        self._assistant = Assistant(
            llm=llm,
            function_list=function_list or None,
            system_message=self.system_prompt,
            name=self.name,
            description=self.description,
        )

        # Message history
        self._history: List[Message] = []
        self._max_history_length = 100

        # Statistics
        self._total_runs = 0
        self._total_tokens = 0

        logger.info(f"[{self.name}] Agent initialized with {len(self._tools)} tools")

    async def run_async(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        **kwargs
    ) -> List[Message]:
        """
        Run the agent asynchronously with a prompt.

        Args:
            prompt: User prompt
            session_id: Optional session ID for multi-turn conversations
            **kwargs: Additional arguments for the agent

        Returns:
            List of response messages
        """
        logger.info(f"[{self.name}] Running agent with prompt: {prompt[:50]}...")

        self._total_runs += 1

        # Create message
        message = Message(
            role="user",
            content=prompt,
        )

        # Add to history
        self._add_to_history(message)

        try:
            # Run the agent (non-streaming for async)
            # Qwen Agent's run_nonstream is synchronous, so we run it in a thread
            import asyncio
            response = await asyncio.to_thread(
                self._assistant.run_nonstream,
                messages=self._history,
                **kwargs
            )

            # Parse response
            if isinstance(response, list):
                response_messages = []
                for msg in response:
                    if isinstance(msg, Message):
                        response_messages.append(msg)
                    elif isinstance(msg, dict):
                        response_messages.append(Message(**msg))

                # Update history with response
                for msg in response_messages:
                    self._add_to_history(msg)

                logger.info(f"[{self.name}] Agent run completed, {len(response_messages)} messages")
                return response_messages
            else:
                logger.warning(f"[{self.name}] Unexpected response type: {type(response)}")
                return []

        except Exception as e:
            logger.error(f"[{self.name}] Error running agent: {e}")
            raise

    async def run_with_reasoning(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        max_iterations: int = 20,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Run the agent with continuous reasoning (multi-step tool use).

        This method implements a manual ReAct loop, allowing the agent to:
        1. Think about the current task
        2. Decide whether to use a tool
        3. Execute the tool and observe results
        4. Continue until the task is complete

        Args:
            prompt: User prompt
            session_id: Optional session ID for multi-turn conversations
            max_iterations: Maximum number of reasoning iterations
            **kwargs: Additional arguments for the agent

        Returns:
            List of reasoning steps, each containing:
            - type: "thought" or "tool_use" or "tool_result" or "final_answer"
            - content: The content of the step
            - tool_name: Tool name (for tool_use/tool_result steps)
            - iteration: Iteration number
        """
        logger.info(f"[{self.name}] Running agent with reasoning: {prompt[:50]}...")

        self._total_runs += 1

        # Create message
        message = Message(
            role="user",
            content=prompt,
        )

        # Add to history
        self._add_to_history(message)

        reasoning_steps = []
        iteration = 0

        try:
            import asyncio
            from qwen_agent.llm.schema import FUNCTION

            # Manual ReAct loop
            while iteration < max_iterations:
                iteration += 1
                logger.debug(f"[{self.name}] Reasoning iteration {iteration}/{max_iterations}")

                # Run the agent (non-streaming) for one step
                response = await asyncio.to_thread(
                    self._assistant.run_nonstream,
                    messages=self._history,
                    **kwargs
                )

                if not response:
                    logger.warning(f"[{self.name}] Empty response at iteration {iteration}")
                    break

                # Process messages from this iteration
                tool_used_this_iteration = False
                assistant_message = None

                for msg in response:
                    if isinstance(msg, dict):
                        msg = Message(**msg)

                    # Track assistant message (for tool_calls)
                    if hasattr(msg, 'role') and msg.role == "assistant":
                        assistant_message = msg

                        # Check for tool calls
                        tool_calls = getattr(msg, 'tool_calls', None) or getattr(msg, 'function_call', None)

                        if tool_calls:
                            tool_used_this_iteration = True
                            # Extract tool call information
                            if isinstance(tool_calls, list):
                                for tc in tool_calls:
                                    tc_name = tc.get("name", "unknown") if isinstance(tc, dict) else getattr(tc, "name", "unknown")
                                    step = {
                                        "type": "tool_use",
                                        "tool_name": tc_name,
                                        "content": msg.content or "",
                                        "iteration": iteration
                                    }
                                    reasoning_steps.append(step)
                                    logger.info(f"[{self.name}] Tool use: {tc_name}")
                            else:
                                tc_name = tool_calls.get("name", "unknown") if isinstance(tool_calls, dict) else getattr(tool_calls, "name", "unknown")
                                step = {
                                    "type": "tool_use",
                                    "tool_name": tc_name,
                                    "content": msg.content or "",
                                    "iteration": iteration
                                }
                                reasoning_steps.append(step)
                                logger.info(f"[{self.name}] Tool use: {tc_name}")

                        elif msg.content:
                            # Regular assistant message (thought)
                            step = {
                                "type": "thought",
                                "content": msg.content,
                                "iteration": iteration
                            }
                            reasoning_steps.append(step)
                            logger.debug(f"[{self.name}] Thought: {msg.content[:100]}...")

                    # Function results (tool outputs)
                    elif hasattr(msg, 'role') and msg.role == FUNCTION:
                        tool_name = getattr(msg, 'name', 'unknown')
                        step = {
                            "type": "tool_result",
                            "tool_name": tool_name,
                            "content": msg.content or "",
                            "iteration": iteration
                        }
                        reasoning_steps.append(step)
                        logger.debug(f"[{self.name}] Tool result from {tool_name}")

                    # Add to history
                    self._add_to_history(msg)

                # If no tool was used, this is the final answer
                if not tool_used_this_iteration:
                    if assistant_message and assistant_message.content:
                        # Mark the last thought as final answer
                        if reasoning_steps and reasoning_steps[-1]["type"] == "thought":
                            reasoning_steps[-1]["type"] = "final_answer"
                            logger.info(f"[{self.name}] Final answer reached")
                    break

            if iteration >= max_iterations:
                logger.warning(f"[{self.name}] Max iterations ({max_iterations}) reached")

            logger.info(f"[{self.name}] Reasoning completed with {len(reasoning_steps)} steps, {iteration} iterations")
            return reasoning_steps

        except Exception as e:
            logger.error(f"[{self.name}] Error running agent with reasoning: {e}")
            raise

    async def run_with_reasoning_stream(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        max_iterations: int = 20,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Run the agent with continuous reasoning (multi-step tool use) - Streaming version.

        This is an async generator that yields reasoning steps as they are generated,
        allowing for real-time display of the agent's thought process.

        Yields:
            Dict[str, Any]: Reasoning step containing:
            - type: "thought" or "tool_use" or "tool_result" or "final_answer"
            - content: The content of the step
            - tool_name: Tool name (for tool_use/tool_result steps)
            - iteration: Iteration number
            - timestamp: Unix timestamp when the step was generated

        Args:
            prompt: User prompt
            session_id: Optional session ID for multi-turn conversations
            max_iterations: Maximum number of reasoning iterations
            **kwargs: Additional arguments for the agent
        """
        import time

        logger.info(f"[{self.name}] Running agent with reasoning stream: {prompt[:50]}...")

        self._total_runs += 1

        # Create message
        message = Message(
            role="user",
            content=prompt,
        )

        # Add to history
        self._add_to_history(message)

        iteration = 0

        try:
            import asyncio
            from qwen_agent.llm.schema import FUNCTION

            # Manual ReAct loop with streaming
            while iteration < max_iterations:
                iteration += 1
                logger.debug(f"[{self.name}] Reasoning iteration {iteration}/{max_iterations}")

                # Run the agent (non-streaming) for one step
                # Note: Qwen Agent doesn't support true streaming in the ReAct loop,
                # so we stream at the iteration level
                response = await asyncio.to_thread(
                    self._assistant.run_nonstream,
                    messages=self._history,
                    **kwargs
                )

                if not response:
                    logger.warning(f"[{self.name}] Empty response at iteration {iteration}")
                    break

                # Process messages from this iteration
                tool_used_this_iteration = False
                assistant_message = None

                for msg in response:
                    if isinstance(msg, dict):
                        msg = Message(**msg)

                    # Track assistant message (for tool_calls)
                    if hasattr(msg, 'role') and msg.role == "assistant":
                        assistant_message = msg

                        # Check for tool calls
                        tool_calls = getattr(msg, 'tool_calls', None) or getattr(msg, 'function_call', None)

                        if tool_calls:
                            tool_used_this_iteration = True
                            # Extract tool call information
                            if isinstance(tool_calls, list):
                                for tc in tool_calls:
                                    tc_name = tc.get("name", "unknown") if isinstance(tc, dict) else getattr(tc, "name", "unknown")
                                    step = {
                                        "type": "tool_use",
                                        "tool_name": tc_name,
                                        "content": msg.content or "",
                                        "iteration": iteration,
                                        "timestamp": time.time()
                                    }
                                    yield step
                                    logger.info(f"[{self.name}] Tool use: {tc_name}")
                            else:
                                tc_name = tool_calls.get("name", "unknown") if isinstance(tool_calls, dict) else getattr(tool_calls, "name", "unknown")
                                step = {
                                    "type": "tool_use",
                                    "tool_name": tc_name,
                                    "content": msg.content or "",
                                    "iteration": iteration,
                                    "timestamp": time.time()
                                }
                                yield step
                                logger.info(f"[{self.name}] Tool use: {tc_name}")

                        elif msg.content:
                            # Regular assistant message (thought)
                            step = {
                                "type": "thought",
                                "content": msg.content,
                                "iteration": iteration,
                                "timestamp": time.time()
                            }
                            yield step
                            logger.debug(f"[{self.name}] Thought: {msg.content[:100]}...")

                    # Function results (tool outputs)
                    elif hasattr(msg, 'role') and msg.role == FUNCTION:
                        tool_name = getattr(msg, 'name', 'unknown')
                        step = {
                            "type": "tool_result",
                            "tool_name": tool_name,
                            "content": msg.content or "",
                            "iteration": iteration,
                            "timestamp": time.time()
                        }
                        yield step
                        logger.debug(f"[{self.name}] Tool result from {tool_name}")

                    # Add to history
                    self._add_to_history(msg)

                # If no tool was used, this is the final answer
                if not tool_used_this_iteration:
                    if assistant_message and assistant_message.content:
                        # Mark the last thought as final answer
                        final_step = {
                            "type": "final_answer",
                            "content": assistant_message.content,
                            "iteration": iteration,
                            "timestamp": time.time()
                        }
                        yield final_step
                        logger.info(f"[{self.name}] Final answer reached")
                    break

            if iteration >= max_iterations:
                logger.warning(f"[{self.name}] Max iterations ({max_iterations}) reached")

            logger.info(f"[{self.name}] Reasoning stream completed with {iteration} iterations")

        except Exception as e:
            logger.error(f"[{self.name}] Error running agent with reasoning stream: {e}")
            # Yield error step
            yield {
                "type": "error",
                "content": str(e),
                "iteration": iteration,
                "timestamp": time.time()
            }
            raise

    def run(
        self,
        prompt: str,
        stream: bool = False,
        **kwargs
    ) -> Union[List[Message], Iterator[List[Message]]]:
        """
        Run the agent with a prompt.

        Args:
            prompt: User prompt
            stream: Whether to stream the response
            **kwargs: Additional arguments for the agent

        Returns:
            List of response messages or iterator of message chunks
        """
        logger.info(f"[{self.name}] Running agent (stream={stream})")

        self._total_runs += 1

        # Create message
        message = Message(
            role="user",
            content=prompt,
        )

        # Add to history
        self._add_to_history(message)

        try:
            if stream:
                return self._assistant.run(messages=self._history, **kwargs)
            else:
                response = self._assistant.run_nonstream(messages=self._history, **kwargs)

                # Parse response
                if isinstance(response, list):
                    response_messages = []
                    for msg in response:
                        if isinstance(msg, Message):
                            response_messages.append(msg)
                        elif isinstance(msg, dict):
                            response_messages.append(Message(**msg))

                    # Update history with response
                    for msg in response_messages:
                        self._add_to_history(msg)

                    logger.info(f"[{self.name}] Agent run completed, {len(response_messages)} messages")
                    return response_messages
                else:
                    logger.warning(f"[{self.name}] Unexpected response type: {type(response)}")
                    return []

        except Exception as e:
            logger.error(f"[{self.name}] Error running agent: {e}")
            raise

    def chat(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Chat interface compatible with Gradio ChatInterface.

        Args:
            message: User message
            history: Chat history from Gradio
            **kwargs: Additional arguments

        Returns:
            Response dictionary with message and metadata
        """
        try:
            # Convert Gradio history to Qwen Agent format
            if history:
                for msg in history:
                    if len(msg) >= 2:
                        role = "user" if msg[0] else "assistant"
                        content = msg[1] if msg[1] else ""
                        if content:
                            self._add_to_history(Message(role=role, content=content))

            # Run agent
            response = self.run(message, stream=False, **kwargs)

            # Extract response text
            response_text = ""
            for msg in response:
                if msg.role == "assistant":
                    response_text += msg.content or ""

            return {
                "message": response_text,
                "history": self.get_history_dict(),
                "metadata": {
                    "agent": self.name,
                    "tools_used": self._extract_used_tools(response),
                }
            }

        except Exception as e:
            logger.error(f"[{self.name}] Error in chat: {e}")
            return {
                "message": f"Error: {str(e)}",
                "history": self.get_history_dict(),
                "metadata": {"error": str(e)}
            }

    def _add_to_history(self, message: Message) -> None:
        """Add a message to history with size limit."""
        self._history.append(message)

        # Trim history if needed
        if len(self._history) > self._max_history_length:
            # Keep system messages and recent messages
            system_messages = [m for m in self._history if m.role == "system"]
            other_messages = [m for m in self._history if m.role != "system"]

            # Keep last N messages
            keep_count = self._max_history_length - len(system_messages)
            self._history = system_messages + other_messages[-keep_count:]

    def _extract_used_tools(self, messages: List[Message]) -> List[str]:
        """Extract names of tools used in the response."""
        tools_used = []
        for msg in messages:
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    if isinstance(tool_call, dict):
                        tools_used.append(tool_call.get("function", {}).get("name", "unknown"))
                    elif hasattr(tool_call, "function"):
                        tools_used.append(tool_call.function.name if hasattr(tool_call.function, "name") else "unknown")
        return tools_used

    def get_history(self) -> List[Message]:
        """Get the current message history."""
        return self._history.copy()

    def get_history_dict(self) -> List[Dict[str, str]]:
        """Get history as a list of dictionaries (for Gradio)."""
        return [
            {"role": msg.role, "content": msg.content or ""}
            for msg in self._history
        ]

    def clear_history(self) -> None:
        """Clear the message history."""
        self._history.clear()
        logger.info(f"[{self.name}] History cleared")

    def set_system_prompt(self, prompt: str) -> None:
        """Update the system prompt."""
        self.system_prompt = prompt
        self._assistant._system_message = prompt
        logger.info(f"[{self.name}] System prompt updated")

    def add_tool(self, tool: Dict[str, Any]) -> None:
        """Add a tool to the agent."""
        if tool["name"] not in self._tool_map:
            self._tools.append(tool)
            self._tool_map[tool["name"]] = tool

            # Update Qwen Agent's function list
            function_list = [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                }
                for t in self._tools
            ]
            self._assistant._function_list = function_list

            logger.info(f"[{self.name}] Added tool: {tool['name']}")

    def remove_tool(self, tool_name: str) -> bool:
        """Remove a tool from the agent."""
        if tool_name in self._tool_map:
            self._tools = [t for t in self._tools if t["name"] != tool_name]
            del self._tool_map[tool_name]

            # Update Qwen Agent's function list
            function_list = [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                }
                for t in self._tools
            ]
            self._assistant._function_list = function_list

            logger.info(f"[{self.name}] Removed tool: {tool_name}")
            return True
        return False

    def get_tools(self) -> List[Dict[str, Any]]:
        """Get all available tools."""
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
            }
            for tool in self._tools
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        return {
            "name": self.name,
            "role": self.role,
            "total_runs": self._total_runs,
            "history_length": len(self._history),
            "tool_count": len(self._tools),
            "mcp_servers": self.mcp_servers,
        }

    def __repr__(self) -> str:
        """String representation."""
        return f"BaseAgent(name={self.name}, role={self.role}, tools={len(self._tools)})"

    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary for serialization."""
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "mcp_servers": self.mcp_servers,
            "tools": self.get_tools(),
            "stats": self.get_stats(),
        }
