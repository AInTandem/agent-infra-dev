# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Test Scenarios

Predefined test scenarios for common agent interaction patterns.
"""

import asyncio
import logging
from typing import Any

from .base import MockAgent
from .registry import AgentRegistry

logger = logging.getLogger(__name__)


class TestScenario:
    """
    Base class for test scenarios.

    Scenarios provide reusable test patterns for agent interactions.
    """

    def __init__(self, name: str, description: str = ""):
        """
        Initialize a test scenario.

        Args:
            name: Scenario name
            description: Scenario description
        """
        self.name = name
        self.description = description
        self.registry: AgentRegistry | None = None
        self.agents: dict[str, MockAgent] = {}

    async def setup(self, registry: AgentRegistry) -> None:
        """
        Set up the scenario with agents.

        Args:
            registry: AgentRegistry to use for creating agents
        """
        self.registry = registry

    async def run(self) -> dict[str, Any]:
        """
        Run the scenario.

        Returns:
            Scenario results
        """
        raise NotImplementedError("Subclasses must implement run()")

    async def cleanup(self) -> None:
        """Clean up after the scenario."""
        pass

    async def execute(self, registry: AgentRegistry) -> dict[str, Any]:
        """
        Execute the complete scenario lifecycle.

        Args:
            registry: AgentRegistry to use

        Returns:
            Scenario results
        """
        await self.setup(registry)
        try:
            results = await self.run()
            return results
        finally:
            await self.cleanup()


class TwoAgentCommunication(TestScenario):
    """
    Scenario: Two agents communicating with each other.

    Tests basic message passing between two agents.
    """

    def __init__(self, agent1_type: str = "echo", agent2_type: str = "echo"):
        """
        Initialize the two-agent communication scenario.

        Args:
            agent1_type: Type of agent 1
            agent2_type: Type of agent 2
        """
        super().__init__(
            name="Two-Agent Communication",
            description="Tests basic message passing between two agents",
        )
        self.agent1_type = agent1_type
        self.agent2_type = agent2_type

    async def setup(self, registry: AgentRegistry) -> None:
        """Set up two agents."""
        await super().setup(registry)

        agent_a = await registry.create_agent("agent_a", self.agent1_type, "Agent A")
        agent_b = await registry.create_agent("agent_b", self.agent2_type, "Agent B")

        self.agents = {"agent_a": agent_a, "agent_b": agent_b}

    async def run(self) -> dict[str, Any]:
        """Run the communication scenario."""
        agent_a = self.agents["agent_a"]
        agent_b = self.agents["agent_b"]

        # Send message from A to B
        test_content = {"type": "echo", "text": "Hello from Agent A!"}
        response = await agent_a.send_to(
            agent_b.sandbox_id,  # type: ignore
            test_content,
        )

        # Wait for message to be processed
        await asyncio.sleep(0.5)

        # Check results
        return {
            "scenario": self.name,
            "success": response is not None,
            "message_sent": test_content,
            "response": response,
            "message_counts": self.registry.get_all_message_counts() if self.registry else {},
            "agent_a_messages": agent_a.get_message_count(),
            "agent_b_messages": agent_b.get_message_count(),
        }


class MultiAgentCollaboration(TestScenario):
    """
    Scenario: Multiple agents collaborating on a task.

    Tests message flow through a chain of agents.
    """

    def __init__(
        self,
        num_agents: int = 3,
        agent_types: list[str] | None = None,
    ):
        """
        Initialize multi-agent collaboration scenario.

        Args:
            num_agents: Number of agents to create
            agent_types: List of agent types (defaults to researcher, developer, tester)
        """
        super().__init__(
            name="Multi-Agent Collaboration",
            description="Tests message flow through multiple agents",
        )
        self.num_agents = num_agents
        self.agent_types = agent_types or ["researcher", "developer", "calculator"]

    async def setup(self, registry: AgentRegistry) -> None:
        """Set up multiple agents."""
        await super().setup(registry)

        for i in range(self.num_agents):
            agent_type = self.agent_types[i % len(self.agent_types)]
            agent = await registry.create_agent(
                f"agent_{i}",
                agent_type,
                f"Agent {i}",
            )
            self.agents[f"agent_{i}"] = agent

    async def run(self) -> dict[str, Any]:
        """Run the collaboration scenario."""
        # Send message from first agent to second
        agents_list = list(self.agents.values())
        if len(agents_list) < 2:
            return {"scenario": self.name, "success": False, "error": "Not enough agents"}

        # Chain: agent_0 -> agent_1 -> agent_2
        message_chain = []
        current_content = {"type": "request", "task": "Collaborative task"}

        for i in range(len(agents_list) - 1):
            sender = agents_list[i]
            receiver = agents_list[i + 1]

            response = await sender.send_to(
                receiver.sandbox_id,  # type: ignore
                current_content,
            )

            message_chain.append({
                "from": sender.agent_id,
                "to": receiver.agent_id,
                "content": current_content,
                "response": response,
            })

            # Wait for processing
            await asyncio.sleep(0.3)

        return {
            "scenario": self.name,
            "success": True,
            "agents_count": len(agents_list),
            "message_chain": message_chain,
            "message_counts": self.registry.get_all_message_counts() if self.registry else {},
        }


class BroadcastScenario(TestScenario):
    """
    Scenario: One agent broadcasting to all others.

    Tests broadcast messaging functionality.
    """

    def __init__(self, num_agents: int = 4):
        """
        Initialize broadcast scenario.

        Args:
            num_agents: Total number of agents (including broadcaster)
        """
        super().__init__(
            name="Broadcast Messaging",
            description="Tests one agent broadcasting to multiple receivers",
        )
        self.num_agents = num_agents

    async def setup(self, registry: AgentRegistry) -> None:
        """Set up agents."""
        await super().setup(registry)

        for i in range(self.num_agents):
            agent = await registry.create_agent(
                f"agent_{i}",
                "echo",
                f"Agent {i}",
            )
            self.agents[f"agent_{i}"] = agent

    async def run(self) -> dict[str, Any]:
        """Run the broadcast scenario."""
        if not self.registry:
            return {"scenario": self.name, "success": False, "error": "No registry"}

        broadcaster = self.agents.get("agent_0")
        if not broadcaster:
            return {"scenario": self.name, "success": False, "error": "No broadcaster"}

        # Broadcast message
        broadcast_content = {
            "type": "announcement",
            "message": "Important announcement to all agents",
        }

        response = await broadcaster.broadcast(
            self.registry.workspace_id,
            broadcast_content,
        )

        await asyncio.sleep(0.5)

        return {
            "scenario": self.name,
            "success": response is not None,
            "broadcast_content": broadcast_content,
            "broadcast_response": response,
            "agents_reached": self.num_agents - 1,  # All except broadcaster
            "message_counts": self.registry.get_all_message_counts(),
        }


class CalculatorWorkflow(TestScenario):
    """
    Scenario: Calculator agent performing calculations.

    Tests calculator agent functionality with various operations.
    """

    def __init__(self):
        """Initialize calculator workflow scenario."""
        super().__init__(
            name="Calculator Workflow",
            description="Tests calculator agent with various operations",
        )

    async def setup(self, registry: AgentRegistry) -> None:
        """Set up calculator and client agents."""
        await super().setup(registry)

        calculator = await registry.create_agent("calculator", "calculator", "Calculator")
        client = await registry.create_agent("client", "echo", "Client")

        self.agents = {"calculator": calculator, "client": client}

    async def run(self) -> dict[str, Any]:
        """Run calculator workflow."""
        calculator = self.agents["calculator"]
        client = self.agents["client"]

        test_cases = [
            {"operation": "add", "a": 10, "b": 5, "expected": 15},
            {"operation": "subtract", "a": 10, "b": 3, "expected": 7},
            {"operation": "multiply", "a": 4, "b": 7, "expected": 28},
            {"operation": "divide", "a": 20, "b": 4, "expected": 5},
        ]

        results = []

        for test_case in test_cases:
            response = await client.send_to(
                calculator.sandbox_id,  # type: ignore
                test_case,
            )

            await asyncio.sleep(0.2)

            results.append({
                "test_case": test_case,
                "response": response,
                "success": response is not None,
            })

        return {
            "scenario": self.name,
            "success": True,
            "test_cases": len(test_cases),
            "results": results,
            "message_counts": self.registry.get_all_message_counts() if self.registry else {},
        }


class ResearchAnalysisWorkflow(TestScenario):
    """
    Scenario: Research and analysis workflow.

    Tests researcher and developer agents collaborating.
    """

    def __init__(self):
        """Initialize research-analysis workflow scenario."""
        super().__init__(
            name="Research-Analysis Workflow",
            description="Tests researcher and developer collaboration",
        )

    async def setup(self, registry: AgentRegistry) -> None:
        """Set up researcher and developer agents."""
        await super().setup(registry)

        researcher = await registry.create_agent("researcher", "researcher", "Researcher")
        developer = await registry.create_agent("developer", "developer", "Developer")
        analyst = await registry.create_agent("analyst", "calculator", "Analyst")

        self.agents = {"researcher": researcher, "developer": developer, "analyst": analyst}

    async def run(self) -> dict[str, Any]:
        """Run research-analysis workflow."""
        researcher = self.agents["researcher"]
        developer = self.agents["developer"]
        analyst = self.agents["analyst"]

        workflow_steps = []

        # Step 1: Research
        research_task = {
            "type": "research",
            "topic": "Microservices architecture patterns",
            "depth": "comprehensive",
        }
        response = await researcher.send_to(
            researcher.sandbox_id,  # type: ignore - self-research
            research_task,
        )
        workflow_steps.append({"step": "research", "response": response})

        # Step 2: Development
        dev_task = {
            "type": "implement",
            "feature": "Microservice API gateway",
            "requirements": ["authentication", "rate limiting", "load balancing"],
        }
        response = await developer.send_to(
            developer.sandbox_id,  # type: ignore - self-task
            dev_task,
        )
        workflow_steps.append({"step": "development", "response": response})

        # Step 3: Analysis
        analysis_task = {
            "type": "calculate",
            "operation": "multiply",
            "a": 100,
            "b": 5,
        }
        response = await analyst.send_to(
            analyst.sandbox_id,  # type: ignore - self-calculation
            analysis_task,
        )
        workflow_steps.append({"step": "analysis", "response": response})

        await asyncio.sleep(0.5)

        return {
            "scenario": self.name,
            "success": True,
            "workflow_steps": len(workflow_steps),
            "steps": workflow_steps,
            "message_counts": self.registry.get_all_message_counts() if self.registry else {},
        }


# Predefined scenario instances
SCENARIOS: dict[str, type[TestScenario]] = {
    "two_agent": TwoAgentCommunication,
    "multi_agent": MultiAgentCollaboration,
    "broadcast": BroadcastScenario,
    "calculator": CalculatorWorkflow,
    "research_analysis": ResearchAnalysisWorkflow,
}


async def run_scenario(
    scenario_name: str,
    registry: AgentRegistry,
    **kwargs,
) -> dict[str, Any]:
    """
    Run a predefined scenario.

    Args:
        scenario_name: Name of the scenario to run
        registry: AgentRegistry to use
        **kwargs: Additional arguments for the scenario

    Returns:
        Scenario results
    """
    scenario_class = SCENARIOS.get(scenario_name)
    if not scenario_class:
        raise ValueError(f"Unknown scenario: {scenario_name}")

    scenario = scenario_class(**kwargs)
    return await scenario.execute(registry)
