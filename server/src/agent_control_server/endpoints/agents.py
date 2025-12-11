from typing import Any
from uuid import UUID

from agent_control_models import list_plugins
from agent_control_models.agent import Agent as APIAgent
from agent_control_models.agent import AgentTool
from agent_control_models.server import (
    AgentControlsResponse,
    DeletePolicyResponse,
    EvaluatorSchema,
    GetAgentResponse,
    GetPolicyResponse,
    InitAgentRequest,
    InitAgentResponse,
    PatchAgentRequest,
    PatchAgentResponse,
    SetPolicyResponse,
)
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pydantic_core._pydantic_core import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_async_db
from ..logging_utils import get_logger
from ..models import Agent, AgentData, Policy
from ..schema_generator import generate_agent_schema, validate_agent_schema
from ..services.controls import list_controls_for_agent, list_controls_for_policy
from ..services.evaluator_utils import parse_evaluator_ref, validate_config_against_schema
from ..services.schema_compat import (
    check_schema_compatibility,
    format_compatibility_error,
)

router = APIRouter(prefix="/agents", tags=["agents"])

_logger = get_logger(__name__)

# Cache for built-in plugin names (populated on first use)
_BUILTIN_PLUGIN_NAMES: set[str] | None = None


def _get_builtin_plugin_names() -> set[str]:
    """Get built-in plugin names (cached)."""
    global _BUILTIN_PLUGIN_NAMES
    if _BUILTIN_PLUGIN_NAMES is None:
        _BUILTIN_PLUGIN_NAMES = set(list_plugins().keys())
    return _BUILTIN_PLUGIN_NAMES


async def _validate_policy_controls_for_agent(
    agent: Agent, policy_id: int, db: AsyncSession
) -> list[str]:
    """Validate all controls in a policy can run on this agent.

    Checks that agent-scoped evaluators referenced by controls:
    1. Exist on the agent (registered via initAgent)
    2. Have config that validates against the evaluator's schema

    Returns:
        List of error messages (empty if all valid)
    """
    errors: list[str] = []

    # Parse agent's registered evaluators
    try:
        agent_data = AgentData.model_validate(agent.data)
    except ValidationError:
        return [f"Agent '{agent.name}' has corrupted data"]

    agent_evaluators = {e.name: e for e in (agent_data.evaluators or [])}

    # Get all controls for this policy
    controls = await list_controls_for_policy(policy_id, db)

    for control in controls:
        if not control.data:
            continue

        evaluator_cfg = control.data.get("evaluator", {})
        plugin = evaluator_cfg.get("plugin", "")
        if not plugin:
            continue

        agent_name, eval_name = parse_evaluator_ref(plugin)
        if agent_name is None:
            continue  # Built-in plugin, already validated at control creation

        # Agent-scoped evaluator - check if target matches this agent
        if agent_name != agent.name:
            errors.append(
                f"Control '{control.name}' references evaluator '{plugin}' "
                f"which belongs to agent '{agent_name}', not '{agent.name}'"
            )
            continue

        # Check if evaluator exists on this agent
        if eval_name not in agent_evaluators:
            errors.append(
                f"Control '{control.name}' references evaluator '{eval_name}' "
                f"which is not registered with agent '{agent.name}'. "
                f"Register it via initAgent or use a different evaluator."
            )
            continue

        # Validate config against schema
        registered_ev = agent_evaluators[eval_name]
        config = evaluator_cfg.get("config", {})
        if registered_ev.config_schema:
            try:
                validate_config_against_schema(config, registered_ev.config_schema)
            except Exception as e:
                errors.append(
                    f"Control '{control.name}' has invalid config for evaluator '{eval_name}': {e}"
                )

    return errors


