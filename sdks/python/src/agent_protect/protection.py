"""Protection check operations for Agent Protect SDK."""

from typing import Any, Literal, cast
from uuid import UUID

from .client import AgentProtectClient

# Import models if available
try:
    from agent_protect_models import (
        LlmCall,
        ProtectionRequest,
        ProtectionResult,
        ToolCall,
    )
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    # Runtime fallbacks
    ToolCall = Any  # type: ignore
    LlmCall = Any  # type: ignore
    ProtectionRequest = Any  # type: ignore
    ProtectionResult = Any  # type: ignore


async def check_protection(
    client: AgentProtectClient,
    agent_uuid: UUID,
    payload: "ToolCall | LlmCall",
    check_stage: Literal["pre", "post"],
) -> ProtectionResult:
    """
    Check if agent interaction is safe.

    Args:
        client: AgentProtectClient instance
        agent_uuid: UUID of the agent making the request
        payload: Either a ToolCall or LlmCall instance
        check_stage: 'pre' for pre-execution check, 'post' for post-execution check

    Returns:
        ProtectionResult with safety analysis

    Raises:
        httpx.HTTPError: If request fails

    Example:
        # Pre-check before LLM call
        async with AgentProtectClient() as client:
            result = await check_protection(
                client=client,
                agent_uuid=agent.agent_id,
                payload=LlmCall(input="User question", output=None),
                check_stage="pre"
            )

        # Post-check after tool execution
        async with AgentProtectClient() as client:
            result = await check_protection(
                client=client,
                agent_uuid=agent.agent_id,
                payload=ToolCall(
                    tool_name="search",
                    arguments={"query": "test"},
                    output={"results": []}
                ),
                check_stage="post"
            )
    """
    if MODELS_AVAILABLE:
        request = ProtectionRequest(
            agent_uuid=agent_uuid,
            payload=payload,
            check_stage=check_stage
        )
        request_payload = request.to_dict()
    else:
        # Fallback for when models aren't available
        payload_dict = {
            "tool_name": getattr(payload, "tool_name", None),
            "arguments": getattr(payload, "arguments", None),
            "input": getattr(payload, "input", None),
            "output": getattr(payload, "output", None),
            "context": getattr(payload, "context", None),
        }
        # Remove None values
        payload_dict = {k: v for k, v in payload_dict.items() if v is not None}

        request_payload = {
            "agent_uuid": str(agent_uuid),
            "payload": payload_dict,
            "check_stage": check_stage,
        }

    response = await client.http_client.post("/api/v1/protect", json=request_payload)
    response.raise_for_status()

    if MODELS_AVAILABLE:
        return cast(ProtectionResult, ProtectionResult.from_dict(response.json()))
    else:
        data = response.json()
        # Create a simple result object
        class _ProtectionResult:
            def __init__(self, is_safe: bool, confidence: float, reason: str | None = None):
                self.is_safe = is_safe
                self.confidence = confidence
                self.reason = reason
        return cast(ProtectionResult, _ProtectionResult(**data))

