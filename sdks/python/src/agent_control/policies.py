"""Policy management operations for Agent Control SDK."""

from typing import Any, cast

from .client import AgentControlClient


async def create_policy(
    client: AgentControlClient,
    name: str
) -> dict[str, Any]:
    """
    Create a new policy with a unique name.

    Policies group controls together and can be assigned to agents.
    A newly created policy has no controls until they are explicitly added.

    Args:
        client: AgentControlClient instance
        name: Unique name for the policy

    Returns:
        Dictionary containing:
            - policy_id: ID of the created policy

    Raises:
        httpx.HTTPError: If request fails
        HTTPException 409: Policy with this name already exists
        HTTPException 500: Database error during creation

    Example:
        async with AgentControlClient() as client:
            result = await create_policy(client, "production-policy")
            policy_id = result["policy_id"]
            print(f"Created policy with ID: {policy_id}")
    """
    response = await client.http_client.put(
        "/api/v1/policies",
        json={"name": name}
    )
    response.raise_for_status()
    return cast(dict[str, Any], response.json())


async def add_control_set_to_policy(
    client: AgentControlClient,
    policy_id: int,
    control_set_id: int
) -> dict[str, Any]:
    """
    Associate a control set with a policy.

    This operation is idempotent - adding the same control set multiple times has no effect.
    Agents with this policy will immediately see controls from the added control set.

    Args:
        client: AgentControlClient instance
        policy_id: ID of the policy
        control_set_id: ID of the control set to add

    Returns:
        Dictionary containing:
            - success: True if operation succeeded

    Raises:
        httpx.HTTPError: If request fails
        HTTPException 404: Policy or control set not found
        HTTPException 500: Database error

    Example:
        async with AgentControlClient() as client:
            result = await add_control_set_to_policy(client, policy_id=1, control_set_id=5)
            print(f"Success: {result['success']}")
    """
    response = await client.http_client.post(
        f"/api/v1/policies/{policy_id}/control_sets/{control_set_id}"
    )
    response.raise_for_status()
    return cast(dict[str, Any], response.json())


async def remove_control_set_from_policy(
    client: AgentControlClient,
    policy_id: int,
    control_set_id: int
) -> dict[str, Any]:
    """
    Remove a control set from a policy.

    This operation is idempotent - removing a non-associated control set has no effect.
    Agents with this policy will immediately lose controls from the removed control set.

    Args:
        client: AgentControlClient instance
        policy_id: ID of the policy
        control_set_id: ID of the control set to remove

    Returns:
        Dictionary containing:
            - success: True if operation succeeded

    Raises:
        httpx.HTTPError: If request fails
        HTTPException 404: Policy or control set not found
        HTTPException 500: Database error

    Example:
        async with AgentControlClient() as client:
            result = await remove_control_set_from_policy(client, policy_id=1, control_set_id=5)
            print(f"Success: {result['success']}")
    """
    response = await client.http_client.delete(
        f"/api/v1/policies/{policy_id}/control_sets/{control_set_id}"
    )
    response.raise_for_status()
    return cast(dict[str, Any], response.json())


async def list_policy_control_sets(
    client: AgentControlClient,
    policy_id: int
) -> dict[str, Any]:
    """
    List all control sets associated with a policy.

    Args:
        client: AgentControlClient instance
        policy_id: ID of the policy

    Returns:
        Dictionary containing:
            - control_set_ids: List of control set IDs associated with the policy

    Raises:
        httpx.HTTPError: If request fails
        HTTPException 404: Policy not found

    Example:
        async with AgentControlClient() as client:
            result = await list_policy_control_sets(client, policy_id=1)
            control_set_ids = result["control_set_ids"]
            print(f"Policy has {len(control_set_ids)} control sets: {control_set_ids}")
    """
    response = await client.http_client.get(
        f"/api/v1/policies/{policy_id}/control_sets"
    )
    response.raise_for_status()
    return cast(dict[str, Any], response.json())


async def assign_policy_to_agent(
    client: AgentControlClient,
    agent_id: str,
    policy_id: int
) -> dict[str, Any]:
    """
    Assign a policy to an agent.

    This makes the policy active for the agent. Any existing policy assignment is replaced.

    Args:
        client: AgentControlClient instance
        agent_id: UUID or string identifier of the agent
        policy_id: ID of the policy to assign

    Returns:
        Dictionary containing success flag/details

    Raises:
        httpx.HTTPError: If request fails
        HTTPException 404: Agent or policy not found
    """
    response = await client.http_client.post(
        f"/api/v1/agents/{agent_id}/policy/{policy_id}"
    )
    response.raise_for_status()
    return cast(dict[str, Any], response.json())