@router.post(
    "/initAgent",
    response_model=InitAgentResponse,
    summary="Initialize or update an agent",
    response_description="Agent registration status with active controls",
)
async def init_agent(
    request: InitAgentRequest, db: AsyncSession = Depends(get_async_db)
) -> InitAgentResponse:
    """
    Register a new agent or update an existing agent's tools and metadata.

    This endpoint is idempotent:
    - If the agent name doesn't exist, creates a new agent
    - If the agent name exists with the same UUID, updates tool schemas
    - If the agent name exists with a different UUID, returns 409 Conflict

    Tool versioning: When tool schemas change (arguments or output_schema),
    a new version is created automatically.

    Args:
        request: Agent metadata and tool schemas
        db: Database session (injected)

    Returns:
        InitAgentResponse with created flag and active controls (if policy assigned)

    Raises:
        HTTPException 409: Agent name exists with different UUID
        HTTPException 500: Database error during creation/update
    """
    # Check for evaluator name collisions with built-in plugins
    builtin_names = _get_builtin_plugin_names()
    for ev in request.evaluators:
        if ev.name in builtin_names:
            raise HTTPException(
                status_code=400,
                detail=f"Evaluator name '{ev.name}' conflicts with built-in plugin. "
                f"Choose a different name.",
            )

    # Look up by name only; name is unique
    result = await db.execute(select(Agent).where(Agent.name == request.agent.agent_name))
    existing: Agent | None = result.scalars().first()

    created = False

    if existing is None:
        created = True

        # Generate agent schema from tools
        tools_dict = [tool.model_dump(mode="json") for tool in request.tools]
        agent_schema = generate_agent_schema(tools_dict)

        # Validate generated schema
        is_valid, errors = validate_agent_schema(agent_schema)
        if not is_valid:
            _logger.warning(
                f"Generated schema validation failed for agent "
                f"'{request.agent.agent_name}': {errors}"
            )

        data_model = AgentData(
            agent_metadata=request.agent.model_dump(mode="json"),
            tools=list(request.tools),
            evaluators=list(request.evaluators),
            agent_schema=agent_schema,
        )

        new_agent = Agent(
            name=request.agent.agent_name,
            agent_uuid=request.agent.agent_id,
            data=data_model.model_dump(mode="json"),
        )
        db.add(new_agent)
        try:
            await db.commit()
            _logger.info(
                f"Created agent '{request.agent.agent_name}' with {len(request.tools)} tools, "
                f"{len(request.evaluators)} evaluators"
            )
        except Exception:
            await db.rollback()
            _logger.error(
                f"Failed to create agent '{request.agent.agent_name}' ({request.agent.agent_id})",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create agent '{request.agent.agent_name}': database error",
            )
        return InitAgentResponse(created=created, controls=[])

    requested_uuid = request.agent.agent_id
    if existing.agent_uuid != requested_uuid:
        # UUID mismatch for the same name: return error
        raise HTTPException(
            status_code=409,
            detail=f"Agent name '{request.agent.agent_name}' already exists with different UUID",
        )

    # Parse existing data via AgentData Pydantic model
    try:
        data_model = AgentData.model_validate(existing.data)
    except ValidationError as e:
        if not request.force_replace:
            _logger.error(
                f"Failed to parse existing agent data for '{request.agent.agent_name}'",
                exc_info=True,
            )
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Agent '{request.agent.agent_name}' has corrupted data and cannot be updated. "
                    f"Validation error: {str(e)}. "
                    f"To replace with new data, set force_replace=true in the request."
                ),
            )
        # User explicitly requested replacement
        _logger.warning(
            f"Force-replacing corrupted data for agent '{request.agent.agent_name}' "
            f"due to force_replace=true. Original error: {e}"
        )
        data_model = AgentData(agent_metadata={}, tools=[], evaluators=[])

    tools_changed = False
    evaluators_changed = False
    force_write = request.force_replace  # Always persist when force_replace=true

    # --- Update agent metadata ---
    new_metadata = request.agent.model_dump(mode="json")
    metadata_changed = data_model.agent_metadata != new_metadata
    if metadata_changed:
        data_model.agent_metadata = new_metadata

    # --- Process tools ---
    incoming_tools_by_name: dict[str, AgentTool] = {t.tool_name: t for t in request.tools}
    new_tools: list[AgentTool] = []
    seen_tools: set[str] = set()

    for tool in data_model.tools or []:
        name = tool.tool_name
        if name in incoming_tools_by_name:
            if name not in seen_tools:
                incoming_tool = incoming_tools_by_name[name]
                if tool.model_dump(mode="json") != incoming_tool.model_dump(mode="json"):
                    tools_changed = True
                new_tools.append(incoming_tool)
                seen_tools.add(name)
        else:
            new_tools.append(tool)

    for name, t in incoming_tools_by_name.items():
        if name not in seen_tools:
            new_tools.append(t)
            tools_changed = True

    data_model.tools = new_tools

    # --- Process evaluators with schema compatibility check ---
    incoming_evals_by_name: dict[str, EvaluatorSchema] = {
        e.name: e for e in request.evaluators
    }
    existing_evals_by_name: dict[str, EvaluatorSchema] = {
        ev.name: ev for ev in (data_model.evaluators or [])
    }
    new_evaluators: list[EvaluatorSchema] = []

    # Check existing evaluators for compatibility
    for name, existing_ev in existing_evals_by_name.items():
        if name in incoming_evals_by_name:
            incoming_ev = incoming_evals_by_name[name]
            old_schema = existing_ev.config_schema
            new_schema = incoming_ev.config_schema

            # Check compatibility
            is_compatible, compat_errors = check_schema_compatibility(old_schema, new_schema)
            if not is_compatible:
                raise HTTPException(
                    status_code=409,
                    detail=format_compatibility_error(name, compat_errors),
                )

            # Schema is compatible - update if changed
            if existing_ev.model_dump(mode="json") != incoming_ev.model_dump(mode="json"):
                evaluators_changed = True
            new_evaluators.append(incoming_ev)
        else:
            # Keep existing evaluator not in incoming request
            new_evaluators.append(existing_ev)

    # Add new evaluators
    for name, ev in incoming_evals_by_name.items():
        if name not in existing_evals_by_name:
            new_evaluators.append(ev)
            evaluators_changed = True

    data_model.evaluators = new_evaluators

    if tools_changed or evaluators_changed or metadata_changed or force_write:
        # Regenerate schema when tools change
        if tools_changed:
            tools_dict = [tool.model_dump(mode="json") for tool in new_tools]
            agent_schema = generate_agent_schema(tools_dict)

            # Validate generated schema
            is_valid, errors = validate_agent_schema(agent_schema)
            if not is_valid:
                _logger.warning(
                    f"Generated schema validation failed for agent "
                    f"'{request.agent.agent_name}': {errors}"
                )
            data_model.agent_schema = agent_schema

        existing.data = data_model.model_dump(mode="json")

        try:
            await db.commit()
            _logger.info(
                f"Updated agent '{request.agent.agent_name}' with {len(new_tools)} tools, "
                f"{len(new_evaluators)} evaluators"
            )
        except Exception:
            await db.rollback()
            _logger.error(
                f"Failed to update agent '{request.agent.agent_name}' ({request.agent.agent_id})",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update agent '{request.agent.agent_name}': database error",
            )

    # If the existing agent has a policy, include its controls; otherwise empty list
    controls = []
    if existing.policy_id is not None:
        controls = await list_controls_for_agent(existing.agent_uuid, db)

    return InitAgentResponse(created=created, controls=controls)


