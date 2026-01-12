# HTTP Streaming API Implementation Plan

## Overview

Implement HTTP-level streaming for the OpenAI-compatible Chat Completions API, enabling real-time token-by-token response streaming for API clients.

**Goal**: Add `stream=True` support to `POST /v1/chat/completions` endpoint

**Current State**:
- ✅ WebSocket Streaming Reasoning (GUI, reasoning steps)
- ❌ HTTP Streaming API (API clients, token-level)

**Target State**:
- ✅ Both streaming methods supported
- ✅ OpenAI-compatible SSE (Server-Sent Events) format
- ✅ Token-level or chunk-level streaming from agents

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           API Client                                  │
│                    (curl, Python SDK, LangChain)                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    POST /v1/chat/completions                         │
│                    ?stream=true (NEW)                                 │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                    ▼                 ▼
            ┌───────────┐      ┌──────────────┐
            │  stream:  │      │  stream:    │
            │   true    │      │   false     │
            └─────┬─────┘      └──────┬───────┘
                  │                   │
                  ▼                   ▼
        ┌─────────────────┐   ┌─────────────────┐
        │ StreamingResponse │   │  Normal JSON    │
        │   (SSE format)   │   │   Response      │
        └─────────┬───────┘   └─────────────────┘
                  │
                  ▼
        ┌─────────────────────────────────┐
        │   AgentManager.run_agent()     │
        │   with streaming callback      │
        └─────────────────┬───────────────┘
                          │
                          ▼
        ┌─────────────────────────────────┐
        │     IAgentAdapter              │
        │  (Qwen/Claude implementations)  │
        └─────────────────┬───────────────┘
                          │
                          ▼
        ┌─────────────────────────────────┐
        │   Token/Chunk Streaming        │
        │   (yield as generated)         │
        └─────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Core Streaming Infrastructure

**Objective**: Add streaming capability to agent adapters

#### Step 1.1: Extend IAgentAdapter Interface

```python
# src/core/agent_adapter.py

class IAgentAdapter(ABC):
    # ... existing methods ...

    @abstractmethod
    async def run_async_stream(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Run the agent with streaming output.

        Yields:
            str: Content chunks as they are generated

        Note:
            - For Qwen: May need to hook into LLM callback
            - For Claude: Can use Anthropic SDK streaming
            - Fallback: Yield complete responses at end
        """
        pass
```

#### Step 1.2: Implement Qwen Streaming

```python
# src/core/qwen_agent_adapter.py

async def run_async_stream(
    self,
    prompt: str,
    session_id: Optional[str] = None,
    **kwargs
) -> AsyncIterator[str]:
    """Stream Qwen agent responses."""
    # Option 1: Use Qwen Agent's streaming (if available)
    # Option 2: Hook into callback to capture tokens
    # Option 3: Fallback to run_async() and yield at end

    # Implementation will explore Qwen Agent SDK capabilities
    yield from self._stream_via_callback(prompt, session_id, **kwargs)
```

#### Step 1.3: Implement Claude Streaming

```python
# src/core/claude_agent_adapter.py

async def run_async_stream(
    self,
    prompt: str,
    session_id: Optional[str] = None,
    **kwargs
) -> AsyncIterator[str]:
    """Stream Claude agent responses."""
    # Claude SDK supports native streaming
    async for text in self._stream_via_anthropic(prompt, **kwargs):
        yield text
```

**Acceptance Criteria**:
- [ ] `IAgentAdapter.run_async_stream()` defined
- [ ] QwenAgentAdapter implements streaming
- [ ] ClaudeAgentAdapter implements streaming
- [ ] Unit tests for streaming methods

---

### Phase 2: FastAPI Streaming Response

**Objective**: Add streaming endpoint to OpenAI server

#### Step 2.1: Update Chat Completions Endpoint

```python
# src/api/openapi_server.py

from fastapi.responses import StreamingResponse
import json

@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    agent_manager: AgentManager = Depends(get_agent_manager)
):
    """Chat completions with streaming support."""

    agent = agent_manager.get_agent(request.model)
    if not agent:
        raise HTTPException(404, f"Agent {request.model} not found")

    if request.stream:
        # Return SSE streaming response
        return StreamingResponse(
            stream_agent_response(agent, request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    else:
        # Existing non-streaming logic
        return await chat_completions_non_streaming(...)
```

#### Step 2.2: Implement SSE Stream Generator

```python
# src/api/openapi_server.py

async def stream_agent_response(
    agent: IAgentAdapter,
    request: ChatCompletionRequest
):
    """
    Stream agent responses in OpenAI-compatible SSE format.

    SSE Format:
    data: {"id": "chatcmpl-xxx", "choices":[{"delta":{"content":"..."}}}

    Yields:
        str: SSE-formatted chunks
    """
    import time

    chat_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())

    # System message (if any)
    if request.system:
        yield _format_sse_chunk(chat_id, created, request.system, "system")

    # Stream agent response
    async for chunk in agent.run_async_stream(
        prompt=_format_messages(request.messages),
        session_id=_generate_session_id()
    ):
        yield _format_sse_chunk(chat_id, created, chunk, "assistant")

    # Final chunk
    yield _format_sse_chunk(chat_id, created, "", "assistant", is_final=True)


def _format_sse_chunk(
    chat_id: str,
    created: int,
    content: str,
    role: str,
    is_final: bool = False
) -> str:
    """Format chunk as OpenAI-compatible SSE."""
    chunk = {
        "id": chat_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": "",
        "choices": [{
            "index": 0,
            "delta": {"content": content} if content else {},
            "finish_reason": "stop" if is_final else None
        }]
    }

    return f"data: {json.dumps(chunk)}\n\n"
```

