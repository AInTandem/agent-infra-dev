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
WebSocket Chat Component for Gradio.

Provides real-time streaming reasoning display via WebSocket.
"""

import uuid
from typing import Optional

import gradio as gr


# CSS for WebSocket chat
WEBSOCKET_CHAT_CSS = """
.ws-status {
    padding: 8px 12px;
    border-radius: 4px;
    font-weight: 600;
    font-size: 14px;
    text-align: center;
    margin-bottom: 10px;
}

.ws-status-connecting {
    background-color: #fff3cd;
    color: #856404;
}

.ws-status-connected {
    background-color: #d4edda;
    color: #155724;
}

.ws-status-disconnected {
    background-color: #f8d7da;
    color: #721c24;
}

.ws-status-error {
    background-color: #f5c6cb;
    color: #721c24;
}

.ws-status-reconnecting {
    background-color: #ffe8d6;
    color: #856404;
}

#ws-session-container {
    max-height: 400px;
    overflow-y: auto;
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 15px;
    background-color: #f9f9f9;
}

.ws-reasoning-step {
    margin-bottom: 12px;
    padding: 10px;
    border-radius: 6px;
    animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(-5px); }
    to { opacity: 1; transform: translateY(0); }
}

.ws-step-thought {
    background-color: #e3f2fd;
    border-left: 4px solid #2196f3;
}

.ws-step-tool_use {
    background-color: #fff3e0;
    border-left: 4px solid #ff9800;
}

.ws-step-tool_result {
    background-color: #f3e5f5;
    border-left: 4px solid #9c27b0;
}

.ws-step-final_answer {
    background-color: #e8f5e9;
    border-left: 4px solid #4caf50;
}

.ws-step-error {
    background-color: #ffebee;
    border-left: 4px solid #f44336;
}

.ws-step-type {
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
    color: #666;
    margin-bottom: 4px;
}

.ws-step-content {
    margin-top: 8px;
    line-height: 1.5;
}

.ws-step-timestamp {
    font-size: 11px;
    color: #999;
    margin-top: 4px;
}

.ws-tool-name {
    font-weight: 600;
    color: #ff9800;
}

