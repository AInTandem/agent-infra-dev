/**
 * WebSocket Chat Client for Real-Time Agent Chat
 *
 * This script provides WebSocket functionality for real-time streaming reasoning display.
 */

console.log('[WS] ===== websocket_chat.js LOADED =====');

// ============================================================================
// WebSocket Chat Client Class
// ============================================================================

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
        return 'session_' + Math.random().toString(36).substring(2, 11);
    }

    connect() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            console.log('[WS] Already connected');
            return;
        }

        this.updateStatus('Connecting...', 'connecting');
        // Session ID should be part of the URL path, not query parameter
        this.ws = new WebSocket(this.wsUrl + this.sessionId);

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
            console.error('[WS] WebSocket error occurred');
            console.error('[WS] URL:', this.wsUrl + this.sessionId);
            console.error('[WS] ReadyState:', this.ws ? this.ws.readyState : 'no ws object');
            this.updateStatus('Connection Error', 'error');
        };

        this.ws.onclose = (event) => {
            console.log('[WS] Connection closed');
            console.log('[WS] Code:', event.code, 'Reason:', event.reason || 'No reason provided');
            console.log('[WS] Was clean:', event.wasClean);
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

        const payloadStr = JSON.stringify(payload);
        console.log('[WS] Sending chat message:', payloadStr);
        console.log('[WS] WebSocket readyState:', this.ws.readyState);
        console.log('[WS] isConnected:', this.isConnected);

        this.ws.send(payloadStr);
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
        console.log('[WS] handleMessage called, type:', data.type);
        console.log('[WS] Message data:', data);

        const handler = this.messageHandlers.get(data.type);
        if (handler) {
            console.log('[WS] Found handler for type:', data.type);
            handler(data);
        } else {
            console.log('[WS] No handler found for type:', data.type);
            console.log('[WS] Available handlers:', Array.from(this.messageHandlers.keys()));
        }

        // Global handlers
        switch (data.type) {
            case 'connected':
                console.log('[WS] Session confirmed:', data.data.session_id);
                this.onConnected(data);
                break;
            case 'reasoning_start':
                console.log('[WS] Reasoning start received');
                this.onReasoningStart(data);
                break;
            case 'reasoning_step':
                console.log('[WS] Reasoning step received:', data);
                this.onReasoningStep(data);
                break;
            case 'reasoning_complete':
                console.log('[WS] Reasoning complete received');
                this.onReasoningComplete(data);
                break;
            case 'error':
                this.onError(data);
                break;
            case 'pong':
                // Heartbeat response
                break;
            default:
                console.log('[WS] Unknown message type:', data.type);
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
        console.log('[WS] Registering handler for event:', event);
        console.log('[WS] Current handlers before:', Array.from(this.messageHandlers.keys()));
        this.messageHandlers.set(event, handler);
        console.log('[WS] Current handlers after:', Array.from(this.messageHandlers.keys()));
    }

    updateStatus(text, status) {
        if (this.statusElement) {
            this.statusElement.textContent = text;
            this.statusElement.className = 'ws-status ws-status-' + status;
        }
    }
}

// ============================================================================
// Global Functions
// ============================================================================

// Global client instance
let wsClient = null;

function initWebSocketChat() {
    console.log('[WS] initWebSocketChat called');
    // Determine WebSocket URL based on current location
    // If running on Gradio port (7860), connect to API port (8000)
    const apiHost = window.location.hostname;
    const apiPort = 8000;  // API server port
    const wsUrl = 'ws://' + apiHost + ':' + apiPort + '/ws/chat/';
    console.log('[WS] Connecting to:', wsUrl);
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
    console.log('[WS] sendWebSocketMessage called:', message);
    console.log('[WS] wsClient exists:', !!wsClient);
    console.log('[WS] wsClient.isConnected:', wsClient ? wsClient.isConnected : 'no client');

    if (!wsClient || !wsClient.isConnected) {
        console.error('[WS] Cannot send message: WebSocket not connected. Please click Connect first.');
        gradioUpdateDebug('❌ Error: WebSocket not connected. Please click Connect first.');
        return;
    }

    wsClient.sendChatMessage(message, agentName, enableReasoning);
}

// Helper function to escape HTML
function escapeHtml(text) {
    if (!text) return "";
    return text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#039;");
}

// ============================================================================
// Initialization
// ============================================================================

