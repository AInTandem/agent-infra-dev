"""
Base Agent implementation extending Qwen Agent's Assistant.

Provides a wrapper for Qwen Agent with MCP tool integration.
"""

from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Union

from loguru import logger
from qwen_agent.agents import Assistant
from qwen_agent.llm.schema import Message
from qwen_agent.llm import get_chat_model

from core.config import AgentConfig


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

        # Store tools
        self._tools = tools or []
        self._tool_map = {tool["name"]: tool for tool in self._tools}

        # Prepare function list for Qwen Agent
        # Extract only the tool definitions (not the callable wrappers)
        function_list = []
        for tool in self._tools:
            function_list.append({
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
            })

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
