"""Control definition models for agent protection."""
from typing import Any, Literal

import re2
from pydantic import Field, field_validator

from .base import BaseModel


class ControlSelector(BaseModel):
    """Selects data from payload using a path."""

    path: str = Field(
        ...,
        description=(
            "Path to data using dot notation. "
            "Examples: 'input', 'output', 'arguments.query', 'context.user_id', 'tool_name', '*'"
        ),
    )

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate path and warn about common typos."""
        if not v:
            raise ValueError("Path cannot be empty")

        # Valid root fields
        valid_roots = {"input", "output", "arguments", "tool_name", "context", "*"}
        root = v.split(".")[0]

        if root not in valid_roots:
            raise ValueError(
                f"Invalid path root '{root}'. "
                f"Must be one of: {', '.join(sorted(valid_roots))}"
            )

        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"path": "output"},
                {"path": "arguments.query"},
                {"path": "context.user_id"},
                {"path": "input"},
                {"path": "*"},
            ]
        }
    }


class RegexConfig(BaseModel):
    """Configuration for regex evaluator."""
    pattern: str = Field(..., description="Regular expression pattern")
    flags: list[str] | None = Field(default=None, description="Regex flags")

    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, v: str) -> str:
        """Validate that the pattern is a valid regex."""
        try:
            re2.compile(v)
        except re2.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")
        return v


class ListConfig(BaseModel):
    """Configuration for list evaluator."""
    values: list[str | int | float] = Field(
        ..., description="List of values to match against"
    )
    logic: Literal["any", "all"] = Field(
        "any", description="Matching logic: any item matches vs all items match"
    )
    match_on: Literal["match", "no_match"] = Field(
        "match", description="Trigger rule on match or no match"
    )
    case_sensitive: bool = Field(False, description="Whether matching is case sensitive")


class RegexControlEvaluator(BaseModel):
    """Evaluator using Regular Expressions."""
    type: Literal["regex"] = "regex"
    config: RegexConfig


class ListControlEvaluator(BaseModel):
    """Evaluator checking against a list of values."""
    type: Literal["list"] = "list"
    config: ListConfig


class CustomControlEvaluator(BaseModel):
    """Custom evaluator configuration."""
    type: Literal["custom"] = "custom"
    config: dict[str, Any]


ControlEvaluator = RegexControlEvaluator | ListControlEvaluator | CustomControlEvaluator


class ControlAction(BaseModel):
    """What to do when control matches."""

    decision: Literal["allow", "deny", "warn", "log"] = Field(
        ..., description="Action to take when control is triggered"
    )


class ControlDefinition(BaseModel):
    """A control definition to evaluate agent interactions.

    This model contains only the logic and configuration.
    Identity fields (id, name) are managed by the database.
    """

    description: str | None = Field(None, description="Detailed description of the control")
    enabled: bool = Field(True, description="Whether this control is active")

    # When to apply
    applies_to: Literal["llm_call", "tool_call"] = Field(
        ..., description="Which type of interaction this control applies to"
    )
    check_stage: Literal["pre", "post"] = Field(
        ..., description="When to execute this control"
    )

    # What to check
    selector: ControlSelector = Field(..., description="What data to select from the payload")

    # How to check
    evaluator: ControlEvaluator = Field(..., description="How to evaluate the selected data")

    # What to do
    action: ControlAction = Field(..., description="What action to take when control matches")

    # Metadata
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "description": "Block outputs containing US Social Security Numbers",
                    "enabled": True,
                    "applies_to": "llm_call",
                    "check_stage": "post",
                    "selector": {"path": "output"},
                    "evaluator": {
                        "type": "regex",
                        "config": {
                            "pattern": r"\b\d{3}-\d{2}-\d{4}\b",
                            "flags": ["IGNORECASE"],
                        },
                    },
                    "action": {
                        "decision": "deny",
                    },
                    "tags": ["pii", "compliance"],
                }
            ]
        }
    }


class EvaluatorResult(BaseModel):
    """Result from a control evaluator."""

    matched: bool = Field(..., description="Whether the pattern matched")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in the evaluation"
    )
    message: str | None = Field(default=None, description="Explanation of the result")
    metadata: dict[str, Any] | None = Field(default=None, description="Additional result metadata")


class ControlMatch(BaseModel):
    """Represents a control match (could be allow, deny, warn, or log)."""

    control_id: int = Field(..., description="Database ID of the control that matched")
    control_name: str = Field(..., description="Name of the control that matched")
    action: Literal["allow", "deny", "warn", "log"] = Field(
        ..., description="Action to take for this match"
    )
    result: EvaluatorResult = Field(
        ..., description="Evaluator result (confidence, message, metadata)"
    )


