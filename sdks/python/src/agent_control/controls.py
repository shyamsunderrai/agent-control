"""Control management operations for Agent Control SDK."""

from typing import Any, cast

# Import models if available
try:
    from agent_control_models import ControlDefinition
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    ControlDefinition = Any # type: ignore

from .client import AgentControlClient


async def create_control(
    client: AgentControlClient,
    name: str
) -> dict[str, Any]:
    """
    Create a new control with a unique name.

    Controls group related rules together and can be added to policies.
    A newly created control has no rules until they are explicitly added.

    Args:
        client: AgentControlClient instance
        name: Unique name for the control

    Returns:
        Dictionary containing:
            - control_id: ID of the created control

    Raises:
        httpx.HTTPError: If request fails
        HTTPException 409: Control with this name already exists
        HTTPException 500: Database error during creation

    Example:
        async with AgentControlClient() as client:
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


async def set_control_data(
    client: AgentControlClient,
    control_id: int,
    data: dict[str, Any] | ControlDefinition
) -> dict[str, Any]:
    """
    Set the configuration data for a control.

    This defines what the control actually does (selector, evaluator, action).

    Args:
        client: AgentControlClient instance
        control_id: ID of the control
        data: Control definition dictionary or Pydantic model

    Returns:
        Dictionary containing success flag

    Raises:
        httpx.HTTPError: If request fails
        HTTPException 422: If data doesn't match schema
    """
    if MODELS_AVAILABLE and isinstance(data, ControlDefinition):
        # Convert model to dict, excluding None to keep payload clean
        payload: dict[str, Any] = data.model_dump(mode="json", exclude_none=True)
    else:
        # We assume it's a dict if it's not a model
        payload = cast(dict[str, Any], data)

    response = await client.http_client.put(
        f"/api/v1/controls/{control_id}/data",
        json={"data": payload}
    )
    response.raise_for_status()
    return cast(dict[str, Any], response.json())


async def add_rule_to_control(
    client: AgentControlClient,
    control_id: int,
    rule_id: int
) -> dict[str, Any]:
    """
    Associate a rule with a control.

    This operation is idempotent - adding the same rule multiple times has no effect.
    Agents with policies containing this control will immediately see the added rule.

    Args:
        client: AgentControlClient instance
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
        async with AgentControlClient() as client:
            result = await add_rule_to_control(client, control_id=5, rule_id=10)
            print(f"Success: {result['success']}")
    """
    response = await client.http_client.post(
        f"/api/v1/controls/{control_id}/rules/{rule_id}"
    )
    response.raise_for_status()
    return cast(dict[str, Any], response.json())


async def remove_rule_from_control(
    client: AgentControlClient,
    control_id: int,
    rule_id: int
) -> dict[str, Any]:
    """
    Remove a rule from a control.

    This operation is idempotent - removing a non-associated rule has no effect.
    Agents with policies containing this control will immediately lose the removed rule.

    Args:
        client: AgentControlClient instance
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
        async with AgentControlClient() as client:
            result = await remove_rule_from_control(client, control_id=5, rule_id=10)
            print(f"Success: {result['success']}")
    """
    response = await client.http_client.delete(
        f"/api/v1/controls/{control_id}/rules/{rule_id}"
    )
    response.raise_for_status()
    return cast(dict[str, Any], response.json())


async def list_control_rules(
    client: AgentControlClient,
    control_id: int
) -> dict[str, Any]:
    """
    List all rules associated with a control.

    Args:
        client: AgentControlClient instance
        control_id: ID of the control

    Returns:
        Dictionary containing:
            - rule_ids: List of rule IDs associated with the control

    Raises:
        httpx.HTTPError: If request fails
        HTTPException 404: Control not found

    Example:
        async with AgentControlClient() as client:
            result = await list_control_rules(client, control_id=5)
            rule_ids = result["rule_ids"]
            print(f"Control has {len(rule_ids)} rules: {rule_ids}")
    """
    response = await client.http_client.get(
        f"/api/v1/controls/{control_id}/rules"
    )
    response.raise_for_status()
    return cast(dict[str, Any], response.json())

