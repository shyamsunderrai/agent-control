from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from agent_control_models.policy import Control as APIControl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Agent, Control, ControlSet, Policy, control_set_controls, policy_control_sets


async def list_controls_for_policy(policy_id: int, db: AsyncSession) -> list[Control]:
    """Return DB Control objects for all controls in a policy's control sets."""
    stmt = (
        select(Control)
        .join(control_set_controls, Control.id == control_set_controls.c.control_id)
        .join(ControlSet, control_set_controls.c.control_set_id == ControlSet.id)
        .join(policy_control_sets, ControlSet.id == policy_control_sets.c.control_set_id)
        .where(policy_control_sets.c.policy_id == policy_id)
    )
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())


async def list_controls_for_agent(agent_id: UUID, db: AsyncSession) -> list[APIControl]:
    """Return API Control models for all controls associated with the agent's policy.

    Traversal: Agent -> Policy -> ControlSets -> Controls.
    Uses explicit joins over association tables to avoid async relationship loading.
    """
    stmt = (
        select(Control)
        .join(control_set_controls, Control.id == control_set_controls.c.control_id)
        .join(ControlSet, control_set_controls.c.control_set_id == ControlSet.id)
        .join(policy_control_sets, ControlSet.id == policy_control_sets.c.control_set_id)
        .join(Policy, policy_control_sets.c.policy_id == Policy.id)
        .join(Agent, Policy.id == Agent.policy_id)
        .where(Agent.agent_uuid == agent_id)
    )

    result = await db.execute(stmt)
    db_controls: Sequence[Control] = result.scalars().unique().all()

    # Map DB Control to API Control with id, name, and control (data)
    return [APIControl(id=c.id, name=c.name, control=c.data) for c in db_controls]
