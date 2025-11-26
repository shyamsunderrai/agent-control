"""Agent entity models."""
from typing import Any
from uuid import UUID

from pydantic import Field

from .base import BaseModel


class Agent(BaseModel):
    """
    Agent metadata for registration and tracking.

    An agent represents an AI system that can be protected and monitored.
    Each agent has a unique ID and can have multiple tools registered with it.
    """
    agent_id: UUID = Field(
        ..., description="Unique identifier for the agent (UUID format)"
    )
    agent_name: str = Field(
        ..., description="Human-readable name for the agent", min_length=1
    )
    agent_description: str | None = Field(
        None, description="Optional description of the agent's purpose"
    )
    agent_created_at: str | None = Field(
        None, description="ISO 8601 timestamp when agent was created"
    )
    agent_updated_at: str | None = Field(
        None, description="ISO 8601 timestamp when agent was last updated"
    )
    agent_version: str | None = Field(
        None, description="Semantic version string (e.g. '1.0.0')"
    )
    agent_metadata: dict | None = Field(
        None, description="Free-form metadata dictionary for custom properties"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
                    "agent_name": "customer-service-bot",
                    "agent_description": "Handles customer inquiries and support tickets",
                    "agent_version": "1.0.0",
                    "agent_metadata": {"team": "support", "environment": "production"}
                }
            ]
        }
    }


class AgentTool(BaseModel):
    """Tool schema for agent capabilities."""
    tool_name: str = Field(
        ..., description="Unique name for the tool", min_length=1
    )
    arguments: dict[str, Any] = Field(
        ..., description="JSON schema describing tool input parameters"
    )
    output_schema: dict[str, Any] = Field(
        ..., description="JSON schema describing tool output structure"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tool_name": "search_knowledge_base",
                    "arguments": {"query": {"type": "string", "description": "Search query"}},
                    "output_schema": {"results": {"type": "array", "items": {"type": "object"}}}
                }
            ]
        }
    }


class AgentContext(BaseModel):
    """Base class for agent interaction context."""
    context: dict[str, Any] | None = Field(
        default=None,
        description="Optional context (conversation history, metadata, etc.)"
    )

class ToolCall(AgentContext):
    """Represents a tool invocation by the agent."""
    tool_name: str = Field(..., description="Name of the tool called")
    arguments: dict[str, Any] = Field(..., description="Arguments passed to the tool")
    output: str | dict[str, Any] | None = Field(
        None, description="Output of the tool (None for pre-checks)"
    )


class LlmCall(AgentContext):
    """Represents an LLM interaction by the agent."""
    input: str | dict[str, Any] = Field(
        ..., description="Input content to analyze for safety (text or structured data)"
    )
    output: str | dict[str, Any] | None = Field(
        None, description="Output content to analyze for safety (None for pre-checks)"
    )
