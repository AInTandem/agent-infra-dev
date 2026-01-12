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
Agents Tab for Gradio GUI.

Provides agent management interface.
"""

from typing import List, Optional

import gradio as gr

from core.agent_manager import AgentManager
from core.config import ConfigManager
from core.task_scheduler import TaskScheduler
from .base_tab import BaseTab


class AgentsTab(BaseTab):
    """
    Agent management tab.

    Features:
    - List all available agents
    - View agent details
    - Refresh agent list
    """

    @property
    def title(self) -> str:
        """Tab title."""
        return "👥 Agents"

    @property
    def description(self) -> Optional[str]:
        """Tab description."""
        return "View and manage AI Agents"

    def create(self) -> gr.Column:
        """
        Create the agents management tab.

        Returns:
            gr.Column: The agents interface column
        """
        with gr.Column() as component:
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

        return component

    # ========================================================================
    # Agent Functions
    # ========================================================================

    def _get_agent_choices(self) -> List[str]:
        """
        Get list of agent names.

        Returns:
            List[str]: List of agent names
        """
        agents = self.agent_manager.list_agents()
        return agents if agents else ["No agents available"]

    def _refresh_agents(self):
        """
        Refresh agent list.

        Returns:
            gr.update: Updated dropdown choices
        """
        # Return updated choices for the dropdown
        return gr.update(choices=self._get_agent_choices())

    def _show_agent_details(self, agent_name: str) -> str:
        """
        Show agent details.

        Args:
            agent_name: Name of the agent to show details for

        Returns:
            str: Formatted agent details in Markdown
        """
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

    def get_custom_css(self) -> str:
        """
        Get custom CSS for this tab.

        Returns:
            str: Custom CSS styles
        """
        return """
        .agents-container {
            padding: 16px;
        }

        .agent-list {
            max-height: 400px;
            overflow-y: auto;
        }

        .agent-details {
            background-color: #f9f9f9;
            border-radius: 8px;
            padding: 16px;
        }
        """
