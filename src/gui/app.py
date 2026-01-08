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
Gradio GUI for AInTandem Agent MCP Scheduler.

Provides web interface for managing agents, tasks, and interactions.
"""

import os
from typing import Dict, List, Optional, Tuple

import gradio as gr
from loguru import logger

from core.agent_manager import AgentManager
from core.config import ConfigManager
from core.task_scheduler import TaskScheduler
from core.task_models import ScheduleType
from gui.config_editor import ConfigEditor


class GradioApp:
    """
    Gradio web application for agent management.

    Features:
    - Chat interface for agent interactions
    - Agent management (list, view, create)
    - Task management (list, create, enable/disable)
    - System status dashboard
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        agent_manager: AgentManager,
        task_scheduler: TaskScheduler,
    ):
        """
        Initialize the Gradio app.

        Args:
            config_manager: Configuration manager
            agent_manager: Agent manager instance
            task_scheduler: Task scheduler instance
        """
        self.config_manager = config_manager
        self.agent_manager = agent_manager
        self.task_scheduler = task_scheduler

        # Initialize config editor
        self.config_editor = ConfigEditor(config_manager)

        # Create Gradio interface
        self.app = self._create_interface()

    def _create_interface(self) -> gr.Blocks:
        """Create the Gradio interface."""
        # Note: In Gradio 6.0+, theme and css are passed to launch(), not Blocks()
        with gr.Blocks(title="AInTandem Agent MCP Scheduler") as app:
            gr.Markdown("# 🤖 AInTandem Agent MCP Scheduler")

            with gr.Tabs():
                # Tab 1: Chat
                with gr.Tab("💬 Chat"):
                    self._create_chat_tab()

                # Tab 2: Tasks
                with gr.Tab("⏰ Tasks"):
                    self._create_tasks_tab()

                # Tab 3: Agents
                with gr.Tab("👥 Agents"):
                    self._create_agents_tab()

                # Tab 4: Settings
                with gr.Tab("📊 System"):
                    self._create_settings_tab()

                # Tab 5: Configuration
                with gr.Tab("📝 Configuration"):
                    self._create_config_tab()

        return app

    def _create_chat_tab(self):
        """Create the chat interface tab."""
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

                # Store reference
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

    def _create_agents_tab(self):
        """Create the agents management tab."""
        gr.Markdown("### Agent Management")

        with gr.Row():
            # Get agent choices once for reuse
            agent_choices = self._get_agent_choices()

            with gr.Column(scale=2):
                # Agent list - Use Dropdown instead of Listbox for Gradio 6.0+
                agent_listbox = gr.Dropdown(
                    label="Available Agents",
                    choices=agent_choices,
                    value=agent_choices[0] if agent_choices else None,
                    interactive=True
                )

            with gr.Column(scale=3):
                # Agent details - initialize with first agent's data
                initial_agent_details = self._show_agent_details(agent_choices[0]) if agent_choices else "### Agent Details\n\nSelect an agent to view details"
                agent_info = gr.Markdown(value=initial_agent_details)

        with gr.Row():
            with gr.Column():
                refresh_agents_btn = gr.Button("🔄 Refresh Agents", variant="secondary")

        # Event handlers
        refresh_agents_btn.click(
            fn=self._refresh_agents,
            outputs=[agent_listbox]
        )

        agent_listbox.change(
            fn=self._show_agent_details,
            inputs=[agent_listbox],
            outputs=[agent_info]
        )

    def _create_tasks_tab(self):
        """Create the task management tab."""
        gr.Markdown("### Task Management")

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("#### Create New Task")

                task_name = gr.Textbox(label="Task Name", placeholder="Daily Report")
                task_agent = gr.Dropdown(
                    label="Agent",
                    choices=self._get_agent_choices(),
                    value=self._get_agent_choices()[0] if self._get_agent_choices() else None
                )
                task_prompt = gr.Textbox(
                    label="Task Prompt",
                    placeholder="Generate daily sales report",
                    lines=3
                )

                with gr.Row():
                    schedule_type = gr.Radio(
                        label="Schedule Type",
                        choices=["cron", "interval", "once"],
                        value="once"
                    )
                    schedule_value = gr.Textbox(
                        label="Schedule Value",
                        placeholder="2026-01-06T20:00:00 or 0 9 * * * or 300"
                    )

                repeat = gr.Checkbox(label="Repeat", value=False)
                task_desc = gr.Textbox(label="Description", placeholder="Optional description")

                create_task_btn = gr.Button("Create Task", variant="primary")

            with gr.Column(scale=1):
                gr.Markdown("#### Task List")

                task_list = gr.Dataframe(
                    label="Scheduled Tasks",
                    headers=["Name", "Agent", "Schedule", "Status", "Next Run"],
                    datatype=["str", "str", "str", "str", "str"],
                    interactive=False,
                    row_count=10
                )

                with gr.Row():
                    refresh_tasks_btn = gr.Button("🔄 Refresh", size="sm")
                    enable_task_btn = gr.Button("✅ Enable", size="sm")
                    disable_task_btn = gr.Button("❌ Disable", size="sm")
                    cancel_task_btn = gr.Button("🗑️ Cancel", size="sm")

                task_id_input = gr.Textbox(label="Task ID (for enable/disable/cancel)", placeholder="Enter task ID...")

        # Event handlers
        create_task_btn.click(
            fn=self._create_task,
            inputs=[task_name, task_agent, task_prompt, schedule_type, schedule_value, repeat, task_desc],
            outputs=[task_list]
        )

        refresh_tasks_btn.click(
            fn=self._refresh_tasks,
            outputs=[task_list]
        )

    def _create_settings_tab(self):
        """Create the settings tab."""
        gr.Markdown("### System Settings")

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("#### System Status")

                status_markdown = gr.Markdown(self._get_system_status())

            with gr.Column(scale=1):
                gr.Markdown("#### Statistics")

                stats_markdown = gr.Markdown(self._get_statistics())

        with gr.Row():
            refresh_status_btn = gr.Button("🔄 Refresh Status", variant="secondary")

        # Event handlers
        refresh_status_btn.click(
            fn=self._refresh_status,
            outputs=[status_markdown, stats_markdown]
        )

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
        """Chat with an agent - supports streaming for reasoning mode."""
        try:
            agent = self.agent_manager.get_agent(agent_name)
            if not agent:
                yield f"Error: Agent '{agent_name}' not found"
                return

            # Run agent with proper async handling
            import asyncio

            def run_async(coro):
                """Helper to run async code in Gradio context."""
                try:
                    loop = asyncio.get_running_loop()
                    # There's already a running loop, use create_task
                    import concurrent.futures
                    import threading

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
                logger.info(f"[GUI] Running agent '{agent_name}' with reasoning (streaming)")

                # Yield initial status
                yield "🤔 Agent is thinking...\n\n"

                reasoning_steps = run_async(agent.run_with_reasoning(message))

                # Debug: Dump reasoning steps structure
                logger.info(f"[GUI DEBUG] Received {len(reasoning_steps)} reasoning steps")
                for i, step in enumerate(reasoning_steps):
                    step_type = step.get("type", "unknown")
                    content = step.get("content", "")
                    tool_name = step.get("tool_name", "")
                    logger.info(f"[GUI DEBUG] Step {i}: type={step_type}, tool_name={tool_name}, content_len={len(content)}, content_preview={repr(content[:100] if content else '')}")

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
                logger.info(f"[GUI] Final result with {len(output_parts)} parts")
                yield result

            else:
                # Simple mode without reasoning - also support streaming
                logger.info(f"[GUI] Running agent '{agent_name}' without reasoning")
                yield "🤔 Processing...\n\n"

                response = run_async(agent.run_async(message))

                # Extract response
                content = ""
                for msg in response:
                    if hasattr(msg, 'content') and msg.content:
                        content += msg.content
                    elif isinstance(msg, dict):
                        content += msg.get('content', '')

                result = content if content else "No response generated"
                yield result

        except Exception as e:
            logger.exception(f"Error in chat with agent '{agent_name}'")
            yield f"Error: {str(e)}"

    def _clear_chat_history(self) -> str:
        """Clear chat history."""
        return "Chat history cleared."

    # ========================================================================
    # Agent Functions
    # ========================================================================

    def _get_agent_choices(self) -> List[str]:
        """Get list of agent names."""
        agents = self.agent_manager.list_agents()
        return agents if agents else ["No agents available"]

    def _refresh_agents(self):
        """Refresh agent list."""
        # Return updated choices for the dropdown
        return gr.update(choices=self._get_agent_choices())

    def _show_agent_details(self, agent_name: str) -> str:
        """Show agent details."""
        agent = self.agent_manager.get_agent_info(agent_name)
        if not agent:
            return "### Agent Details\n\nAgent not found."

        # Safely get values with defaults
        name = agent.get('name', agent_name)
        role = agent.get('role', 'N/A')
        description = agent.get('description', 'No description')
        mcp_servers = agent.get('mcp_servers', [])
        llm_model = agent.get('llm_model', 'N/A')
        stats = agent.get('stats', {})

        details = f"""### {name} - {role}

**Description:** {description}

**MCP Servers:** {', '.join(mcp_servers) if mcp_servers else 'None'}

**LLM Model:** {llm_model}

**Statistics:**
- Total runs: {stats.get('total_runs', 0)}
- History length: {stats.get('history_length', 0)}
- Tool count: {stats.get('tool_count', 0)}
"""
        return details

    # ========================================================================
    # Task Functions
    # ========================================================================

    def _create_task(
        self,
        name: str,
        agent_name: str,
        prompt: str,
        schedule_type: str,
        schedule_value: str,
        repeat: bool,
        description: str
    ) -> str:
        """Create a new task."""
        try:
            import asyncio

            async def _create():
                return await self.task_scheduler.schedule_task(
                    name=name,
                    agent_name=agent_name,
                    task_prompt=prompt,
                    schedule_type=ScheduleType(schedule_type),
                    schedule_value=schedule_value,
                    repeat=repeat,
                    description=description,
                )

            task = asyncio.run(_create())

            return f"✓ Task '{name}' created with ID: {task.id}"

        except Exception as e:
            return f"✗ Failed to create task: {str(e)}"

    def _refresh_tasks(self) -> List[List[str]]:
        """Refresh task list."""
        try:
            tasks = self.task_scheduler.list_tasks()

            data = []
            for task in tasks:
                next_run_str = task.next_run.isoformat() if task.next_run else "N/A"
                data.append([
                    task.name,
                    task.agent_name,
                    f"{task.schedule_type.value}:{task.schedule_value[:20]}",
                    task.last_status.value,
                    next_run_str[:19]
                ])
            return data

        except Exception as e:
            return [["Error", str(e), "", "", ""]]

    # ========================================================================
    # Settings Functions
    # ========================================================================

    def _get_system_status(self) -> str:
        """Get system status."""
        agents = self.agent_manager.list_agents()
        tasks = self.task_scheduler.list_tasks()

        status = f"""
| Component | Status |
|-----------|--------|
| Agents | {len(agents)} available |
| Tasks | {len(tasks)} scheduled |
| Scheduler | {"Running" if self.task_scheduler.is_running else "Stopped"} |

**Enabled Agents:**
{chr(10).join(f"- {agent}" for agent in agents if self.agent_manager.get_agent(agent))}
"""
        return status

    def _get_statistics(self) -> str:
        """Get system statistics."""
        agent_stats = self.agent_manager.get_all_stats()
        task_stats = self.task_scheduler.get_stats()

        stats = f"""
**Agent Statistics:**
- Total Agents: {len(agent_stats)}
- Total Runs: {sum(s['total_runs'] for s in agent_stats.values())}

**Task Statistics:**
- Total Tasks: {task_stats['total_tasks']}
- Enabled: {task_stats['enabled_tasks']}
- Disabled: {task_stats['disabled_tasks']}
- Executions: {task_stats['total_executions']}
"""
        return stats

    def _refresh_status(self) -> Tuple[str, str]:
        """Refresh system status."""
        return self._get_system_status(), self._get_statistics()

    def _format_args_for_form(self, args_list: List[str]) -> str:
        """Format args list for textarea display."""
        return "\n".join(args_list) if args_list else ""

    def _format_env_for_form(self, env_dict: Dict[str, str]) -> str:
        """Format env dict for textarea display."""
        return "\n".join([f"{k}={v}" for k, v in env_dict.items()]) if env_dict else ""

    def _create_config_tab(self):
        """Create the configuration editor tab."""
        gr.Markdown("### Configuration Editor")

        # Pending changes indicator
        with gr.Row():
            pending_info = gr.Markdown("**Pending Changes:** 0")
            refresh_config_btn = gr.Button("🔄 Reload from Files", size="sm")

        with gr.Tabs():
            # LLM Configuration
            with gr.Tab("🧠 LLM"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("#### Providers Management")
                        llm_providers_df = gr.Dataframe(
                            headers=["Name", "Description", "API Key", "Base URL"],
                            datatype=["str", "str", "str", "str"],
                            value=self.config_editor.get_llm_providers_list(),
                            interactive=False
                        )
                        with gr.Row():
                            refresh_providers_btn = gr.Button("🔄 Refresh", size="sm")
                            llm_provider_names = self.config_editor.get_llm_provider_names()
                            selected_llm_provider = gr.Dropdown(
                                label="Select Provider to Edit",
                                choices=llm_provider_names,
                                value=llm_provider_names[0] if llm_provider_names else None,
                                interactive=True
                            )
                            delete_provider_btn = gr.Button("🗑️ Delete Provider", variant="stop", size="sm")

                        gr.Markdown("---")

                        gr.Markdown("#### LLM Models List")
                        llm_models_df = gr.Dataframe(
                            headers=["Default", "Name", "Provider", "Description", "Max Tokens", "Key", "URL", "FC", "Stream"],
                            datatype=["str", "str", "str", "str", "number", "str", "str", "str", "str"],
                            value=self.config_editor.get_llm_models_list(),
                            interactive=False
                        )
                        with gr.Row():
                            refresh_models_btn = gr.Button("🔄 Refresh", size="sm")
                            llm_model_names = self.config_editor.get_llm_model_names()
                            selected_llm_model = gr.Dropdown(
                                label="Select Model to Edit",
                                choices=llm_model_names,
                                value=llm_model_names[0] if llm_model_names else None,
                                interactive=True
                            )
                            delete_model_btn = gr.Button("🗑️ Delete Model", variant="stop", size="sm")

                        with gr.Accordion("Generation Settings", open=False):
                            llm_default_model_dropdown = gr.Dropdown(
                                label="Default Model",
                                choices=llm_model_names,
                                value=self.config_editor.get_llm_default_model() if llm_model_names else None,
                                interactive=True
                            )
                            llm_temperature = gr.Slider(label="Temperature", minimum=0, maximum=2, step=0.1, value=0.7)
                            llm_top_p = gr.Slider(label="Top-P", minimum=0, maximum=1, step=0.05, value=0.9)
                            llm_max_retries = gr.Slider(label="Max Retries", minimum=1, maximum=10, step=1, value=3)
                            llm_timeout = gr.Slider(label="Timeout (seconds)", minimum=10, maximum=300, step=10, value=60)
                            update_generation_btn = gr.Button("Update Generation Settings", variant="primary")

                        llm_status = gr.Markdown("")

                    with gr.Column(scale=1):
                        gr.Markdown("#### Add/Edit Provider")
                        # Get initial values for the first provider
                        initial_provider_name = llm_provider_names[0] if llm_provider_names else ""
                        initial_provider_config = self.config_editor.get_llm_provider_config(initial_provider_name) if initial_provider_name else {}

                        llm_provider_name = gr.Textbox(
                            label="Provider Name",
                            placeholder="modelscope",
                            value=initial_provider_config.get("name", initial_provider_name) if initial_provider_name else initial_provider_name
                        )
                        llm_provider_description = gr.Textbox(
                            label="Description",
                            placeholder="ModelScope (魔搭社區) - 個人開源社群推薦",
                            value=initial_provider_config.get("description", "") if initial_provider_name else ""
                        )
                        llm_provider_api_key = gr.Textbox(
                            label="API Key (use ${VAR_NAME} for env var)",
                            placeholder="${MODELSCOPE_API_TOKEN}",
                            value=initial_provider_config.get("api_key", "") if initial_provider_name else ""
                        )
                        llm_provider_base_url = gr.Textbox(
                            label="Base URL",
                            placeholder="https://api-inference.modelscope.cn/v1",
                            value=initial_provider_config.get("base_url", "") if initial_provider_name else ""
                        )
                        save_provider_btn = gr.Button("💾 Save Provider", variant="primary")

                        gr.Markdown("---")
                        gr.Markdown("#### Add/Edit Model")
                        # Get initial values for the first model
                        initial_llm_model_name = llm_model_names[0] if llm_model_names else ""
                        initial_llm_model_config = self.config_editor.get_llm_model_config(initial_llm_model_name) if initial_llm_model_name else None

                        llm_model_name = gr.Textbox(
                            label="Model Name",
                            placeholder="Qwen/Qwen3-7B-Instruct",
                            value=initial_llm_model_config.get("name", initial_llm_model_name) if initial_llm_model_config else ""
                        )
                        llm_model_provider = gr.Dropdown(
                            label="Provider",
                            choices=llm_provider_names if llm_provider_names else ["modelscope", "deepseek", "openai"],
                            value=initial_llm_model_config.get("provider", llm_provider_names[0] if llm_provider_names else "modelscope") if initial_llm_model_config else (llm_provider_names[0] if llm_provider_names else "modelscope")
                        )
                        llm_model_description = gr.Textbox(
                            label="Description",
                            placeholder="Qwen3-7B - 平衡型，適合多數場景",
                            value=initial_llm_model_config.get("description", "") if initial_llm_model_config else ""
                        )
                        llm_model_max_tokens = gr.Slider(
                            label="Max Tokens",
                            minimum=2048,
                            maximum=128000,
                            step=1024,
                            value=initial_llm_model_config.get("max_tokens", 32768) if initial_llm_model_config else 32768
                        )
                        llm_model_function_calling = gr.Checkbox(
                            label="Supports Function Calling",
                            value=initial_llm_model_config.get("supports_function_calling", True) if initial_llm_model_config else True
                        )
                        llm_model_streaming = gr.Checkbox(
                            label="Supports Streaming",
                            value=initial_llm_model_config.get("supports_streaming", True) if initial_llm_model_config else True
                        )

                        with gr.Accordion("Override Provider Settings (Optional)", open=False):
                            llm_model_api_key = gr.Textbox(
                                label="Custom API Key (override provider)",
                                type="password",
                                placeholder="Leave empty to use provider's setting",
                                value=initial_llm_model_config.get("api_key", "") if initial_llm_model_config else ""
                            )
                            llm_model_base_url = gr.Textbox(
                                label="Custom Base URL (override provider)",
                                placeholder="Leave empty to use provider's setting",
                                value=initial_llm_model_config.get("base_url", "") if initial_llm_model_config else ""
                            )

                        save_model_btn = gr.Button("💾 Save Model", variant="primary")

                        gr.Markdown("---")
                        gr.Markdown("#### LLM Configuration (YAML Mode)")
                        llm_yaml = gr.Code(
                            label="YAML Configuration",
                            language="yaml",
                            value=self.config_editor.get_llm_yaml(),
                            lines=15
                        )
                        update_llm_from_yaml_btn = gr.Button("Update from YAML", variant="secondary")

            # Agents Configuration
            with gr.Tab("👥 Agents"):
                with gr.Row():
                    with gr.Column(scale=2):
                        gr.Markdown("#### Agents List")
                        agents_df = gr.Dataframe(
                            headers=["Name", "Role", "LLM", "Enabled", "MCP Servers"],
                            datatype=["str", "str", "str", "str", "str"],
                            value=self.config_editor.get_agents_list(),
                            interactive=False
                        )
                        refresh_agents_btn = gr.Button("🔄 Refresh", size="sm")

                    with gr.Column(scale=1):
                        gr.Markdown("#### Actions")
                        agent_names = self.config_editor.get_agent_names()
                        selected_agent = gr.Dropdown(
                            label="Select Agent",
                            choices=agent_names,
                            value=agent_names[0] if agent_names else None,
                            interactive=True
                        )
                        delete_agent_btn = gr.Button("🗑️ Delete Agent", variant="stop")

                with gr.Accordion("Add/Edit Agent", open=False):
                    # Get initial values for the first agent
                    initial_agent_name = agent_names[0] if agent_names else ""
                    initial_agent_config = self.config_editor.get_agent_config(initial_agent_name) if initial_agent_name else None

                    agent_name = gr.Textbox(
                        label="Agent Name",
                        placeholder="researcher",
                        value=initial_agent_config.get("name", initial_agent_name) if initial_agent_config else ""
                    )
                    agent_role = gr.Textbox(
                        label="Role",
                        placeholder="研究助理",
                        value=initial_agent_config.get("role", "") if initial_agent_config else ""
                    )
                    agent_description = gr.TextArea(
                        label="Description",
                        lines=3,
                        max_lines=10,
                        placeholder="專精於資料收集...",
                        value=initial_agent_config.get("description", "") if initial_agent_config else "",
                        autoscroll=True
                    )
                    agent_system_prompt = gr.TextArea(
                        label="System Prompt",
                        lines=6,
                        max_lines=15,
                        placeholder="你是一位專業的研究助理...",
                        value=initial_agent_config.get("system_prompt", "") if initial_agent_config else "",
                        autoscroll=True
                    )
                    llm_model_choices = self.config_editor.get_llm_model_names_with_provider()
                    llm_model_names_raw = self.config_editor.get_llm_model_names()

                    # Create a mapping from display name to actual model name
                    llm_model_mapping = dict(zip(llm_model_choices, llm_model_names_raw))

                    # Get current model name and find its corresponding display name
                    current_model_name = initial_agent_config.get("llm_model", "") if initial_agent_config else ""
                    current_model_display = None
                    if current_model_name:
                        for display, raw in llm_model_mapping.items():
                            if raw == current_model_name:
                                current_model_display = display
                                break

                    agent_llm_model = gr.Dropdown(
                        label="LLM Model",
                        choices=llm_model_choices,
                        value=current_model_display if current_model_display else (llm_model_choices[0] if llm_model_choices else ""),
                        interactive=True
                    )
                    agent_mcp_servers = gr.CheckboxGroup(
                        label="MCP Servers",
                        choices=["filesystem", "web-search", "github", "postgres", "google-maps", "puppeteer"],
                        value=initial_agent_config.get("mcp_servers", []) if initial_agent_config else []
                    )
                    agent_enabled = gr.Checkbox(
                        label="Enabled",
                        value=initial_agent_config.get("enabled", True) if initial_agent_config else True
                    )
                    save_agent_btn = gr.Button("💾 Save Agent", variant="primary")

                agents_status = gr.Markdown("")

            # MCP Servers Configuration
            with gr.Tab("🔌 MCP Servers"):
                with gr.Row():
                    with gr.Column(scale=2):
                        gr.Markdown("#### MCP Servers List")
                        mcp_servers_df = gr.Dataframe(
                            headers=["Name", "Description", "Command", "Enabled"],
                            datatype=["str", "str", "str", "str"],
                            value=self.config_editor.get_mcp_servers_list(),
                            interactive=False
                        )
                        refresh_mcp_btn = gr.Button("🔄 Refresh", size="sm")

                    with gr.Column(scale=1):
                        gr.Markdown("#### Actions")
                        mcp_server_names = self.config_editor.get_mcp_server_names()
                        selected_mcp_server = gr.Dropdown(
                            label="Select Server",
                            choices=mcp_server_names,
                            value=mcp_server_names[0] if mcp_server_names else None,
                            interactive=True
                        )
                        delete_mcp_btn = gr.Button("🗑️ Delete Server", variant="stop")

                with gr.Accordion("Add/Edit MCP Server", open=False):
                    # Get initial values for the first MCP server
                    initial_mcp_name = mcp_server_names[0] if mcp_server_names else ""
                    initial_mcp_config = self.config_editor.get_mcp_server_config(initial_mcp_name) if initial_mcp_name else None

                    mcp_name = gr.Textbox(
                        label="Server Name",
                        placeholder="filesystem",
                        value=initial_mcp_config.get("name", initial_mcp_name) if initial_mcp_config else ""
                    )
                    mcp_description = gr.Textbox(
                        label="Description",
                        placeholder="檔案系統讀寫存取",
                        value=initial_mcp_config.get("description", "") if initial_mcp_config else ""
                    )
                    mcp_command = gr.Textbox(
                        label="Command",
                        placeholder="npx",
                        value=initial_mcp_config.get("command", "npx") if initial_mcp_config else "npx"
                    )
                    mcp_args = gr.TextArea(
                        label="Arguments (one per line)",
                        placeholder='-y\n@modelcontextprotocol/server-filesystem\n/path',
                        value=self._format_args_for_form(initial_mcp_config.get("args", [])) if initial_mcp_config else ""
                    )
                    mcp_env = gr.TextArea(
                        label="Environment Variables (KEY=VALUE, one per line)",
                        placeholder="API_KEY=your_key",
                        value=self._format_env_for_form(initial_mcp_config.get("env", {})) if initial_mcp_config else ""
                    )
                    mcp_timeout = gr.Slider(
                        label="Timeout (seconds)",
                        minimum=5,
                        maximum=120,
                        step=5,
                        value=initial_mcp_config.get("timeout", 30) if initial_mcp_config else 30
                    )
                    mcp_enabled = gr.Checkbox(
                        label="Enabled",
                        value=initial_mcp_config.get("enabled", True) if initial_mcp_config else True
                    )
                    mcp_health_check = gr.Checkbox(
                        label="Enable Health Check",
                        value=initial_mcp_config.get("health_check", {}).get("enabled", True) if initial_mcp_config else True
                    )
                    mcp_health_interval = gr.Slider(
                        label="Health Check Interval (seconds)",
                        minimum=30,
                        maximum=300,
                        step=30,
                        value=initial_mcp_config.get("health_check", {}).get("interval", 60) if initial_mcp_config else 60
                    )
                    save_mcp_btn = gr.Button("💾 Save Server", variant="primary")

                mcp_status = gr.Markdown("")

            # Storage Configuration
            with gr.Tab("💾 Storage"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("#### Storage Settings (Form Mode)")
                        storage_type = gr.Radio(
                            label="Storage Type",
                            choices=["sqlite", "postgresql"],
                            value="sqlite"
                        )

                        with gr.Accordion("SQLite Settings", open=True):
                            sqlite_path = gr.Textbox(label="Database Path", value="./storage/data.db")
                            sqlite_pool_size = gr.Slider(label="Pool Size", minimum=1, maximum=20, step=1, value=5)
                            sqlite_enable_wal = gr.Checkbox(label="Enable WAL Mode", value=True)

                        with gr.Accordion("PostgreSQL Settings", open=False):
                            postgres_host = gr.Textbox(label="Host", placeholder="localhost")
                            postgres_port = gr.Slider(label="Port", minimum=1, maximum=65535, step=1, value=5432)
                            postgres_database = gr.Textbox(label="Database", placeholder="qwen_agent")
                            postgres_user = gr.Textbox(label="User", placeholder="postgres")

                        with gr.Accordion("Cache Settings", open=True):
                            cache_type = gr.Radio(
                                label="Cache Type",
                                choices=["none", "redis", "memory"],
                                value="none"
                            )
                            redis_host = gr.Textbox(label="Redis Host", placeholder="localhost")
                            redis_port = gr.Slider(label="Redis Port", minimum=1, maximum=65535, step=1, value=6379)

                        update_storage_btn = gr.Button("Update Storage Config", variant="primary")

                    with gr.Column(scale=1):
                        gr.Markdown("#### Storage Configuration (YAML Mode)")
                        storage_yaml = gr.Code(
                            label="YAML Configuration",
                            language="yaml",
                            value=self.config_editor.get_storage_yaml(),
                            lines=20
                        )
                        update_storage_from_yaml_btn = gr.Button("Update from YAML", variant="secondary")
                        storage_status = gr.Markdown("")

            # App Configuration
            with gr.Tab("⚙️ App"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("#### Application Settings (Form Mode)")
                        app_name = gr.Textbox(label="Application Name", value="AInTandem Agent MCP Scheduler")
                        server_host = gr.Textbox(label="Server Host", value="0.0.0.0")
                        api_port = gr.Slider(label="API Port", minimum=1000, maximum=9999, step=1, value=8000)
                        gui_port = gr.Slider(label="GUI Port", minimum=1000, maximum=9999, step=1, value=7860)
                        log_level = gr.Dropdown(
                            label="Log Level",
                            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                            value="INFO"
                        )
                        scheduler_timezone = gr.Textbox(label="Scheduler Timezone", value="Asia/Shanghai")
                        max_concurrent_tasks = gr.Slider(label="Max Concurrent Tasks", minimum=1, maximum=20, step=1, value=5)

                        update_app_btn = gr.Button("Update App Config", variant="primary")

                    with gr.Column(scale=1):
                        gr.Markdown("#### App Configuration (YAML Mode)")
                        app_yaml = gr.Code(
                            label="YAML Configuration",
                            language="yaml",
                            value=self.config_editor.get_app_yaml(),
                            lines=20
                        )
                        update_app_from_yaml_btn = gr.Button("Update from YAML", variant="secondary")
                        app_status = gr.Markdown("")

        # Batch operations
        with gr.Row():
            with gr.Column(scale=3):
                gr.Markdown("#### Batch Operations")
            with gr.Column(scale=1):
                pending_count = gr.Number(label="Pending Changes", value=0, interactive=False)
                discard_btn = gr.Button("🗑️ Discard All", variant="secondary")
                save_all_btn = gr.Button("💾 Save All Changes", variant="primary")

        save_result = gr.Markdown("")

        # Event handlers
        def update_pending_info():
            count = self.config_editor.get_pending_changes_count()
            changes = self.config_editor.get_pending_changes_list()
            if changes:
                return f"**Pending Changes:** {count} ({', '.join(changes)})", count
            return "**Pending Changes:** 0", 0

        # LLM Events
        # Provider Events
        def load_provider_for_editing(provider_name: str):
            """Load provider data into form for editing."""
            if not provider_name:
                return (
                    gr.update(value=""),  # llm_provider_name
                    gr.update(value=""),  # llm_provider_description
                    gr.update(value=""),  # llm_provider_api_key
                    gr.update(value=""),  # llm_provider_base_url
                )

            config = self.config_editor.get_llm_provider_config(provider_name)
            if not config:
                return (
                    gr.update(value=""),  # llm_provider_name
                    gr.update(value=""),  # llm_provider_description
                    gr.update(value=""),  # llm_provider_api_key
                    gr.update(value=""),  # llm_provider_base_url
                )

            return (
                gr.update(value=provider_name),
                gr.update(value=config.get("description", "")),
                gr.update(value=config.get("api_key", "")),
                gr.update(value=config.get("base_url", "")),
            )

        refresh_providers_btn.click(
            fn=lambda: (
                self.config_editor.get_llm_providers_list(),
                self.config_editor.get_llm_provider_names(),
            ),
            outputs=[llm_providers_df, selected_llm_provider]
        )

        # Load provider data when selected
        selected_llm_provider.change(
            fn=load_provider_for_editing,
            inputs=[selected_llm_provider],
            outputs=[llm_provider_name, llm_provider_description,
                    llm_provider_api_key, llm_provider_base_url]
        )

        save_provider_btn.click(
            fn=lambda n, d, k, u: (
                self.config_editor.update_llm_provider(n, d, k, u) if n else "❌ Provider name is required",
                *update_pending_info()
            ),
            inputs=[llm_provider_name, llm_provider_description,
                   llm_provider_api_key, llm_provider_base_url],
            outputs=[llm_status, pending_info, pending_count]
        )

        delete_provider_btn.click(
            fn=lambda p: (
                self.config_editor.delete_llm_provider(p) if p else "❌ Please select a provider",
                *update_pending_info()
            ),
            inputs=[selected_llm_provider],
            outputs=[llm_status, pending_info, pending_count]
        )

        # Model Events
        def load_llm_model_for_editing(model_name: str):
            """Load LLM model data into form for editing."""
            if not model_name:
                return (
                    gr.update(value=""),  # llm_model_name
                    gr.update(value="modelscope"),  # llm_model_provider
                    gr.update(value=""),  # llm_model_description
                    gr.update(value=32768),  # llm_model_max_tokens
                    gr.update(value=True),  # llm_model_function_calling
                    gr.update(value=True),  # llm_model_streaming
                    gr.update(value=""),  # llm_model_api_key
                    gr.update(value=""),  # llm_model_base_url
                )

            config = self.config_editor.get_llm_model_config(model_name)
            if not config:
                return (
                    gr.update(value=""),  # llm_model_name
                    gr.update(value="modelscope"),  # llm_model_provider
                    gr.update(value=""),  # llm_model_description
                    gr.update(value=32768),  # llm_model_max_tokens
                    gr.update(value=True),  # llm_model_function_calling
                    gr.update(value=True),  # llm_model_streaming
                    gr.update(value=""),  # llm_model_api_key
                    gr.update(value=""),  # llm_model_base_url
                )

            return (
                gr.update(value=config.get("name", "")),
                gr.update(value=config.get("provider", "modelscope")),
                gr.update(value=config.get("description", "")),
                gr.update(value=config.get("max_tokens", 32768)),
                gr.update(value=config.get("supports_function_calling", True)),
                gr.update(value=config.get("supports_streaming", True)),
                gr.update(value=config.get("api_key", "")),
                gr.update(value=config.get("base_url", "")),
            )

        refresh_models_btn.click(
            fn=lambda: (
                self.config_editor.get_llm_models_list(),
                self.config_editor.get_llm_model_names(),
                self.config_editor.get_llm_default_model()
            ),
            outputs=[llm_models_df, selected_llm_model, llm_default_model_dropdown]
        )

        # Load model data when selected
        selected_llm_model.change(
            fn=load_llm_model_for_editing,
            inputs=[selected_llm_model],
            outputs=[llm_model_name, llm_model_provider, llm_model_description,
                    llm_model_max_tokens, llm_model_function_calling, llm_model_streaming,
                    llm_model_api_key, llm_model_base_url]
        )

        save_model_btn.click(
            fn=lambda old_name, n, p, d, mt, fc, s, ak, bu: (
                self.config_editor.update_llm_model(old_name, n, p, d, mt, fc, s, ak, bu)
                if old_name else (
                    self.config_editor.add_llm_model(n, p, d, mt, fc, s, ak, bu)
                ) if n else "❌ Model name is required",
                *update_pending_info()
            ),
            inputs=[selected_llm_model, llm_model_name, llm_model_provider, llm_model_description,
                   llm_model_max_tokens, llm_model_function_calling, llm_model_streaming,
                   llm_model_api_key, llm_model_base_url],
            outputs=[llm_status, pending_info, pending_count]
        )

        delete_model_btn.click(
            fn=lambda m: (
                self.config_editor.delete_llm_model(m) if m else "❌ Please select a model",
                *update_pending_info()
            ),
            inputs=[selected_llm_model],
            outputs=[llm_status, pending_info, pending_count]
        )

        # Generation Settings Events
        update_generation_btn.click(
            fn=lambda m, t, tp, mr, to: (
                self.config_editor.update_llm_generation_config(m, t, tp, mr, to)[0],
                *update_pending_info()
            ),
            inputs=[llm_default_model_dropdown, llm_temperature, llm_top_p,
                   llm_max_retries, llm_timeout],
            outputs=[llm_status, pending_info, pending_count]
        )

        update_llm_from_yaml_btn.click(
            fn=lambda y: (self.config_editor.update_llm_from_yaml(y), *update_pending_info()),
            inputs=[llm_yaml],
            outputs=[llm_status, pending_info, pending_count]
        )

        # Agents Events
        def convert_display_to_model_name(display_name: str) -> str:
            """Convert display name (model / provider) to actual model name."""
            if " / " not in display_name:
                return display_name
            llm_model_choices = self.config_editor.get_llm_model_names_with_provider()
            llm_model_names_raw = self.config_editor.get_llm_model_names()
            llm_model_mapping = dict(zip(llm_model_choices, llm_model_names_raw))
            return llm_model_mapping.get(display_name, display_name)

        def load_agent_for_editing(agent_name: str):
            """Load agent data into form for editing."""
            llm_model_choices = self.config_editor.get_llm_model_names_with_provider()

            if not agent_name:
                return (
                    gr.update(value=""),  # agent_name
                    gr.update(value=""),  # agent_role
                    gr.update(value=""),  # agent_description
                    gr.update(value=""),  # agent_system_prompt
                    gr.update(value=llm_model_choices[0] if llm_model_choices else "", choices=llm_model_choices),  # agent_llm_model
                    gr.update(value=[]),  # agent_mcp_servers
                    gr.update(value=True),  # agent_enabled
                )

            config = self.config_editor.get_agent_config(agent_name)
            if not config:
                return (
                    gr.update(value=""),  # agent_name
                    gr.update(value=""),  # agent_role
                    gr.update(value=""),  # agent_description
                    gr.update(value=""),  # agent_system_prompt
                    gr.update(value=llm_model_choices[0] if llm_model_choices else "", choices=llm_model_choices),  # agent_llm_model
                    gr.update(value=[]),  # agent_mcp_servers
                    gr.update(value=True),  # agent_enabled
                )

            # Get model names with provider for display
            llm_model_names_raw = self.config_editor.get_llm_model_names()
            llm_model_mapping = dict(zip(llm_model_choices, llm_model_names_raw))

            # Find display name for current model
            current_model_name = config.get("llm_model", "Qwen/Qwen3-7B-Instruct")
            current_model_display = current_model_name
            for display, raw in llm_model_mapping.items():
                if raw == current_model_name:
                    current_model_display = display
                    break

            return (
                gr.update(value=config.get("name", "")),
                gr.update(value=config.get("role", "")),
                gr.update(value=config.get("description", "")),
                gr.update(value=config.get("system_prompt", "")),
                gr.update(value=current_model_display, choices=llm_model_choices),
                gr.update(value=config.get("mcp_servers", [])),
                gr.update(value=config.get("enabled", True)),
            )

        refresh_agents_btn.click(
            fn=lambda: (
                self.config_editor.get_agents_list(),
                self.config_editor.get_agent_names(),
                gr.update(choices=self.config_editor.get_llm_model_names_with_provider())
            ),
            outputs=[agents_df, selected_agent, agent_llm_model]
        )

        # Load agent data when selected
        selected_agent.change(
            fn=load_agent_for_editing,
            inputs=[selected_agent],
            outputs=[agent_name, agent_role, agent_description, agent_system_prompt,
                    agent_llm_model, agent_mcp_servers, agent_enabled]
        )

        save_agent_btn.click(
            fn=lambda sel, n, r, d, sp, lm, ms, e: (
                self.config_editor.update_agent(sel, n, r, d, sp, convert_display_to_model_name(lm), ms, e) if sel and n else
                self.config_editor.add_agent(n, r, d, sp, convert_display_to_model_name(lm), ms, e) if n else "❌ Agent name is required",
                *update_pending_info()
            ),
            inputs=[selected_agent, agent_name, agent_role, agent_description, agent_system_prompt,
                   agent_llm_model, agent_mcp_servers, agent_enabled],
            outputs=[agents_status, pending_info, pending_count]
        )

        delete_agent_btn.click(
            fn=lambda a: (self.config_editor.delete_agent(a) if a else "❌ Please select an agent", *update_pending_info()),
            inputs=[selected_agent],
            outputs=[agents_status, pending_info, pending_count]
        )

        # MCP Servers Events
        def load_mcp_server_for_editing(server_name: str):
            """Load MCP server data into form for editing."""
            if not server_name:
                return (
                    gr.update(value=""),  # mcp_name
                    gr.update(value=""),  # mcp_description
                    gr.update(value="npx"),  # mcp_command
                    gr.update(value=""),  # mcp_args
                    gr.update(value=""),  # mcp_env
                    gr.update(value=30),  # mcp_timeout
                    gr.update(value=True),  # mcp_enabled
                    gr.update(value=True),  # mcp_health_check
                    gr.update(value=60),  # mcp_health_interval
                )

            config = self.config_editor.get_mcp_server_config(server_name)
            if not config:
                return (
                    gr.update(value=""),  # mcp_name
                    gr.update(value=""),  # mcp_description
                    gr.update(value="npx"),  # mcp_command
                    gr.update(value=""),  # mcp_args
                    gr.update(value=""),  # mcp_env
                    gr.update(value=30),  # mcp_timeout
                    gr.update(value=True),  # mcp_enabled
                    gr.update(value=True),  # mcp_health_check
                    gr.update(value=60),  # mcp_health_interval
                )

            # Format args list back to textarea
            args_list = config.get("args", [])
            args_text = "\n".join(args_list) if args_list else ""

            # Format env dict back to textarea
            env_dict = config.get("env", {})
            env_text = "\n".join([f"{k}={v}" for k, v in env_dict.items()]) if env_dict else ""

            # Get health check settings
            health_check = config.get("health_check", {})
            health_enabled = health_check.get("enabled", True)
            health_interval = health_check.get("interval", 60)

            return (
                gr.update(value=config.get("name", "")),
                gr.update(value=config.get("description", "")),
                gr.update(value=config.get("command", "npx")),
                gr.update(value=args_text),
                gr.update(value=env_text),
                gr.update(value=config.get("timeout", 30)),
                gr.update(value=config.get("enabled", True)),
                gr.update(value=health_enabled),
                gr.update(value=health_interval),
            )

        refresh_mcp_btn.click(
            fn=lambda: (self.config_editor.get_mcp_servers_list(), self.config_editor.get_mcp_server_names()),
            outputs=[mcp_servers_df, selected_mcp_server]
        )

        # Load MCP server data when selected
        selected_mcp_server.change(
            fn=load_mcp_server_for_editing,
            inputs=[selected_mcp_server],
            outputs=[mcp_name, mcp_description, mcp_command, mcp_args, mcp_env,
                    mcp_timeout, mcp_enabled, mcp_health_check, mcp_health_interval]
        )

        save_mcp_btn.click(
            fn=lambda sel, n, d, c, a, e, t, en, hc, hi: (
                self.config_editor.update_mcp_server(sel, n, d, c, a, e, t, en, hc, hi) if sel and n else
                self.config_editor.add_mcp_server(n, d, c, a, e, t, en, hc, hi) if n else "❌ Server name is required",
                *update_pending_info()
            ),
            inputs=[selected_mcp_server, mcp_name, mcp_description, mcp_command, mcp_args, mcp_env,
                   mcp_timeout, mcp_enabled, mcp_health_check, mcp_health_interval],
            outputs=[mcp_status, pending_info, pending_count]
        )

        delete_mcp_btn.click(
            fn=lambda s: (self.config_editor.delete_mcp_server(s) if s else "❌ Please select a server", *update_pending_info()),
            inputs=[selected_mcp_server],
            outputs=[mcp_status, pending_info, pending_count]
        )

        # Storage Events
        update_storage_btn.click(
            fn=lambda st, sp, sps, sw, ph, pp, pd, pu, ct, rh, rp: self.config_editor.update_storage_config(
                st, sp, sps, sw, ph, pp, pd, pu, ct, rh, rp
            ),
            inputs=[storage_type, sqlite_path, sqlite_pool_size, sqlite_enable_wal,
                   postgres_host, postgres_port, postgres_database, postgres_user,
                   cache_type, redis_host, redis_port],
            outputs=[storage_status, storage_yaml]
        ).then(
            fn=update_pending_info,
            outputs=[pending_info, pending_count]
        )

        update_storage_from_yaml_btn.click(
            fn=lambda y: (self.config_editor.update_storage_from_yaml(y), *update_pending_info()),
            inputs=[storage_yaml],
            outputs=[storage_status, pending_info, pending_count]
        )

        # App Events
        update_app_btn.click(
            fn=lambda an, sh, ap, gp, ll, st, mc: self.config_editor.update_app_config(
                an, sh, ap, gp, ll, st, mc
            ),
            inputs=[app_name, server_host, api_port, gui_port, log_level, scheduler_timezone, max_concurrent_tasks],
            outputs=[app_status, app_yaml]
        ).then(
            fn=update_pending_info,
            outputs=[pending_info, pending_count]
        )

        update_app_from_yaml_btn.click(
            fn=lambda y: (self.config_editor.update_app_from_yaml(y), *update_pending_info()),
            inputs=[app_yaml],
            outputs=[app_status, pending_info, pending_count]
        )

        # Batch operations
        refresh_config_btn.click(
            fn=lambda: (self.config_editor.reload_configs(), *update_pending_info()),
            outputs=[pending_info, pending_count]
        )

        discard_btn.click(
            fn=lambda: (self.config_editor.discard_pending_changes(), *update_pending_info()),
            outputs=[pending_info, pending_count]
        )

        save_all_btn.click(
            fn=self.config_editor.save_all_changes,
            outputs=[save_result]
        ).then(
            fn=update_pending_info,
            outputs=[pending_info, pending_count]
        )

    # ========================================================================
    # Utility Functions
    # ========================================================================

    def _get_custom_css(self) -> str:
        """Get custom CSS for the interface."""
        return """
        .gradio-container {
            max-width: 1200px !important;
        }
        .chatbot {
            min-height: 400px;
        }
        """


# ============================================================================
# Application Factory
# ============================================================================

def create_gradio_app(
    config_manager: ConfigManager,
    agent_manager: AgentManager,
    task_scheduler: TaskScheduler,
) -> gr.Blocks:
    """
    Create and configure the Gradio application.

    Args:
        config_manager: Configuration manager
        agent_manager: Agent manager instance
        task_scheduler: Task scheduler instance

    Returns:
        Configured Gradio Blocks app
    """
    app_instance = GradioApp(config_manager, agent_manager, task_scheduler)
    return app_instance.app
