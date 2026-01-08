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


# JavaScript code for WebSocket client
WEBSOCKET_CLIENT_JS = """
class WebSocketChatClient {
    constructor(wsUrl, sessionContainer, statusElement) {
        this.wsUrl = wsUrl;
        this.sessionContainer = sessionContainer;
        this.statusElement = statusElement;
        this.ws = null;
        this.sessionId = this.generateSessionId();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000; // 2 seconds
        this.isConnected = false;
        this.messageHandlers = new Map();
    }

    generateSessionId() {
        return 'session_' + Math.random().toString(36).substr(2, 9);
    }

    connect() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            console.log('[WS] Already connected');
            return;
        }

        this.updateStatus('Connecting...', 'connecting');
        this.ws = new WebSocket(this.wsUrl + '?session_id=' + this.sessionId);

        this.ws.onopen = () => {
            console.log('[WS] Connected:', this.sessionId);
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.updateStatus('Connected', 'connected');
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.ws.onerror = (error) => {
            console.error('[WS] Error:', error);
            this.updateStatus('Error', 'error');
        };

        this.ws.onclose = () => {
            console.log('[WS] Disconnected');
            this.isConnected = false;
            this.updateStatus('Disconnected', 'disconnected');
            this.attemptReconnect();
        };
    }

    disconnect() {
        if (this.ws) {
            this.reconnectAttempts = this.maxReconnectAttempts; // Prevent reconnection
            this.ws.close();
            this.ws = null;
        }
        this.isConnected = false;
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = this.reconnectDelay * this.reconnectAttempts;
            this.updateStatus(`Reconnecting in ${delay/1000}s...`, 'reconnecting');

            setTimeout(() => {
                console.log(`[WS] Reconnect attempt ${this.reconnectAttempts}`);
                this.connect();
            }, delay);
        }
    }

    sendChatMessage(message, agentName, enableReasoning) {
        if (!this.isConnected) {
            console.error('[WS] Not connected');
            return;
        }

        const payload = {
            type: 'chat',
            payload: {
                message: message,
                agent_name: agentName,
                enable_reasoning: enableReasoning
            }
        };

        this.ws.send(JSON.stringify(payload));
        console.log('[WS] Sent chat message');
    }

    sendPing() {
        if (!this.isConnected) return;

        const payload = {
            type: 'ping',
            payload: {
                timestamp: Date.now() / 1000
            }
        };

        this.ws.send(JSON.stringify(payload));
    }

    handleMessage(data) {
        const handler = this.messageHandlers.get(data.type);
        if (handler) {
            handler(data);
        }

        // Global handlers
        switch (data.type) {
            case 'connected':
                console.log('[WS] Session confirmed:', data.data.session_id);
                this.onConnected(data);
                break;
            case 'reasoning_start':
                this.onReasoningStart(data);
                break;
            case 'reasoning_step':
                this.onReasoningStep(data);
                break;
            case 'reasoning_complete':
                this.onReasoningComplete(data);
                break;
            case 'error':
                this.onError(data);
                break;
            case 'pong':
                // Heartbeat response
                break;
        }
    }

    onConnected(data) {
        // Can be overridden
    }

    onReasoningStart(data) {
        // Can be overridden
    }

    onReasoningStep(data) {
        // Can be overridden
    }

    onReasoningComplete(data) {
        // Can be overridden
    }

    onError(data) {
        console.error('[WS] Server error:', data.data.message);
    }

    on(event, handler) {
        this.messageHandlers.set(event, handler);
    }

    updateStatus(text, status) {
        if (this.statusElement) {
            this.statusElement.textContent = text;
            this.statusElement.className = 'ws-status ws-status-' + status;
        }
    }
}

// Global client instance
let wsClient = null;

function initWebSocketChat() {
    const wsUrl = 'ws://' + window.location.host + '/ws/chat/';
    const sessionContainer = document.getElementById('ws-session-container');
    const statusElement = document.getElementById('ws-status');

    wsClient = new WebSocketChatClient(wsUrl, sessionContainer, statusElement);
    wsClient.connect();

    // Send heartbeat every 30 seconds
    setInterval(() => {
        if (wsClient && wsClient.isConnected) {
            wsClient.sendPing();
        }
    }, 30000);

    return wsClient;
}

function sendWebSocketMessage(message, agentName, enableReasoning) {
    if (!wsClient) {
        wsClient = initWebSocketChat();
    }

    if (!wsClient.isConnected) {
        wsClient.connect();
        // Wait for connection
        setTimeout(() => {
            wsClient.sendChatMessage(message, agentName, enableReasoning);
        }, 500);
    } else {
        wsClient.sendChatMessage(message, agentName, enableReasoning);
    }
}
"""

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
                return f"""
                <script>
                if (typeof wsClient === 'undefined' || !wsClient.isConnected) {{
                    wsClient = initWebSocketChat();

                    // Set up message handlers
                    wsClient.on('reasoning_start', (data) => {{
                        const container = document.getElementById('ws-session-container');
                        container.innerHTML = '<div class="ws-reasoning-step ws-step-thought"><div class="ws-step-type">Starting reasoning...</div></div>';
                    }});

                    wsClient.on('reasoning_step', (data) => {{
                        const container = document.getElementById('ws-session-container');
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
                        const iteration = step.iteration ? `<span class="ws-iteration">Iter: {{step.iteration}}</span>` : '';
                        const toolName = step.tool_name ? `<span class="ws-tool-name">{{step.tool_name}}</span>` : '';

                        const stepHtml = `
                            <div class="ws-reasoning-step {{stepClass}}">
                                <div class="ws-step-type">{{typeLabel}} {{iteration}} {{toolName}}</div>
                                <div class="ws-step-content">{{escapeHtml(step.content)}}</div>
                                <div class="ws-step-timestamp">{{timestamp}}</div>
                            </div>
                        `;

                        container.insertAdjacentHTML('beforeend', stepHtml);
                        container.scrollTop = container.scrollHeight;
                    }});

                    wsClient.on('reasoning_complete', () => {{
                        const container = document.getElementById('ws-session-container');
                        container.insertAdjacentHTML('beforeend',
                            '<div class="ws-reasoning-step ws-step-final_answer"><div class="ws-step-type">✓ Complete</div></div>'
                        );
                    }});

                    wsClient.on('error', (data) => {{
                        const container = document.getElementById('ws-session-container');
                        container.insertAdjacentHTML('beforeend',
                            `<div class="ws-reasoning-step ws-step-error"><div class="ws-step-type">Error</div><div class="ws-step-content">{{escapeHtml(data.data.message)}}</div></div>`
                        );
                    }});
                }}
                </script>
                """

            def on_send(message, agent_name, enable_reasoning):
                # Return JavaScript to send message via WebSocket
                escaped_message = message.replace("'", "\\'").replace('"', '\\"')
                return f"""
                <script>
                sendWebSocketMessage('{escaped_message}', '{agent_name}', {str(enable_reasoning).lower()});
                </script>
                """

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
        """Get the JavaScript code for the WebSocket client."""
        return WEBSOCKET_CLIENT_JS

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
