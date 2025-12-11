"""Evaluation analysis endpoints."""

from typing import Any

from agent_control_engine.core import ControlEngine
from agent_control_models import ControlDefinition, EvaluationRequest, EvaluationResponse
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_async_db
from ..logging_utils import get_logger
from ..services.controls import list_controls_for_agent

router = APIRouter(prefix="/evaluation", tags=["evaluation"])

_logger = get_logger(__name__)


class ControlAdapter:
    """Adapts API Control to Engine ControlWithIdentity protocol."""

    def __init__(self, id: int, name: str, control_data: dict[str, Any]):
        self.id = id
        self.name = name
        self.control = ControlDefinition.model_validate(control_data)


@router.post(
    "",
    response_model=EvaluationResponse,
    summary="Analyze content safety",
    response_description="Safety analysis result",
)
async def evaluate(
    request: EvaluationRequest,
    db: AsyncSession = Depends(get_async_db),
) -> EvaluationResponse:
    """Analyze content for safety and control violations.

    Runs all controls assigned to the agent via policy through the
    evaluation engine. Controls are evaluated in parallel with
    cancel-on-deny for efficiency.

    Custom evaluators must be deployed as PluginEvaluator classes
    with the engine. Their schemas are registered via initAgent.
    """
    # Fetch controls for the agent
    api_controls = await list_controls_for_agent(request.agent_uuid, db)

    # Adapt controls for the engine
    engine_controls = []
    for c in api_controls:
        try:
            engine_controls.append(ControlAdapter(c.id, c.name, c.control))
        except Exception as e:
            _logger.warning(f"Failed to adapt control '{c.name}': {e}")
            continue

    # Execute Control Engine (parallel with cancel-on-deny)
    engine = ControlEngine(engine_controls)
    try:
        return await engine.process(request)
    except ValueError as e:
        _logger.error(f"Evaluation failed: {e}")
        raise HTTPException(status_code=422, detail=str(e))
