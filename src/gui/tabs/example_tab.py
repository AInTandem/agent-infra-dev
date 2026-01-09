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
Example Tab Implementation

This is an example showing how to implement a tab using BaseTab.
"""

import gradio as gr

from core.config import ConfigManager
from core.agent_manager import AgentManager
from .base_tab import BaseTab


class ExampleTab(BaseTab):
    """
    Example tab implementation for demonstration purposes.
    """

    @property
    def title(self) -> str:
        """Tab title."""
        return "📝 Example"

    @property
    def description(self) -> str:
        """Tab description."""
        return "This is an example tab implementation."

    def create(self) -> gr.Column:
        """
        Create the tab interface.

        Returns:
            Gradio Column component
        """
        with gr.Column() as component:
            gr.Markdown(f"### {self.title}")
            gr.Markdown(self.description)

            gr.Markdown("#### Features")

            with gr.Row():
                with gr.Column():
                    gr.Textbox(
                        label="Input",
                        placeholder="Type something...",
                        value="Hello from Example Tab!"
                    )
                with gr.Column():
                    gr.Textbox(
                        label="Output",
                        value="This tab inherits from BaseTab",
                        interactive=False
                    )

            gr.Button("Click Me", variant="primary")

        return component

    def get_custom_css(self) -> str:
        """Optional custom CSS."""
        return """
        .example-tab {
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            padding: 16px;
        }
        """

    def get_custom_js(self) -> str:
        """Optional custom JavaScript."""
        return """
        console.log('Example Tab loaded!');
        """
