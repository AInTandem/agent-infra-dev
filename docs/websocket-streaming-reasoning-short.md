## ⚡ WebSocket Streaming Reasoning (New!)

Real-time visibility into agent reasoning with streaming display of thought processes, tool usage, and results.

### Features
- 📡 **WebSocket-based** real-time communication
- 💭 **Step-by-step** reasoning visualization
- 🎨 **Color-coded** step types (thoughts, tools, results)
- 🔄 **Auto-reconnect** with exponential backoff
- ✅ **Backward compatible** with existing chat

### Quick Start
```bash
python main.py
# Open http://localhost:7860
# Click "⚡ Real-Time Chat" tab
# Connect and start chatting!
```

### Architecture
```
Gradio GUI ←→ WebSocket ←→ FastAPI ←→ AgentManager ←→ BaseAgent
   (Browser)     (Real-time)    (Server)    (Streaming)
```

[Read full documentation →](docs/websocket-streaming-reasoning.md)
