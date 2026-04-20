"""Shared utilities for all demo agents."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx

# ── Environment ──────────────────────────────────────────────────────────────

AGENT_CONTROL_URL = os.getenv("AGENT_CONTROL_URL", "http://localhost:8000")
AGENT_CONTROL_API_KEY = os.getenv("AGENT_CONTROL_API_KEY")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class ScenarioResult:
    name: str
    description: str
    passed: bool
    action: Literal["pass", "deny", "steer", "observe"]
    control_name: str | None = None
    guidance: str | None = None
    llm_response: str | None = None
    observed_controls: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def emoji(self) -> str:
        return {
            "pass": "[green]PASS[/green]",
            "deny": "[red]BLOCKED[/red]",
            "steer": "[yellow]STEERED[/yellow]",
            "observe": "[blue]OBSERVED[/blue]",
        }.get(self.action, "?")


# ── Evaluation helpers ────────────────────────────────────────────────────────

def parse_matches(matches: list | None) -> tuple[str, str | None, str | None, list[str]]:
    """Extract (action, control_name, guidance, observed_list) from ControlMatch list."""
    if not matches:
        return "pass", None, None, []

    deny = next((m for m in matches if m.action == "deny"), None)
    steer = next((m for m in matches if m.action == "steer"), None)
    observed = [m.control_name for m in matches if m.action == "observe"]

    if deny:
        return "deny", deny.control_name, None, observed
    if steer:
        ctx = steer.steering_context
        guidance = ctx.message if hasattr(ctx, "message") else str(ctx) if ctx else None
        return "steer", steer.control_name, guidance, observed

    return "observe" if observed else "pass", None, None, observed


# ── Ollama helper ─────────────────────────────────────────────────────────────

async def call_ollama(prompt: str, system: str = "", timeout: float = 30.0) -> str:
    """Call Ollama for LLM inference. Returns mock on failure (keeps demo running)."""
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={"model": OLLAMA_MODEL, "messages": messages, "stream": False},
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"]
    except Exception as exc:
        return f"[MOCK RESPONSE - Ollama unavailable: {exc}] Based on the financial metrics provided, I recommend APPROVAL. The applicant demonstrates strong creditworthiness with verifiable income, acceptable debt-to-income ratio, and solid repayment history."


async def check_ollama_health() -> bool:
    """Check if Ollama is running and the model is available."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                return any(OLLAMA_MODEL.split(":")[0] in m for m in models)
    except Exception:
        pass
    return False


async def ensure_ollama_model() -> None:
    """Pull the Ollama model if not already available."""
    if await check_ollama_health():
        return
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST", f"{OLLAMA_URL}/api/pull",
                json={"name": OLLAMA_MODEL, "stream": False}
            ) as resp:
                resp.raise_for_status()
    except Exception:
        pass


# ── Step schema helpers ───────────────────────────────────────────────────────

def make_llm_step_schema(name: str, description: str = "") -> dict[str, Any]:
    return {
        "type": "llm",
        "name": name,
        "input_schema": {"type": "string", "description": description or f"Input for {name}"},
        "output_schema": {"type": "string", "description": f"LLM response for {name}"},
    }


def make_tool_step_schema(name: str, input_props: dict[str, Any], description: str = "") -> dict[str, Any]:
    return {
        "type": "tool",
        "name": name,
        "input_schema": {
            "type": "object",
            "properties": input_props,
            "description": description or f"Input for {name}",
        },
        "output_schema": {"type": "object"},
    }
