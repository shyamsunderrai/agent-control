"""Integration tests for the full policy→control set→control chain."""

import uuid

from fastapi.testclient import TestClient


def _create_agent(client: TestClient, name: str | None = None) -> tuple[str, str]:
    """Helper: Create an agent and return (agent_id, agent_name)."""
    agent_id = str(uuid.uuid4())
    agent_name = name or f"agent-{uuid.uuid4()}"
    payload = {
        "agent": {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "agent_description": "test",
            "agent_version": "1.0",
            "agent_metadata": {},
        },
        "tools": [],
    }
    resp = client.post("/api/v1/agents/initAgent", json=payload)
    assert resp.status_code == 200
    return agent_id, agent_name


def _create_policy(client: TestClient, name: str | None = None) -> int:
    """Helper: Create a policy and return policy_id."""
    policy_name = name or f"policy-{uuid.uuid4()}"
    resp = client.put("/api/v1/policies", json={"name": policy_name})
    assert resp.status_code == 200
    return resp.json()["policy_id"]


def _create_control_set(client: TestClient, name: str | None = None) -> int:
    """Helper: Create a control set and return control_set_id."""
    control_set_name = name or f"cs-{uuid.uuid4()}"
    resp = client.put("/api/v1/control-sets", json={"name": control_set_name})
    assert resp.status_code == 200
    return resp.json()["control_set_id"]


from .utils import VALID_CONTROL_PAYLOAD

def _create_control(client: TestClient, name: str | None = None, data: dict | None = None) -> int:
    """Helper: Create a control and return control_id."""
    control_name = name or f"control-{uuid.uuid4()}"
    resp = client.put("/api/v1/controls", json={"name": control_name})
    assert resp.status_code == 200
    control_id = resp.json()["control_id"]
    
    # Always set valid data, using name/data in description for traceability
    payload = VALID_CONTROL_PAYLOAD.copy()
    payload["description"] = f"Name: {control_name}, Data: {data}"
    
    resp = client.put(f"/api/v1/controls/{control_id}/data", json={"data": payload})
    assert resp.status_code == 200
    
    return control_id


def test_agent_gets_controls_from_multiple_control_sets(client: TestClient) -> None:
    """Agent should see all controls from all control sets in its policy."""
    # Given: Agent with policy containing 3 control sets, each with 2 controls
    agent_id, _ = _create_agent(client)
    policy_id = _create_policy(client)
    
    # Create 3 control sets, each with 2 unique controls
    control_data_by_cs = {}
    for i in range(3):
        control_set_id = _create_control_set(client, f"cs-{i}")
        controls = []
        for j in range(2):
            control_data = {"cs": i, "control": j, "level": i * 10 + j}
            control_id = _create_control(client, f"control-{i}-{j}", control_data)
            controls.append((control_id, control_data))
            # Associate control with control set
            resp = client.post(f"/api/v1/control-sets/{control_set_id}/controls/{control_id}")
            assert resp.status_code == 200
        control_data_by_cs[control_set_id] = controls
        # Associate control set with policy
        resp = client.post(f"/api/v1/policies/{policy_id}/control_sets/{control_set_id}")
        assert resp.status_code == 200
    
    # Assign policy to agent
    resp = client.post(f"/api/v1/agents/{agent_id}/policy/{policy_id}")
    assert resp.status_code == 200
    
    # When: Get agent's controls
    resp = client.get(f"/api/v1/agents/{agent_id}/controls")
    assert resp.status_code == 200
    controls = resp.json()["controls"]
    
    # Then: Agent sees all 6 controls (3 CS × 2 controls)
    assert len(controls) == 6
    
    # Verify all control IDs are present
    received_ids = {r["id"] for r in controls}
    expected_ids = set()
    for cs_controls in control_data_by_cs.values():
        for cid, _ in cs_controls:
            expected_ids.add(cid)
    assert received_ids == expected_ids


