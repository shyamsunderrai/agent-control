
from agent_control_models.server import (
    AssocResponse,
    CreateControlSetRequest,
    CreateControlSetResponse,
    GetControlSetControlsResponse,
)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_async_db
from ..logging_utils import get_logger
from ..models import Control, ControlSet

router = APIRouter(prefix="/control-sets", tags=["control-sets"])

_logger = get_logger(__name__)


@router.put(
    "",
    response_model=CreateControlSetResponse,
    summary="Create a new control set",
    response_description="Created control set ID",
)
async def create_control_set(
    request: CreateControlSetRequest, db: AsyncSession = Depends(get_async_db)
) -> CreateControlSetResponse:
    """
    Create a new control set with a unique name.

    Control sets group multiple atomic controls together.
    Example: "Input Sanitization" control set might contain
    "SQL Injection" and "XSS" controls.

    Args:
        request: Control set creation request
        db: Database session (injected)

    Returns:
        CreateControlSetResponse with the new ID

    Raises:
        HTTPException 409: Control set with this name already exists
        HTTPException 500: Database error
    """
    existing = await db.execute(
        select(ControlSet.id).where(ControlSet.name == request.name)
    )
    if existing.first() is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Control set with name '{request.name}' already exists",
        )

    control_set = ControlSet(name=request.name)
    db.add(control_set)
    try:
        await db.commit()
        await db.refresh(control_set)
    except Exception:
        await db.rollback()
        _logger.error(
            f"Failed to create control set '{request.name}'",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create control set '{request.name}': database error",
        )
    return CreateControlSetResponse(control_set_id=control_set.id)


@router.post(
    "/{control_set_id}/controls/{control_id}",
    response_model=AssocResponse,
    summary="Add a control to a control set",
    response_description="Success confirmation",
)
async def add_control_to_control_set(
    control_set_id: int, control_id: int, db: AsyncSession = Depends(get_async_db)
) -> AssocResponse:
    """
    Associate an atomic control with a control set.

    This operation is idempotent.

    Args:
        control_set_id: ID of the control set
        control_id: ID of the control to add
        db: Database session

    Returns:
        AssocResponse(success=True)

    Raises:
        HTTPException 404: Control set or control not found
    """
    # 1. Fetch Control Set
    from sqlalchemy.orm import selectinload

    res_cs = await db.execute(
        select(ControlSet)
        .options(selectinload(ControlSet.controls))
        .where(ControlSet.id == control_set_id)
    )
    control_set = res_cs.scalars().first()
    if not control_set:
        raise HTTPException(
            status_code=404, detail=f"Control set '{control_set_id}' not found"
        )

    # 2. Fetch Control
    res_c = await db.execute(select(Control).where(Control.id == control_id))
    control = res_c.scalars().first()
    if not control:
        raise HTTPException(
            status_code=404, detail=f"Control '{control_id}' not found"
        )

    # 3. Associate (if not already present)
    # Note: SQLAlchemy collection handling usually manages uniqueness for sets,
    # but explicit check prevents overhead/errors depending on config.
    if control not in control_set.controls:
        control_set.controls.append(control)
        await db.commit()

    return AssocResponse(success=True)


@router.delete(
    "/{control_set_id}/controls/{control_id}",
    response_model=AssocResponse,
    summary="Remove a control from a control set",
    response_description="Success confirmation",
)
async def remove_control_from_control_set(
    control_set_id: int, control_id: int, db: AsyncSession = Depends(get_async_db)
) -> AssocResponse:
    """
    Remove an atomic control from a control set.

    Args:
        control_set_id: ID of the control set
        control_id: ID of the control to remove
        db: Database session

    Returns:
        AssocResponse(success=True)

    Raises:
        HTTPException 404: Control set or control not found
    """
    # 1. Fetch Control Set (with controls loaded)
    # We typically rely on lazy loading or explicit join.
    # AsyncORM requires awaiting the relationship access or select options.
    # Here we rely on the fact that we're in an async session context.
    # Ideally we should use .options(selectinload(ControlSet.controls))
    from sqlalchemy.orm import selectinload

    res_cs = await db.execute(
        select(ControlSet)
        .options(selectinload(ControlSet.controls))
        .where(ControlSet.id == control_set_id)
    )
    control_set = res_cs.scalars().first()
    if not control_set:
        raise HTTPException(
            status_code=404, detail=f"Control set '{control_set_id}' not found"
        )

    # 2. Find and remove
    target_control = next((c for c in control_set.controls if c.id == control_id), None)
    if target_control:
        control_set.controls.remove(target_control)
        await db.commit()

    return AssocResponse(success=True)


@router.get(
    "/{control_set_id}/controls",
    response_model=GetControlSetControlsResponse,
    summary="List controls in a control set",
    response_description="List of control IDs",
)
async def list_control_set_controls(
    control_set_id: int, db: AsyncSession = Depends(get_async_db)
) -> GetControlSetControlsResponse:
    """
    List all atomic controls associated with a control set.

    Args:
        control_set_id: ID of the control set
        db: Database session

    Returns:
        GetControlSetControlsResponse with list of control IDs

    Raises:
        HTTPException 404: Control set not found
    """
    from sqlalchemy.orm import selectinload

    res = await db.execute(
        select(ControlSet)
        .options(selectinload(ControlSet.controls))
        .where(ControlSet.id == control_set_id)
    )
    control_set = res.scalars().first()
    if not control_set:
        raise HTTPException(
            status_code=404, detail=f"Control set '{control_set_id}' not found"
        )

    return GetControlSetControlsResponse(
        control_ids=[c.id for c in control_set.controls]
    )