console.log('[WS] Functions defined:', typeof initWebSocketChat, typeof sendWebSocketMessage);
console.log('[WS] ===== websocket_chat.js READY =====');

// ============================================================================
// Gradio Integration Functions (Glue Code)
// ============================================================================

/**
 * Connect button handler for Gradio
 * Called when user clicks "Connect" button in the UI
 */
function gradioConnect(agentName) {
    console.log('[WS] ==================================================');
    console.log('[WS] Connect button clicked at:', new Date().toLocaleTimeString());
    console.log('[WS] Agent:', agentName);
    console.log('[WS] Checking if functions exist...');

    // Check if initWebSocketChat function exists
    if (typeof initWebSocketChat !== 'function') {
        console.error('[WS] ✗ initWebSocketChat function NOT found!');
        gradioUpdateDebug('❌ Error: initWebSocketChat function not loaded');
        return agentName;
    }

    // Check if sendWebSocketMessage function exists
    if (typeof sendWebSocketMessage !== 'function') {
        console.error('[WS] ✗ sendWebSocketMessage function NOT found!');
    } else {
        console.log('[WS] ✓ sendWebSocketMessage function found');
    }

    console.log('[WS] Checking WebSocket client status...');
    console.log('[WS] typeof wsClient:', typeof wsClient);
    console.log('[WS] wsClient value:', wsClient);

    // Check WebSocket client status
    let needNewConnection = false;

    console.log('[WS] Checking if wsClient needs connection...');
    if (wsClient === null || wsClient === undefined) {
        console.log('[WS] wsClient is null/undefined, creating new...');
        console.log('[WS] Creating new WebSocket client...');
        gradioUpdateDebug('🔧 Creating new WebSocket client...');
        needNewConnection = true;
    } else if (!wsClient.isConnected) {
        console.log('[WS] wsClient exists but not connected, reconnecting...');
        console.log('[WS] Reconnecting existing client...');
        gradioUpdateDebug('🔄 Reconnecting WebSocket client...');
        needNewConnection = true;
    } else {
        console.log('[WS] wsClient is already connected');
        console.log('[WS] Client already connected');
        gradioUpdateDebug('✅ WebSocket client already connected');
    }

    console.log('[WS] needNewConnection:', needNewConnection);

    // Initialize WebSocket (only if needed)
    if (needNewConnection) {
        console.log('[WS] About to call initWebSocketChat...');
        wsClient = initWebSocketChat();
        console.log('[WS] WebSocket client created:', wsClient);
        console.log('[WS] WebSocket client type:', typeof wsClient);
        console.log('[WS] WebSocket client isConnected:', wsClient ? wsClient.isConnected : 'no client');
    }

    console.log('[WS] About to register message handlers...');
    console.log('[WS] wsClient is:', wsClient);
    console.log('[WS] wsClient.on is:', wsClient ? typeof wsClient.on : 'no wsClient');

    // Set up message handlers (do this every time to ensure handlers are registered)
    try {
        console.log('[WS] Starting handler registration...');
        wsClient.on('connected', (data) => {
            console.log('[WS] ✓ Connected event received:', data);
            gradioUpdateDebug('✅ WebSocket Connected! Session: ' + data.data.session_id);
        });

        wsClient.on('reasoning_start', (data) => {
            console.log('[WS] Reasoning started');
            gradioUpdateDebug('🤔 Reasoning started...');
            const container = document.getElementById('ws-session-container');
            if (container) {
                container.innerHTML = '<div class="ws-reasoning-step ws-step-thought"><div class="ws-step-type">Starting reasoning...</div></div>';
            }
        });

        wsClient.on('reasoning_step', (data) => {
            console.log('[WS] Reasoning step received:', data);
            gradioUpdateDebug('📨 Step received: ' + data.data.type);

            const container = document.getElementById('ws-session-container');
            console.log('[WS] Container element:', container);
            if (!container) {
                console.error('[WS] Container not found!');
                return;
            }

            const step = data.data;
            const stepType = step.type;
            console.log('[WS] Step type:', stepType);
            console.log('[WS] Step content:', step.content);

            let stepClass = 'ws-step-thought';
            let typeLabel = 'Thought';

            if (stepType === 'tool_use') {
                stepClass = 'ws-step-tool_use';
                typeLabel = 'Tool Use';
            } else if (stepType === 'tool_result') {
                stepClass = 'ws-step-tool_result';
                typeLabel = 'Tool Result';
            } else if (stepType === 'final_answer') {
                stepClass = 'ws-step-final_answer';
                typeLabel = 'Final Answer';
            } else if (stepType === 'error') {
                stepClass = 'ws-step-error';
                typeLabel = 'Error';
            }

            const timestamp = new Date(step.timestamp * 1000).toLocaleTimeString();
            const iteration = step.iteration ? `<span class="ws-iteration">Iter: ${step.iteration}</span>` : '';
            const toolName = step.tool_name ? `<span class="ws-tool-name">${step.tool_name}</span>` : '';

            const stepHtml = `
                <div class="${stepClass}">
                    <div class="ws-step-type">${typeLabel} ${iteration} ${toolName}</div>
                    <div class="ws-step-content">${escapeHtml(step.content)}</div>
                    <div class="ws-step-timestamp">${timestamp}</div>
                </div>
            `;

            console.log('[WS] Step HTML length:', stepHtml.length);
            console.log('[WS] About to insert HTML...');
            container.insertAdjacentHTML('beforeend', stepHtml);
            console.log('[WS] HTML inserted, scrolling to bottom...');
            container.scrollTop = container.scrollHeight;
            console.log('[WS] UI updated successfully');
        });

        wsClient.on('reasoning_complete', () => {
            console.log('[WS] Reasoning complete');
            gradioUpdateDebug('✅ Reasoning complete!');
            const container = document.getElementById('ws-session-container');
            if (container) {
                container.insertAdjacentHTML('beforeend',
                    '<div class="ws-reasoning-step ws-step-final_answer"><div class="ws-step-type">✓ Complete</div></div>'
                );
            }
        });

        wsClient.on('error', (data) => {
            console.error('[WS] Error:', data);
            gradioUpdateDebug('❌ Error: ' + data.data.message);
            const container = document.getElementById('ws-session-container');
            if (container) {
                container.insertAdjacentHTML('beforeend',
                    `<div class="ws-reasoning-step ws-step-error"><div class="ws-step-type">Error</div><div class="ws-step-content">${escapeHtml(data.data.message)}</div></div>`
                );
            }
        });

        console.log('[WS] Message handlers registered');
        gradioUpdateDebug('⚙️ Message handlers registered, waiting for connection...');

    } catch (error) {
        console.error('[WS] Handler registration error:', error);
        console.error('[WS] Error name:', error.name);
        console.error('[WS] Error message:', error.message);
        console.error('[WS] Error stack:', error.stack);
        gradioUpdateDebug('❌ Handler registration error: ' + error.message);
    }

    console.log('[WS] ==================================================');
    return agentName;
}

