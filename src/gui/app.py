"""
Gradio GUI for Qwen Agent MCP Scheduler.

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

        # Create Gradio interface
        self.app = self._create_interface()

    def _create_interface(self) -> gr.Blocks:
        """Create the Gradio interface."""
        # Note: In Gradio 6.0+, theme and css are passed to launch(), not Blocks()
        with gr.Blocks(title="Qwen Agent MCP Scheduler") as app:
            gr.Markdown("# 🤖 Qwen Agent MCP Scheduler")

            with gr.Tabs():
                # Tab 1: Chat
                with gr.Tab("💬 Chat"):
                    self._create_chat_tab()

                # Tab 2: Agents
                with gr.Tab("👥 Agents"):
                    self._create_agents_tab()

                # Tab 3: Tasks
                with gr.Tab("⏰ Tasks"):
                    self._create_tasks_tab()

                # Tab 4: Settings
                with gr.Tab("⚙️ Settings"):
                    self._create_settings_tab()

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

                # Chat interface - Gradio 6.0+ compatible
                chat_interface = gr.ChatInterface(
                    fn=self._chat_with_agent,
                    additional_inputs=[agent_dropdown],
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
            with gr.Column(scale=2):
                # Agent list - Use Dropdown instead of Listbox for Gradio 6.0+
                agent_listbox = gr.Dropdown(
                    label="Available Agents",
                    choices=self._get_agent_choices(),
                    value=self._get_agent_choices()[0] if self._get_agent_choices() else None,
                    interactive=True
                )

            with gr.Column(scale=3):
                # Agent details
                agent_info = gr.Markdown("### Agent Details\n\nSelect an agent to view details")

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
        agent_name: str
    ) -> Tuple[str, List[Tuple[str, str]]]:
        """Chat with an agent."""
        try:
            agent = self.agent_manager.get_agent(agent_name)
            if not agent:
                return f"Error: Agent '{agent_name}' not found", history

            # Run agent
            import asyncio
            response = asyncio.run(agent.run_async(message))

            # Extract response
            content = ""
            for msg in response:
                if hasattr(msg, 'content') and msg.content:
                    content += msg.content
                elif isinstance(msg, dict):
                    content += msg.get('content', '')

            # Update history
            history.append((message, content))

            return content, history

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            history.append((message, error_msg))
            return error_msg, history

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

        details = f"""### {agent['name']} - {agent['role']}

**Description:** {agent['description']}

**MCP Servers:** {', '.join(agent['mcp_servers']) if agent['mcp_servers'] else 'None'}

**LLM Model:** {agent['llm_model']}

**Statistics:**
- Total runs: {agent['stats']['total_runs']}
- History length: {agent['stats']['history_length']}
- Tool count: {agent['stats']['tool_count']}
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