def test_agent_gets_no_duplicate_controls_from_shared_control(client: TestClient) -> None:
    """When same control is in multiple control sets, agent should see it only once."""
    # Given: Policy with 2 control sets sharing the same control
    agent_id, _ = _create_agent(client)
    policy_id = _create_policy(client)
    cs_1_id = _create_control_set(client, "cs-1")
    cs_2_id = _create_control_set(client, "cs-2")
    
    # Create a shared control and a unique control per CS
    shared_control_data = {"type": "shared", "value": 42}
    shared_control_id = _create_control(client, "shared-control", shared_control_data)
    
    unique_control_1_data = {"type": "unique-1", "value": 1}
    unique_control_1_id = _create_control(client, "unique-1", unique_control_1_data)
    
    unique_control_2_data = {"type": "unique-2", "value": 2}
    unique_control_2_id = _create_control(client, "unique-2", unique_control_2_data)
    
    # Add shared control to both CS
    client.post(f"/api/v1/control-sets/{cs_1_id}/controls/{shared_control_id}")
    client.post(f"/api/v1/control-sets/{cs_2_id}/controls/{shared_control_id}")
    
    # Add unique controls
    client.post(f"/api/v1/control-sets/{cs_1_id}/controls/{unique_control_1_id}")
    client.post(f"/api/v1/control-sets/{cs_2_id}/controls/{unique_control_2_id}")
    
    # Associate control sets with policy
    client.post(f"/api/v1/policies/{policy_id}/control_sets/{cs_1_id}")
    client.post(f"/api/v1/policies/{policy_id}/control_sets/{cs_2_id}")
    
    # Assign policy to agent
    client.post(f"/api/v1/agents/{agent_id}/policy/{policy_id}")
    
    # When: Get agent's controls
    resp = client.get(f"/api/v1/agents/{agent_id}/controls")
    assert resp.status_code == 200
    controls = resp.json()["controls"]
    
    # Then: Agent sees 3 unique controls (not 4)
    assert len(controls) == 3
    
    # Verify IDs
    received_ids = {r["id"] for r in controls}
    assert shared_control_id in received_ids
    assert unique_control_1_id in received_ids
    assert unique_control_2_id in received_ids


def test_agent_controls_update_when_control_set_added_to_policy(client: TestClient) -> None:
    """Adding a control set to policy should add its controls to the agent."""
    # Given: Agent with policy that has 1 control set with 2 controls
    agent_id, _ = _create_agent(client)
    policy_id = _create_policy(client)
    cs_1_id = _create_control_set(client, "cs-1")
    
    control_1_id = _create_control(client, "control-1", {"id": 1})
    control_2_id = _create_control(client, "control-2", {"id": 2})
    
    client.post(f"/api/v1/control-sets/{cs_1_id}/controls/{control_1_id}")
    client.post(f"/api/v1/control-sets/{cs_1_id}/controls/{control_2_id}")
    client.post(f"/api/v1/policies/{policy_id}/control_sets/{cs_1_id}")
    client.post(f"/api/v1/agents/{agent_id}/policy/{policy_id}")
    
    # Verify initial state: 2 controls
    resp = client.get(f"/api/v1/agents/{agent_id}/controls")
    assert len(resp.json()["controls"]) == 2
    
    # When: Add another control set with 3 controls to the policy
    cs_2_id = _create_control_set(client, "cs-2")
    control_3_id = _create_control(client, "control-3", {"id": 3})
    control_4_id = _create_control(client, "control-4", {"id": 4})
    control_5_id = _create_control(client, "control-5", {"id": 5})
    
    client.post(f"/api/v1/control-sets/{cs_2_id}/controls/{control_3_id}")
    client.post(f"/api/v1/control-sets/{cs_2_id}/controls/{control_4_id}")
    client.post(f"/api/v1/control-sets/{cs_2_id}/controls/{control_5_id}")
    client.post(f"/api/v1/policies/{policy_id}/control_sets/{cs_2_id}")
    
    # Then: Agent now sees 5 controls total
    resp = client.get(f"/api/v1/agents/{agent_id}/controls")
    controls = resp.json()["controls"]
    assert len(controls) == 5
    
    control_ids = {r["id"] for r in controls}
    assert control_ids == {control_1_id, control_2_id, control_3_id, control_4_id, control_5_id}


def test_agent_controls_update_when_control_added_to_control_set(client: TestClient) -> None:
    """Adding a control to control set should make it visible to agents via policy."""
    # Given: Agent → Policy → ControlSet → 2 controls
    agent_id, _ = _create_agent(client)
    policy_id = _create_policy(client)
    cs_id = _create_control_set(client)
    
    control_1_id = _create_control(client, "control-1", {"id": 1})
    control_2_id = _create_control(client, "control-2", {"id": 2})
    
    client.post(f"/api/v1/control-sets/{cs_id}/controls/{control_1_id}")
    client.post(f"/api/v1/control-sets/{cs_id}/controls/{control_2_id}")
    client.post(f"/api/v1/policies/{policy_id}/control_sets/{cs_id}")
    client.post(f"/api/v1/agents/{agent_id}/policy/{policy_id}")
    
    # Verify initial state: 2 controls
    resp = client.get(f"/api/v1/agents/{agent_id}/controls")
    assert len(resp.json()["controls"]) == 2
    
    # When: Add new control to the control set
    control_3_id = _create_control(client, "control-3", {"id": 3})
    resp = client.post(f"/api/v1/control-sets/{cs_id}/controls/{control_3_id}")
    assert resp.status_code == 200
    
    # Then: Agent immediately sees 3 controls
    resp = client.get(f"/api/v1/agents/{agent_id}/controls")
    controls = resp.json()["controls"]
    assert len(controls) == 3
    
    control_ids = {r["id"] for r in controls}
    assert control_ids == {control_1_id, control_2_id, control_3_id}