@router.get(
    "/{agent_id}",
    response_model=GetAgentResponse,
    summary="Get agent details",
    response_description="Agent metadata and registered tools",
)
async def get_agent(agent_id: UUID, db: AsyncSession = Depends(get_async_db)) -> GetAgentResponse:
    """
    Retrieve agent metadata and all registered tools.

    Returns the latest version of each tool (tools are deduplicated by name).

    Args:
        agent_id: UUID of the agent
        db: Database session (injected)

    Returns:
        GetAgentResponse with agent metadata and tool list

    Raises:
        HTTPException 404: Agent not found
        HTTPException 422: Agent data is corrupted
    """
    result = await db.execute(select(Agent).where(Agent.agent_uuid == agent_id))
    existing: Agent | None = result.scalars().first()
    if existing is None:
        raise HTTPException(
            status_code=404, detail=f"Agent with ID '{agent_id}' not found"
        )

    try:
        data_model = AgentData.model_validate(existing.data)
    except ValidationError:
        _logger.error(
            f"Failed to parse agent data for agent '{existing.name}' ({agent_id})",
            exc_info=True,
        )
        raise HTTPException(
            status_code=422,
            detail=f"Agent data is corrupted for agent '{existing.name}'",
        )

    try:
        tools_by_name: dict[str, AgentTool] = {}
        for tool in data_model.tools or []:
            tools_by_name[tool.tool_name] = tool
        latest_tools: list[AgentTool] = list(tools_by_name.values())
        agent_meta = APIAgent.model_validate(data_model.agent_metadata)
    except ValidationError:
        _logger.error(
            f"Failed to parse agent metadata for agent '{existing.name}' ({agent_id})",
            exc_info=True,
        )
        raise HTTPException(
            status_code=422,
            detail=f"Agent metadata is corrupted for agent '{existing.name}'",
        )

    return GetAgentResponse(agent=agent_meta, tools=latest_tools)


