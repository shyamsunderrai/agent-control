"""
Interactive CLI for the LangGraph agent with Agent Protect.

This provides a simple command-line interface to interact with the agent.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

from agent import run_agent, AGENT_PROTECT_AVAILABLE


def print_banner():
    """Print the application banner."""
    print("=" * 60)
    print("🤖  LangGraph Agent with Agent Protect")
    print("=" * 60)
    print()
    
    if AGENT_PROTECT_AVAILABLE:
        print("✅ Agent Protect: Enabled")
    else:
        print("⚠️  Agent Protect: Disabled (safety checks skipped)")
    
    print()
    print("Type your message and press Enter to chat.")
    print("Type 'quit', 'exit', or press Ctrl+C to exit.")
    print("=" * 60)
    print()


async def interactive_chat():
    """Run an interactive chat session with the agent."""
    print_banner()
    
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            # Check for exit commands
            if user_input.lower() in ["quit", "exit", "q"]:
                print("\n👋 Goodbye!")
                break
            
            # Skip empty input
            if not user_input:
                continue
            
            # Show thinking indicator
            print("🤔 Agent is thinking...", end="\r")
            
            # Get agent response
            response = await run_agent(user_input)
            
            # Clear thinking indicator and show response
            print(" " * 30, end="\r")  # Clear the thinking message
            print(f"Agent: {response}")
            print()
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print()


async def single_query(query: str):
    """Run a single query and exit."""
    print(f"User: {query}")
    response = await run_agent(query)
    print(f"Agent: {response}")


def main():
    """Main entry point for the CLI."""
    # Load environment variables
    load_dotenv()
    
    # Check for required environment variables
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in environment variables.")
        print("Please set it in your .env file or environment.")
        sys.exit(1)
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        # Single query mode
        query = " ".join(sys.argv[1:])
        asyncio.run(single_query(query))
    else:
        # Interactive mode
        asyncio.run(interactive_chat())


if __name__ == "__main__":
    main()