.ws-iteration {
    display: inline-block;
    background-color: #e0e0e0;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 11px;
    margin-left: 8px;
}
"""


class WebSocketChatComponent:
    """
    Gradio component for WebSocket-based real-time chat.

    Provides:
    - WebSocket client with auto-reconnect
    - Real-time reasoning step display
    - Status indicator
    - Custom HTML rendering
    """

    def __init__(self, api_host: str = "localhost", api_port: int = 8000):
        """
        Initialize the WebSocket chat component.

        Args:
            api_host: API server host
            api_port: API server port
        """
        self.api_host = api_host
        self.api_port = api_port
        self.ws_url = f"ws://{api_host}:{api_port}/ws/chat/"

    def create_interface(self) -> gr.Column:
        """
        Create the Gradio interface for WebSocket chat.

        Returns:
            Gradio Column component
        """
        with gr.Column() as component:
            # Debug info container
            debug_info = gr.HTML(
                value='<div id="ws-debug" style="background: #f0f0f0; padding: 10px; margin: 10px 0; border-radius: 4px; font-family: monospace; font-size: 12px;">🔍 Debug: Loading JavaScript...</div>'
            )

            # Status indicator
            status_html = gr.HTML(
                value='<div id="ws-status" class="ws-status ws-status-disconnected">Disconnected</div>'
            )

            # Session container for reasoning steps
            session_html = gr.HTML(
                value='<div id="ws-session-container"><p style="color: #666; text-align: center;">Connect to start chatting</p></div>'
            )

            # Input area
            with gr.Row():
                with gr.Column(scale=3):
                    message_input = gr.Textbox(
                        label="Message",
                        placeholder="Type your message here...",
                        lines=2,
                        interactive=True
                    )
                with gr.Column(scale=1):
                    send_btn = gr.Button("Send", variant="primary", size="lg")

            # Additional controls
            with gr.Row():
                agent_dropdown = gr.Dropdown(
                    label="Agent",
                    choices=["researcher", "developer", "writer", "analyst"],
                    value="researcher",
                    interactive=True
                )
                reasoning_toggle = gr.Checkbox(
                    label="Enable Reasoning",
                    value=True,
                    info="Show reasoning steps"
                )
                connect_btn = gr.Button("Connect", variant="secondary")

            # Hidden components for JavaScript interaction
            hidden_trigger = gr.Textbox(visible=False)
            hidden_output = gr.Textbox(visible=False)

            # Event handlers
            def on_connect(agent_name):
                # Return JavaScript to initialize WebSocket
                # Update debug info first
                debug_update = f"""
                <div id="ws-debug" style="background: #e3f2fd; padding: 10px; margin: 10px 0; border-radius: 4px; font-family: monospace; font-size: 12px;">
                🔍 Debug: Connect button clicked for agent '{agent_name}'<br>
                📝 Time: {__import__('datetime').datetime.now().strftime('%H:%M:%S')}<br>
                ⏳ Initializing WebSocket...
                </div>
                """

                # Return the JavaScript and debug update
                return f"""
                {debug_update}
                <script>
                (function() {{
                    console.log('[WS] ==================================================');
                    console.log('[WS] Connect button clicked at:', new Date().toLocaleTimeString());
                    console.log('[WS] Agent:', '{agent_name}');
                    console.log('[WS] Checking if functions exist...');

                    // Check if initWebSocketChat function exists
                    if (typeof initWebSocketChat === 'function') {{
                        console.log('[WS] ✓ initWebSocketChat function found');
                    }} else {{
                        console.error('[WS] ✗ initWebSocketChat function NOT found!');
                        updateDebug('❌ Error: initWebSocketChat function not loaded');
                        return;
                    }}

                    // Check if sendWebSocketMessage function exists
                    if (typeof sendWebSocketMessage === 'function') {{
                        console.log('[WS] ✓ sendWebSocketMessage function found');
                    }} else {{
                        console.error('[WS] ✗ sendWebSocketMessage function NOT found!');
                    }}

                    // Check WebSocket client status
                    if (typeof wsClient === 'undefined') {{
                        console.log('[WS] Creating new WebSocket client...');
                        updateDebug('🔧 Creating new WebSocket client...');
                    }} else if (!wsClient.isConnected) {{
                        console.log('[WS] Reconnecting existing client...');
                        updateDebug('🔄 Reconnecting WebSocket client...');
                    }} else {{
                        console.log('[WS] Client already connected');
                        updateDebug('✅ WebSocket client already connected');
                        return;
                    }}

                    // Initialize WebSocket
                    try {{
                        wsClient = initWebSocketChat();
                        console.log('[WS] WebSocket client created:', wsClient);

                        // Set up message handlers
                        wsClient.on('connected', (data) => {{
                            console.log('[WS] ✓ Connected event received:', data);
                            updateDebug('✅ WebSocket Connected! Session: ' + data.data.session_id);
                        }});

                        wsClient.on('reasoning_start', (data) => {{
                            console.log('[WS] Reasoning started');
                            updateDebug('🤔 Reasoning started...');
                            const container = document.getElementById('ws-session-container');
                            if (container) {{
                                container.innerHTML = '<div class="ws-reasoning-step ws-step-thought"><div class="ws-step-type">Starting reasoning...</div></div>';
                            }}
                        }});

                        wsClient.on('reasoning_step', (data) => {{
                            console.log('[WS] Reasoning step received:', data);
                            updateDebug('📨 Step received: ' + data.data.type);
                            const container = document.getElementById('ws-session-container');
                            if (!container) return;

                            const step = data.data;
                            const stepType = step.type;

                            let stepClass = 'ws-step-thought';
                            let typeLabel = 'Thought';

                            if (stepType === 'tool_use') {{
                                stepClass = 'ws-step-tool_use';
                                typeLabel = 'Tool Use';
                            }} else if (stepType === 'tool_result') {{
                                stepClass = 'ws-step-tool_result';
                                typeLabel = 'Tool Result';
                            }} else if (stepType === 'final_answer') {{
                                stepClass = 'ws-step-final_answer';
                                typeLabel = 'Final Answer';
                            }} else if (stepType === 'error') {{
                                stepClass = 'ws-step-error';
                                typeLabel = 'Error';
                            }}

                            const timestamp = new Date(step.timestamp * 1000).toLocaleTimeString();
                            const iteration = step.iteration ? `<span class="ws-iteration">Iter: ${{step.iteration}}</span>` : '';
                            const toolName = step.tool_name ? `<span class="ws-tool-name">${{step.tool_name}}</span>` : '';

                            const stepHtml = `
                                <div class="${{stepClass}}">
                                    <div class="ws-step-type">${{typeLabel}} ${{iteration}} ${{toolName}}</div>
                                    <div class="ws-step-content">${{escapeHtml(step.content)}}</div>
                                    <div class="ws-step-timestamp">${{timestamp}}</div>
                                </div>
                            `;

                            container.insertAdjacentHTML('beforeend', stepHtml);
                            container.scrollTop = container.scrollHeight;
                        }});

                        wsClient.on('reasoning_complete', () => {{
                            console.log('[WS] Reasoning complete');
                            updateDebug('✅ Reasoning complete!');
                            const container = document.getElementById('ws-session-container');
                            if (container) {{
                                container.insertAdjacentHTML('beforeend',
                                    '<div class="ws-reasoning-step ws-step-final_answer"><div class="ws-step-type">✓ Complete</div></div>'
                                );
                            }}
                        }});

                        wsClient.on('error', (data) => {{
                            console.error('[WS] Error:', data);
                            updateDebug('❌ Error: ' + data.data.message);
                            const container = document.getElementById('ws-session-container');
                            if (container) {{
                                container.insertAdjacentHTML('beforeend',
                                    `<div class="ws-reasoning-step ws-step-error"><div class="ws-step-type">Error</div><div class="ws-step-content">${{escapeHtml(data.data.message)}}</div></div>`
                                );
                            }}
                        }});

                        console.log('[WS] Message handlers registered');
                        updateDebug('⚙️ Message handlers registered, waiting for connection...');

                    }} catch (error) {{
                        console.error('[WS] Initialization error:', error);
                        updateDebug('❌ Initialization error: ' + error.message);
                    }}

                    console.log('[WS] ==================================================');

                    // Helper function to update debug info
                    function updateDebug(message) {{
                        const debugDiv = document.getElementById('ws-debug');
                        if (debugDiv) {{
                            const time = new Date().toLocaleTimeString();
                            debugDiv.innerHTML = `<div style="background: #e3f2fd; padding: 10px; margin: 10px 0; border-radius: 4px; font-family: monospace; font-size: 12px;">🔍 [${{time}}] ${{message}}</div>`;
                        }}
                    }}
                }})();
                </script>
                """

            def on_send(message, agent_name, enable_reasoning):
                # Return JavaScript to send message via WebSocket
                import json
                escaped_message = json.dumps(message)  # Properly escape the message
                reasoning_bool = "true" if enable_reasoning else "false"
                # Use format() instead of f-string to avoid brace escaping issues
                return """
                <script>
                (function() {{
                    console.log('[WS] ==================================================');
                    console.log('[WS] Send button clicked');
                    console.log('[WS] Message:', {escaped_msg});
                    console.log('[WS] Agent:', '{agent}');
                    console.log('[WS] Enable Reasoning:', {reasoning});

                    // Update debug info
                    const debugDiv = document.getElementById('ws-debug');
                    if (debugDiv) {{
                        const time = new Date().toLocaleTimeString();
                        debugDiv.innerHTML = `<div style="background: #fff3e0; padding: 10px; margin: 10px 0; border-radius: 4px; font-family: monospace; font-size: 12px;">📤 [${{time}}] Sending message to '{agent}'...</div>`;
                    }}

                    if (typeof sendWebSocketMessage === 'function') {{
                        console.log('[WS] ✓ sendWebSocketMessage function found');
                        console.log('[WS] Calling sendWebSocketMessage...');
                        sendWebSocketMessage({escaped_msg}, '{agent}', {reasoning});
                        console.log('[WS] sendWebSocketMessage called');
                    }} else {{
                        console.error('[WS] ✗ sendWebSocketMessage function NOT found!');
                        if (debugDiv) {{
                            const time = new Date().toLocaleTimeString();
                            debugDiv.innerHTML = `<div style="background: #ffebee; padding: 10px; margin: 10px 0; border-radius: 4px; font-family: monospace; font-size: 12px;">❌ [${{time}}] Error: sendWebSocketMessage function not loaded. Please click Connect first.</div>`;
                        }}
                    }}
                    console.log('[WS] ==================================================');
                }})();
                </script>
                """.format(
                    escaped_msg=escaped_message,
                    agent=agent_name,
                    reasoning=reasoning_bool
                )

            connect_btn.click(
                fn=on_connect,
                inputs=[agent_dropdown],
                outputs=[session_html]
            )

            send_btn.click(
                fn=on_send,
                inputs=[message_input, agent_dropdown, reasoning_toggle],
                outputs=[session_html]
            )

            # Allow Enter key to send
            message_input.submit(
                fn=on_send,
                inputs=[message_input, agent_dropdown, reasoning_toggle],
                outputs=[session_html]
            )

        return component

    def get_custom_js(self) -> str:
        """
        Get the JavaScript code for the WebSocket client.

        Note: JavaScript is now loaded externally via Gradio's head_paths parameter.
        This method returns empty string as the JavaScript is in static/websocket_chat.js.
        """
        return ""

    def get_custom_css(self) -> str:
        """Get the CSS for the WebSocket chat component."""
        return WEBSOCKET_CHAT_CSS


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    if not text:
        return ""
    return (text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#039;"))
