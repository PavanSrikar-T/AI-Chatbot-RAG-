import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_current_active_user
from app.core.db import get_db
from app.models.user import User
from app.models.module_state import ModuleState
from app.schemas.module_state import ModuleStateUpdate, ModuleStateResponse

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/states", response_model=List[ModuleStateResponse])
async def get_all_module_states(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all saved module states for the authenticated user."""
    result = await db.execute(
        select(ModuleState).filter(ModuleState.user_id == current_user.id)
    )
    states = result.scalars().all()
    return [
        ModuleStateResponse(
            module=s.module,
            state_json=s.state_json or {},
            updated_at=s.updated_at
        )
        for s in states
    ]


@router.get("/{module}/state", response_model=ModuleStateResponse)
async def get_module_state(
    module: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve persistent state for a specific module.
    If no state has been saved yet, returns an empty default state.
    """
    clean_module = module.lower().strip()
    result = await db.execute(
        select(ModuleState).filter(
            ModuleState.user_id == current_user.id,
            ModuleState.module == clean_module
        )
    )
    state = result.scalars().first()
    if not state:
        return ModuleStateResponse(
            module=clean_module,
            state_json={},
            updated_at=None
        )
    return ModuleStateResponse(
        module=state.module,
        state_json=state.state_json or {},
        updated_at=state.updated_at
    )


@router.put("/{module}/state", response_model=ModuleStateResponse)
async def update_module_state(
    module: str,
    update_in: ModuleStateUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upsert persistent module state for the authenticated user.
    Merges or replaces the state_json and updates timestamp.
    """
    clean_module = module.lower().strip()
    result = await db.execute(
        select(ModuleState).filter(
            ModuleState.user_id == current_user.id,
            ModuleState.module == clean_module
        )
    )
    state = result.scalars().first()

    if state:
        # Merge dictionary updates to prevent accidental full-overwrite of unrelated keys
        current_data = dict(state.state_json or {})
        current_data.update(update_in.state_json)
        state.state_json = current_data
    else:
        state = ModuleState(
            user_id=current_user.id,
            module=clean_module,
            state_json=update_in.state_json
        )
        db.add(state)

    await db.commit()
    await db.refresh(state)

    return ModuleStateResponse(
        module=state.module,
        state_json=state.state_json,
        updated_at=state.updated_at
    )
