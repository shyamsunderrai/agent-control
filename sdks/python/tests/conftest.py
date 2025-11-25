"""
Pytest configuration and fixtures for Agent Protect SDK integration tests.

These fixtures provide shared setup and teardown for integration tests
that run against a live Agent Protect server.
"""

import os
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import agent_protect
import httpx
import pytest
import pytest_asyncio


@pytest.fixture(scope="session")
def server_url() -> str:
    """
    Get the Agent Protect server URL from environment or use default.

    Override with AGENT_PROTECT_TEST_URL environment variable.
    """
    return os.getenv("AGENT_PROTECT_TEST_URL", "http://localhost:8000")


@pytest_asyncio.fixture(scope="session")
async def verify_server_running(server_url: str) -> None:
    """
    Verify that the Agent Protect server is running before tests.

    Raises pytest.skip if server is not available.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{server_url}/health", timeout=5.0)
            response.raise_for_status()
            print(f"\n✓ Server is running at {server_url}")
    except Exception as e:
        pytest.skip(f"Agent Protect server not available at {server_url}: {e}")


@pytest_asyncio.fixture
async def client(
    server_url: str,
    verify_server_running: None
) -> AsyncGenerator[agent_protect.AgentProtectClient, None]:
    """
    Provide an authenticated Agent Protect client for tests.

    The client is automatically closed after the test completes.
    """
    async with agent_protect.AgentProtectClient(base_url=server_url) as client:
        yield client


@pytest.fixture
def unique_name() -> str:
    """Generate a unique name for test resources to avoid conflicts."""
    return f"test-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_agent_id() -> str:
    """Generate a unique agent ID for testing."""
    return f"test-agent-{uuid.uuid4().hex[:12]}"


@pytest_asyncio.fixture
async def test_agent(
    client: agent_protect.AgentProtectClient,
    test_agent_id: str,
    server_url: str
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Create and register a test agent.

    Returns the agent data and cleans up after test completes.
    """
    # Create agent instance
    from datetime import UTC, datetime

    from agent_protect_models import Agent

    # Generate a proper UUID4 for the agent
    agent_uuid = uuid.uuid4()

    agent = Agent(
        agent_id=agent_uuid,
        agent_name=f"Test Agent {test_agent_id}",
        agent_description="Integration test agent",
        agent_created_at=datetime.now(UTC).isoformat(),
        agent_updated_at=None,
        agent_version="1.0.0",
        agent_metadata={"test": True}
    )

    # Register agent
    response = await agent_protect.agents.register_agent(
        client,
        agent,
        tools=[
            {
                "tool_name": "test_search",
                "arguments": {"query": {"type": "string"}},
                "output_schema": {"results": {"type": "array"}}
            }
        ]
    )

    yield {
        "agent": agent,
        "agent_id": str(agent_uuid),
        "response": response
    }

    # Cleanup is handled by the server (agents persist)


@pytest_asyncio.fixture
async def test_policy(
    client: agent_protect.AgentProtectClient,
    unique_name: str
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Create a test policy.

    Returns the policy data. Note: Cleanup should be done manually
    as we don't have a delete endpoint yet.
    """
    result = await agent_protect.policies.create_policy(
        client,
        f"test-policy-{unique_name}"
    )

    yield result

    # TODO: Add cleanup when delete endpoint is available


@pytest_asyncio.fixture
async def test_control(
    client: agent_protect.AgentProtectClient,
    unique_name: str
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Create a test control.

    Returns the control data. Note: Cleanup should be done manually
    as we don't have a delete endpoint yet.
    """
    result = await agent_protect.controls.create_control(
        client,
        f"test-control-{unique_name}"
    )

    yield result

    # TODO: Add cleanup when delete endpoint is available


@pytest.fixture
def sample_tools() -> list[dict[str, Any]]:
    """Provide sample tool definitions for testing."""
    return [
        {
            "tool_name": "search_database",
            "arguments": {
                "query": {"type": "string", "required": True},
                "limit": {"type": "integer", "default": 10}
            },
            "output_schema": {
                "results": {"type": "array"},
                "count": {"type": "integer"}
            }
        },
        {
            "tool_name": "send_email",
            "arguments": {
                "to": {"type": "string", "required": True},
                "subject": {"type": "string"},
                "body": {"type": "string"}
            },
            "output_schema": {
                "success": {"type": "boolean"},
                "message_id": {"type": "string"}
            }
        }
    ]

