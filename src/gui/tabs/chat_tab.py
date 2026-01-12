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
Chat Tab for Gradio GUI.

Provides traditional chat interface for agent interactions.
"""

import asyncio
import concurrent.futures
import threading
from typing import List, Tuple, Optional

import gradio as gr
from loguru import logger

from core.agent_manager import AgentManager
from core.config import ConfigManager
from core.task_scheduler import TaskScheduler
from .base_tab import BaseTab


class ChatTab(BaseTab):
    """
    Traditional chat interface tab for agent interactions.

    Features:
    - Agent selection dropdown
    - Continuous reasoning mode toggle
    - Streaming chat with reasoning steps
    - Chat history display
    """

    @property
    def title(self) -> str:
        """Tab title."""
        return "💬 Chat"

    @property
    def description(self) -> Optional[str]:
        """Tab description."""
        return "Chat with AI Agents using traditional interface"

    def create(self) -> gr.Column:
        """
        Create the chat interface tab.

        Returns:
            gr.Column: The chat interface column
        """
        with gr.Column() as component:
            gr.Markdown("### Chat with AI Agents")

            with gr.Row():
                with gr.Column(scale=1):
                    # Agent selector
                    agent_dropdown = gr.Dropdown(
                        label="Select Agent",
                        choices=self._get_agent_choices(),
                        value=self._get_agent_choices()[0] if self._get_agent_choices() else None,
                        interactive=True
                    )

                    # Reasoning mode toggle
                    reasoning_toggle = gr.Checkbox(
                        label="Enable Continuous Reasoning",
                        value=True,
                        info="Agent will use tools and think step-by-step"
                    )

                    # Chat interface - Gradio 6.0+ compatible
                    chat_interface = gr.ChatInterface(
                        fn=self._chat_with_agent,
                        additional_inputs=[agent_dropdown, reasoning_toggle],
                        examples=[
                            ["Hello! How can you help me?"],
                            ["搜索最近的 AI 論文"],
                            ["檢查系統狀態"],
                        ],
                    )

                    # Store reference for potential future use
                    self.chat_component = chat_interface

            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Chat History")
                    clear_btn = gr.Button("Clear History", variant="secondary")
                    history_output = gr.Textbox(
                        label="Conversation History",
                        lines=10,
                        interactive=False
                    )

            # Event handlers
            clear_btn.click(
                fn=self._clear_chat_history,
                outputs=[history_output]
            )

        return component

    # ========================================================================
    # Chat Functions
    # ========================================================================

    def _chat_with_agent(
        self,
        message: str,
        history: List[Tuple[str, str]],
        agent_name: str,
        enable_reasoning: bool = True
    ):
        """
        Chat with an agent - supports streaming for reasoning mode.

        Args:
            message: User message
            history: Chat history (not currently used)
            agent_name: Name of the agent to chat with
            enable_reasoning: Whether to use continuous reasoning mode

        Yields:
            str: Streaming response updates
        """
        try:
            agent = self.agent_manager.get_agent(agent_name)
            if not agent:
                yield f"Error: Agent '{agent_name}' not found"
                return

            # Run agent with proper async handling
            def run_async(coro):
                """
                Helper to run async code in Gradio context.

                Gradio runs in sync context, but agent methods are async.
                This helper bridges the gap.
                """
                try:
                    loop = asyncio.get_running_loop()
                    # There's already a running loop, use create_task
                    result_holder = []
                    exception_holder = []

                    def run_in_new_loop():
                        try:
                            new_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(new_loop)
                            try:
                                result = new_loop.run_until_complete(coro)
                                result_holder.append(result)
                            finally:
                                new_loop.close()
                        except Exception as e:
                            exception_holder.append(e)

                    thread = threading.Thread(target=run_in_new_loop)
                    thread.start()
                    thread.join(timeout=120)  # 2 minute timeout

                    if exception_holder:
                        raise exception_holder[0]
                    if not result_holder:
                        raise TimeoutError("Agent call timed out after 120 seconds")

                    return result_holder[0]
                except RuntimeError:
                    # No running loop, safe to use asyncio.run
                    return asyncio.run(coro)

            if enable_reasoning:
                # Use continuous reasoning mode with streaming
                logger.info(f"[ChatTab] Running agent '{agent_name}' with reasoning (streaming)")

                # Yield initial status
                yield "🤔 Agent is thinking...\n\n"

                reasoning_steps = run_async(agent.run_with_reasoning(message))

                # Debug: Dump reasoning steps structure
                logger.info(f"[ChatTab DEBUG] Received {len(reasoning_steps)} reasoning steps")
                for i, step in enumerate(reasoning_steps):
                    step_type = step.get("type", "unknown")
                    content = step.get("content", "")
                    tool_name = step.get("tool_name", "")
                    logger.info(
                        f"[ChatTab DEBUG] Step {i}: type={step_type}, "
                        f"tool_name={tool_name}, content_len={len(content)}, "
                        f"content_preview={repr(content[:100] if content else '')}"
                    )

                # Stream reasoning steps
                output_parts = ["🤔 Agent is thinking...\n\n"]

                for step in reasoning_steps:
                    step_type = step.get("type", "unknown")

                    if step_type == "thought":
                        # Agent's thinking process
                        content = step.get("content", "")
                        if content and content.strip():
                            formatted = f"🤔 **Thinking:**\n{content}"
                            output_parts.append(formatted)
                            # Stream current progress
                            yield "\n\n".join(output_parts) + "\n\n*...continuing to think...*"

                    elif step_type == "final_answer":
                        # Final answer from agent
                        content = step.get("content", "")
                        if content and content.strip():
                            formatted = f"\n\n✅ **Final Answer:**\n{content}"
                            output_parts.append(formatted)
                            # Stream final result
                            yield "\n\n".join(output_parts)

                    elif step_type == "tool_use":
                        # Agent decided to use a tool
                        tool_name = step.get("tool_name", "unknown")
                        content = step.get("content", "")
                        formatted = f"\n\n🔧 **Using tool:** `{tool_name}`"
                        if content and content.strip():
                            formatted += f"\n_{content}_"
                        output_parts.append(formatted)
                        # Stream tool use
                        yield "\n\n".join(output_parts)

                    elif step_type == "tool_result":
                        # Tool execution result
                        tool_name = step.get("tool_name", "unknown")
                        content = step.get("content", "")
                        # Truncate long results
                        if content and len(content) > 500:
                            content = content[:500] + "...\n[Result truncated]"
                        formatted = f"\n\n📊 **Result from `{tool_name}`:**\n```\n{content}\n```"
                        output_parts.append(formatted)
                        # Stream tool result
                        yield "\n\n".join(output_parts)

                # Final yield with complete result
                result = "\n\n".join(output_parts)
                logger.info(f"[ChatTab] Final result with {len(output_parts)} parts")
                yield result

            else:
                # Simple mode without reasoning - also support streaming
                logger.info(f"[ChatTab] Running agent '{agent_name}' without reasoning")
                yield "🤔 Processing...\n\n"

                response = run_async(agent.run_async(message))

                # Extract response from result
                if isinstance(response, dict):
                    response_text = response.get("response", str(response))
                else:
                    response_text = str(response)

                yield f"🤔 Processing...\n\n{response_text}"

        except Exception as e:
            logger.error(f"[ChatTab] Error in chat: {e}", exc_info=True)
            yield f"Error: {str(e)}"

    def _clear_chat_history(self) -> str:
        """
        Clear chat history.

        Returns:
            str: Confirmation message
        """
        return "Chat history cleared."

    def _get_agent_choices(self) -> List[str]:
        """
        Get list of agent names.

        Returns:
            List[str]: List of agent names
        """
        agents = self.agent_manager.list_agents()
        return agents if agents else ["No agents available"]

    def get_custom_css(self) -> str:
        """
        Get custom CSS for this tab.

        Returns:
            str: Custom CSS styles
        """
        return """
        .chat-container {
            padding: 16px;
        }

        .chat-history {
            max-height: 400px;
            overflow-y: auto;
        }
        """
