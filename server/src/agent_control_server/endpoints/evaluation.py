"""Evaluation analysis endpoints."""
from typing import Any

from agent_control_engine.core import ControlEngine
from agent_control_models import ControlDefinition, EvaluationRequest, EvaluationResponse
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_async_db
from ..services.controls import list_controls_for_agent

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


class ControlAdapter:
    """Adapts API Control to Engine ControlWithIdentity protocol."""
    def __init__(self, id: int, name: str, control_data: dict[str, Any]):
        self.id = id
        self.name = name
        # Convert dict to Pydantic model
        self.control = ControlDefinition.model_validate(control_data)


@router.post(
    "",
    response_model=EvaluationResponse,
    summary="Analyze content safety",
    response_description="Safety analysis result",
)
async def evaluate(
    request: EvaluationRequest,
    db: AsyncSession = Depends(get_async_db)
) -> EvaluationResponse:
    """
    Analyze content for safety and control violations.
    """
    # 1. Fetch controls for the agent
    api_controls = await list_controls_for_agent(request.agent_uuid, db)

    # 2. Adapt controls for the engine
    engine_controls = []
    for c in api_controls:
        try:
            engine_controls.append(ControlAdapter(c.id, c.name, c.control))
        except Exception:
            # TODO: Log invalid control error
            continue

    # 3. Execute Control Engine
    engine = ControlEngine(engine_controls)
    response = engine.process(request)

    return response
