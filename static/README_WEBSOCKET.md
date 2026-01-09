# WebSocket Chat Architecture

## Overview

This document describes the refactored WebSocket chat implementation for the Gradio GUI.

## Architecture

### File Structure

```
agent-infra/
├── main.py                          # Application entry point
│   └── Uses Gradio 6.x `head_paths` to load external JavaScript
├── src/gui/
│   ├── app.py                       # Main Gradio application
│   │   └── Loads CSS only (JavaScript via head_paths)
│   └── websocket_chat.py            # WebSocket chat component
│       └── Defines CSS and interface (NO embedded JavaScript)
└── static/
    └── websocket_chat.js            # Standalone WebSocket client (247 lines)
```

### Key Changes from Previous Implementation

1. **External JavaScript Loading**: Uses Gradio 6.x `head_paths` parameter in `main.py`
2. **Removed Embedded JavaScript**: Deleted `WEBSOCKET_CLIENT_JS` constant from `websocket_chat.py`
3. **Cleaner Separation**: JavaScript in separate file, CSS and Python logic in their own files
4. **Simplified Loading**: No more file reading or string embedding in Python code

## How It Works

### 1. JavaScript Loading (main.py)

The JavaScript file is loaded via Gradio 6.x's `head_paths` parameter:

```python
js_file = Path(__file__).parent / "static" / "websocket_chat.js"

launch_kwargs = {
    "server_name": api_host,
    "server_port": gui_port,
    "share": False,
    "quiet": True,
    "show_error": True,
}

if js_file.exists():
    launch_kwargs["head_paths"] = [str(js_file)]

self.gradio_app.app.launch(**launch_kwargs)
```

This automatically includes `websocket_chat.js` in the `<head>` of the Gradio HTML page.

### 2. CSS Loading (app.py)

CSS is loaded in the Gradio interface via `gr.HTML()`:

```python
gr.HTML(f"<style>{self.ws_chat.get_custom_css()}</style>")
```

### 3. WebSocket Client (static/websocket_chat.js)

The JavaScript file provides:

- **WebSocketChatClient Class**: Main WebSocket client with:
  - Auto-reconnect logic
  - Message handling
  - Status updates
  - Heartbeat (ping/pong)

- **Global Functions**:
  - `initWebSocketChat()`: Initialize the WebSocket client
  - `sendWebSocketMessage()`: Send chat messages
  - `escapeHtml()`: Helper for HTML escaping

### 4. Event Handlers (websocket_chat.py)

Python event handlers return JavaScript that calls the global functions:

```python
def on_connect(agent_name):
    return f"""
    <script>
    (function() {{
        if (typeof initWebSocketChat === 'function') {{
            wsClient = initWebSocketChat();
            // Set up message handlers...
        }}
    }})();
    </script>
    """
```

## WebSocket Protocol

### Client → Server Messages

```json
{
  "type": "chat",
  "payload": {
    "message": "user message",
    "agent_name": "agent_name",
    "enable_reasoning": true
  }
}
```

### Server → Client Messages

- **connected**: Session confirmation
- **reasoning_start**: Reasoning started
- **reasoning_step**: Individual reasoning step
- **reasoning_complete**: Reasoning finished
- **error**: Error occurred
- **pong**: Heartbeat response

## Benefits of This Architecture

1. **Clean Separation**: JavaScript, CSS, and Python code are in separate files
2. **Maintainability**: Easy to update JavaScript without touching Python code
3. **Gradio 6.x Compatible**: Uses official `head_paths` parameter
4. **Browser Debugging**: Standalone JavaScript file easier to debug
5. **Version Control**: Clear file ownership and changes

## Testing

To verify the WebSocket chat is working:

1. Start the application: `python main.py`
2. Open browser to `http://localhost:7860`
3. Navigate to "Real-Time Streaming Chat" tab
4. Open browser console (F12)
5. Look for: `[WS] ===== websocket_chat.js LOADED =====`
6. Click "Connect" button
7. Check for: `[WS] Connected: session_xxxxx`
8. Send a message and watch reasoning steps appear

## Troubleshooting

### JavaScript Not Loading

1. Check if `static/websocket_chat.js` exists
2. Verify Gradio 6.x is installed: `pip show gradio`
3. Check console for errors
4. Verify `head_paths` is set in `main.py`

### WebSocket Connection Issues

1. Ensure API server is running on port 8000
2. Check WebSocket endpoint: `ws://localhost:8000/ws/chat/{session_id}`
3. Verify `src/api/websocket_endpoints.py` is loaded
4. Check `src/core/websocket_manager.py` for connection issues

### CSS Not Applied

1. Check if `WEBSOCKET_CHAT_CSS` is defined in `websocket_chat.py`
2. Verify CSS is loaded via `gr.HTML()` in `app.py`
3. Use browser inspector to check if styles are applied

## Future Improvements

1. **Dynamic Agent List**: Load available agents dynamically from API
2. **Session Persistence**: Save chat history across sessions
3. **Message Batching**: Batch multiple reasoning steps for performance
4. **Error Recovery**: Better error handling and user feedback
5. **Authentication**: Add user authentication for WebSocket connections
