"""
OpenAI-Compatible API Server.

Provides FastAPI endpoints compatible with OpenAI's Chat Completions API.
"""

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel, Field

from core.agent_manager import AgentManager
from core.config import ConfigManager
from core.task_models import ScheduleType
from core.task_scheduler import TaskScheduler, get_task_scheduler


# ============================================================================
# Request/Response Models (OpenAI Compatible)
# ============================================================================

class ChatMessage(BaseModel):
    """Chat message model."""
    role: str
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    """Chat completion request model."""
    model: str  # Agent name
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict]] = None
    top_p: Optional[float] = None
    n: Optional[int] = 1


class ChatCompletionResponse(BaseModel):
    """Chat completion response model."""
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:24]}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, int]] = None


class ChatCompletionChunk(BaseModel):
    """Streaming response chunk."""
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[Dict[str, Any]]


# ============================================================================
# Scheduled Task Function Definitions
# ============================================================================

SCHEDULED_TASK_FUNCTIONS = [
    {
        "type": "function",
        "function": {
            "name": "create_scheduled_task",
            "description": "建立一個定時執行的 Agent 任務",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "任務名稱"
                    },
                    "agent_name": {
                        "type": "string",
                        "description": "要執行的 Agent 名稱",
                        "enum": ["researcher", "developer", "writer", "analyst"]
                    },
                    "task_prompt": {
                        "type": "string",
                        "description": "任務提示詞"
                    },
                    "schedule_type": {
                        "type": "string",
                        "description": "排程類型",
                        "enum": ["cron", "interval", "once"]
                    },
                    "schedule_value": {
                        "type": "string",
                        "description": "排程值（cron 表達式、秒數、或 ISO datetime）"
                    },
                    "repeat": {
                        "type": "boolean",
                        "description": "是否重複執行"
                    },
                    "description": {
                        "type": "string",
                        "description": "任務描述"
                    }
                },
                "required": ["name", "agent_name", "task_prompt", "schedule_type", "schedule_value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_scheduled_tasks",
            "description": "列出所有排程任務",
            "parameters": {
                "type": "object",
                "properties": {
                    "enabled_only": {
                        "type": "boolean",
                        "description": "只顯示已啟用的任務"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_task",
            "description": "取消一個排程任務",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "任務 ID"
                    }
                },
                "required": ["task_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "enable_task",
            "description": "啟用一個排程任務",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "任務 ID"
                    }
                },
                "required": ["task_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "disable_task",
            "description": "停用一個排程任務",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "任務 ID"
                    }
                },
                "required": ["task_id"]
            }
        }
    },
]


# ============================================================================
# API Server
# ============================================================================

