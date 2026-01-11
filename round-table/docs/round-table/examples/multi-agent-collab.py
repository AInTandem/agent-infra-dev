#!/usr/bin/env python3
"""
Round Table - Multi-Agent Collaboration Example

This example demonstrates how to orchestrate a collaboration
between multiple AI agents using the Round Table Python SDK.
"""

import asyncio
import os
from roundtable import RoundTableClient


async def main():
    # Initialize client
    api_key = os.getenv("ROUND_TABLE_API_KEY", "demo-api-key")
    base_url = os.getenv("ROUND_TABLE_BASE_URL", "http://localhost:8000/api/v1")

    async with RoundTableClient(api_key=api_key, base_url=base_url) as client:
        print("=" * 60)
        print("Round Table - Multi-Agent Collaboration Example")
        print("=" * 60)

        # 1. Create workspace for the project
        print("\n1. Creating project workspace...")
        workspace = await client.workspaces.create(
            name="API Development Project",
            description="Building a REST API with multi-agent collaboration"
        )
        print(f"   ✓ Workspace: {workspace.workspace_id}")

        # 2. Create specialized agents
        print("\n2. Creating specialized agents...")

        # Research Agent
        researcher = await client.sandboxes.create(
            workspace_id=workspace.workspace_id,
            name="Research Specialist",
            description="Handles research and planning",
            agent_config={
                "primary_agent": "researcher",
                "model": "gpt-4",
                "temperature": 0.7
            }
        )
        print(f"   ✓ Created researcher: {researcher.sandbox_id}")

        # Developer Agent
        developer = await client.sandboxes.create(
            workspace_id=workspace.workspace_id,
            name="Developer",
            description="Handles implementation",
            agent_config={
                "primary_agent": "developer",
                "model": "gpt-4",
                "temperature": 0.5
            }
        )
        print(f"   ✓ Created developer: {developer.sandbox_id}")

        # Tester Agent
        tester = await client.sandboxes.create(
            workspace_id=workspace.workspace_id,
            name="QA Tester",
            description="Handles testing and validation",
            agent_config={
                "primary_agent": "tester",
                "model": "gpt-4",
                "temperature": 0.3
            }
        )
        print(f"   ✓ Created tester: {tester.sandbox_id}")

        # 3. Start all agents
        print("\n3. Starting all agents...")
        await client.sandboxes.start(researcher.sandbox_id)
        await client.sandboxes.start(developer.sandbox_id)
        await client.sandboxes.start(tester.sandbox_id)
        print("   ✓ All agents started")

        # 4. Discover available agents
        print("\n4. Discovering agents...")
        agents = await client.collaborations.discover_agents(
            workspace.workspace_id
        )
        print(f"   ✓ Found {agents.count} agents:")
        for agent in agents.agents:
            print(f"     - {agent.name} ({agent.agent_type})")

        # 5. Orchestrate collaboration
        print("\n5. Orchestrating collaboration...")
        task = "Build a REST API for user authentication with JWT tokens"

        collaboration = await client.collaborations.orchestrate(
            workspace_id=workspace.workspace_id,
            task=task,
            participants=[
                researcher.sandbox_id,
                developer.sandbox_id,
                tester.sandbox_id
            ],
            mode="orchestrated",
            config={
                "max_duration": 600,  # 10 minutes
                "timeout": 60,        # 1 minute per operation
                "max_rounds": 20
            }
        )
        print(f"   ✓ Collaboration ID: {collaboration.collaboration_id}")
        print(f"   ✓ Status: {collaboration.status}")

        # 6. Monitor collaboration progress
        print("\n6. Monitoring collaboration progress...")
        status = await client.collaborations.get_collaboration(
            collaboration.collaboration_id
        )
        print(f"   ✓ Current status: {status.status}")
        print(f"   ✓ Progress: {status.progress}%")

        # 7. Send coordination message
        print("\n7. Sending coordination message...")
        message = await client.messages.send(
            from_sandbox_id=researcher.sandbox_id,
            to_sandbox_id=developer.sandbox_id,
            content={
                "type": "task_assignment",
                "task": "Implement user endpoints",
                "specification": {
                    "endpoints": ["/register", "/login", "/logout"],
                    "authentication": "JWT"
                }
            }
        )
        print(f"   ✓ Message sent: {message.message_id}")

        # 8. Check messages received
        print("\n8. Checking developer messages...")
        messages = await client.messages.list(developer.sandbox_id)
        print(f"   ✓ Total messages: {len(messages.messages)}")

        # 9. Get workspace metrics
        print("\n9. Getting workspace metrics...")
        metrics = await client.aggregate_metrics(workspace.workspace_id)
        print(f"   ✓ Total sandboxes: {metrics.total_sandboxes}")
        print(f"   ✓ Active sandboxes: {metrics.active_sandboxes}")
        print(f"   ✓ Total messages: {metrics.total_messages}")

        # 10. Cleanup
        print("\n10. Cleaning up...")
        await client.sandboxes.stop(researcher.sandbox_id)
        await client.sandboxes.stop(developer.sandbox_id)
        await client.sandboxes.stop(tester.sandbox_id)

        await client.sandboxes.delete(researcher.sandbox_id)
        await client.sandboxes.delete(developer.sandbox_id)
        await client.sandboxes.delete(tester.sandbox_id)

        await client.workspaces.delete(workspace.workspace_id)
        print("   ✓ Cleanup complete")

        print("\n" + "=" * 60)
        print("Multi-Agent Collaboration Example completed!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
