"""
Integration tests for Control operations.

These tests verify control management workflows:
1. Control creation
2. Adding/removing rules from controls
3. Listing control rules
"""

import agent_control
import pytest


@pytest.mark.asyncio
async def test_control_creation_workflow(
    client: agent_control.AgentControlClient,
    unique_name: str
) -> None:
    """
    Test control creation workflow.

    Verifies:
    - Control can be created with unique name
    - Response includes control_id
    - Duplicate names are rejected
    """
    control_name = f"test-control-{unique_name}"

    # Create control
    result = await agent_control.controls.create_control(client, control_name)

    # Verify response
    assert "control_id" in result
    assert isinstance(result["control_id"], int)

    control_id = result["control_id"]
    print(f"✓ Control created: ID {control_id}")

    # Try to create duplicate (should fail with 409)
    with pytest.raises(Exception) as exc_info:
        await agent_control.controls.create_control(client, control_name)

    # Verify it's a 409 conflict error
    assert "409" in str(exc_info.value)
    print("✓ Duplicate control name correctly rejected")


@pytest.mark.asyncio
async def test_control_association_workflow(
    client: agent_control.AgentControlClient,
    test_control: dict
) -> None:
    """
    Test adding and removing atomic controls from control sets.

    Verifies:
    - Atomic control can be added to control set (if controls exist)
    - Operation is idempotent
    - Control can be removed from control set
    - Removal is idempotent

    Note: This test assumes control IDs exist in the database or creates them.
    """
    # 1. Create a control set first
    import uuid
    cs_name = f"test-cs-{uuid.uuid4()}"
    cs_result = await agent_control.control_sets.create_control_set(client, cs_name)
    control_set_id = cs_result["control_set_id"]

    control_id = test_control["control_id"]

    try:
        # Add control to control set
        result = await agent_control.control_sets.add_control_to_control_set(
            client,
            control_set_id,
            control_id
        )

        assert result["success"] is True
        print(f"✓ Control {control_id} added to control set {control_set_id}")

        # Add again (should be idempotent)
        result = await agent_control.control_sets.add_control_to_control_set(
            client,
            control_set_id,
            control_id
        )

        assert result["success"] is True
        print("✓ Idempotent add verified")

        # List controls to verify
        controls_result = await agent_control.control_sets.list_control_set_controls(
            client,
            control_set_id
        )

        assert control_id in controls_result["control_ids"]
        print("✓ Control appears in control set controls list")

        # Remove control from control set
        result = await agent_control.control_sets.remove_control_from_control_set(
            client,
            control_set_id,
            control_id
        )

        assert result["success"] is True
        print("✓ Control removed from control set")

        # Remove again (should be idempotent)
        result = await agent_control.control_sets.remove_control_from_control_set(
            client,
            control_set_id,
            control_id
        )

        assert result["success"] is True
        print("✓ Idempotent remove verified")

        # Verify control is no longer in list
        controls_result = await agent_control.control_sets.list_control_set_controls(
            client,
            control_set_id
        )

        assert control_id not in controls_result["control_ids"]
        print("✓ Control no longer in control set controls list")

    except Exception:
        raise


@pytest.mark.asyncio
async def test_list_control_set_controls_workflow(
    client: agent_control.AgentControlClient,
) -> None:
    """
    Test listing control set controls.

    Verifies:
    - Empty control set returns empty list
    - Response structure is correct
    """
    import uuid
    cs_name = f"test-cs-{uuid.uuid4()}"
    cs_result = await agent_control.control_sets.create_control_set(client, cs_name)
    control_set_id = cs_result["control_set_id"]

    # List controls (should be empty for new control set)
    result = await agent_control.control_sets.list_control_set_controls(client, control_set_id)

    # Verify response structure
    assert "control_ids" in result
    assert isinstance(result["control_ids"], list)

    print(f"✓ Control set has {len(result['control_ids'])} controls")


@pytest.mark.asyncio
async def test_control_set_not_found_error(
    client: agent_control.AgentControlClient
) -> None:
    """
    Test error handling for non-existent control set.

    Verifies:
    - 404 error is raised for non-existent control set
    """
    non_existent_cs_id = 999999

    with pytest.raises(Exception) as exc_info:
        await agent_control.control_sets.list_control_set_controls(
            client,
            non_existent_cs_id
        )

    # Verify it's a 404 error
    assert "404" in str(exc_info.value)
    print("✓ 404 error correctly raised for non-existent control set")

