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
Gradio GUI for AInTandem Agent MCP Scheduler.

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
from gui.config_editor import ConfigEditor
from gui.websocket_chat import WebSocketChatComponent


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

        # Initialize config editor
        self.config_editor = ConfigEditor(config_manager)

        # Initialize tab modules (using new modular architecture)
        # Phase 4: Gradually migrating to tab modules
        from .tabs import AgentsTab, ChatTab, ConfigTab, RealtimeChatTab, SettingsTab, TasksTab

        self.chat_tab = ChatTab(
            config_manager=config_manager,
            agent_manager=agent_manager,
            task_scheduler=task_scheduler
        )

        self.realtime_chat_tab = RealtimeChatTab(
            config_manager=config_manager,
            agent_manager=agent_manager,
            api_host="localhost",
            api_port=8000
        )

        self.agents_tab = AgentsTab(
            config_manager=config_manager,
            agent_manager=agent_manager,
            task_scheduler=task_scheduler
        )

        self.tasks_tab = TasksTab(
            config_manager=config_manager,
            agent_manager=agent_manager,
            task_scheduler=task_scheduler
        )

        self.settings_tab = SettingsTab(
            config_manager=config_manager,
            agent_manager=agent_manager,
            task_scheduler=task_scheduler
        )

        self.config_tab = ConfigTab(
            config_manager=config_manager
        )

        # Keep legacy ws_chat for backward compatibility (will be removed)
        self.ws_chat = self.realtime_chat_tab.ws_chat

        # Create Gradio interface
        self.app = self._create_interface()

    def _create_interface(self) -> gr.Blocks:
        """Create the Gradio interface."""
        # Note: In Gradio 6.0+, theme and css are passed to launch(), not Blocks()
        # We'll inject JavaScript/CSS through the interface itself
        with gr.Blocks(title="AInTandem Agent MCP Scheduler") as app:
            gr.Markdown("# 🤖 AInTandem Agent MCP Scheduler")

            with gr.Tabs():
                # Tab 1: Chat (Original)
                with gr.Tab(self.chat_tab.title):
                    self.chat_tab.create()

                # Tab 1.5: Real-Time Chat (WebSocket Streaming)
                # Phase 4: Using modular tab instead of inline method
                with gr.Tab(self.realtime_chat_tab.title):
                    self.realtime_chat_tab.create()

                # Tab 2: Tasks
                with gr.Tab(self.tasks_tab.title):
                    self.tasks_tab.create()

                # Tab 3: Agents
                with gr.Tab(self.agents_tab.title):
                    self.agents_tab.create()

                # Tab 4: Settings
                with gr.Tab(self.settings_tab.title):
                    self.settings_tab.create()

                # Tab 5: Configuration
                with gr.Tab(self.config_tab.title):
                    self.config_tab.create()

        return app

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
