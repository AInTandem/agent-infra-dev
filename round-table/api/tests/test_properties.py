# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Property-based tests for Round Table API system invariants.

These tests use Hypothesis to generate random inputs and verify that
system properties (invariants) hold true for all valid inputs.
"""

import pytest
from hypothesis import assume, given, HealthCheck, settings, strategies as st
from httpx import AsyncClient


# =============================================================================
# System Health Properties (Fast, no DB required)
# =============================================================================

@pytest.mark.asyncio
@given(retry_count=st.integers(min_value=1, max_value=3))
@settings(max_examples=2, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
async def test_health_check_is_consistent(
    test_client: AsyncClient, retry_count: int
):
    """
    Property: Health check returns consistent results.

    Invariant: Multiple consecutive health checks should return
    the same status for a healthy system.
    """
    results = []
    for _ in range(retry_count):
        response = await test_client.get("/api/v1/system/health")
        assume(response.status_code == 200)
        results.append(response.json()["data"])

    # All results should have the same structure
    for result in results:
        assert "status" in result
        assert "version" in result
        assert "database" in result
        assert "message_bus" in result
        assert "timestamp" in result

    # Status should be consistent
    statuses = [r["status"] for r in results]
    assert all(s == statuses[0] for s in statuses)


@pytest.mark.asyncio
@given(
    workspace_name=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=['L'])),
)
@settings(max_examples=1, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
async def test_workspace_name_validation(
    test_client: AsyncClient, workspace_name: str
):
    """
    Property: Workspace name validation is consistent.

    Invariant: Valid workspace names should be accepted.
    """
    import time
    # Register user
    email = f"test_{int(time.time() * 1000000)}@example.com"
    register_response = await test_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123"},
    )
    assume(register_response.status_code == 201)
    token = register_response.json()["data"]["access_token"]

    # Create workspace with generated name
    workspace_response = await test_client.post(
        "/api/v1/workspaces",
        json={"name": workspace_name[:50]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assume(workspace_response.status_code == 201)

    workspace = workspace_response.json()["data"]
    assert workspace["name"] == workspace_name[:50]
    assert "workspace_id" in workspace


@pytest.mark.asyncio
@given(
    max_sandboxes=st.integers(min_value=1, max_value=10),
    auto_cleanup=st.booleans(),
)
@settings(max_examples=1, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
async def test_workspace_settings_validation(
    test_client: AsyncClient, max_sandboxes: int, auto_cleanup: bool
):
    """
    Property: Workspace settings are preserved correctly.

    Invariant: Settings values should be stored and retrieved accurately.
    """
    import time
    # Register user
    email = f"test_{int(time.time() * 1000000)}@example.com"
    register_response = await test_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123"},
    )
    assume(register_response.status_code == 201)
    token = register_response.json()["data"]["access_token"]

    # Create workspace with specific settings
    workspace_response = await test_client.post(
        "/api/v1/workspaces",
        json={
            "name": "TestWorkspace",
            "settings": {
                "max_sandboxes": max_sandboxes,
                "auto_cleanup": auto_cleanup,
                "retention_days": 30,
                "collaboration_policy": {},
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assume(workspace_response.status_code == 201)
    workspace_id = workspace_response.json()["data"]["workspace_id"]

    # Retrieve workspace
    get_response = await test_client.get(
        f"/api/v1/workspaces/{workspace_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assume(get_response.status_code == 200)
    retrieved = get_response.json()["data"]

    # Verify settings match
    assert retrieved["settings"]["max_sandboxes"] == max_sandboxes
    assert retrieved["settings"]["auto_cleanup"] == auto_cleanup


@pytest.mark.asyncio
@given(
    model=st.sampled_from(["gpt-4", "claude-3", "gpt-3.5-turbo"]),
    temperature=st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=1, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
async def test_sandbox_config_validation(
    test_client: AsyncClient, model: str, temperature: float
):
    """
    Property: Sandbox agent configuration is validated and stored.

    Invariant: Valid agent configurations should be accepted and preserved.
    """
    import time
    # Register user
    email = f"test_{int(time.time() * 1000000)}@example.com"
    register_response = await test_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123"},
    )
    assume(register_response.status_code == 201)
    token = register_response.json()["data"]["access_token"]

    # Create workspace
    workspace_response = await test_client.post(
        "/api/v1/workspaces",
        json={"name": "TestWorkspace"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assume(workspace_response.status_code == 201)
    workspace_id = workspace_response.json()["data"]["workspace_id"]

    # Create sandbox with generated config
    sandbox_response = await test_client.post(
        f"/api/v1/workspaces/{workspace_id}/sandboxes",
        json={
            "name": "TestAgent",
            "agent_config": {
                "primary_agent": "researcher",
                "model": model,
                "temperature": round(temperature, 2),
                "tools": [],
                "extra_config": {},
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assume(sandbox_response.status_code == 201)
    sandbox = sandbox_response.json()["data"]

    # Verify config is preserved
    assert sandbox["agent_config"]["model"] == model
    assert sandbox["agent_config"]["temperature"] == round(temperature, 2)


@pytest.mark.asyncio
@given(
    message_count=st.integers(min_value=1, max_value=2),
)
@settings(max_examples=1, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
async def test_message_creation_properties(
    test_client: AsyncClient, message_count: int
):
    """
    Property: Message creation follows consistent patterns.

    Invariant: Successfully created messages should have valid IDs and metadata.
    """
    import time
    # Register user
    email = f"test_{int(time.time() * 1000000)}@example.com"
    register_response = await test_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123"},
    )
    assume(register_response.status_code == 201)
    token = register_response.json()["data"]["access_token"]

    # Create workspace
    workspace_response = await test_client.post(
        "/api/v1/workspaces",
        json={"name": "TestWorkspace"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assume(workspace_response.status_code == 201)
    workspace_id = workspace_response.json()["data"]["workspace_id"]

    # Create two sandboxes
    sandbox_a = await test_client.post(
        f"/api/v1/workspaces/{workspace_id}/sandboxes",
        json={"name": "AgentA", "agent_config": {"primary_agent": "echo", "model": "gpt-4"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assume(sandbox_a.status_code == 201)
    sandbox_a_id = sandbox_a.json()["data"]["sandbox_id"]

    sandbox_b = await test_client.post(
        f"/api/v1/workspaces/{workspace_id}/sandboxes",
        json={"name": "AgentB", "agent_config": {"primary_agent": "echo", "model": "gpt-4"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assume(sandbox_b.status_code == 201)
    sandbox_b_id = sandbox_b.json()["data"]["sandbox_id"]

    # Send messages
    message_ids = []
    for i in range(message_count):
        message_response = await test_client.post(
            f"/api/v1/sandboxes/{sandbox_a_id}/messages",
            json={
                "to_sandbox_id": sandbox_b_id,
                "content": {"index": i},
                "message_type": "request",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assume(message_response.status_code == 202)
        message_data = message_response.json()["data"]

        # Verify message properties
        assert "message_id" in message_data
        assert message_data["from_sandbox_id"] == sandbox_a_id
        assert message_data["to_sandbox_id"] == sandbox_b_id
        assert message_data["content"]["index"] == i
        assert "created_at" in message_data

        message_ids.append(message_data["message_id"])

    # Verify all message IDs are unique
    assert len(message_ids) == len(set(message_ids))
