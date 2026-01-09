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
Base Tab Class for Gradio GUI

Provides a common interface for all tab implementations.
"""

from abc import ABC, abstractmethod
from typing import Optional

import gradio as gr

from core.config import ConfigManager
from core.agent_manager import AgentManager


class BaseTab(ABC):
    """
    Base class for all Gradio tabs.

    All tab implementations should inherit from this class and implement
    the required abstract methods.
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        agent_manager: AgentManager,
        task_scheduler: Optional["TaskScheduler"] = None,
    ):
        """
        Initialize the tab with shared dependencies.

        Args:
            config_manager: Configuration manager instance
            agent_manager: Agent manager instance
            task_scheduler: Optional task scheduler instance
        """
        self.config_manager = config_manager
        self.agent_manager = agent_manager
        self.task_scheduler = task_scheduler

    @property
    @abstractmethod
    def title(self) -> str:
        """
        Tab title displayed in the UI.

        Examples:
            "💬 Chat"
            "⚡ Real-Time Chat"
            "🤖 Agents"
        """
        pass

    @property
    def description(self) -> Optional[str]:
        """
        Optional tab description shown below the title.

        Returns:
            Description text or None
        """
        return None

    @abstractmethod
    def create(self) -> gr.Blocks:
        """
        Create and return the Gradio interface for this tab.

        This method should build the entire tab interface using Gradio components.

        Returns:
            Gradio Blocks or Column component containing the tab interface
        """
        pass

    def get_custom_css(self) -> str:
        """
        Optional custom CSS for this tab.

        Returns:
            CSS string to inject into the page
        """
        return ""

    def get_custom_js(self) -> str:
        """
        Optional custom JavaScript for this tab.

        Note: For Gradio 6.x, consider using head_paths parameter
        in the main app.launch() instead.

        Returns:
            JavaScript string to inject into the page
        """
        return ""

    def get_tab_id(self) -> str:
        """
        Get a unique identifier for this tab.

        Can be used for CSS targeting or state management.

        Returns:
            Unique tab identifier (e.g., "chat", "realtime_chat")
        """
        # Generate from class name: RealtimeChatTab -> "realtime_chat"
        class_name = self.__class__.__name__
        if class_name.endswith("Tab"):
            class_name = class_name[:-3]
        # Convert CamelCase to snake_case
        import re
        name = re.sub("([A-Z])", r"_\1", class_name).lower().lstrip("_")
        return name
