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
App Configuration Section

Handles application-level configuration.
"""

from typing import Callable

import gradio as gr

from gui.config_editor import ConfigEditor
from .base_section import BaseConfigSection


class AppSection(BaseConfigSection):
    """App configuration section."""

    @property
    def title(self) -> str:
        return "⚙️ App"

    @property
    def tab_id(self) -> str:
        return "app"

    def create(self) -> gr.Tab:
        """Create the App configuration section."""
        with gr.Tab(self.title) as tab:
            with gr.Row():
                with gr.Column(scale=1):
                    self._create_app_form()
                with gr.Column(scale=1):
                    self._create_app_yaml_editor()

        return tab

    def _create_app_form(self):
        """Create the app configuration form."""
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

    def _create_app_yaml_editor(self):
        """Create the YAML editor for app configuration."""
        gr.Markdown("#### App Configuration (YAML Mode)")
        app_yaml = gr.Code(
            label="YAML Configuration",
            language="yaml",
            value=self.config_editor.get_app_yaml(),
            lines=20
        )
        update_app_from_yaml_btn = gr.Button("Update from YAML", variant="secondary")
        app_status = gr.Markdown("")
