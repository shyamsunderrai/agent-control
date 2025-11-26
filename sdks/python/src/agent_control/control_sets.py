"""Control Set management operations for Agent Control SDK."""

from typing import Any, cast

from .client import AgentControlClient


async def create_control_set(
    client: AgentControlClient,
    name: str
) -> dict[str, Any]:
    """
    Create a new control set with a unique name.

    Control sets group multiple atomic controls together.

    Args:
        client: AgentControlClient instance
        name: Unique name for the control set

    Returns:
        Dictionary containing:
            - control_set_id: ID of the created control set

    Raises:
        httpx.HTTPError: If request fails
    """
    response = await client.http_client.put(
        "/api/v1/control-sets",
        json={"name": name}
    )
    response.raise_for_status()
    return cast(dict[str, Any], response.json())


async def add_control_to_control_set(
    client: AgentControlClient,
    control_set_id: int,
    control_id: int
) -> dict[str, Any]:
    """
    Associate an atomic control with a control set.

    Args:
        client: AgentControlClient instance
        control_set_id: ID of the control set
        control_id: ID of the control to add

    Returns:
        Dictionary containing:
            - success: True if operation succeeded
    """
    response = await client.http_client.post(
        f"/api/v1/control-sets/{control_set_id}/controls/{control_id}"
    )
    response.raise_for_status()
    return cast(dict[str, Any], response.json())


async def remove_control_from_control_set(
    client: AgentControlClient,
    control_set_id: int,
    control_id: int
) -> dict[str, Any]:
    """
    Remove an atomic control from a control set.

    Args:
        client: AgentControlClient instance
        control_set_id: ID of the control set
        control_id: ID of the control to remove

    Returns:
        Dictionary containing:
            - success: True if operation succeeded
    """
    response = await client.http_client.delete(
        f"/api/v1/control-sets/{control_set_id}/controls/{control_id}"
    )
    response.raise_for_status()
    return cast(dict[str, Any], response.json())


async def list_control_set_controls(
    client: AgentControlClient,
    control_set_id: int
) -> dict[str, Any]:
    """
    List all controls associated with a control set.

    Args:
        client: AgentControlClient instance
        control_set_id: ID of the control set

    Returns:
        Dictionary containing:
            - control_ids: List of control IDs associated with the control set
    """
    response = await client.http_client.get(
        f"/api/v1/control-sets/{control_set_id}/controls"
    )
    response.raise_for_status()
    return cast(dict[str, Any], response.json())