def test_switching_agent_policy_changes_controls(client: TestClient) -> None:
    """Switching agent's policy should completely change its controls."""
    # Given: Two policies with different control sets/control sets
    agent_id, _ = _create_agent(client)
    
    # Policy A with controls {1, 2}
    policy_a_id = _create_policy(client, "policy-a")
    cs_a_id = _create_control_set(client, "cs-a")
    control_1_id = _create_control(client, "control-1", {"policy": "A", "id": 1})
    control_2_id = _create_control(client, "control-2", {"policy": "A", "id": 2})
    client.post(f"/api/v1/control-sets/{cs_a_id}/controls/{control_1_id}")
    client.post(f"/api/v1/control-sets/{cs_a_id}/controls/{control_2_id}")
    client.post(f"/api/v1/policies/{policy_a_id}/control_sets/{cs_a_id}")
    
    # Policy B with controls {3, 4}
    policy_b_id = _create_policy(client, "policy-b")
    cs_b_id = _create_control_set(client, "cs-b")
    control_3_id = _create_control(client, "control-3", {"policy": "B", "id": 3})
    control_4_id = _create_control(client, "control-4", {"policy": "B", "id": 4})
    client.post(f"/api/v1/control-sets/{cs_b_id}/controls/{control_3_id}")
    client.post(f"/api/v1/control-sets/{cs_b_id}/controls/{control_4_id}")
    client.post(f"/api/v1/policies/{policy_b_id}/control_sets/{cs_b_id}")
    
    # Assign policy A to agent
    client.post(f"/api/v1/agents/{agent_id}/policy/{policy_a_id}")
    resp = client.get(f"/api/v1/agents/{agent_id}/controls")
    controls_a = resp.json()["controls"]
    assert len(controls_a) == 2
    assert {r["id"] for r in controls_a} == {control_1_id, control_2_id}
    
    # When: Switch to policy B
    resp = client.post(f"/api/v1/agents/{agent_id}/policy/{policy_b_id}")
    assert resp.status_code == 200
    
    # Then: Agent's controls change completely
    resp = client.get(f"/api/v1/agents/{agent_id}/controls")
    controls_b = resp.json()["controls"]
    assert len(controls_b) == 2
    assert {r["id"] for r in controls_b} == {control_3_id, control_4_id}


def test_removing_agent_policy_clears_controls(client: TestClient) -> None:
    """Removing policy from agent should result in empty controls list."""
    # Given: Agent with policy that has controls
    agent_id, _ = _create_agent(client)
    policy_id = _create_policy(client)
    cs_id = _create_control_set(client)
    control_id = _create_control(client, "control-1", {"id": 1})
    
    client.post(f"/api/v1/control-sets/{cs_id}/controls/{control_id}")
    client.post(f"/api/v1/policies/{policy_id}/control_sets/{cs_id}")
    client.post(f"/api/v1/agents/{agent_id}/policy/{policy_id}")
    
    # Verify agent has controls
    resp = client.get(f"/api/v1/agents/{agent_id}/controls")
    assert len(resp.json()["controls"]) > 0
    
    # When: Remove policy from agent
    resp = client.delete(f"/api/v1/agents/{agent_id}/policy")
    assert resp.status_code == 200
    
    # Then: Agent returns empty controls list
    resp = client.get(f"/api/v1/agents/{agent_id}/controls")
    assert resp.status_code == 200
    assert resp.json()["controls"] == []


def test_removing_control_set_from_policy_removes_its_controls_from_agent(
    client: TestClient,
) -> None:
    """Removing control set from policy should remove its controls from agent."""
    # Given: Agent → Policy → 2 control sets (A, B) each with controls
    agent_id, _ = _create_agent(client)
    policy_id = _create_policy(client)
    
    # CS A with controls {1, 2}
    cs_a_id = _create_control_set(client, "cs-a")
    control_1_id = _create_control(client, "control-1", {"cs": "A", "id": 1})
    control_2_id = _create_control(client, "control-2", {"cs": "A", "id": 2})
    client.post(f"/api/v1/control-sets/{cs_a_id}/controls/{control_1_id}")
    client.post(f"/api/v1/control-sets/{cs_a_id}/controls/{control_2_id}")
    
    # CS B with controls {3, 4}
    cs_b_id = _create_control_set(client, "cs-b")
    control_3_id = _create_control(client, "control-3", {"cs": "B", "id": 3})
    control_4_id = _create_control(client, "control-4", {"cs": "B", "id": 4})
    client.post(f"/api/v1/control-sets/{cs_b_id}/controls/{control_3_id}")
    client.post(f"/api/v1/control-sets/{cs_b_id}/controls/{control_4_id}")
    
    # Add both CS to policy
    client.post(f"/api/v1/policies/{policy_id}/control_sets/{cs_a_id}")
    client.post(f"/api/v1/policies/{policy_id}/control_sets/{cs_b_id}")
    client.post(f"/api/v1/agents/{agent_id}/policy/{policy_id}")
    
    # Verify initial state: 4 controls
    resp = client.get(f"/api/v1/agents/{agent_id}/controls")
    assert len(resp.json()["controls"]) == 4
    
    # When: Remove CS A from policy
    resp = client.delete(f"/api/v1/policies/{policy_id}/control_sets/{cs_a_id}")
    assert resp.status_code == 200
    
    # Then: Agent only sees controls from CS B
    resp = client.get(f"/api/v1/agents/{agent_id}/controls")
    controls = resp.json()["controls"]
    assert len(controls) == 2
    assert {r["id"] for r in controls} == {control_3_id, control_4_id}