@router.post(
    "/{agent_id}/policy/{policy_id}",
    response_model=SetPolicyResponse,
    summary="Assign policy to agent",
    response_description="Success status with previous policy ID",
)
async def set_agent_policy(
    agent_id: UUID, policy_id: int, db: AsyncSession = Depends(get_async_db)
) -> SetPolicyResponse:
    """
    Assign a policy to an agent, replacing any existing policy assignment.

    The agent will immediately inherit all controls from control sets in the assigned policy.

    Args:
        agent_id: UUID of the agent
        policy_id: ID of the policy to assign
        db: Database session (injected)

    Returns:
        SetPolicyResponse with success flag and previous policy ID (if any)

    Raises:
        HTTPException 404: Agent or policy not found
        HTTPException 500: Database error during assignment
    """
    # Find agent
    result = await db.execute(select(Agent).where(Agent.agent_uuid == agent_id))
    agent: Agent | None = result.scalars().first()
    if agent is None:
        raise HTTPException(
            status_code=404, detail=f"Agent with ID '{agent_id}' not found"
        )

    # Find policy by id
    policy_result = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy: Policy | None = policy_result.scalars().first()
    if policy is None:
        raise HTTPException(
            status_code=404, detail=f"Policy with ID '{policy_id}' not found"
        )

    # Validate controls can run on this agent
    errors = await _validate_policy_controls_for_agent(agent, policy_id, db)
    if errors:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Policy contains controls incompatible with this agent",
                "errors": errors,
            },
        )

    # Store old policy ID if exists
    old_policy_id: int | None = None
    if agent.policy_id is not None:
        old_policy_id = agent.policy_id

    # Assign new policy
    agent.policy_id = policy.id
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        _logger.error(
            f"Failed to assign policy '{policy_id}' to agent '{agent.name}' ({agent_id})",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to assign policy to agent '{agent.name}': database error",
        )

    return SetPolicyResponse(success=True, old_policy_id=old_policy_id)


@router.get(
    "/{agent_id}/policy",
    response_model=GetPolicyResponse,
    summary="Get agent's assigned policy",
    response_description="Policy ID",
)
async def get_agent_policy(
    agent_id: UUID, db: AsyncSession = Depends(get_async_db)
) -> GetPolicyResponse:
    """
    Retrieve the policy currently assigned to an agent.

    Args:
        agent_id: UUID of the agent
        db: Database session (injected)

    Returns:
        GetPolicyResponse with policy ID

    Raises:
        HTTPException 404: Agent not found or agent has no policy assigned
    """
    # Find agent
    result = await db.execute(select(Agent).where(Agent.agent_uuid == agent_id))
    agent: Agent | None = result.scalars().first()
    if agent is None:
        raise HTTPException(
            status_code=404, detail=f"Agent with ID '{agent_id}' not found"
        )

    # Check if agent has a policy
    if agent.policy_id is None:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent.name}' has no policy assigned",
        )

    # Find policy
    policy_result = await db.execute(select(Policy).where(Policy.id == agent.policy_id))
    policy: Policy | None = policy_result.scalars().first()
    if policy is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Policy with ID '{agent.policy_id}' not found "
                f"(referenced by agent '{agent.name}')"
            ),
        )

    return GetPolicyResponse(policy_id=policy.id)


