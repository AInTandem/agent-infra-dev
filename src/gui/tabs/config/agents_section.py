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
Agents Configuration Section

Handles agent configuration management.
"""

from typing import Callable

import gradio as gr

from gui.config_editor import ConfigEditor
from .base_section import BaseConfigSection


class AgentsSection(BaseConfigSection):
    """Agents configuration section."""

    @property
    def title(self) -> str:
        return "👥 Agents"

    @property
    def tab_id(self) -> str:
        return "agents"

    def create(self) -> gr.Tab:
        """Create the Agents configuration section."""
        with gr.Tab(self.title) as tab:
            with gr.Row():
                with gr.Column(scale=2):
                    self._create_agents_list()
                with gr.Column(scale=1):
                    self._create_actions()

            with gr.Accordion("Add/Edit Agent", open=False):
                self._create_agent_form()

            agents_status = gr.Markdown("")

        return tab

    def _create_agents_list(self):
        """Create the agents list panel."""
        gr.Markdown("#### Agents List")
        agents_df = gr.Dataframe(
            headers=["Name", "Role", "LLM", "Enabled", "MCP Servers"],
            datatype=["str", "str", "str", "str", "str"],
            value=self.config_editor.get_agents_list(),
            interactive=False
        )
        refresh_agents_btn = gr.Button("🔄 Refresh", size="sm")

    def _create_actions(self):
        """Create the actions panel."""
        gr.Markdown("#### Actions")
        agent_names = self.config_editor.get_agent_names()
        selected_agent = gr.Dropdown(
            label="Select Agent",
            choices=agent_names,
            value=agent_names[0] if agent_names else None,
            interactive=True
        )
        delete_agent_btn = gr.Button("🗑️ Delete Agent", variant="stop")

    def _create_agent_form(self):
        """Create the agent add/edit form."""
        agent_names = self.config_editor.get_agent_names()
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