def test_removing_control_from_control_set_removes_from_agent(client: TestClient) -> None:
    """Removing control from control set should remove it from agent."""
    # Given: Agent → Policy → ControlSet → 3 controls
    agent_id, _ = _create_agent(client)
    policy_id = _create_policy(client)
    cs_id = _create_control_set(client)
    
    control_1_id = _create_control(client, "control-1", {"id": 1})
    control_2_id = _create_control(client, "control-2", {"id": 2})
    control_3_id = _create_control(client, "control-3", {"id": 3})
    
    client.post(f"/api/v1/control-sets/{cs_id}/controls/{control_1_id}")
    client.post(f"/api/v1/control-sets/{cs_id}/controls/{control_2_id}")
    client.post(f"/api/v1/control-sets/{cs_id}/controls/{control_3_id}")
    client.post(f"/api/v1/policies/{policy_id}/control_sets/{cs_id}")
    client.post(f"/api/v1/agents/{agent_id}/policy/{policy_id}")
    
    # Verify initial state: 3 controls
    resp = client.get(f"/api/v1/agents/{agent_id}/controls")
    assert len(resp.json()["controls"]) == 3
    
    # When: Remove 1 control from CS
    resp = client.delete(f"/api/v1/control-sets/{cs_id}/controls/{control_2_id}")
    assert resp.status_code == 200
    
    # Then: Agent sees 2 controls
    resp = client.get(f"/api/v1/agents/{agent_id}/controls")
    controls = resp.json()["controls"]
    assert len(controls) == 2
    assert {r["id"] for r in controls} == {control_1_id, control_3_id}


def test_multiple_agents_same_policy(client: TestClient) -> None:
    """Multiple agents with same policy should all see the same controls."""
    # Given: 2 agents assigned to same policy
    agent_1_id, _ = _create_agent(client, "agent-1")
    agent_2_id, _ = _create_agent(client, "agent-2")
    
    policy_id = _create_policy(client)
    cs_id = _create_control_set(client)
    
    control_1_id = _create_control(client, "control-1", {"id": 1})
    control_2_id = _create_control(client, "control-2", {"id": 2})
    
    client.post(f"/api/v1/control-sets/{cs_id}/controls/{control_1_id}")
    client.post(f"/api/v1/control-sets/{cs_id}/controls/{control_2_id}")
    client.post(f"/api/v1/policies/{policy_id}/control_sets/{cs_id}")
    
    # Assign same policy to both agents
    client.post(f"/api/v1/agents/{agent_1_id}/policy/{policy_id}")
    client.post(f"/api/v1/agents/{agent_2_id}/policy/{policy_id}")
    
    # Verify both see same controls initially
    resp_1 = client.get(f"/api/v1/agents/{agent_1_id}/controls")
    resp_2 = client.get(f"/api/v1/agents/{agent_2_id}/controls")
    assert len(resp_1.json()["controls"]) == 2
    assert len(resp_2.json()["controls"]) == 2
    
    # When: Add new control to policy's control set
    control_3_id = _create_control(client, "control-3", {"id": 3})
    client.post(f"/api/v1/control-sets/{cs_id}/controls/{control_3_id}")
    
    # Then: Both agents see the new control
    resp_1 = client.get(f"/api/v1/agents/{agent_1_id}/controls")
    resp_2 = client.get(f"/api/v1/agents/{agent_2_id}/controls")
    
    controls_1 = resp_1.json()["controls"]
    controls_2 = resp_2.json()["controls"]
    
    assert len(controls_1) == 3
    assert len(controls_2) == 3
    expected = {control_1_id, control_2_id, control_3_id}
    assert {r["id"] for r in controls_1} == expected
    assert {r["id"] for r in controls_2} == expected
