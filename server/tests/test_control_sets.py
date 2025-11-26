import uuid

from fastapi.testclient import TestClient


def _create_control_set(client: TestClient) -> int:
    name = f"cs-{uuid.uuid4()}"
    r = client.put("/api/v1/control-sets", json={"name": name})
    assert r.status_code == 200
    return r.json()["control_set_id"]


def _create_control(client: TestClient) -> int:
    name = f"ctl-{uuid.uuid4()}"
    r = client.put("/api/v1/controls", json={"name": name})
    assert r.status_code == 200
    return r.json()["control_id"]


def test_create_control_set_and_duplicate_name(client: TestClient) -> None:
    # Given: a control set name
    name = f"cs-{uuid.uuid4()}"
    # When: creating control set
    r1 = client.put("/api/v1/control-sets", json={"name": name})
    # Then: 200 with id
    assert r1.status_code == 200
    assert isinstance(r1.json()["control_set_id"], int)

    # When: creating same name again
    r2 = client.put("/api/v1/control-sets", json={"name": name})
    # Then: 409
    assert r2.status_code == 409


def test_control_set_add_control_and_list(client: TestClient) -> None:
    # Given: a control set and a control
    cs_id = _create_control_set(client)
    ctl_id = _create_control(client)

    # When: associating control to control set
    r = client.post(f"/api/v1/control-sets/{cs_id}/controls/{ctl_id}")
    # Then: success
    assert r.status_code == 200
    assert r.json()["success"] is True

    # When: listing control set controls
    l = client.get(f"/api/v1/control-sets/{cs_id}/controls")
    # Then: contains control id
    assert l.status_code == 200
    assert ctl_id in l.json()["control_ids"]


def test_control_set_add_control_idempotent(client: TestClient) -> None:
    # Given: a control set with an associated control
    cs_id = _create_control_set(client)
    ctl_id = _create_control(client)
    client.post(f"/api/v1/control-sets/{cs_id}/controls/{ctl_id}")

    # When: adding same control again
    r = client.post(f"/api/v1/control-sets/{cs_id}/controls/{ctl_id}")
    # Then: still success
    assert r.status_code == 200
    assert r.json()["success"] is True

    # And list shows once
    l = client.get(f"/api/v1/control-sets/{cs_id}/controls")
    assert l.status_code == 200
    ids = l.json()["control_ids"]
    assert ids.count(ctl_id) == 1


def test_control_set_remove_control(client: TestClient) -> None:
    # Given: a control set with a control
    cs_id = _create_control_set(client)
    ctl_id = _create_control(client)
    client.post(f"/api/v1/control-sets/{cs_id}/controls/{ctl_id}")

    # When: removing association
    d = client.delete(f"/api/v1/control-sets/{cs_id}/controls/{ctl_id}")
    # Then: success
    assert d.status_code == 200
    assert d.json()["success"] is True

    # When: listing
    l = client.get(f"/api/v1/control-sets/{cs_id}/controls")
    # Then: control not present
    assert l.status_code == 200
    assert ctl_id not in l.json()["control_ids"]


def test_control_set_control_assoc_404s(client: TestClient) -> None:
    # Given: ids
    cs_id = _create_control_set(client)
    ctl_id = _create_control(client)

    # When: control set missing
    r1 = client.post(f"/api/v1/control-sets/999999/controls/{ctl_id}")
    # Then: 404
    assert r1.status_code == 404

    # When: control missing
    r2 = client.post(f"/api/v1/control-sets/{cs_id}/controls/999999")
    # Then: 404
    assert r2.status_code == 404

    # When: list on missing control set
    r3 = client.get("/api/v1/control-sets/999999/controls")
    # Then: 404
    assert r3.status_code == 404

    # When: delete with missing both sides
    r4 = client.delete("/api/v1/control-sets/999999/controls/999999")
    # Then: 404
    assert r4.status_code == 404
