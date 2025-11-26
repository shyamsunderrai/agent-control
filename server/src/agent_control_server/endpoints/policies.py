
from agent_control_models.server import (
    AssocResponse,
    CreatePolicyRequest,
    CreatePolicyResponse,
    GetPolicyControlSetsResponse,
)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_async_db
from ..logging_utils import get_logger
from ..models import ControlSet, Policy, policy_control_sets

router = APIRouter(prefix="/policies", tags=["policies"])

_logger = get_logger(__name__)


@router.put(
    "",
    response_model=CreatePolicyResponse,
    summary="Create a new policy",
    response_description="Created policy ID",
)
async def create_policy(
    request: CreatePolicyRequest, db: AsyncSession = Depends(get_async_db)
) -> CreatePolicyResponse:
    """
    Create a new empty policy with a unique name.

    Policies group control sets together and can be assigned to agents.
    A newly created policy has no control sets until they are explicitly added.

    Args:
        request: Policy creation request with unique name
        db: Database session (injected)

    Returns:
        CreatePolicyResponse with the new policy's ID

    Raises:
        HTTPException 409: Policy with this name already exists
        HTTPException 500: Database error during creation
    """
    # Uniqueness check
    existing = await db.execute(select(Policy.id).where(Policy.name == request.name))
    if existing.first() is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Policy with name '{request.name}' already exists",
        )

    policy = Policy(name=request.name)
    db.add(policy)
    try:
        await db.commit()
        await db.refresh(policy)
    except Exception:
        await db.rollback()
        _logger.error(
            f"Failed to create policy '{request.name}'",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create policy '{request.name}': database error",
        )
    return CreatePolicyResponse(policy_id=policy.id)


@router.post(
    "/{policy_id}/control_sets/{control_set_id}",
    response_model=AssocResponse,
    summary="Add control set to policy",
    response_description="Success confirmation",
)
async def add_control_set_to_policy(
    policy_id: int, control_set_id: int, db: AsyncSession = Depends(get_async_db)
) -> AssocResponse:
    """
    Associate a control set with a policy.

    This operation is idempotent - adding the same control set multiple times has no effect.
    Agents with this policy will immediately see controls from the added control set.

    Args:
        policy_id: ID of the policy
        control_set_id: ID of the control set to add
        db: Database session (injected)

    Returns:
        AssocResponse with success flag

    Raises:
        HTTPException 404: Policy or control set not found
        HTTPException 500: Database error
    """
    # Find policy and control set
    pol_res = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy = pol_res.scalars().first()
    if policy is None:
        raise HTTPException(
            status_code=404, detail=f"Policy with ID '{policy_id}' not found"
        )

    ctl_res = await db.execute(select(ControlSet).where(ControlSet.id == control_set_id))
    control_set = ctl_res.scalars().first()
    if control_set is None:
        raise HTTPException(
            status_code=404, detail=f"Control set with ID '{control_set_id}' not found"
        )

    # Add association using INSERT ... ON CONFLICT DO NOTHING for idempotency
    # This is more efficient than check-then-insert
    try:
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = (
            pg_insert(policy_control_sets)
            .values(policy_id=policy_id, control_set_id=control_set_id)
            .on_conflict_do_nothing()
        )
        await db.execute(stmt)
        await db.commit()
    except Exception as e:
        await db.rollback()
        _logger.error(
            (
                f"Failed to add control set '{control_set.name}' ({control_set_id}) "
                f"to policy '{policy.name}' ({policy_id}): {e}"
            ),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to add control set '{control_set.name}' to policy '{policy.name}': "
                f"database error {str(e)}"
            ),
        )

    return AssocResponse(success=True)


@router.delete(
    "/{policy_id}/control_sets/{control_set_id}",
    response_model=AssocResponse,
    summary="Remove control set from policy",
    response_description="Success confirmation",
)
async def remove_control_set_from_policy(
    policy_id: int, control_set_id: int, db: AsyncSession = Depends(get_async_db)
) -> AssocResponse:
    """
    Remove a control set from a policy.

    This operation is idempotent - removing a non-associated control set has no effect.
    Agents with this policy will immediately lose controls from the removed control set.

    Args:
        policy_id: ID of the policy
        control_set_id: ID of the control set to remove
        db: Database session (injected)

    Returns:
        AssocResponse with success flag

    Raises:
        HTTPException 404: Policy or control set not found
        HTTPException 500: Database error
    """
    pol_res = await db.execute(select(Policy).where(Policy.id == policy_id))
    policy = pol_res.scalars().first()
    if policy is None:
        raise HTTPException(
            status_code=404, detail=f"Policy with ID '{policy_id}' not found"
        )

    ctl_res = await db.execute(select(ControlSet).where(ControlSet.id == control_set_id))
    control_set = ctl_res.scalars().first()
    if control_set is None:
        raise HTTPException(
            status_code=404, detail=f"Control set with ID '{control_set_id}' not found"
        )

    # Remove association (idempotent - deleting non-existent is no-op)
    try:
        await db.execute(
            delete(policy_control_sets).where(
                (policy_control_sets.c.policy_id == policy_id)
                & (policy_control_sets.c.control_set_id == control_set_id)
            )
        )
        await db.commit()
    except Exception:
        await db.rollback()
        _logger.error(
            (
                f"Failed to remove control set '{control_set.name}' ({control_set_id}) "
                f"from policy '{policy.name}' ({policy_id})"
            ),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to remove control set '{control_set.name}' from policy '{policy.name}': "
                "database error"
            ),
        )

    return AssocResponse(success=True)


@router.get(
    "/{policy_id}/control_sets",
    response_model=GetPolicyControlSetsResponse,
    summary="List policy's control sets",
    response_description="List of control set IDs",
)
async def list_policy_control_sets(
    policy_id: int, db: AsyncSession = Depends(get_async_db)
) -> GetPolicyControlSetsResponse:
    """
    List all control sets associated with a policy.

    Args:
        policy_id: ID of the policy
        db: Database session (injected)

    Returns:
        GetPolicyControlSetsResponse with list of control set IDs

    Raises:
        HTTPException 404: Policy not found
    """
    pol_res = await db.execute(select(Policy.id).where(Policy.id == policy_id))
    if pol_res.first() is None:
        raise HTTPException(
            status_code=404, detail=f"Policy with ID '{policy_id}' not found"
        )

    rows = await db.execute(
        select(policy_control_sets.c.control_set_id).where(
            policy_control_sets.c.policy_id == policy_id
        )
    )
    control_set_ids = [r[0] for r in rows.fetchall()]
    return GetPolicyControlSetsResponse(control_set_ids=control_set_ids)
