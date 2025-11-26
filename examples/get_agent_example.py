"""
Example demonstrating how to fetch agent details from the server.
"""

import asyncio
import agent_control


async def example_with_client():
    """Example using AgentControlClient directly."""
    print("=" * 80)
    print("EXAMPLE 1: Using AgentControlClient")
    print("=" * 80)
    print()

    async with agent_control.AgentControlClient() as client:
        try:
            # Get agent by ID using the agents module
            agent_id = "550e8400-e29b-41d4-a716-446655440000"
            agent_data = await agent_control.agents.get_agent(client, agent_id)
            
            print(f"✓ Found agent!")
            print(f"  Name: {agent_data['agent']['agent_name']}")
            print(f"  ID: {agent_data['agent']['agent_id']}")
            print(f"  Description: {agent_data['agent'].get('agent_description', 'N/A')}")
            print(f"  Version: {agent_data['agent'].get('agent_version', 'N/A')}")
            print(f"  Tools: {len(agent_data['tools'])} registered")
            
            if agent_data['tools']:
                print(f"\n  Tool names:")
                for tool in agent_data['tools']:
                    print(f"    - {tool['tool_name']}")
            
        except Exception as e:
            print(f"✗ Error: {e}")
    
    print()


async def example_module_function():
    """Example using the module-level function."""
    print("=" * 80)
    print("EXAMPLE 2: Using get_agent() module function")
    print("=" * 80)
    print()

    try:
        agent_id = "550e8400-e29b-41d4-a716-446655440000"
        agent_data = await agent_control.get_agent(agent_id)
        
        print(f"✓ Found agent: {agent_data['agent']['agent_name']}")
        print(f"  Tools: {len(agent_data['tools'])}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
    
    print()


def example_current_agent():
    """Example getting currently initialized agent."""
    print("=" * 80)
    print("EXAMPLE 3: Get current agent (initialized locally)")
    print("=" * 80)
    print()

    # Initialize an agent
    agent = agent_control.init(
        agent_name="Test Bot",
        agent_id="test-bot-123",
        agent_description="A test bot for demonstration"
    )
    
    # Get the current agent
    current = agent_control.current_agent()
    
    if current:
        print(f"✓ Current agent: {current.agent_name}")
        print(f"  ID: {current.agent_id}")
    else:
        print("✗ No agent initialized")
    
    print()


async def main():
    """Run all examples."""
    print()
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "GET AGENT EXAMPLES" + " " * 40 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    
    # Example 1: Using client directly
    await example_with_client()
    
    # Example 2: Using module function
    await example_module_function()
    
    # Example 3: Get current agent
    example_current_agent()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("• Use client.get_agent(id) for full control")
    print("• Use agent_control.get_agent(id) for simple async fetch")
    print("• Use agent_control.current_agent() for locally initialized agent")
    print()


if __name__ == "__main__":
    asyncio.run(main())

