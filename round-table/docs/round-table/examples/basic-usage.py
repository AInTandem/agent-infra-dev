#!/usr/bin/env python3
"""
Round Table - Basic Usage Example

This example demonstrates basic operations with the Round Table Python SDK.
"""

import asyncio
import os
from roundtable import RoundTableClient


async def main():
    # Initialize client
    api_key = os.getenv("ROUND_TABLE_API_KEY", "demo-api-key")
    base_url = os.getenv("ROUND_TABLE_BASE_URL", "http://localhost:8000/api/v1")

    async with RoundTableClient(api_key=api_key, base_url=base_url) as client:
        print("=" * 50)
        print("Round Table - Basic Usage Example")
        print("=" * 50)

        # 1. Create a workspace
        print("\n1. Creating workspace...")
        workspace = await client.workspaces.create(
            name="Demo Workspace",
            description="A simple demo workspace"
        )
        print(f"   ✓ Created workspace: {workspace.workspace_id}")
        print(f"   ✓ Name: {workspace.name}")
        print(f"   ✓ Status: {workspace.status}")

        # 2. Create a sandbox
        print("\n2. Creating sandbox...")
        sandbox = await client.sandboxes.create(
            workspace_id=workspace.workspace_id,
            name="Demo Agent",
            description="A demo AI agent",
            agent_config={
                "primary_agent": "researcher",
                "model": "gpt-4",
                "temperature": 0.7
            }
        )
        print(f"   ✓ Created sandbox: {sandbox.sandbox_id}")
        print(f"   ✓ Name: {sandbox.name}")
        print(f"   ✓ Status: {sandbox.status}")

        # 3. Start the sandbox
        print("\n3. Starting sandbox...")
        started = await client.sandboxes.start(sandbox.sandbox_id)
        print(f"   ✓ Sandbox status: {started.status}")

        # 4. Get sandbox status
        print("\n4. Checking sandbox status...")
        status = await client.sandboxes.status(sandbox.sandbox_id)
        print(f"   ✓ Status: {status.status}")
        print(f"   ✓ Uptime: {status.uptime}")

        # 5. Get sandbox metrics
        print("\n5. Getting sandbox metrics...")
        metrics = await client.sandboxes.metrics(sandbox.sandbox_id)
        print(f"   ✓ Messages sent: {metrics.messages_sent}")
        print(f"   ✓ Messages received: {metrics.messages_received}")

        # 6. List all workspaces
        print("\n6. Listing all workspaces...")
        workspaces = await client.workspaces.list()
        print(f"   ✓ Total workspaces: {workspaces.count}")
        for ws in workspaces.workspaces:
            print(f"     - {ws.name} ({ws.workspace_id})")

        # 7. List all sandboxes in workspace
        print("\n7. Listing sandboxes in workspace...")
        sandboxes = await client.sandboxes.list(workspace.workspace_id)
        print(f"   ✓ Total sandboxes: {sandboxes.count}")
        for sb in sandboxes.sandboxes:
            print(f"     - {sb.name} ({sb.sandbox_id})")

        # 8. Stop the sandbox
        print("\n8. Stopping sandbox...")
        stopped = await client.sandboxes.stop(sandbox.sandbox_id)
        print(f"   ✓ Sandbox status: {stopped.status}")

        # 9. Delete the sandbox
        print("\n9. Deleting sandbox...")
        await client.sandboxes.delete(sandbox.sandbox_id)
        print(f"   ✓ Deleted sandbox: {sandbox.sandbox_id}")

        # 10. Delete the workspace
        print("\n10. Deleting workspace...")
        await client.workspaces.delete(workspace.workspace_id)
        print(f"   ✓ Deleted workspace: {workspace.workspace_id}")

        print("\n" + "=" * 50)
        print("Example completed successfully!")
        print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
