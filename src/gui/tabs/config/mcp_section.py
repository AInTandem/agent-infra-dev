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
MCP Servers Configuration Section

Handles MCP server configuration management.
"""

from typing import Callable

import gradio as gr

from gui.config_editor import ConfigEditor
from .base_section import BaseConfigSection


class MCPSection(BaseConfigSection):
    """MCP Servers configuration section."""

    @property
    def title(self) -> str:
        return "🔌 MCP Servers"

    @property
    def tab_id(self) -> str:
        return "mcp_servers"

    def create(self) -> gr.Tab:
        """Create the MCP Servers configuration section."""
        with gr.Tab(self.title) as tab:
            with gr.Row():
                with gr.Column(scale=2):
                    self._create_mcp_servers_list()
                with gr.Column(scale=1):
                    self._create_mcp_actions()

            with gr.Accordion("Add/Edit MCP Server", open=False):
                self._create_mcp_form()

            mcp_status = gr.Markdown("")

        return tab

    def _create_mcp_servers_list(self):
        """Create the MCP servers list panel."""
        gr.Markdown("#### MCP Servers List")
        mcp_servers_df = gr.Dataframe(
            headers=["Name", "Description", "Command", "Enabled"],
            datatype=["str", "str", "str", "str"],
            value=self.config_editor.get_mcp_servers_list(),
            interactive=False
        )
        refresh_mcp_btn = gr.Button("🔄 Refresh", size="sm")

    def _create_mcp_actions(self):
        """Create the MCP server actions panel."""
        gr.Markdown("#### Actions")
        mcp_server_names = self.config_editor.get_mcp_server_names()
        selected_mcp_server = gr.Dropdown(
            label="Select Server",
            choices=mcp_server_names,
            value=mcp_server_names[0] if mcp_server_names else None,
            interactive=True
        )
        delete_mcp_btn = gr.Button("🗑️ Delete Server", variant="stop")

    def _create_mcp_form(self):
        """Create the MCP server add/edit form."""
        mcp_server_names = self.config_editor.get_mcp_server_names()
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
            value=self.format_args_for_form(initial_mcp_config.get("args", [])) if initial_mcp_config else ""
        )
        mcp_env = gr.TextArea(
            label="Environment Variables (KEY=VALUE, one per line)",
            placeholder="API_KEY=your_key",
            value=self.format_env_for_form(initial_mcp_config.get("env", {})) if initial_mcp_config else ""
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
