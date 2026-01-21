"""
LangGraph Agent with Agent Control integration.

This package provides a complete example of integrating Agent Control
with a LangGraph agent for safe AI interactions.
"""

from .agent import (
    AgentState,
    create_graph,
    graph,
    run_agent,
)

__all__ = [
    "AgentState",
    "create_graph",
    "run_agent",
    "graph",
]

__version__ = "0.1.0"