**Acceptance Criteria**:
- [ ] Streaming endpoint returns `text/event-stream`
- [ ] SSE format matches OpenAI specification
- [ ] Includes proper headers (Cache-Control, Connection)
- [ ] Works with curl, Python SDK, LangChain

---

### Phase 3: Testing & Validation

**Objective**: Ensure streaming works with various clients

#### Step 3.1: CLI Testing

```bash
# Test with curl
curl -N http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "researcher",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": true
  }'

# Expected: SSE chunks streamed
```

#### Step 3.2: Python SDK Testing

```python
# tests/test_streaming_api.py

import openai

def test_streaming_with_openai_sdk():
    client = openai.OpenAI(
        base_url="http://localhost:8000/v1",
        api_key="test"
    )

    stream = client.chat.completions.create(
        model="researcher",
        messages=[{"role": "user", "content": "Count to 5"}],
        stream=True
    )

    chunks = []
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            chunks.append(content)
            print(content, end="", flush=True)

    assert len(chunks) > 0
```

#### Step 3.3: LangChain Integration Test

```python
# tests/test_langchain_streaming.py

from langchain_openai import ChatOpenAI

def test_langchain_streaming():
    llm = ChatOpenAI(
        base_url="http://localhost:8000/v1",
        model="researcher",
        streaming=True
    )

    response = llm.stream("Say hello")
    chunks = list(response)

    assert len(chunks) > 0
```

**Acceptance Criteria**:
- [ ] curl test shows SSE streaming
- [ ] OpenAI Python SDK works
- [ ] LangChain integration works
- [ ] At least 3 integration tests pass

---

### Phase 4: Documentation

**Objective**: Document streaming usage

#### Step 4.1: Update README

Add streaming section to `README.md`:

```markdown
## Streaming API

### Python SDK

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1")

stream = client.chat.completions.create(
    model="researcher",
    messages=[{"role": "user", "content": "Hello"}],
    stream=True
)

for chunk in stream:
    print(chunk.choices[0].delta.content, end="")
```

### cURL

```bash
curl -N http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"researcher","messages":[{"role":"user","content":"Hi"}],"stream":true}'
```
```

#### Step 4.2: API Documentation

Update OpenAPI docs with streaming examples.

**Acceptance Criteria**:
- [ ] README has streaming section
- [ ] API docs include streaming examples
- [ ] Migration guide from non-streaming

---

## Implementation Details

### Streaming Strategy by SDK

| SDK | Streaming Approach | Complexity |
|-----|-------------------|------------|
| **Claude** | Native SDK streaming support | Low |
| **Qwen** | Callback hook or simulation | Medium |
| **Fallback** | Complete response at end | Low |

### SSE Format Specification

```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1234567890,"model":"researcher","choices":[{"index":0,"delta":{"content":"Hello"}}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1234567890,"model":"researcher","choices":[{"index":0,"delta":{"content":" there"}}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1234567890,"model":"researcher","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

### Error Handling

```python
async def stream_agent_response(...):
    try:
        async for chunk in agent.run_async_stream(...):
            yield _format_sse_chunk(...)
    except Exception as e:
        # Send error chunk
        error_chunk = {
            "error": {
                "message": str(e),
                "type": "streaming_error"
            }
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
```

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Qwen SDK doesn't support streaming | High | Implement callback fallback |
| Memory leaks in long streams | Medium | Add timeout and chunk limits |
| Client disconnection handling | Medium | Monitor client connection |
| OpenAI format compatibility | Low | Test with official SDK |

---

## Success Metrics

- [ ] Streaming endpoint responds within 100ms
- [ ] First chunk arrives within 500ms
- [ ] Compatible with OpenAI Python SDK v1.x
- [ ] Compatible with LangChain streaming
- [ ] No memory leaks in 10-minute streams
- [ ] Graceful handling of client disconnect

---

## Estimated Effort

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1 | Adapter interface + implementations | 4-6 hours |
| Phase 2 | FastAPI endpoint + SSE format | 2-3 hours |
| Phase 3 | Testing with various clients | 2-3 hours |
| Phase 4 | Documentation | 1-2 hours |
| **Total** | | **9-14 hours** |

---

## Dependencies

- FastAPI `StreamingResponse` (built-in)
- Agent adapters (existing)
- OpenAI API specification (reference)

---

## Related Work

- [WebSocket Streaming Reasoning](../docs/websocket-streaming-reasoning.md) - Already implemented for GUI
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference/streaming)

---

## Next Steps

Once this plan is approved:

1. Create feature branch: `feature/http-streaming-api`
2. Implement Phase 1 (Adapter streaming)
3. Implement Phase 2 (FastAPI endpoint)
4. Implement Phase 3 (Testing)
5. Implement Phase 4 (Documentation)
6. Create PR and merge

---

## Notes

- This implementation complements (not replaces) WebSocket streaming
- GUI users can continue using WebSocket for reasoning steps
- API users get standard HTTP streaming for token-level output
- Both methods can coexist without conflicts
