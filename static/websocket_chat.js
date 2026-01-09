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
