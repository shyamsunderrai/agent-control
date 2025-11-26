"""Examples of working with Agent Protect models directly."""

from agent_control_models import (
    HealthResponse,
    EvaluationRequest,
    EvaluationResponse,
    EvaluationResult,
)


def example_basic_models() -> None:
    """Demonstrate basic model usage."""
    print("1. Creating models from scratch")
    print("-" * 60)

    # Create a request
    request = EvaluationRequest(
        content="Test content",
        context={"source": "example", "user": "demo"},
    )
    print(f"Request: {request}")
    print(f"Content: {request.content}")
    print(f"Context: {request.context}\n")

    # Create a response
    response = EvaluationResponse(
        is_safe=True,
        confidence=0.95,
        reason="All checks passed",
    )
    print(f"Response: {response}")
    print(f"Is safe: {response.is_safe}")
    print(f"Confidence: {response.confidence}\n")


def example_json_serialization() -> None:
    """Demonstrate JSON serialization."""
    print("2. JSON Serialization")
    print("-" * 60)

    # Create a model
    request = EvaluationRequest(content="Test", context={"key": "value"})

    # Serialize to JSON
    json_str = request.to_json()
    print(f"JSON string: {json_str}\n")

    # Deserialize from JSON
    request2 = EvaluationRequest.from_json(json_str)
    print(f"Deserialized: {request2}")
    print(f"Are they equal? {request == request2}\n")


def example_dict_conversion() -> None:
    """Demonstrate dictionary conversion."""
    print("3. Dictionary Conversion")
    print("-" * 60)

    # Create from dict
    data = {
        "is_safe": True,
        "confidence": 0.92,
        "reason": "Content appears safe",
    }

    response = EvaluationResponse.from_dict(data)
    print(f"From dict: {response}\n")

    # Convert to dict
    result_dict = response.to_dict()
    print(f"To dict: {result_dict}\n")


def example_protection_result() -> None:
    """Demonstrate EvaluationResult with extra methods."""
    print("4. EvaluationResult (Client-side)")
    print("-" * 60)

    result = EvaluationResult(
        is_safe=True,
        confidence=0.88,
        reason="Moderate confidence",
    )

    # String representation
    print(f"String repr: {result}\n")

    # Boolean check
    if result:
        print("✓ Content is safe\n")

    # Confidence checks
    print(f"Is confident (>= 80%)? {result.is_confident(0.8)}")
    print(f"Is confident (>= 90%)? {result.is_confident(0.9)}")
    print(f"Is confident (>= 95%)? {result.is_confident(0.95)}\n")


def example_validation() -> None:
    """Demonstrate Pydantic validation."""
    print("5. Pydantic Validation")
    print("-" * 60)

    # Valid confidence (0.0 to 1.0)
    try:
        response = EvaluationResponse(is_safe=True, confidence=0.95)
        print(f"✓ Valid: {response}\n")
    except Exception as e:
        print(f"✗ Error: {e}\n")

    # Invalid confidence (> 1.0)
    try:
        response = EvaluationResponse(is_safe=True, confidence=1.5)
        print(f"✓ Valid: {response}\n")
    except Exception as e:
        print(f"✗ Validation error (expected): {type(e).__name__}\n")

    # Missing required field
    try:
        request = EvaluationRequest()  # type: ignore
        print(f"✓ Valid: {request}\n")
    except Exception as e:
        print(f"✗ Validation error (expected): {type(e).__name__}\n")


def example_forward_compatibility() -> None:
    """Demonstrate forward compatibility."""
    print("6. Forward Compatibility")
    print("-" * 60)

    # Server sends new fields that client doesn't know about yet
    data_with_future_fields = {
        "is_safe": True,
        "confidence": 0.95,
        "reason": "All checks passed",
        "new_field_v2": "future feature",  # This will be ignored
        "another_new_field": {"nested": "data"},  # This too
    }

    response = EvaluationResponse.from_dict(data_with_future_fields)
    print(f"Parsed response: {response}")
    print("✓ Extra fields were ignored (forward compatible)\n")


def example_health_response() -> None:
    """Demonstrate HealthResponse model."""
    print("7. HealthResponse Model")
    print("-" * 60)

    health = HealthResponse(status="healthy", version="0.1.0")
    print(f"Health: {health}")
    print(f"JSON: {health.to_json()}\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Agent Protect Models - Usage Examples")
    print("=" * 60)
    print()

    example_basic_models()
    example_json_serialization()
    example_dict_conversion()
    example_protection_result()
    example_validation()
    example_forward_compatibility()
    example_health_response()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)