class APIServer:
    """
    OpenAI-compatible API server.

    Provides chat completions API with function calling support for scheduled tasks.
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        agent_manager: AgentManager,
        task_scheduler: TaskScheduler,
    ):
        """
        Initialize the API server.

        Args:
            config_manager: Configuration manager
            agent_manager: Agent manager instance
            task_scheduler: Task scheduler instance
        """
        self.config_manager = config_manager
        self.agent_manager = agent_manager
        self.task_scheduler = task_scheduler

        # Create FastAPI app
        self.app = FastAPI(
            title="Qwen Agent MCP Scheduler",
            description="OpenAI-compatible API for agent interactions",
            version="0.1.0",
        )

        # Setup CORS
        self._setup_cors()

        # Setup routes
        self._setup_routes()

    def _setup_cors(self):
        """Setup CORS middleware."""
        app_config = self.config_manager.app
        cors_origins = app_config.server.cors_origins

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_routes(self):
        """Setup API routes."""

        @self.app.get("/")
        async def root():
            """Root endpoint."""
            return {
                "name": "Qwen Agent MCP Scheduler",
                "version": "0.1.0",
                "status": "running",
                "endpoints": {
                    "chat_completions": "/v1/chat/completions",
                    "agents": "/v1/agents",
                    "tasks": "/v1/tasks",
                }
            }

        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            return {"status": "healthy"}

        @self.app.get("/v1/agents")
        async def list_agents():
            """List all available agents."""
            agents_info = self.agent_manager.get_all_agent_info()
            return {
                "object": "list",
                "data": agents_info
            }

        @self.app.get("/v1/agents/{agent_name}")
        async def get_agent(agent_name: str):
            """Get specific agent info."""
            agent_info = self.agent_manager.get_agent_info(agent_name)
            if not agent_info:
                raise HTTPException(status_code=404, detail="Agent not found")
            return agent_info

        @self.app.post("/v1/chat/completions")
        async def chat_completions(request: ChatCompletionRequest):
            """
            Chat completions endpoint (OpenAI-compatible).

            Supports:
            - Agent selection via model parameter
            - Function calling for scheduled tasks
            - Streaming responses
            """
            # Validate agent exists
            agent = self.agent_manager.get_agent(request.model)
            if not agent:
                raise HTTPException(
                    status_code=400,
                    detail=f"Agent '{request.model}' not found"
                )

            # Check for tool calls
            tool_calls = self._extract_tool_calls(request)

            if tool_calls:
                # Handle function calls
                return await self._handle_tool_calls(request, tool_calls)
            else:
                # Normal chat completion
                return await self._handle_chat_completion(request)

        @self.app.get("/v1/tasks")
        async def list_tasks(enabled_only: bool = False):
            """List all scheduled tasks."""
            tasks = self.task_scheduler.list_tasks(enabled_only=enabled_only)
            return {
                "object": "list",
                "data": [task.model_dump() for task in tasks]
            }

        @self.app.get("/v1/tasks/{task_id}")
        async def get_task(task_id: str):
            """Get specific task info."""
            task = self.task_scheduler.get_task(task_id)
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            return task.model_dump()

        @self.app.post("/v1/tasks/{task_id}/enable")
        async def enable_task(task_id: str):
            """Enable a task."""
            success = await self.task_scheduler.enable_task(task_id)
            if not success:
                raise HTTPException(status_code=404, detail="Task not found")
            return {"success": True, "task_id": task_id}

        @self.app.post("/v1/tasks/{task_id}/disable")
        async def disable_task(task_id: str):
            """Disable a task."""
            success = await self.task_scheduler.disable_task(task_id)
            if not success:
                raise HTTPException(status_code=404, detail="Task not found")
            return {"success": True, "task_id": task_id}

        @self.app.delete("/v1/tasks/{task_id}")
        async def cancel_task(task_id: str):
            """Cancel/remove a task."""
            success = await self.task_scheduler.remove_task(task_id)
            if not success:
                raise HTTPException(status_code=404, detail="Task not found")
            return {"success": True, "task_id": task_id}

    def _extract_tool_calls(self, request: ChatCompletionRequest) -> List[Dict[str, Any]]:
        """Extract tool calls from the request."""
        tool_calls = []

        # Check if user is calling a tool
        for message in request.messages:
            if message.tool_calls:
                tool_calls.extend(message.tool_calls)

        # Check if request specifies tool_choice
        if request.tool_choice:
            if isinstance(request.tool_choice, dict) and request.tool_choice.get("type") == "function":
                tool_calls.append(request.tool_choice)

        return tool_calls

    async def _handle_tool_calls(
        self,
        request: ChatCompletionRequest,
        tool_calls: List[Dict[str, Any]]
    ) -> ChatCompletionResponse:
        """Handle function calls for scheduled tasks."""
        results = []

        for tool_call in tool_calls:
            function_name = tool_call.get("function", {}).get("name")
            arguments_str = tool_call.get("function", {}).get("arguments", "{}")

            # Parse arguments
            try:
                import json
                arguments = json.loads(arguments_str)
            except json.JSONDecodeError:
                arguments = {}

            # Execute function
            result = await self._execute_function(function_name, arguments)
            results.append({
                "id": tool_call.get("id", f"call_{len(results)}"),
                "type": "function",
                "function": {
                    "name": function_name,
                    "arguments": arguments_str,
                    "result": result,
                }
            })

        # Return response with tool call results
        return ChatCompletionResponse(
            model=request.model,
            choices=[{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": results
                },
                "finish_reason": "tool_calls"
            }],
            usage={
                "prompt_tokens": sum(len(m.content) for m in request.messages),
                "completion_tokens": 0,
                "total_tokens": sum(len(m.content) for m in request.messages),
            }
        )

    async def _execute_function(self, name: str, arguments: Dict[str, Any]) -> str:
        """Execute a scheduled task function."""
        if name == "create_scheduled_task":
            task = await self.task_scheduler.schedule_task(
                name=arguments.get("name", "Unnamed Task"),
                agent_name=arguments.get("agent_name"),
                task_prompt=arguments.get("task_prompt"),
                schedule_type=ScheduleType(arguments.get("schedule_type")),
                schedule_value=arguments.get("schedule_value"),
                repeat=arguments.get("repeat", False),
                description=arguments.get("description", ""),
            )
            return f"Task '{task.name}' created with ID: {task.id}"

        elif name == "list_scheduled_tasks":
            enabled_only = arguments.get("enabled_only", False)
            tasks = self.task_scheduler.list_tasks(enabled_only=enabled_only)
            task_list = "\n".join([
                f"- {task.name} (ID: {task.id}, Status: {task.last_status})"
                for task in tasks
            ])
            return f"Tasks:\n{task_list}"

        elif name == "cancel_task":
            task_id = arguments.get("task_id")
            success = await self.task_scheduler.cancel_task(task_id)
            if success:
                return f"Task {task_id} cancelled"
            else:
                return f"Failed to cancel task {task_id}"

        elif name == "enable_task":
            task_id = arguments.get("task_id")
            success = await self.task_scheduler.enable_task(task_id)
            if success:
                return f"Task {task_id} enabled"
            else:
                return f"Failed to enable task {task_id}"

        elif name == "disable_task":
            task_id = arguments.get("task_id")
            success = await self.task_scheduler.disable_task(task_id)
            if success:
                return f"Task {task_id} disabled"
            else:
                return f"Failed to disable task {task_id}"

        else:
            return f"Unknown function: {name}"

    async def _handle_chat_completion(
        self,
        request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """Handle normal chat completion."""
        # Convert messages to prompt
        prompt = self._messages_to_prompt(request.messages)

        # Run agent
        try:
            response = await self.agent_manager.run_agent(
                request.model,
                prompt
            )

            # Extract response content
            content = ""
            for msg in response:
                if hasattr(msg, 'content'):
                    content += msg.content or ""
                elif isinstance(msg, dict):
                    content += msg.get('content', "")

            return ChatCompletionResponse(
                model=request.model,
                choices=[{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": "stop"
                }],
                usage={
                    "prompt_tokens": sum(len(m.content) for m in request.messages),
                    "completion_tokens": len(content),
                    "total_tokens": sum(len(m.content) for m in request.messages) + len(content),
                }
            )

        except Exception as e:
            logger.error(f"Chat completion error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def _messages_to_prompt(self, messages: List[ChatMessage]) -> str:
        """Convert OpenAI messages to prompt format."""
        prompt_parts = []
        for msg in messages:
            if msg.role == "system":
                prompt_parts.append(f"System: {msg.content}")
            elif msg.role == "user":
                prompt_parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                prompt_parts.append(f"Assistant: {msg.content}")

        return "\n\n".join(prompt_parts)


# ============================================================================
# Server Factory
# ============================================================================

def create_api_server(
    config_manager: ConfigManager,
    agent_manager: AgentManager,
    task_scheduler: TaskScheduler,
) -> APIServer:
    """
    Create and configure the API server.

    Args:
        config_manager: Configuration manager
        agent_manager: Agent manager instance
        task_scheduler: Task scheduler instance

    Returns:
        Configured APIServer instance
    """
    return APIServer(config_manager, agent_manager, task_scheduler)


def get_scheduled_task_functions() -> List[Dict[str, Any]]:
    """Get the scheduled task function definitions."""
    return SCHEDULED_TASK_FUNCTIONS
