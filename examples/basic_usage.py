"""Basic usage example for Agent Protect."""

import asyncio

from agent_protect import AgentProtectClient


async def main() -> None:
    """Demonstrate basic SDK usage."""
    # Create client with context manager (recommended)
    async with AgentProtectClient(base_url="http://localhost:8000") as client:
        # 1. Health check
        print("1. Checking server health...")
        health = await client.health_check()
        print(f"   Server status: {health['status']}")
        print(f"   Version: {health['version']}\n")

        # 2. Simple protection check
        print("2. Simple protection check...")
        result = await client.check_protection("Hello, this is a safe message")
        print(f"   Is safe: {result.is_safe}")
        print(f"   Confidence: {result.confidence:.2f}")
        print(f"   Reason: {result.reason}\n")

        # 3. Protection check with context
        print("3. Protection check with context...")
        result = await client.check_protection(
            content="User submitted content here",
            context={"source": "user_input", "user_id": "12345"},
        )
        print(f"   Result: {result}\n")

        # 4. Boolean evaluation
        print("4. Boolean evaluation...")
        if result:
            print("   ✓ Content is safe!\n")
        else:
            print("   ✗ Content is unsafe!\n")

        # 5. Confidence check
        print("5. Confidence threshold check...")
        if result.is_confident(threshold=0.9):
            print("   ✓ High confidence result (>= 0.9)\n")
        else:
            print("   ⚠ Low confidence, manual review recommended\n")

        # 6. JSON serialization
        print("6. JSON serialization...")
        json_str = result.to_json()
        print(f"   JSON: {json_str}\n")

        # 7. Dictionary conversion
        print("7. Dictionary conversion...")
        data = result.to_dict()
        print(f"   Dict: {data}\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Agent Protect SDK - Basic Usage Example")
    print("=" * 60)
    print()
    print("Make sure the server is running:")
    print("  cd server && uv run agent-protect-server")
    print()
    print("=" * 60)
    print()

    asyncio.run(main())

