"""Core logic for the control engine."""
from collections.abc import Sequence
from typing import Protocol

from agent_control_models import (
    ControlDefinition,
    ControlMatch,
    EvaluationRequest,
    EvaluationResponse,
)

from .evaluators import get_evaluator
from .selectors import select_data


class ControlWithIdentity(Protocol):
    """Protocol for a control with identity information."""
    id: int
    name: str
    control: ControlDefinition


class ControlEngine:
    """Executes controls against requests."""

    def __init__(self, controls: Sequence[ControlWithIdentity]):
        self.controls = controls

    def get_applicable_controls(self, request: EvaluationRequest) -> list[ControlWithIdentity]:
        """
        Get all controls that apply to the current request without evaluating them.
        """
        applicable = []
        payload_is_tool = hasattr(request.payload, "tool_name")

        for item in self.controls:
            control_def = item.control

            if not control_def.enabled:
                continue

            if control_def.check_stage != request.check_stage:
                continue

            if control_def.applies_to == "tool_call" and not payload_is_tool:
                continue
            if control_def.applies_to == "llm_call" and payload_is_tool:
                continue

            applicable.append(item)

        return applicable

    def process(self, request: EvaluationRequest) -> EvaluationResponse:
        """
        Process a control check request against all applicable controls.
        """
        matches: list[ControlMatch] = []
        is_safe = True

        applicable_controls = self.get_applicable_controls(request)

        for item in applicable_controls:
            control_def = item.control

            # 2. Select Data
            data = select_data(request.payload, control_def.selector.path)

            # 3. Evaluate
            evaluator = get_evaluator(control_def.evaluator)
            result = evaluator.evaluate(data)

            # 4. Act on match
            if result.matched:
                matches.append(ControlMatch(
                    control_id=item.id,
                    control_name=item.name,
                    action=control_def.action.decision,
                    result=result
                ))

                if control_def.action.decision == "deny":
                    is_safe = False

        return EvaluationResponse(
            is_safe=is_safe,
            confidence=1.0, # Placeholder: simplistic aggregation
            matches=matches if matches else None
        )