@router.delete(
    "/{agent_id}/policy",
    response_model=DeletePolicyResponse,
    summary="Remove agent's policy assignment",
    response_description="Success confirmation",
)
async def delete_agent_policy(
    agent_id: UUID, db: AsyncSession = Depends(get_async_db)
) -> DeletePolicyResponse:
    """
    Remove the policy assignment from an agent.

    The agent will no longer have any protection controls active.

    Args:
        agent_id: UUID of the agent
        db: Database session (injected)

    Returns:
        DeletePolicyResponse with success flag

    Raises:
        HTTPException 404: Agent not found or agent has no policy assigned
        HTTPException 500: Database error during removal
    """
    # Find agent
    result = await db.execute(select(Agent).where(Agent.agent_uuid == agent_id))
    agent: Agent | None = result.scalars().first()
    if agent is None:
        raise HTTPException(
            status_code=404, detail=f"Agent with ID '{agent_id}' not found"
        )

    # Check if agent has a policy
    if agent.policy_id is None:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent.name}' has no policy assigned",
        )

    # Remove policy assignment
    agent.policy_id = None
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        _logger.error(
            f"Failed to remove policy from agent '{agent.name}' ({agent_id})",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove policy from agent '{agent.name}': database error",
        )

    return DeletePolicyResponse(success=True)


@router.get(
    "/{agent_id}/controls",
    response_model=AgentControlsResponse,
    summary="List agent's active controls",
    response_description="List of controls from agent's policy",
)
async def list_agent_controls(
    agent_id: UUID, db: AsyncSession = Depends(get_async_db)
) -> AgentControlsResponse:
    """
    List all protection controls active for an agent.

    Controls are inherited from all control sets in the agent's assigned policy.
    Returns an empty list if the agent has no policy.

    Args:
        agent_id: UUID of the agent
        db: Database session (injected)

    Returns:
        AgentControlsResponse with list of controls (empty if no policy)

    Raises:
        HTTPException 404: Agent not found
    """
    result = await db.execute(select(Agent).where(Agent.agent_uuid == agent_id))
    agent: Agent | None = result.scalars().first()
    if agent is None:
        raise HTTPException(
            status_code=404, detail=f"Agent with ID '{agent_id}' not found"
        )

    if agent.policy_id is None:
        return AgentControlsResponse(controls=[])

    controls = await list_controls_for_agent(agent_id, db)
    return AgentControlsResponse(controls=controls)


@router.get(
    "/{agent_id}/schema",
    summary="Get agent's auto-generated schema",
    response_description="Schema generated from registered tools",
)
async def get_agent_schema(
    agent_id: UUID, db: AsyncSession = Depends(get_async_db)
) -> dict[str, Any]:
    """
    Retrieve the auto-generated schema for an agent.

    The schema is automatically generated from the agent's registered tools
    and includes:
    - Tool definitions with input/output schemas
    - Extracted capabilities
    - Validation rules

    Args:
        agent_id: UUID of the agent
        db: Database session (injected)

    Returns:
        Auto-generated agent schema

    Raises:
        HTTPException 404: Agent not found or no schema available
    """
    result = await db.execute(select(Agent).where(Agent.agent_uuid == agent_id))
    agent: Agent | None = result.scalars().first()
    if agent is None:
        raise HTTPException(
            status_code=404, detail=f"Agent with ID '{agent_id}' not found"
        )

    # Extract schema from agent data
    schema = agent.data.get("agent_schema")
    if schema is None:
        # Check if agent has tools - if so, we can generate schema on-demand
        try:
            data_model = AgentData.model_validate(agent.data)
            if data_model.tools:
                # Generate schema from existing tools for backward compatibility
                _logger.info(f"Generating schema for legacy agent '{agent.name}'")
                tools_dict = [tool.model_dump(mode="json") for tool in data_model.tools]
                schema = generate_agent_schema(tools_dict)

                # Optionally persist it for next time
                data_model.agent_schema = schema
                agent.data = data_model.model_dump(mode="json")
                await db.commit()
                _logger.info(f"Persisted auto-generated schema for agent '{agent.name}'")

                return schema
        except ValidationError:
            _logger.error(f"Failed to parse agent data for '{agent.name}'", exc_info=True)

        raise HTTPException(
            status_code=404,
            detail=f"No schema available for agent '{agent.name}'. "
                   f"Schema is auto-generated when agents are registered with tools."
        )

    # Cast to satisfy mypy since we know schema is dict[str, Any] at this point
    return dict(schema)


