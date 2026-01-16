"""Agent Control Models - Shared data models for server and SDK."""

__version__ = "0.1.0"

from .agent import Agent, AgentContext, AgentTool, LlmCall, ToolCall
from .controls import (
    ControlAction,
    ControlDefinition,
    ControlMatch,
    ControlSelector,
    EvaluatorConfig,
    EvaluatorResult,
    JSONControlEvaluatorPluginConfig,
    ListConfig,
    RegexConfig,
    SQLControlEvaluatorPluginConfig,
)
from .errors import (
    ERROR_TITLES,
    ErrorCode,
    ErrorDetails,
    ErrorMetadata,
    ErrorReason,
    ProblemDetail,
    ValidationErrorItem,
    get_error_title,
    make_error_type,
)
from .evaluation import (
    EvaluationRequest,
    EvaluationResponse,
    EvaluationResult,
)
from .health import HealthResponse
from .plugin import (
    PluginEvaluator,
    PluginMetadata,
    clear_plugins,
    get_all_plugins,
    get_plugin,
    register_plugin,
)
from .policy import Policy
from .server import (
    AgentSummary,
    ControlSummary,
    DeleteControlResponse,
    EvaluatorSchema,
    GetPolicyControlsResponse,
    ListAgentsResponse,
    ListControlsResponse,
    PaginationInfo,
    PatchControlRequest,
    PatchControlResponse,
)

__all__ = [
    # Health
    "HealthResponse",
    # Agent
    "Agent",
    "AgentTool",
    "AgentContext",
    "LlmCall",
    "ToolCall",
    # Policy
    "Policy",
    # Evaluation
    "EvaluationRequest",
    "EvaluationResponse",
    "EvaluationResult",
    # Controls
    "ControlDefinition",
    "ControlAction",
    "ControlMatch",
    "ControlSelector",
    "EvaluatorConfig",
    "EvaluatorResult",
    # Plugin configs
    "JSONControlEvaluatorPluginConfig",
    "ListConfig",
    "RegexConfig",
    "SQLControlEvaluatorPluginConfig",
    # Plugin system
    "PluginEvaluator",
    "PluginMetadata",
    "register_plugin",
    "get_plugin",
    "get_all_plugins",
    "clear_plugins",
    # Error models (RFC 7807 / Kubernetes / GitHub-style)
    "ProblemDetail",
    "ErrorCode",
    "ErrorReason",
    "ErrorDetails",
    "ErrorMetadata",
    "ValidationErrorItem",
    "make_error_type",
    "get_error_title",
    "ERROR_TITLES",
    # Server models
    "AgentSummary",
    "ControlSummary",
    "DeleteControlResponse",
    "EvaluatorSchema",
    "GetPolicyControlsResponse",
    "ListAgentsResponse",
    "ListControlsResponse",
    "PaginationInfo",
    "PatchControlRequest",
    "PatchControlResponse",
]

