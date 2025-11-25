"""Tests for rule validation and schema enforcement."""
import uuid
from fastapi.testclient import TestClient
from .utils import VALID_RULE_PAYLOAD

def create_rule(client: TestClient) -> int:
    name = f"rule-{uuid.uuid4()}"
    resp = client.put("/api/v1/rules", json={"name": name})
    assert resp.status_code == 200
    return resp.json()["rule_id"]

def test_validation_invalid_logic_enum(client: TestClient):
    """Test that invalid enum values in config are rejected."""
    rule_id = create_rule(client)
    
    # Given: Payload with invalid 'logic' value
    payload = VALID_RULE_PAYLOAD.copy()
    payload["evaluator"] = {
        "type": "list",
        "config": {
            "values": ["a", "b"],
            "logic": "invalid_logic", # Should be 'any' or 'all'
            "match_on": "match"
        }
    }
    
    # When: Setting rule data
    resp = client.put(f"/api/v1/rules/{rule_id}/data", json={"data": payload})
    
    # Then: 422 Unprocessable Entity
    assert resp.status_code == 422
    
    # Verify error message mentions the field
    errors = resp.json()["detail"]
    # Pydantic error path usually: data.evaluator.list.config.logic
    # Message: "Input should be 'any' or 'all'"
    assert any("logic" in str(e["loc"]) for e in errors)
    assert any("any" in e["msg"] or "all" in e["msg"] for e in errors)


def test_validation_discriminator_mismatch(client: TestClient):
    """Test that config must match the evaluator type."""
    rule_id = create_rule(client)
    
    # Given: type='list' but config has 'pattern' (RegexConfig)
    payload = VALID_RULE_PAYLOAD.copy()
    payload["evaluator"] = {
        "type": "list", 
        "config": {
            "pattern": "some_regex", # Invalid for ListConfig
            # Missing 'values'
        }
    }
    
    # When: Setting rule data
    resp = client.put(f"/api/v1/rules/{rule_id}/data", json={"data": payload})
    
    # Then: 422 Unprocessable Entity
    assert resp.status_code == 422
    
    # Verify error mentions missing required field for ListConfig
    errors = resp.json()["detail"]
    # Expecting 'values' field missing
    assert any("values" in str(e["loc"]) for e in errors)
    assert any("Field required" in e["msg"] for e in errors)


def test_validation_regex_flags_list(client: TestClient):
    """Test validation of regex flags list."""
    rule_id = create_rule(client)
    
    # Given: regex config with invalid flags type (string instead of list)
    payload = VALID_RULE_PAYLOAD.copy()
    payload["evaluator"] = {
        "type": "regex",
        "config": {
            "pattern": "abc",
            "flags": "IGNORECASE" # Should be ["IGNORECASE"]
        }
    }
    
    # When: Setting rule data
    resp = client.put(f"/api/v1/rules/{rule_id}/data", json={"data": payload})
    
    # Then: 422
    assert resp.status_code == 422
    errors = resp.json()["detail"]
    assert any("flags" in str(e["loc"]) for e in errors)


def test_validation_invalid_regex_pattern(client: TestClient):
    """Test validation of regex pattern syntax."""
    rule_id = create_rule(client)
    
    # Given: regex config with invalid pattern (unclosed bracket)
    payload = VALID_RULE_PAYLOAD.copy()
    payload["evaluator"] = {
        "type": "regex",
        "config": {
            "pattern": "[", # Invalid regex
            "flags": []
        }
    }
    
    # When: Setting rule data
    resp = client.put(f"/api/v1/rules/{rule_id}/data", json={"data": payload})
    
    # Then: 422 Unprocessable Entity
    assert resp.status_code == 422
    
    errors = resp.json()["detail"]
    # Verify error message mentions regex compilation failure
    assert any("pattern" in str(e["loc"]) for e in errors)
    assert any("Invalid regex pattern" in e["msg"] for e in errors)
