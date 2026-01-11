# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Predefined Behaviors for Mock Agents

Provides ready-to-use behavior configurations for common agent types.
"""

import operator
import random
import time
from typing import Any

from .base import MockAgent


class BehaviorRegistry:
    """Registry for predefined behaviors."""

    _behaviors = {}

    @classmethod
    def register(cls, name: str, behavior: dict[str, Any]) -> None:
        """Register a behavior."""
        cls._behaviors[name] = behavior

    @classmethod
    def get(cls, name: str) -> dict[str, Any] | None:
        """Get a behavior by name."""
        return cls._behaviors.get(name)


# Echo Behavior - Echoes received messages
ECHO_BEHAVIOR: dict[str, dict[str, Any]] = {
    "echo": {
        "type": "response",
        "action": "echo",
    },
    "ping": {
        "type": "response",
        "action": "pong",
    },
    "request": {
        "type": "response",
        "action": "echo",
    },
}


def create_echo_agent(agent_id: str, name: str | None = None) -> MockAgent:
    """
    Create an echo agent that echoes back received messages.

    Args:
        agent_id: Unique identifier for the agent
        name: Optional display name

    Returns:
        Configured MockAgent with echo behavior
    """
    agent = MockAgent(
        agent_id=agent_id,
        behavior=ECHO_BEHAVIOR,
        name=name or f"EchoAgent-{agent_id}",
        description="Echoes received messages back to sender",
    )

    # Add custom handler for dynamic echoing
    def echo_handler(message):
        content = message.content
        return {
            "type": "response",
            "action": "echo",
            "echoed_content": content,
            "original_sender": message.from_agent,
            "timestamp": time.time(),
        }

    agent.on_message("echo", echo_handler)
    agent.on_message("request", echo_handler)

    return agent


# Calculator Behavior - Performs calculations
CALCULATOR_BEHAVIOR: dict[str, dict[str, Any]] = {
    "calculate": {
        "type": "response",
        "status": "calculated",
    },
    "add": {"type": "response", "operation": "add"},
    "subtract": {"type": "response", "operation": "subtract"},
    "multiply": {"type": "response", "operation": "multiply"},
    "divide": {"type": "response", "operation": "divide"},
}


def create_calculator_agent(agent_id: str, name: str | None = None) -> MockAgent:
    """
    Create a calculator agent that performs mathematical operations.

    Args:
        agent_id: Unique identifier for the agent
        name: Optional display name

    Returns:
        Configured MockAgent with calculator behavior
    """
    agent = MockAgent(
        agent_id=agent_id,
        behavior=CALCULATOR_BEHAVIOR,
        name=name or f"CalculatorAgent-{agent_id}",
        description="Performs mathematical calculations",
    )

    # Operation mapping
    operations = {
        "add": operator.add,
        "subtract": operator.sub,
        "multiply": operator.mul,
        "divide": operator.truediv,
    }

    def calculate_handler(message):
        content = message.content
        op = content.get("operation", "add")
        a = content.get("a", 0)
        b = content.get("b", 0)

        if op in operations:
            try:
                result = operations[op](a, b)
                return {
                    "type": "response",
                    "operation": op,
                    "operands": [a, b],
                    "result": result,
                    "status": "success",
                }
            except ZeroDivisionError:
                return {
                    "type": "response",
                    "operation": op,
                    "status": "error",
                    "error": "Division by zero",
                }

        return {
            "type": "response",
            "status": "error",
            "error": f"Unknown operation: {op}",
        }

    agent.on_message("calculate", calculate_handler)
    for op_name in operations:
        agent.on_message(op_name, calculate_handler)

    return agent


# Researcher Behavior - Simulates research tasks
RESEARCHER_BEHAVIOR: dict[str, dict[str, Any]] = {
    "research": {
        "type": "response",
        "status": "researching",
    },
    "query": {
        "type": "response",
        "status": "querying",
    },
    "analyze": {
        "type": "response",
        "status": "analyzing",
    },
}


def create_researcher_agent(agent_id: str, name: str | None = None) -> MockAgent:
    """
    Create a researcher agent that simulates research tasks.

    Args:
        agent_id: Unique identifier for the agent
        name: Optional display name

    Returns:
        Configured MockAgent with researcher behavior
    """
    agent = MockAgent(
        agent_id=agent_id,
        behavior=RESEARCHER_BEHAVIOR,
        name=name or f"ResearcherAgent-{agent_id}",
        description="Simulates research and analysis tasks",
    )

    def research_handler(message):
        content = message.content
        topic = content.get("topic", "unknown")
        depth = content.get("depth", "basic")

        # Simulate research process
        findings_count = random.randint(3, 10)
        confidence = random.uniform(0.7, 0.95)

        return {
            "type": "response",
            "status": "completed",
            "topic": topic,
            "depth": depth,
            "findings": [
                {
                    "id": f"finding_{i}",
                    "summary": f"Research finding {i+1} about {topic}",
                    "confidence": confidence - (i * 0.05),
                }
                for i in range(findings_count)
            ],
            "timestamp": time.time(),
        }

    def query_handler(message):
        content = message.content
        query = content.get("query", "")

        return {
            "type": "response",
            "status": "completed",
            "query": query,
            "results": [
                {
                    "title": f"Result {i+1} for '{query}'",
                    "snippet": f"Relevant information snippet {i+1}",
                    "relevance": random.uniform(0.6, 0.95),
                }
                for i in range(random.randint(2, 5))
            ],
        }

    def analyze_handler(message):
        content = message.content
        data = content.get("data", {})

        return {
            "type": "response",
            "status": "completed",
            "analysis_type": content.get("analysis_type", "general"),
            "summary": "Analysis completed successfully",
            "insights": [
                f"Insight {i+1}: {random.choice(['positive', 'neutral', 'negative'])} trend detected"
                for i in range(random.randint(2, 4))
            ],
            "recommendations": [
                f"Recommendation {i+1}: Suggested action based on analysis"
                for i in range(random.randint(1, 3))
            ],
        }

    agent.on_message("research", research_handler)
    agent.on_message("query", query_handler)
    agent.on_message("analyze", analyze_handler)

    return agent


# Developer Behavior - Simulates development tasks
DEVELOPER_BEHAVIOR: dict[str, dict[str, Any]] = {
    "develop": {
        "type": "response",
        "status": "developing",
    },
    "implement": {
        "type": "response",
        "status": "implementing",
    },
    "test": {
        "type": "response",
        "status": "testing",
    },
    "refactor": {
        "type": "response",
        "status": "refactoring",
    },
}


def create_developer_agent(agent_id: str, name: str | None = None) -> MockAgent:
    """
    Create a developer agent that simulates software development tasks.

    Args:
        agent_id: Unique identifier for the agent
        name: Optional display name

    Returns:
        Configured MockAgent with developer behavior
    """
    agent = MockAgent(
        agent_id=agent_id,
        behavior=DEVELOPER_BEHAVIOR,
        name=name or f"DeveloperAgent-{agent_id}",
        description="Simulates software development tasks",
    )

    def develop_handler(message):
        content = message.content
        task = content.get("task", "unknown task")
        language = content.get("language", "python")

        # Simulate code generation
        lines_count = random.randint(10, 50)
        complexity = random.choice(["low", "medium", "high"])

        return {
            "type": "response",
            "status": "completed",
            "task": task,
            "language": language,
            "code": f"# Generated code for {task}\n" + "\n".join(
                [f"# Line {i+1}: Implementation detail" for i in range(lines_count)]
            ),
            "complexity": complexity,
            "estimated_test_coverage": random.randint(70, 95),
        }

    def implement_handler(message):
        content = message.content
        feature = content.get("feature", "unknown feature")
        requirements = content.get("requirements", [])

        return {
            "type": "response",
            "status": "completed",
            "feature": feature,
            "requirements_met": len(requirements),
            "total_requirements": len(requirements),
            "implementation_details": {
                "files_created": random.randint(1, 5),
                "files_modified": random.randint(0, 3),
                "lines_added": random.randint(50, 200),
                "tests_added": random.randint(5, 20),
            },
        }

    def test_handler(message):
        content = message.content
        target = content.get("target", "code")

        tests_run = random.randint(10, 50)
        tests_passed = random.randint(int(tests_run * 0.8), tests_run)

        return {
            "type": "response",
            "status": "completed",
            "target": target,
            "tests_run": tests_run,
            "tests_passed": tests_passed,
            "tests_failed": tests_run - tests_passed,
            "coverage": random.randint(75, 98),
            "passed": tests_passed == tests_run,
        }

    def refactor_handler(message):
        content = message.content
        file = content.get("file", "unknown.py")
        refactor_type = content.get("refactor_type", "general")

        return {
            "type": "response",
            "status": "completed",
            "file": file,
            "refactor_type": refactor_type,
            "improvements": [
                "Reduced code duplication",
                "Improved readability",
                "Better error handling",
                "Optimized performance",
            ][: random.randint(2, 4)],
            "complexity_reduction": random.randint(10, 30),
        }

    agent.on_message("develop", develop_handler)
    agent.on_message("implement", implement_handler)
    agent.on_message("test", test_handler)
    agent.on_message("refactor", refactor_handler)

    return agent


# Behavior classes for type checking
class EchoBehavior:
    """Type hint for echo behavior configuration."""

    pass


class CalculatorBehavior:
    """Type hint for calculator behavior configuration."""

    pass


class ResearcherBehavior:
    """Type hint for researcher behavior configuration."""

    pass


class DeveloperBehavior:
    """Type hint for developer behavior configuration."""

    pass


# Register all behaviors
BehaviorRegistry.register("echo", ECHO_BEHAVIOR)
BehaviorRegistry.register("calculator", CALCULATOR_BEHAVIOR)
BehaviorRegistry.register("researcher", RESEARCHER_BEHAVIOR)
BehaviorRegistry.register("developer", DEVELOPER_BEHAVIOR)