# =============================================================================
# Evaluator Schema Endpoints
# =============================================================================


class EvaluatorSchemaItem(BaseModel):
    """Evaluator schema summary for list response."""

    name: str
    description: str | None
    config_schema: dict[str, Any]


class PaginationInfo(BaseModel):
    """Pagination metadata."""

    offset: int
    limit: int
    total: int


class ListEvaluatorsResponse(BaseModel):
    """Response for listing agent's evaluator schemas."""

    evaluators: list[EvaluatorSchemaItem]
    pagination: PaginationInfo


@router.get(
    "/{agent_id}/evaluators",
    response_model=ListEvaluatorsResponse,
    summary="List agent's registered evaluator schemas",
    response_description="Evaluator schemas registered with this agent",
)
async def list_agent_evaluators(
    agent_id: UUID,
    offset: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_async_db),
) -> ListEvaluatorsResponse:
    """
    List all evaluator schemas registered with an agent.

    Evaluator schemas are registered via initAgent and used for:
    - Config validation when creating Controls
    - UI to display available config options

    Args:
        agent_id: UUID of the agent
        offset: Pagination offset (default 0)
        limit: Pagination limit (default 20, max 100)
        db: Database session (injected)

    Returns:
        ListEvaluatorsResponse with evaluator schemas and pagination

    Raises:
        HTTPException 404: Agent not found
    """
    # Clamp limit
    limit = min(max(1, limit), 100)

    result = await db.execute(select(Agent).where(Agent.agent_uuid == agent_id))
    agent: Agent | None = result.scalars().first()
    if agent is None:
        raise HTTPException(
            status_code=404, detail=f"Agent with ID '{agent_id}' not found"
        )

    try:
        data_model = AgentData.model_validate(agent.data)
    except ValidationError:
        data_model = AgentData(agent_metadata={}, tools=[], evaluators=[])

    all_evaluators = data_model.evaluators or []
    total = len(all_evaluators)

    # Apply pagination
    paginated = all_evaluators[offset : offset + limit]

    return ListEvaluatorsResponse(
        evaluators=[
            EvaluatorSchemaItem(
                name=ev.name,
                description=ev.description,
                config_schema=ev.config_schema,
            )
            for ev in paginated
        ],
        pagination=PaginationInfo(offset=offset, limit=limit, total=total),
    )


@router.get(
    "/{agent_id}/evaluators/{evaluator_name}",
    response_model=EvaluatorSchemaItem,
    summary="Get specific evaluator schema",
    response_description="Evaluator schema details",
)
async def get_agent_evaluator(
    agent_id: UUID,
    evaluator_name: str,
    db: AsyncSession = Depends(get_async_db),
) -> EvaluatorSchemaItem:
    """
    Get a specific evaluator schema registered with an agent.

    Args:
        agent_id: UUID of the agent
        evaluator_name: Name of the evaluator
        db: Database session (injected)

    Returns:
        EvaluatorSchemaItem with schema details

    Raises:
        HTTPException 404: Agent or evaluator not found
    """
    result = await db.execute(select(Agent).where(Agent.agent_uuid == agent_id))
    agent: Agent | None = result.scalars().first()
    if agent is None:
        raise HTTPException(
            status_code=404, detail=f"Agent with ID '{agent_id}' not found"
        )

    try:
        data_model = AgentData.model_validate(agent.data)
    except ValidationError:
        raise HTTPException(
            status_code=404, detail=f"Evaluator '{evaluator_name}' not found"
        )

    for ev in data_model.evaluators or []:
        if ev.name == evaluator_name:
            return EvaluatorSchemaItem(
                name=ev.name,
                description=ev.description,
                config_schema=ev.config_schema,
            )

    raise HTTPException(
        status_code=404, detail=f"Evaluator '{evaluator_name}' not found"
    )


