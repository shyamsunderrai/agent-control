"""
Integration tests for Policy operations.

These tests verify policy management workflows:
1. Policy creation
2. Adding/removing controls from policies
3. Listing policy controls
"""

import agent_control
import pytest


@pytest.mark.asyncio
async def test_policy_creation_workflow(
    client: agent_control.AgentControlClient,
    unique_name: str
) -> None:
    """
    Test policy creation workflow.

    Verifies:
    - Policy can be created with unique name
    - Response includes policy_id
    - Duplicate names are rejected
    """
    policy_name = f"test-policy-{unique_name}"

    # Create policy
    result = await agent_control.policies.create_policy(client, policy_name)

    # Verify response
    assert "policy_id" in result
    assert isinstance(result["policy_id"], int)

    policy_id = result["policy_id"]
    print(f"✓ Policy created: ID {policy_id}")

    # Try to create duplicate (should fail with 409)
    with pytest.raises(Exception) as exc_info:
        await agent_control.policies.create_policy(client, policy_name)

    # Verify it's a 409 conflict error
    assert "409" in str(exc_info.value)
    print("✓ Duplicate policy name correctly rejected")


@pytest.mark.asyncio
async def test_control_association_workflow(
    client: agent_control.AgentControlClient,
    test_policy: dict,
    test_control: dict
) -> None:
    """
    Test adding and removing control sets from policies.

    Verifies:
    - Control set can be added to policy
    - Operation is idempotent (adding twice works)
    - Control set can be removed from policy
    - Removal is idempotent
    """
    policy_id = test_policy["policy_id"]
    control_id = test_control["control_id"]

    # 1. Create a control set and add control to it (prerequisite)
    import uuid
    cs_name = f"test-cs-{uuid.uuid4()}"
    cs_result = await agent_control.control_sets.create_control_set(client, cs_name)
    control_set_id = cs_result["control_set_id"]

    await agent_control.control_sets.add_control_to_control_set(
        client,
        control_set_id,
        control_id
    )

    # 2. Add control set to policy
    result = await agent_control.policies.add_control_set_to_policy(
        client,
        policy_id,
        control_set_id
    )

    assert result["success"] is True
    print(f"✓ Control set {control_set_id} added to policy {policy_id}")

    # Add again (should be idempotent)
    result = await agent_control.policies.add_control_set_to_policy(
        client,
        policy_id,
        control_set_id
    )

    assert result["success"] is True
    print("✓ Idempotent add verified")

    # List control sets to verify
    cs_result = await agent_control.policies.list_policy_control_sets(
        client,
        policy_id
    )

    assert control_set_id in cs_result["control_set_ids"]
    print("✓ Control set appears in policy control sets list")

    # Remove control set from policy
    result = await agent_control.policies.remove_control_set_from_policy(
        client,
        policy_id,
        control_set_id
    )

    assert result["success"] is True
    print("✓ Control set removed from policy")

    # Remove again (should be idempotent)
    result = await agent_control.policies.remove_control_set_from_policy(
        client,
        policy_id,
        control_set_id
    )

    assert result["success"] is True
    print("✓ Idempotent remove verified")

    # Verify control set is no longer in list
    cs_result = await agent_control.policies.list_policy_control_sets(
        client,
        policy_id
    )

    assert control_set_id not in cs_result["control_set_ids"]
    print("✓ Control set no longer in policy control sets list")


@pytest.mark.asyncio
async def test_list_policy_control_sets_workflow(
    client: agent_control.AgentControlClient,
    test_policy: dict
) -> None:
    """
    Test listing policy control sets.

    Verifies:
    - Empty policy returns empty list
    - Response structure is correct
    """
    policy_id = test_policy["policy_id"]

    # List control sets (should be empty for new policy)
    result = await agent_control.policies.list_policy_control_sets(client, policy_id)

    # Verify response structure
    assert "control_set_ids" in result
    assert isinstance(result["control_set_ids"], list)

    print(f"✓ Policy has {len(result['control_set_ids'])} control sets")


@pytest.mark.asyncio
async def test_policy_not_found_error(
    client: agent_control.AgentControlClient
) -> None:
    """
    Test error handling for non-existent policy.

    Verifies:
    - 404 error is raised for non-existent policy
    """
    non_existent_policy_id = 999999

    with pytest.raises(Exception) as exc_info:
        await agent_control.policies.list_policy_control_sets(
            client,
            non_existent_policy_id
        )

    # Verify it's a 404 error
    assert "404" in str(exc_info.value)
    print("✓ 404 error correctly raised for non-existent policy")