/**
 * Send button handler for Gradio
 * Called when user clicks "Send" button or presses Enter
 */
function gradioSend(message, agentName, enableReasoning) {
    console.log('[WS] ==================================================');
    console.log('[WS] Send button clicked');
    console.log('[WS] Message:', message);
    console.log('[WS] Agent:', agentName);
    console.log('[WS] Enable Reasoning:', enableReasoning);

    if (typeof sendWebSocketMessage === 'function') {
        console.log('[WS] ✓ sendWebSocketMessage function found');
        console.log('[WS] Calling sendWebSocketMessage...');
        sendWebSocketMessage(message, agentName, enableReasoning);
        console.log('[WS] sendWebSocketMessage called');
        gradioUpdateDebug(`Sending message to '${agentName}'...`);
    } else {
        console.error('[WS] ✗ sendWebSocketMessage function NOT found!');
        gradioUpdateDebug('❌ Error: sendWebSocketMessage function not loaded. Please click Connect first.');
    }

    console.log('[WS] ==================================================');
    return [message, agentName, enableReasoning];
}

/**
 * Helper function to update debug info in the UI
 */
function gradioUpdateDebug(message) {
    try {
        const debugDiv = document.getElementById('ws-debug');
        if (debugDiv) {
            const time = new Date().toLocaleTimeString();
            debugDiv.innerHTML = `<div style="background: #e3f2fd; padding: 10px; margin: 10px 0; border-radius: 4px; font-family: monospace; font-size: 12px;">🔍 [${time}] ${message}</div>`;
        } else {
            console.warn('[WS] Debug div not found!');
        }
    } catch (error) {
        console.error('[WS] Error updating debug:', error);
    }
}
