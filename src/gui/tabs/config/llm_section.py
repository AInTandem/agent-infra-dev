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
LLM Configuration Section

Handles LLM provider and model configuration.
"""

from typing import Callable

import gradio as gr

from gui.config_editor import ConfigEditor
from .base_section import BaseConfigSection


class LLMSection(BaseConfigSection):
    """LLM configuration section with providers and models management."""

    @property
    def title(self) -> str:
        return "🧠 LLM"

    @property
    def tab_id(self) -> str:
        return "llm"

    def create(self) -> gr.Tab:
        """Create the LLM configuration section."""
        with gr.Tab(self.title) as tab:
            with gr.Row():
                with gr.Column(scale=1):
                    self._create_providers_panel()
                with gr.Column(scale=1):
                    self._create_provider_form()
                    self._create_model_form()
                    self._create_yaml_editor()

        return tab

    def _create_providers_panel(self):
        """Create the providers list and management panel."""
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

    def _create_provider_form(self):
        """Create the provider add/edit form."""
        gr.Markdown("#### Add/Edit Provider")

        llm_provider_names = self.config_editor.get_llm_provider_names()
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

    def _create_model_form(self):
        """Create the model add/edit form."""
        gr.Markdown("---")
        gr.Markdown("#### Add/Edit Model")

        llm_model_names = self.config_editor.get_llm_model_names()
        llm_provider_names = self.config_editor.get_llm_provider_names()

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

    def _create_yaml_editor(self):
        """Create the YAML editor for LLM configuration."""
        gr.Markdown("---")
        gr.Markdown("#### LLM Configuration (YAML Mode)")
        llm_yaml = gr.Code(
            label="YAML Configuration",
            language="yaml",
            value=self.config_editor.get_llm_yaml(),
            lines=15
        )
        update_llm_from_yaml_btn = gr.Button("Update from YAML", variant="secondary")
