"""
Example using the new agent_control.init() interface.

This is the cleanest way to initialize and protect your agent.
"""

import asyncio
import sys
from pathlib import Path

# Add sdks to path
sdk_path = Path(__file__).parents[3] / "sdks" / "python" / "src"
sys.path.insert(0, str(sdk_path))

import agent_control
from agent_control import protect

# ============================================================================
# STEP 1: Initialize at the base of your agent - ONE LINE with YOUR metadata!
# ============================================================================
agent_control.init(
    agent_name="Example Customer Service Bot",
    agent_id="csbot-example-v1",
    agent_description="Handles customer inquiries with safety checks",
    agent_version="1.0.0",
    # Optional: Add any custom metadata
    team="customer-success",
    environment="development"
)


# ============================================================================
# STEP 2: Use @protect decorator on your functions
# ============================================================================
@protect('input-llm-span', input='content', context='ctx')
async def check_before_llm(content: str, ctx: dict) -> str:
    """
    This function is protected by rules in rules.yaml.
    Rules with step_id: "input-llm-span" will be applied.
    """
    return f"Processed: {content}"


@protect('output-validation', output='response', context='ctx')
async def generate_response(query: str, ctx: dict) -> str:
    """Output is automatically validated and PII is redacted."""
    # Simulate LLM response
    response = f"Response to {query}: Contact support@example.com or call 555-123-4567"
    return response


# ============================================================================
# STEP 3: Use your protected functions
# ============================================================================
async def main():
    """Demonstrate the agent_control.init() approach."""

    print("=" * 80)
    print("AGENT PROTECT - SIMPLIFIED INITIALIZATION")
    print("=" * 80)
    print()

    # Get agent info
    agent = agent_control.get_agent("csbot-example-v1")
    print(f"Agent Name: {agent.agent_name}")
    print(f"Agent ID: {agent.agent_id}")
    print(f"Description: {agent.agent_description}")
    print(f"Version: {agent.agent_version}")
    print()

    # Test 1: Safe input
    print("Test 1: Safe input")
    print("-" * 80)
    try:
        result = await check_before_llm(
            "Hello, I need help with my order",
            {"user_id": "user123", "session": "abc"}
        )
        print(f"✓ Success: {result}")
    except Exception as e:
        print(f"✗ Blocked: {e}")
    print()

    # Test 2: Input with restricted name (from rules.yaml)
    print("Test 2: Input with restricted name")
    print("-" * 80)
    try:
        result = await check_before_llm(
            "Hi, my name is Nachiket and I need help",
            {"user_id": "user123"}
        )
        print(f"✓ Success: {result}")
    except Exception as e:
        print(f"✗ Blocked: {e}")
    print()

    # Test 3: Output with PII (should be redacted)
    print("Test 3: Output with PII redaction")
    print("-" * 80)
    try:
        result = await generate_response(
            "How do I contact support?",
            {"user_id": "user123"}
        )
        print(f"✓ Success (PII redacted): {result}")
    except Exception as e:
        print(f"✗ Blocked: {e}")
    print()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("✓ Agent registered with full metadata")
    print("✓ Rules auto-discovered and applied")
    print("✓ Server connection established")
    print("✓ Protection active on all decorated functions")
    print()
    print("Usage:")
    print("  import agent_control")
    print("  agent_control.init(agent_name='...', agent_id='...')")
    print("  from agent_control import protect")
    print()


if __name__ == "__main__":
    asyncio.run(main())

