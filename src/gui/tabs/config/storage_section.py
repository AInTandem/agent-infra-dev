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
Storage Configuration Section

Handles storage and cache configuration.
"""

from typing import Callable

import gradio as gr

from gui.config_editor import ConfigEditor
from .base_section import BaseConfigSection


class StorageSection(BaseConfigSection):
    """Storage configuration section."""

    @property
    def title(self) -> str:
        return "💾 Storage"

    @property
    def tab_id(self) -> str:
        return "storage"

    def create(self) -> gr.Tab:
        """Create the Storage configuration section."""
        with gr.Tab(self.title) as tab:
            with gr.Row():
                with gr.Column(scale=1):
                    self._create_storage_form()
                with gr.Column(scale=1):
                    self._create_storage_yaml_editor()

        return tab

    def _create_storage_form(self):
        """Create the storage configuration form."""
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

    def _create_storage_yaml_editor(self):
        """Create the YAML editor for storage configuration."""
        gr.Markdown("#### Storage Configuration (YAML Mode)")
        storage_yaml = gr.Code(
            label="YAML Configuration",
            language="yaml",
            value=self.config_editor.get_storage_yaml(),
            lines=20
        )
        update_storage_from_yaml_btn = gr.Button("Update from YAML", variant="secondary")
        storage_status = gr.Markdown("")
