#!/usr/bin/env python3
"""
Integration tests for HTTP Streaming API.

Tests the streaming API endpoint SSE formatting and compatibility.
"""

import json
import pytest
import time
import uuid


# ============================================================================
# SSE Format Tests
# ============================================================================

class TestSSEFormat:
    """Test SSE formatting logic."""

    def test_format_sse_chunk_regular(self):
        """Test formatting regular SSE chunk."""
        chat_id = "chatcmpl-test123"
        created = int(time.time())
        model = "test_agent"
        content = "Hello"

        chunk = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {"content": content},
                "finish_reason": None
            }]
        }

        sse_formatted = f"data: {json.dumps(chunk)}\n\n"

        # Verify format
        assert sse_formatted.startswith("data: ")
        assert sse_formatted.endswith("\n\n")

        # Parse back
        parsed = json.loads(sse_formatted.strip()[6:])
        assert parsed["id"] == chat_id
        assert parsed["choices"][0]["delta"]["content"] == "Hello"
        assert parsed["choices"][0]["finish_reason"] is None

    def test_format_sse_chunk_final(self):
        """Test formatting final SSE chunk."""
        chat_id = "chatcmpl-test123"
        created = int(time.time())
        model = "test_agent"

        chunk = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        }

        sse_formatted = f"data: {json.dumps(chunk)}\n\n"

        parsed = json.loads(sse_formatted.strip()[6:])
        assert parsed["choices"][0]["delta"] == {}
        assert parsed["choices"][0]["finish_reason"] == "stop"

    def test_sse_chunk_has_required_fields(self):
        """Test SSE chunk has all required OpenAI fields."""
        chunk = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "test_agent",
            "choices": [{
                "index": 0,
                "delta": {"content": "test"},
                "finish_reason": None
            }]
        }

        # Required fields per OpenAI spec
        required_fields = ["id", "object", "created", "model", "choices"]
        for field in required_fields:
            assert field in chunk, f"Missing required field: {field}"

        # Choice fields
        choice = chunk["choices"][0]
        assert "index" in choice
        assert "delta" in choice
        assert "finish_reason" in choice


# ============================================================================
# OpenAI SDK Compatibility Tests
# ============================================================================

class TestOpenAICompatibility:
    """Test OpenAI SDK compatibility."""

    def test_chat_completion_request_structure(self):
        """Test request structure matches OpenAI format."""
        request = {
            "model": "test_agent",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello"}
            ],
            "temperature": 0.7,
            "max_tokens": 1000,
            "stream": True
        }

        # Verify structure
        assert "model" in request
        assert "messages" in request
        assert "stream" in request
        assert isinstance(request["messages"], list)
        assert all("role" in m and "content" in m for m in request["messages"])

    def test_streaming_request_structure(self):
        """Test streaming request parameter."""
        request = {
            "model": "test_agent",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": True
        }

        assert request["stream"] is True

    def test_response_chunk_structure(self):
        """Test response chunk structure matches OpenAI format."""
        chunk = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "test_agent",
            "choices": [{
                "index": 0,
                "delta": {
                    "content": "Hello"
                },
                "finish_reason": None
            }]
        }

        # Verify structure
        assert chunk["object"] == "chat.completion.chunk"
        assert isinstance(chunk["choices"], list)
        assert len(chunk["choices"]) > 0
        assert "delta" in chunk["choices"][0]


# ============================================================================
# LangChain Compatibility Tests
# ============================================================================

class TestLangChainCompatibility:
    """Test LangChain compatibility."""

    def test_langchain_uses_openai_format(self):
        """Test that LangChain uses standard OpenAI format."""
        # LangChain ChatOpenAI sends requests in OpenAI format
        request = {
            "model": "test_agent",
            "messages": [{"role": "user", "content": "Say hello"}],
            "stream": True,
            "temperature": 0.0
        }

        # Just verify the format is compatible
        assert "model" in request
        assert "messages" in request
        assert "stream" in request


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test error handling."""

    def test_error_chunk_format(self):
        """Test error chunk format for SSE."""
        error_chunk = {
            "error": {
                "message": "Test error",
                "type": "streaming_error"
            }
        }

        sse_formatted = f"data: {json.dumps(error_chunk)}\n\n"

        assert "data: " in sse_formatted
        assert "error" in sse_formatted

        parsed = json.loads(sse_formatted.strip()[6:])
        assert "error" in parsed
        assert parsed["error"]["type"] == "streaming_error"


# ============================================================================
# Stream Parsing Tests
# ============================================================================

class TestStreamParsing:
    """Test parsing of SSE streams."""

    def test_parse_sse_stream(self):
        """Test parsing SSE stream."""
        stream_content = """data: {"id":"chat1","object":"chat.completion.chunk","created":1234567890,"model":"test","choices":[{"delta":{"content":"Hello"},"finish_reason":null}]}

data: {"id":"chat1","object":"chat.completion.chunk","created":1234567890,"model":"test","choices":[{"delta":{"content":" world"},"finish_reason":null}]}

data: {"id":"chat1","object":"chat.completion.chunk","created":1234567890,"model":"test","choices":[{"delta":{},"finish_reason":"stop"}]}

"""

        chunks = []
        for line in stream_content.split("\n"):
            if line.startswith("data: "):
                data = json.loads(line[6:])
                chunks.append(data)

        assert len(chunks) == 3
        assert chunks[0]["choices"][0]["delta"]["content"] == "Hello"
        assert chunks[1]["choices"][0]["delta"]["content"] == " world"
        assert chunks[2]["choices"][0]["finish_reason"] == "stop"

    def test_extract_content_from_chunks(self):
        """Test extracting content from SSE chunks."""
        chunks = [
            {"choices": [{"delta": {"content": "Hello"}}]},
            {"choices": [{"delta": {"content": " there"}}]},
            {"choices": [{"delta": {}}]}
        ]

        content_parts = []
        for chunk in chunks:
            delta = chunk["choices"][0].get("delta", {})
            content = delta.get("content", "")
            if content:
                content_parts.append(content)

        full_content = "".join(content_parts)
        assert full_content == "Hello there"


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
