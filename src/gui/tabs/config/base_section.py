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
Base Configuration Section Class

Provides common functionality for all configuration sections.
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable, Tuple, List, Any

import gradio as gr

from gui.config_editor import ConfigEditor


class BaseConfigSection(ABC):
    """
    Base class for configuration sections.

    Each section (LLM, Agents, MCP, Storage, App) inherits from this class.
    """

    def __init__(self, config_editor: ConfigEditor, update_pending_fn: Callable):
        """
        Initialize the configuration section.

        Args:
            config_editor: ConfigEditor instance for configuration management
            update_pending_fn: Function to update pending changes info
        """
        self.config_editor = config_editor
        self.update_pending_fn = update_pending_fn

    @property
    @abstractmethod
    def title(self) -> str:
        """Section title (e.g., '🧠 LLM')."""
        pass

    @property
    @abstractmethod
    def tab_id(self) -> str:
        """Tab ID (e.g., 'llm')."""
        pass

    @abstractmethod
    def create(self) -> gr.Tab:
        """
        Create the configuration section interface.

        Returns:
            gr.Tab: The Gradio Tab component
        """
        pass

    def format_args_for_form(self, args_list: List[str]) -> str:
        """
        Format args list for textarea display.

        Args:
            args_list: List of command line arguments

        Returns:
            str: Arguments formatted as text (one per line)
        """
        return "\n".join(args_list) if args_list else ""

    def format_env_for_form(self, env_dict: dict) -> str:
        """
        Format env dict for textarea display.

        Args:
            env_dict: Dictionary of environment variables

        Returns:
            str: Environment variables formatted as text (KEY=VALUE, one per line)
        """
        return "\n".join([f"{k}={v}" for k, v in env_dict.items()]) if env_dict else ""

    def parse_args_from_form(self, args_text: str) -> List[str]:
        """
        Parse args from textarea input.

        Args:
            args_text: Arguments text (one per line)

        Returns:
            List[str]: List of arguments
        """
        if not args_text or not args_text.strip():
            return []
        return [line.strip() for line in args_text.strip().split("\n") if line.strip()]

    def parse_env_from_form(self, env_text: str) -> dict:
        """
        Parse env variables from textarea input.

        Args:
            env_text: Environment variables text (KEY=VALUE, one per line)

        Returns:
            dict: Dictionary of environment variables
        """
        if not env_text or not env_text.strip():
            return {}
        env_dict = {}
        for line in env_text.strip().split("\n"):
            line = line.strip()
            if "=" in line:
                key, value = line.split("=", 1)
                env_dict[key.strip()] = value.strip()
        return env_dict

    def update_with_pending_info(self, result: str) -> Tuple[str, str, int]:
        """
        Update result with pending changes info.

        Args:
            result: Operation result message

        Returns:
            Tuple of (result, pending_info_text, pending_count)
        """
        pending_info, pending_count = self.update_pending_fn()
        return result, pending_info, pending_count
