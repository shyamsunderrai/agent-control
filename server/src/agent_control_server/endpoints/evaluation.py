"""Evaluation analysis endpoints."""

from agent_control_engine.core import ControlEngine
from agent_control_models import ControlDefinition, EvaluationRequest, EvaluationResponse
from agent_control_models.errors import ErrorCode, ValidationErrorItem
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_async_db
from ..errors import APIValidationError
from ..logging_utils import get_logger
from ..services.controls import list_controls_for_agent

router = APIRouter(prefix="/evaluation", tags=["evaluation"])

_logger = get_logger(__name__)


class ControlAdapter:
    """Adapts API Control to Engine ControlWithIdentity protocol."""

    def __init__(self, id: int, name: str, control: ControlDefinition):
        self.id = id
        self.name = name
        self.control = control


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
    # Fetch controls for the agent (already validated as ControlDefinition)
    api_controls = await list_controls_for_agent(request.agent_uuid, db)

    # Adapt controls for the engine
    engine_controls = [ControlAdapter(c.id, c.name, c.control) for c in api_controls]

    # Execute Control Engine (parallel with cancel-on-deny)
    engine = ControlEngine(engine_controls)
    try:
        return await engine.process(request)
    except ValueError as e:
        _logger.error(f"Evaluation failed: {e}")
        raise APIValidationError(
            error_code=ErrorCode.EVALUATION_FAILED,
            detail="Evaluation failed due to invalid configuration or input",
            resource="Evaluation",
            hint="Check the evaluation request format and control configurations.",
            errors=[
                ValidationErrorItem(
                    resource="Evaluation",
                    field=None,
                    code="evaluation_error",
                    message=str(e),
                )
            ],
        )
