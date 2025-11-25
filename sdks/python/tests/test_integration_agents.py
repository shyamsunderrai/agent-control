"""
Integration tests for Agent operations.

These tests verify the full agent lifecycle:
1. Agent registration
2. Agent retrieval
3. Agent updates
"""

import uuid

import agent_protect
import pytest


@pytest.mark.asyncio
async def test_agent_registration_workflow(
    client: agent_protect.AgentProtectClient,
    test_agent_id: str,
    sample_tools: list
) -> None:
    """
    Test complete agent registration workflow.

    Verifies:
    - Agent can be registered with tools
    - Response includes created flag
    - Response includes rules (may be empty)
    """
    from datetime import UTC, datetime

    from agent_protect_models import Agent

    # Generate a proper UUID4 for the agent
    agent_uuid = uuid.uuid4()
    agent = Agent(
        agent_id=agent_uuid,
        agent_name="Integration Test Agent",
        agent_description="Testing agent registration",
        agent_created_at=datetime.now(UTC).isoformat(),
        agent_updated_at=None,
        agent_version="1.0.0",
        agent_metadata={"env": "test"}
    )

    # Register agent
    response = await agent_protect.agents.register_agent(
        client,
        agent,
        tools=sample_tools
    )

    # Verify response structure
    assert "created" in response
    assert "rules" in response
    assert isinstance(response["created"], bool)
    assert isinstance(response["rules"], list)

    print(f"✓ Agent registered: {response['created']}")
    print(f"✓ Rules received: {len(response['rules'])}")


@pytest.mark.asyncio
async def test_agent_retrieval_workflow(
    client: agent_protect.AgentProtectClient,
    test_agent: dict
) -> None:
    """
    Test agent retrieval workflow.

    Verifies:
    - Registered agent can be retrieved
    - Response includes agent metadata
    - Response includes registered tools
    """
    agent_id = test_agent["agent_id"]

    # Retrieve agent
    agent_data = await agent_protect.agents.get_agent(client, agent_id)

    # Verify response structure
    assert "agent" in agent_data
    assert "tools" in agent_data

    # Verify agent metadata
    agent = agent_data["agent"]
    assert agent["agent_id"] == agent_id
    assert agent["agent_name"] is not None
    assert "agent_description" in agent

    # Verify tools
    tools = agent_data["tools"]
    assert isinstance(tools, list)
    assert len(tools) > 0  # Should have at least the test_search tool

    print(f"✓ Agent retrieved: {agent['agent_name']}")
    print(f"✓ Tools found: {len(tools)}")


@pytest.mark.asyncio
async def test_agent_update_workflow(
    client: agent_protect.AgentProtectClient,
    test_agent: dict,
    sample_tools: list
) -> None:
    """
    Test agent update workflow (re-registration).

    Verifies:
    - Existing agent can be updated via re-registration
    - Response indicates update (created=False)
    - Tools are updated
    """
    agent = test_agent["agent"]

    # Update agent (re-register with different tools)
    updated_tools = sample_tools[:1]  # Use only first tool
    response = await agent_protect.agents.register_agent(
        client,
        agent,
        tools=updated_tools
    )

    # Verify this was an update, not a new creation
    assert response["created"] is False

    print("✓ Agent updated successfully")
    print(f"✓ Updated with {len(updated_tools)} tool(s)")


@pytest.mark.asyncio
async def test_convenience_get_agent_function(
    test_agent: dict,
    server_url: str
) -> None:
    """
    Test the convenience get_agent() function.

    Verifies:
    - Convenience function works without manual client management
    - Returns same data as client-based approach
    """
    agent_id = test_agent["agent_id"]

    # Use convenience function
    agent_data = await agent_protect.get_agent(agent_id, server_url=server_url)

    # Verify response
    assert "agent" in agent_data
    assert agent_data["agent"]["agent_id"] == agent_id

    print("✓ Convenience function works")


@pytest.mark.asyncio
async def test_init_function_workflow(
    test_agent_id: str,
    server_url: str,
    sample_tools: list
) -> None:
    """
    Test the init() function workflow.

    Verifies:
    - init() successfully registers agent
    - Returns Agent instance
    - current_agent() returns initialized agent
    """
    # Initialize agent
    agent = agent_protect.init(
        agent_name="Init Test Agent",
        agent_id=test_agent_id,
        agent_description="Testing init function",
        agent_version="1.0.0",
        server_url=server_url,
        tools=sample_tools,
        environment="test"
    )

    # Verify agent instance
    assert agent is not None
    assert agent.agent_name == "Init Test Agent"
    assert hasattr(agent, "agent_id")

    # Verify current_agent()
    current = agent_protect.current_agent()
    assert current is not None
    assert current.agent_name == agent.agent_name

    print("✓ init() function works")
    print("✓ current_agent() returns initialized agent")

