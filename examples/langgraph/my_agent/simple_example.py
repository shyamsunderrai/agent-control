"""
Simplest possible example using init_protect() with auto-configuration.

This demonstrates the new streamlined approach:
1. Just call init_protect() - no arguments needed!
2. Rules are auto-discovered from rules.yaml
3. Agent is automatically registered with the server
"""

import asyncio
from protect_engine import init_protect, protect, RuleViolation


# ============================================================================
# STEP 1: Initialize at the base of your agent - ONE LINE!
# ============================================================================
init_protect()  # That's it! Auto-discovers rules.yaml and registers with server


# ============================================================================
# STEP 2: Use @protect decorator on your functions
# ============================================================================
@protect('input-llm-span', input='content', context='ctx')
async def check_before_llm(content: str, ctx: dict) -> str:
    """
    This function is protected by the rules in rules.yaml.
    
    Rules with step_id: "input-llm-span" will be applied automatically.
    """
    return f"Processed: {content}"


@protect('output-validation', output='response', context='ctx')
async def generate_response(query: str, ctx: dict) -> str:
    """
    Output is automatically validated and PII is redacted.
    """
    # Simulate LLM response
    response = f"Response to {query}: User SSN is 123-45-6789"
    return response


# ============================================================================
# STEP 3: Use your protected functions normally
# ============================================================================
async def main():
    """Demonstrate the simplified approach."""
    
    print("=" * 80)
    print("SIMPLIFIED PROTECT ENGINE - AUTO-CONFIGURED")
    print("=" * 80)
    print()
    print("✓ init_protect() called - agent auto-configured")
    print("✓ Rules auto-discovered from rules.yaml")
    print("✓ Agent registered with server")
    print()
    
    # Test 1: Safe input
    print("Test 1: Safe input")
    print("-" * 80)
    try:
        result = await check_before_llm(
            "Hello, how are you?",
            {"user_id": "123"}
        )
        print(f"✓ Success: {result}")
    except RuleViolation as e:
        print(f"✗ Blocked: {e.message}")
    print()
    
    # Test 2: Input with restricted name (from rules.yaml)
    print("Test 2: Input with restricted name")
    print("-" * 80)
    try:
        result = await check_before_llm(
            "My name is Nachiket",
            {"user_id": "123"}
        )
        print(f"✓ Success: {result}")
    except RuleViolation as e:
        print(f"✗ Blocked: {e.message}")
    print()
    
    # Test 3: Output with PII (should be redacted)
    print("Test 3: Output with PII")
    print("-" * 80)
    try:
        result = await generate_response(
            "Get user info",
            {"user_id": "123"}
        )
        print(f"✓ Success (PII redacted): {result}")
    except RuleViolation as e:
        print(f"✗ Blocked: {e.message}")
    print()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("• Only ONE line to initialize: init_protect()")
    print("• No need to specify rules.yaml path")
    print("• No need to configure server URL")
    print("• Everything auto-configured!")
    print()


if __name__ == "__main__":
    asyncio.run(main())

