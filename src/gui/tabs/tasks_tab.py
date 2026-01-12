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
Tasks Tab for Gradio GUI.

Provides task scheduling and management interface.
"""

import asyncio
from typing import List

import gradio as gr

from core.agent_manager import AgentManager
from core.config import ConfigManager
from core.task_scheduler import TaskScheduler
from core.task_models import ScheduleType
from .base_tab import BaseTab


class TasksTab(BaseTab):
    """
    Task management and scheduling tab.

    Features:
    - Create new scheduled tasks
    - View task list
    - Refresh task list
    """

    @property
    def title(self) -> str:
        """Tab title."""
        return "⏰ Tasks"

    @property
    def description(self) -> str:
        """Tab description."""
        return "Manage scheduled tasks"

    def create(self) -> gr.Column:
        """
        Create the task management tab.

        Returns:
            gr.Column: The tasks interface column
        """
        with gr.Column() as component:
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

        return component

    # ========================================================================
    # Task Functions
    # ========================================================================

    def _get_agent_choices(self) -> List[str]:
        """
        Get list of agent names.

        Returns:
            List[str]: List of agent names
        """
        agents = self.agent_manager.list_agents()
        return agents if agents else ["No agents available"]

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
        """
        Create a new task.

        Args:
            name: Task name
            agent_name: Agent to run the task
            prompt: Task prompt
            schedule_type: Type of schedule (cron, interval, once)
            schedule_value: Schedule value
            repeat: Whether to repeat the task
            description: Optional task description

        Returns:
            str: Success or error message
        """
        try:
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
        """
        Refresh task list.

        Returns:
            List[List[str]]: Task data for display
        """
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

    def get_custom_css(self) -> str:
        """
        Get custom CSS for this tab.

        Returns:
            str: Custom CSS styles
        """
        return """
        .tasks-container {
            padding: 16px;
        }

        .task-list {
            max-height: 400px;
            overflow-y: auto;
        }

        .task-create {
            background-color: #f9f9f9;
            border-radius: 8px;
            padding: 16px;
        }
        """