@router.patch(
    "/{agent_id}",
    response_model=PatchAgentResponse,
    summary="Modify agent (remove tools/evaluators)",
    response_description="Lists of removed items",
)
async def patch_agent(
    agent_id: UUID,
    request: PatchAgentRequest,
    db: AsyncSession = Depends(get_async_db),
) -> PatchAgentResponse:
    """
    Remove tools and/or evaluators from an agent.

    This is the complement to initAgent which only adds items.
    Removals are idempotent - attempting to remove non-existent items is not an error.

    Args:
        agent_id: UUID of the agent
        request: Lists of tool/evaluator names to remove
        db: Database session (injected)

    Returns:
        PatchAgentResponse with lists of actually removed items

    Raises:
        HTTPException 404: Agent not found
        HTTPException 500: Database error during update
    """
    result = await db.execute(select(Agent).where(Agent.agent_uuid == agent_id))
    agent: Agent | None = result.scalars().first()
    if agent is None:
        raise HTTPException(
            status_code=404, detail=f"Agent with ID '{agent_id}' not found"
        )

    try:
        data_model = AgentData.model_validate(agent.data)
    except ValidationError:
        raise HTTPException(
            status_code=422,
            detail=f"Agent '{agent.name}' has corrupted data",
        )

    tools_removed: list[str] = []
    evaluators_removed: list[str] = []

    # Remove tools
    if request.remove_tools:
        remove_set = set(request.remove_tools)
        new_tools = []
        for tool in data_model.tools or []:
            if tool.tool_name in remove_set:
                tools_removed.append(tool.tool_name)
            else:
                new_tools.append(tool)
        data_model.tools = new_tools

    # Remove evaluators (with dependency check)
    if request.remove_evaluators:
        remove_set = set(request.remove_evaluators)

        # Check if any controls reference evaluators being removed
        if agent.policy_id is not None:
            # Get all controls for this agent's policy
            controls = await list_controls_for_agent(agent.agent_uuid, db)
            referencing_controls: list[tuple[str, str]] = []  # (control_name, evaluator)

            for ctrl in controls:
                ctrl_data = ctrl.control or {}
                evaluator_ref = ctrl_data.get("evaluator", {}).get("plugin", "")
                if ":" in evaluator_ref:
                    ref_agent, ref_eval = evaluator_ref.split(":", 1)
                    # Check if this control references an evaluator we're removing
                    # AND it's scoped to this agent (by name match)
                    if ref_agent == agent.name and ref_eval in remove_set:
                        referencing_controls.append((ctrl.name, ref_eval))

            if referencing_controls:
                refs_str = ", ".join(
                    f"'{ctrl}' uses '{ev}'" for ctrl, ev in referencing_controls
                )
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Cannot remove evaluators: active controls reference them. "
                        f"Remove or update these controls first: {refs_str}"
                    ),
                )

        new_evaluators = []
        for ev in data_model.evaluators or []:
            if ev.name in remove_set:
                evaluators_removed.append(ev.name)
            else:
                new_evaluators.append(ev)
        data_model.evaluators = new_evaluators

    # Only update if something changed
    if tools_removed or evaluators_removed:
        # Regenerate agent_schema if tools were removed
        if tools_removed:
            tools_dict = [tool.model_dump(mode="json") for tool in data_model.tools]
            agent_schema = generate_agent_schema(tools_dict)

            is_valid, errors = validate_agent_schema(agent_schema)
            if not is_valid:
                _logger.warning(
                    f"Generated schema validation failed after PATCH for agent "
                    f"'{agent.name}': {errors}"
                )

            data_model.agent_schema = agent_schema

        agent.data = data_model.model_dump(mode="json")
        try:
            await db.commit()
            _logger.info(
                f"Patched agent '{agent.name}': removed {len(tools_removed)} tools, "
                f"{len(evaluators_removed)} evaluators"
            )
        except Exception:
            await db.rollback()
            _logger.error(
                f"Failed to patch agent '{agent.name}' ({agent_id})",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update agent '{agent.name}': database error",
            )

    return PatchAgentResponse(
        tools_removed=tools_removed,
        evaluators_removed=evaluators_removed,
    )
