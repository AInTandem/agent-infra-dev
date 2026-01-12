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
Settings Tab for Gradio GUI.

Provides system status and statistics dashboard.
"""

from typing import Tuple

import gradio as gr

from core.agent_manager import AgentManager
from core.config import ConfigManager
from core.task_scheduler import TaskScheduler
from .base_tab import BaseTab


class SettingsTab(BaseTab):
    """
    System settings and status tab.

    Features:
    - View system status
    - View statistics
    - Refresh status
    """

    @property
    def title(self) -> str:
        """Tab title."""
        return "📊 System"

    @property
    def description(self) -> str:
        """Tab description."""
        return "View system status and statistics"

    def create(self) -> gr.Column:
        """
        Create the settings tab.

        Returns:
            gr.Column: The settings interface column
        """
        with gr.Column() as component:
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

        return component

    # ========================================================================
    # Settings Functions
    # ========================================================================

    def _get_system_status(self) -> str:
        """
        Get system status.

        Returns:
            str: System status in Markdown format
        """
        agents = self.agent_manager.list_agents()
        tasks = self.task_scheduler.list_tasks()

        status = f"""
| Component | Status |
|-----------|--------|
| Agents | {len(agents)} available |
| Tasks | {len(tasks)} scheduled |
| Scheduler | {"Running" if self.task_scheduler.is_running else "Stopped"} |

**Enabled Agents:**
{_format_agent_list(agents, self.agent_manager)}
"""
        return status

    def _get_statistics(self) -> str:
        """
        Get system statistics.

        Returns:
            str: System statistics in Markdown format
        """
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
        """
        Refresh system status.

        Returns:
            Tuple[str, str]: Updated status and statistics
        """
        return self._get_system_status(), self._get_statistics()

    def get_custom_css(self) -> str:
        """
        Get custom CSS for this tab.

        Returns:
            str: Custom CSS styles
        """
        return """
        .settings-container {
            padding: 16px;
        }

        .status-panel {
            background-color: #f9f9f9;
            border-radius: 8px;
            padding: 16px;
            margin: 8px 0;
        }

        .stats-panel {
            background-color: #e3f2fd;
            border-radius: 8px;
            padding: 16px;
            margin: 8px 0;
        }
        """


def _format_agent_list(agents: list, agent_manager: AgentManager) -> str:
    """
    Format agent list for display.

    Args:
        agents: List of agent names
        agent_manager: Agent manager instance

    Returns:
        str: Formatted agent list
    """
    if not agents:
        return "- No agents available"

    enabled_agents = [agent for agent in agents if agent_manager.get_agent(agent)]
    if not enabled_agents:
        return "- No enabled agents"

    return "\n".join(f"- {agent}" for agent in enabled_agents)
