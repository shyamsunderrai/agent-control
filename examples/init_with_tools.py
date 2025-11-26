"""
Example demonstrating agent_control.init() with tool registration.

This shows how to register an agent with the server including tool schemas.
"""

import asyncio
import agent_control
from agent_control import protect


# Define tool schemas
tools = [
    {
        "tool_name": "search_knowledge_base",
        "arguments": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "default": 5}
            },
            "required": ["query"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "results": {
                    "type": "array",
                    "items": {"type": "object"}
                },
                "count": {"type": "integer"}
            }
        }
    },
    {
        "tool_name": "send_email",
        "arguments": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "format": "email"},
                "subject": {"type": "string"},
                "body": {"type": "string"}
            },
            "required": ["to", "subject", "body"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "sent": {"type": "boolean"},
                "message_id": {"type": "string"}
            }
        }
    }
]


# Initialize agent with tools
agent = agent_control.init(
    agent_name="Customer Support Agent",
    agent_id="cs-agent-prod-v1",
    agent_description="Handles customer support inquiries with knowledge base search and email",
    agent_version="1.0.0",
    tools=tools,
    # Additional metadata
    team="customer-success",
    environment="production",
    owner="support-team@example.com"
)


@protect('input-validation', input='query')
async def search_knowledge_base(query: str, max_results: int = 5):
    """Search the knowledge base."""
    print(f"Searching for: {query}")
    # Actual search logic here
    return {
        "results": [
            {"title": "How to reset password", "relevance": 0.95},
            {"title": "Account recovery guide", "relevance": 0.87}
        ],
        "count": 2
    }


@protect('email-check', input='body', context='metadata')
async def send_email(to: str, subject: str, body: str, metadata: dict = None):
    """Send an email to customer."""
    print(f"Sending email to: {to}")
    print(f"Subject: {subject}")
    # Actual email sending logic here
    return {
        "sent": True,
        "message_id": "msg-12345"
    }


async def main():
    """Demonstrate tool usage with protection."""
    print("\n" + "=" * 80)
    print("AGENT WITH TOOLS - EXAMPLE")
    print("=" * 80)
    print()
    
    # Show agent info
    print(f"Agent: {agent.agent_name}")
    print(f"ID: {agent.agent_id}")
    print(f"Version: {agent.agent_version}")
    print(f"Tools: {len(tools)} registered")
    print()
    
    # Use tools with protection
    print("Testing tools with protection...")
    print("-" * 80)
    
    try:
        # Search knowledge base
        results = await search_knowledge_base("password reset")
        print(f"✓ Search results: {results['count']} found")
        print()
        
        # Send email
        response = await send_email(
            to="customer@example.com",
            subject="Password Reset Instructions",
            body="Here's how to reset your password...",
            metadata={"user_id": "user123", "request_id": "req456"}
        )
        print(f"✓ Email sent: {response['sent']}")
        print()
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("• Agent registered with server")
    print("• Tools versioned and tracked")
    print("• Protection rules applied to all tool calls")
    print("• Server can monitor and control tool usage")
    print()


if __name__ == "__main__":
    asyncio.run(main())

