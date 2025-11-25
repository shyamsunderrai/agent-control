"""Control management operations for Agent Protect SDK."""

from typing import Any, cast

from .client import AgentProtectClient


async def create_control(
    client: AgentProtectClient,
    name: str
) -> dict[str, Any]:
    """
    Create a new control with a unique name.

    Controls group related rules together and can be added to policies.
    A newly created control has no rules until they are explicitly added.

    Args:
        client: AgentProtectClient instance
        name: Unique name for the control

    Returns:
        Dictionary containing:
            - control_id: ID of the created control

    Raises:
        httpx.HTTPError: If request fails
        HTTPException 409: Control with this name already exists
        HTTPException 500: Database error during creation

    Example:
        async with AgentProtectClient() as client:
            result = await create_control(client, "pii-protection")
            control_id = result["control_id"]
            print(f"Created control with ID: {control_id}")
    """
    response = await client.http_client.put(
        "/api/v1/controls",
        json={"name": name}
    )
    response.raise_for_status()
    return cast(dict[str, Any], response.json())


async def add_rule_to_control(
    client: AgentProtectClient,
    control_id: int,
    rule_id: int
) -> dict[str, Any]:
    """
    Associate a rule with a control.

    This operation is idempotent - adding the same rule multiple times has no effect.
    Agents with policies containing this control will immediately see the added rule.

    Args:
        client: AgentProtectClient instance
        control_id: ID of the control
        rule_id: ID of the rule to add

    Returns:
        Dictionary containing:
            - success: True if operation succeeded

    Raises:
        httpx.HTTPError: If request fails
        HTTPException 404: Control or rule not found
        HTTPException 500: Database error

    Example:
        async with AgentProtectClient() as client:
            result = await add_rule_to_control(client, control_id=5, rule_id=10)
            print(f"Success: {result['success']}")
    """
    response = await client.http_client.post(
        f"/api/v1/controls/{control_id}/rules/{rule_id}"
    )
    response.raise_for_status()
    return cast(dict[str, Any], response.json())


async def remove_rule_from_control(
    client: AgentProtectClient,
    control_id: int,
    rule_id: int
) -> dict[str, Any]:
    """
    Remove a rule from a control.

    This operation is idempotent - removing a non-associated rule has no effect.
    Agents with policies containing this control will immediately lose the removed rule.

    Args:
        client: AgentProtectClient instance
        control_id: ID of the control
        rule_id: ID of the rule to remove

    Returns:
        Dictionary containing:
            - success: True if operation succeeded

    Raises:
        httpx.HTTPError: If request fails
        HTTPException 404: Control or rule not found
        HTTPException 500: Database error

    Example:
        async with AgentProtectClient() as client:
            result = await remove_rule_from_control(client, control_id=5, rule_id=10)
            print(f"Success: {result['success']}")
    """
    response = await client.http_client.delete(
        f"/api/v1/controls/{control_id}/rules/{rule_id}"
    )
    response.raise_for_status()
    return cast(dict[str, Any], response.json())


async def list_control_rules(
    client: AgentProtectClient,
    control_id: int
) -> dict[str, Any]:
    """
    List all rules associated with a control.

    Args:
        client: AgentProtectClient instance
        control_id: ID of the control

    Returns:
        Dictionary containing:
            - rule_ids: List of rule IDs associated with the control

    Raises:
        httpx.HTTPError: If request fails
        HTTPException 404: Control not found

    Example:
        async with AgentProtectClient() as client:
            result = await list_control_rules(client, control_id=5)
            rule_ids = result["rule_ids"]
            print(f"Control has {len(rule_ids)} rules: {rule_ids}")
    """
    response = await client.http_client.get(
        f"/api/v1/controls/{control_id}/rules"
    )
    response.raise_for_status()
    return cast(dict[str, Any], response.json())

