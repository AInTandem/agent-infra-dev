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
Config Tab for Gradio GUI.

Provides configuration editing interface with modular sub-sections.
"""

from typing import Optional

import gradio as gr

from core.agent_manager import AgentManager
from core.config import ConfigManager
from core.task_scheduler import TaskScheduler
from gui.config_editor import ConfigEditor
from ..base_tab import BaseTab


class ConfigTab(BaseTab):
    """
    Configuration editor tab with modular sub-sections.

    This tab orchestrates multiple configuration sections:
    - LLM Configuration
    - Agents Configuration
    - MCP Servers Configuration
    - Storage Configuration
    - App Configuration
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        agent_manager: Optional[AgentManager] = None,
        task_scheduler: Optional[TaskScheduler] = None
    ):
        """
        Initialize the Config tab.

        Args:
            config_manager: Configuration manager
            agent_manager: Agent manager instance (optional)
            task_scheduler: Task scheduler instance (optional)
        """
        super().__init__(config_manager, agent_manager, task_scheduler)
        self.config_editor = ConfigEditor(config_manager)

    @property
    def title(self) -> str:
        """Tab title."""
        return "📝 Configuration"

    @property
    def description(self) -> Optional[str]:
        """Tab description."""
        return "Edit system configuration"

    def create(self) -> gr.Column:
        """
        Create the configuration editor tab.

        Returns:
            gr.Column: The configuration interface column
        """
        with gr.Column() as component:
            gr.Markdown("### Configuration Editor")

            # Pending changes indicator
            with gr.Row():
                pending_info = gr.Markdown("**Pending Changes:** 0")
                refresh_config_btn = gr.Button("🔄 Reload from Files", size="sm")

            # Import section modules here to avoid circular imports
            from .llm_section import LLMSection
            from .agents_section import AgentsSection
            from .mcp_section import MCPSection
            from .storage_section import StorageSection
            from .app_section import AppSection

            # Define update_pending function
            def update_pending_info():
                count = self.config_editor.get_pending_changes_count()
                changes = self.config_editor.get_pending_changes_list()
                if changes:
                    return f"**Pending Changes:** {count} ({', '.join(changes)})", count
                return "**Pending Changes:** 0", 0

            # Create sections
            llm_section = LLMSection(self.config_editor, update_pending_info)
            agents_section = AgentsSection(self.config_editor, update_pending_info)
            mcp_section = MCPSection(self.config_editor, update_pending_info)
            storage_section = StorageSection(self.config_editor, update_pending_info)
            app_section = AppSection(self.config_editor, update_pending_info)

            with gr.Tabs():
                llm_tab = llm_section.create()
                agents_tab = agents_section.create()
                mcp_tab = mcp_section.create()
                storage_tab = storage_section.create()
                app_tab = app_section.create()

            # Batch operations
            with gr.Row():
                with gr.Column(scale=3):
                    gr.Markdown("#### Batch Operations")
                with gr.Column(scale=1):
                    pending_count = gr.Number(label="Pending Changes", value=0, interactive=False)
                    discard_btn = gr.Button("🗑️ Discard All", variant="secondary")
                    save_all_btn = gr.Button("💾 Save All Changes", variant="primary")

            save_result = gr.Markdown("")

            # Batch operation event handlers
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

        return component

    def get_custom_css(self) -> str:
        """
        Get custom CSS for this tab.

        Returns:
            str: Custom CSS styles
        """
        return """
        .config-container {
            padding: 16px;
        }

        .config-section {
            background-color: #f9f9f9;
            border-radius: 8px;
            padding: 16px;
            margin: 8px 0;
        }

        .config-form {
            background-color: #ffffff;
            border-radius: 8px;
            padding: 16px;
        }

        .pending-indicator {
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 8px 12px;
            border-radius: 4px;
        }
        """
