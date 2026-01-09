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
Real-Time Chat Tab

WebSocket-based real-time streaming chat interface with reasoning display.
"""

import gradio as gr

from core.config import ConfigManager
from core.agent_manager import AgentManager
from .base_tab import BaseTab
from ..websocket_chat import WebSocketChatComponent


class RealtimeChatTab(BaseTab):
    """
    Real-time streaming chat tab using WebSocket.

    Provides live reasoning step display as the agent thinks.
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        agent_manager: AgentManager,
        api_host: str = "localhost",
        api_port: int = 8000,
    ):
        """
        Initialize the Real-Time Chat tab.

        Args:
            config_manager: Configuration manager instance
            agent_manager: Agent manager instance
            api_host: WebSocket server host
            api_port: WebSocket server port
        """
        super().__init__(config_manager, agent_manager)

        self.api_host = api_host
        self.api_port = api_port

        # Initialize WebSocket chat component
        self.ws_chat = WebSocketChatComponent(
            api_host=api_host,
            api_port=api_port
        )

    @property
    def title(self) -> str:
        """Tab title."""
        return "⚡ Real-Time Chat"

    @property
    def description(self) -> str:
        """Tab description."""
        return "WebSocket-based real-time agent chat with streaming reasoning display."

    def create(self) -> gr.Column:
        """
        Create the Real-Time Chat tab interface.

        Returns:
            Gradio Column component
        """
        with gr.Column() as component:
            # Load custom CSS for this tab
            gr.HTML(f"<style>{self.get_custom_css()}</style>")

            # Debug info - JavaScript loading status
            debug_html = gr.HTML(
                value='<div id="ws-debug" style="background: #e3f2fd; padding: 10px; margin: 10px 0; border-radius: 4px; font-family: monospace; font-size: 12px;">🔍 Debug: Initializing...</div>'
            )

            # Tab header and instructions
            gr.Markdown("### ⚡ Real-Time Streaming Chat")
            gr.Markdown("""
            **WebSocket-based real-time agent chat with streaming reasoning display.**

            **Instructions:**
            1. Open browser console (F12) to see detailed logs
            2. Check for "[WS] ===== websocket_chat.js LOADED =====" message
            3. Click "Connect" to establish WebSocket connection
            4. Type your message and click "Send"
            5. Watch reasoning steps appear in real-time

            **Troubleshooting:**
            - If you don't see "[WS] ===== websocket_chat.js LOADED =====" in console,
              the JavaScript file may not be loading correctly.
            - Check that static/websocket_chat.js exists
            - Verify head_paths parameter is set in main.py
            """)

            # Create the WebSocket chat component
            ws_component = self.ws_chat.create_interface()

            # Store reference for potential future use
            self._ws_component = ws_component

        return component

    def get_custom_css(self) -> str:
        """
        Get custom CSS for the Real-Time Chat tab.

        Returns:
            CSS string for styling the tab
        """
        # Combine tab-specific CSS with WebSocket component CSS
        tab_css = """
        .realtime-chat-container {
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 16px;
            background-color: #fafafa;
        }

        .realtime-chat-debug {
            background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%);
            border-left: 4px solid #2196f3;
            padding: 12px;
            margin: 16px 0;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }
        """

        return tab_css + self.ws_chat.get_custom_css()

    def get_custom_js(self) -> str:
        """
        Get custom JavaScript for this tab.

        Note: The main WebSocket JavaScript is loaded via head_paths
        in main.py. This method returns additional debugging JS.

        Returns:
            JavaScript string for tab functionality
        """
        return f"""
        console.log('[RealTimeChatTab] Tab initialized');

        // Verify that the WebSocket JavaScript has been loaded
        setTimeout(function() {{
            if (typeof initWebSocketChat === 'function') {{
                console.log('[RealTimeChatTab] ✓ WebSocket JavaScript is available');
                updateDebug('✅ WebSocket JavaScript loaded successfully!');
            }} else {{
                console.error('[RealTimeChatTab] ✗ WebSocket JavaScript NOT found!');
                updateDebug('❌ Error: WebSocket JavaScript not loaded. Check head_paths in main.py');
            }}
        }}, 1000);

        function updateDebug(message) {{
            const debugDiv = document.getElementById('ws-debug');
            if (debugDiv) {{
                const time = new Date().toLocaleTimeString();
                debugDiv.innerHTML = `<div class="realtime-chat-debug">🔍 [${{time}}] ${{message}}</div>`;
            }}
        }}
        """

    def get_tab_id(self) -> str:
        """
        Get unique identifier for this tab.

        Returns:
            Tab identifier string
        """
        return "realtime_chat"
