"""Router for dashboard layout CRUD operations."""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import DashboardLayout, User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.dashboard.default_widgets import DEFAULT_WIDGETS, get_widgets_for_role

router = APIRouter(tags=["dashboard-layout"])


class LayoutResponse(BaseModel):
    id: str
    name: str
    year: int
    widgets: list[dict]

    model_config = {"from_attributes": True}


class LayoutUpdateRequest(BaseModel):
    widgets: list[dict]
    year: int


async def _get_or_create_layout(
    db: AsyncSession, user: User,
) -> DashboardLayout:
    """Get the user's layout or create a default one."""
    result = await db.execute(
        select(DashboardLayout).where(
            DashboardLayout.user_id == user.id,
            DashboardLayout.tenant_id == user.tenant_id,
        )
    )
    layout = result.scalar_one_or_none()
    role_widgets = get_widgets_for_role(user.role)

    if layout is None:
        layout = DashboardLayout(
            tenant_id=user.tenant_id,
            user_id=user.id,
            name="default",
            year=datetime.now().year,
            widgets=role_widgets,
        )
        db.add(layout)
        await db.flush()
    else:
        # Auto-reset if saved widgets don't match role
        # Compare first widget ID to detect mismatch
        saved_ids = {w.get("id") for w in (layout.widgets or [])}
        role_ids = {w.get("id") for w in role_widgets}
        if saved_ids and role_ids and not saved_ids.intersection(role_ids):
            layout.widgets = role_widgets
            await db.flush()

    return layout


@router.get("/dashboard/layout", response_model=LayoutResponse)
async def get_layout(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LayoutResponse:
    """Get the current user's dashboard layout. Creates default if missing."""
    layout = await _get_or_create_layout(db, user)
    return LayoutResponse(
        id=str(layout.id),
        name=layout.name,
        year=layout.year,
        widgets=layout.widgets or [],
    )


@router.put("/dashboard/layout", response_model=LayoutResponse)
async def save_layout(
    body: LayoutUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LayoutResponse:
    """Save the user's dashboard layout (widgets + year)."""
    layout = await _get_or_create_layout(db, user)
    layout.widgets = body.widgets
    layout.year = body.year
    await db.flush()
    return LayoutResponse(
        id=str(layout.id),
        name=layout.name,
        year=layout.year,
        widgets=layout.widgets or [],
    )


@router.post("/dashboard/layout/reset", response_model=LayoutResponse)
async def reset_layout(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LayoutResponse:
    """Reset the user's dashboard to default widgets for their role."""
    layout = await _get_or_create_layout(db, user)
    layout.widgets = get_widgets_for_role(user.role)
    await db.flush()
    return LayoutResponse(
        id=str(layout.id),
        name=layout.name,
        year=layout.year,
        widgets=layout.widgets or [],
    )
