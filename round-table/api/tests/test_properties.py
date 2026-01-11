# Copyright (c) 2025 AInTandem
# SPDX-License-Identifier: MIT

"""
Property-based tests for Round Table API system invariants.

These tests use Hypothesis to generate random inputs and verify that
system properties (invariants) hold true for all valid inputs.

Note: These tests use simplified strategies and max_examples=1 to avoid
CPU overload. For production use, consider unit-level property tests instead
of full API integration tests.
"""

import pytest
import uuid
from hypothesis import given, settings, strategies as st, HealthCheck
from httpx import AsyncClient


# Counter for generating unique test data
_test_counter = 0


def _get_unique_email():
    """Generate unique email for testing."""
    global _test_counter
    _test_counter += 1
    return f"prop_{_test_counter}_{uuid.uuid4().hex[:8]}@test.example"


# =============================================================================
# Optimized Property-Based Tests
# =============================================================================

@pytest.mark.asyncio
@given(retry_count=st.integers(min_value=1, max_value=2))
@settings(max_examples=2, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
async def test_health_check_is_consistent(
    test_client: AsyncClient, retry_count: int
):
    """
    Property: Health check returns consistent results across multiple calls.

    Invariant: Multiple consecutive health checks should return the same status.
    """
    results = []
    for _ in range(retry_count):
        response = await test_client.get("/api/v1/system/health")
        assert response.status_code == 200
        results.append(response.json()["data"])

    # All results should have the same structure
    for result in results:
        assert "status" in result
        assert "version" in result
        assert "database" in result
        assert "message_bus" in result

    # Status should be consistent
    statuses = [r["status"] for r in results]
    assert all(s == statuses[0] for s in statuses)


@pytest.mark.asyncio
@given(workspace_num=st.integers(min_value=1, max_value=5))
@settings(max_examples=1, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
async def test_workspace_name_accepts_valid_input(
    test_client: AsyncClient, workspace_num: int
):
    """
    Property: Workspace API accepts valid name inputs.

    Invariant: For valid name formats, creation should succeed.
    """
    # Register user
    email = _get_unique_email()
    register_response = await test_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123"},
    )
    assert register_response.status_code == 200
    token = register_response.json()["data"]["access_token"]

    # Create workspace with generated name
    workspace_name = f"TestWorkspace{workspace_num}"
    workspace_response = await test_client.post(
        "/api/v1/workspaces",
        json={"name": workspace_name},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert workspace_response.status_code == 201

    workspace = workspace_response.json()["data"]
    assert workspace["name"] == workspace_name
    assert "workspace_id" in workspace


@pytest.mark.asyncio
@given(max_sandboxes=st.integers(min_value=1, max_value=5))
@settings(max_examples=1, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
async def test_workspace_settings_roundtrip(
    test_client: AsyncClient, max_sandboxes: int
):
    """
    Property: Workspace settings survive round-trip to database.

    Invariant: Settings stored match settings retrieved.
    """
    # Register user
    email = _get_unique_email()
    register_response = await test_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123"},
    )
    assert register_response.status_code == 200
    token = register_response.json()["data"]["access_token"]

    # Create workspace with specific setting
    workspace_response = await test_client.post(
        "/api/v1/workspaces",
        json={
            "name": "SettingsTestWorkspace",
            "settings": {
                "max_sandboxes": max_sandboxes,
                "auto_cleanup": True,
                "retention_days": 30,
                "collaboration_policy": {},
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert workspace_response.status_code == 201
    workspace_id = workspace_response.json()["data"]["workspace_id"]

    # Retrieve workspace
    get_response = await test_client.get(
        f"/api/v1/workspaces/{workspace_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_response.status_code == 200
    retrieved = get_response.json()["data"]

    # Verify setting survived round-trip
    assert retrieved["settings"]["max_sandboxes"] == max_sandboxes


@pytest.mark.asyncio
@given(temperature=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
@settings(max_examples=1, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
async def test_sandbox_temperature_preserved(
    test_client: AsyncClient, temperature: float
):
    """
    Property: Sandbox temperature setting is preserved accurately.

    Invariant: The temperature value stored matches what was provided.
    """
    # Register user
    email = _get_unique_email()
    register_response = await test_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123"},
    )
    assert register_response.status_code == 200
    token = register_response.json()["data"]["access_token"]

    # Create workspace
    workspace_response = await test_client.post(
        "/api/v1/workspaces",
        json={"name": "TempTestWorkspace"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert workspace_response.status_code == 201
    workspace_id = workspace_response.json()["data"]["workspace_id"]

    # Create sandbox with generated temperature
    temp_value = round(temperature, 2)
    sandbox_response = await test_client.post(
        f"/api/v1/sandboxes/{workspace_id}/sandboxes",
        json={
            "name": "TempTestAgent",
            "agent_config": {
                "primary_agent": "researcher",
                "model": "gpt-4",
                "temperature": temp_value,
                "tools": [],
                "extra_config": {},
            },
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sandbox_response.status_code == 201
    sandbox = sandbox_response.json()["data"]

    # Verify temperature is preserved
    assert sandbox["agent_config"]["temperature"] == temp_value


@pytest.mark.asyncio
@given(content_num=st.integers(min_value=0, max_value=9))
@settings(max_examples=1, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
async def test_message_content_preservation(
    test_client: AsyncClient, content_num: int
):
    """
    Property: Message content is preserved through the API.

    Invariant: Content sent matches content stored.
    """
    # Register user
    email = _get_unique_email()
    register_response = await test_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123"},
    )
    assert register_response.status_code == 200
    token = register_response.json()["data"]["access_token"]

    # Create workspace
    workspace_response = await test_client.post(
        "/api/v1/workspaces",
        json={"name": "MessageTestWorkspace"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert workspace_response.status_code == 201
    workspace_id = workspace_response.json()["data"]["workspace_id"]

    # Create two sandboxes
    sandbox_a = await test_client.post(
        f"/api/v1/sandboxes/{workspace_id}/sandboxes",
        json={"name": "SenderA", "agent_config": {"primary_agent": "echo", "model": "gpt-4"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sandbox_a.status_code == 201
    sandbox_a_id = sandbox_a.json()["data"]["sandbox_id"]

    sandbox_b = await test_client.post(
        f"/api/v1/sandboxes/{workspace_id}/sandboxes",
        json={"name": "ReceiverB", "agent_config": {"primary_agent": "echo", "model": "gpt-4"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sandbox_b.status_code == 201
    sandbox_b_id = sandbox_b.json()["data"]["sandbox_id"]

    # Send message with generated content
    test_content = {"index": content_num, "test": True}
    message_response = await test_client.post(
        f"/api/v1/messages/sandboxes/{sandbox_a_id}/messages",
        json={
            "to_sandbox_id": sandbox_b_id,
            "content": test_content,
            "message_type": "request",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert message_response.status_code == 202
    message = message_response.json()["data"]

    # Verify content is preserved
    assert message["content"] == test_content
    assert message["from_sandbox_id"] == sandbox_a_id
    assert message["to_sandbox_id"] == sandbox_b_id
    assert "message_id" in message
