# Agent Protect Models

Shared data models for Agent Protect server and SDK. This package contains all the Pydantic models used for API requests, responses, and data validation.

## Why Shared Models?

Having a separate models package provides several benefits:

1. **Single Source of Truth**: Models are defined once and used everywhere
2. **Type Safety**: Ensures server and SDK use identical data structures
3. **Versioning**: Models can be versioned independently
4. **Easier Maintenance**: Changes propagate automatically to both server and SDK
5. **Clear Contract**: API contract is explicitly defined

## Common Patterns in Popular Python Packages

This design follows patterns used by popular packages:

### 1. Shared Models (Our Approach)
- **Google APIs** (`google-api-core`): Separate proto/model definitions
- **Stripe** (`stripe-python`): Models package shared across components
- **PySpark**: Shared types and schemas

### 2. JSON/Pydantic Hybrid
- **FastAPI**: Pydantic models with JSON serialization
- **Anthropic SDK**: Pydantic models with `.to_dict()` and `.from_dict()`
- **OpenAI SDK**: Typed models with JSON compatibility

## Installation

This package is typically installed as a dependency:

```bash
# Server depends on it
cd server
uv add agent-protect-models

# SDK depends on it
cd sdk
uv add agent-protect-models
```

## Usage

### Basic Usage

```python
from agent_control_models import ProtectionRequest, ProtectionResponse

# Create a request
request = ProtectionRequest(
    content="Hello, world!",
    context={"source": "user_input"}
)

# Serialize to JSON
json_str = request.to_json()
print(json_str)
# {"content": "Hello, world!", "context": {"source": "user_input"}}

# Deserialize from JSON
request_copy = ProtectionRequest.from_json(json_str)
```

### Dictionary Conversion

```python
from agent_control_models import ProtectionResponse

# Create from dict
response = ProtectionResponse.from_dict({
    "is_safe": True,
    "confidence": 0.95,
    "reason": "Content appears safe"
})

# Convert to dict
data = response.to_dict()
print(data)
# {'is_safe': True, 'confidence': 0.95, 'reason': 'Content appears safe'}
```

### Client-Side Result

```python
from agent_control_models import ProtectionResult

result = ProtectionResult(
    is_safe=True,
    confidence=0.92,
    reason="All checks passed"
)

# Boolean evaluation
if result:
    print("Content is safe!")

# Confidence check
if result.is_confident(threshold=0.9):
    print("High confidence result")

# String representation
print(result)
# [SAFE] Confidence: 92% - All checks passed
```

## Models

### BaseModel

Base class for all models with common utilities:

- `to_dict()`: Convert to Python dictionary
- `to_json()`: Convert to JSON string
- `from_dict(data)`: Create from dictionary
- `from_json(json_str)`: Create from JSON string

Configuration:
- Accepts both snake_case and camelCase fields
- Ignores extra fields (forward compatibility)
- Validates on assignment
- Excludes None values in serialization

### HealthResponse

Health check response.

**Fields:**
- `status` (str): Health status
- `version` (str): Application version

### ProtectionRequest

Request for content protection analysis.

**Fields:**
- `content` (str): Content to analyze (required, min length 1)
- `context` (Optional[Dict[str, str]]): Optional context information

### ProtectionResponse

Server response from protection analysis.

**Fields:**
- `is_safe` (bool): Whether content is safe
- `confidence` (float): Confidence score (0.0 to 1.0)
- `reason` (Optional[str]): Explanation for the decision

### ProtectionResult

Client-side result extending ProtectionResponse.

**Additional Methods:**
- `is_confident(threshold=0.8)`: Check if confidence exceeds threshold
- `__bool__()`: Enables `if result:` checks
- `__str__()`: Human-readable representation

## Design Patterns

### 1. Pydantic + JSON

All models support both Pydantic validation and JSON serialization:

```python
# Pydantic validation
request = ProtectionRequest(content="test")  # Validates automatically

# JSON round-trip
json_str = request.to_json()
request_copy = ProtectionRequest.from_json(json_str)
assert request == request_copy
```

### 2. Inheritance for Specialization

`ProtectionResult` extends `ProtectionResponse` with client-side conveniences:

```python
# Server uses ProtectionResponse
response = ProtectionResponse(is_safe=True, confidence=0.95)

# SDK transforms to ProtectionResult
result = ProtectionResult(**response.to_dict())

# Now has extra methods
if result.is_confident():
    print("Confident result!")
```

### 3. Forward Compatibility

Models ignore extra fields, allowing server updates without breaking clients:

```python
# Server adds new field in v2
response_data = {
    "is_safe": True,
    "confidence": 0.95,
    "new_field": "future_feature"  # Will be ignored by v1 clients
}

# V1 client still works
result = ProtectionResponse.from_dict(response_data)
# No error, new_field is simply ignored
```

## Development

### Adding New Models

1. Create a new file in `src/agent_control_models/`
2. Define models extending `BaseModel`
3. Export in `__init__.py`
4. Update both server and SDK to use the new models

Example:

```python
# src/agent_control_models/auth.py
from .base import BaseModel

class AuthRequest(BaseModel):
    api_key: str
    
# src/agent_control_models/__init__.py
from .auth import AuthRequest

__all__ = [..., "AuthRequest"]
```

### Testing

```bash
cd models
uv run pytest
```

## Best Practices

1. **Always extend BaseModel**: Get free JSON/dict conversion
2. **Use Field for validation**: Add constraints and descriptions
3. **Keep models simple**: No business logic, just data
4. **Version carefully**: Model changes affect both server and SDK
5. **Document fields**: Use Field's `description` parameter
6. **Use Optional appropriately**: Mark optional fields clearly

