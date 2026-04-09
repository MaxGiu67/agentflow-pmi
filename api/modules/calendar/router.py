"""Calendar router — OAuth Microsoft 365, calendar status, Calendly URL (US-151→US-155).

Prefix: /calendar
Tags: calendar
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import User
from api.db.session import get_db
from api.middleware.auth import get_current_user
from api.modules.calendar.microsoft_service import MicrosoftCalendarService

router = APIRouter(prefix="/calendar", tags=["calendar"])


# ── US-153: Microsoft 365 OAuth ───────────────────────


@router.get("/microsoft/connect")
async def microsoft_connect(
    user: User = Depends(get_current_user),
):
    """AC-153.1: Redirect to Microsoft OAuth login."""
    svc = MicrosoftCalendarService(None)  # No DB needed for URL generation
    auth_url = svc.get_auth_url(state=str(user.id))
    return {"auth_url": auth_url}


@router.get("/microsoft/callback")
async def microsoft_callback(
    code: str = Query(...),
    state: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    """AC-153.1: Handle OAuth callback from Microsoft."""
    import os
    import uuid
    from sqlalchemy import select

    user_id = uuid.UUID(state)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "Utente non trovato")

    svc = MicrosoftCalendarService(db)
    token_result = await svc.exchange_code(code, user)

    if "error" in token_result:
        raise HTTPException(400, token_result["error"])

    await db.commit()

    # Redirect back to frontend profile page
    frontend_url = os.getenv("FRONTEND_URL", "https://agentflow.iridia.tech")
    return RedirectResponse(url=f"{frontend_url}/profilo?calendar=connected")


@router.get("/microsoft/status")
async def microsoft_status(
    user: User = Depends(get_current_user),
):
    """Check if Microsoft 365 is connected."""
    connected = bool(user.microsoft_token)
    return {"connected": connected}


@router.post("/microsoft/disconnect")
async def microsoft_disconnect(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AC-153.4: Disconnect Microsoft 365 Calendar."""
    svc = MicrosoftCalendarService(db)
    result = await svc.disconnect(user)
    await db.commit()
    return result


# ── US-155: Calendly URL ──────────────────────────────


@router.get("/calendly")
async def get_calendly(
    user: User = Depends(get_current_user),
):
    """Get Calendly URL for current user."""
    return {"calendly_url": user.calendly_url or ""}


@router.patch("/calendly")
async def update_calendly(
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AC-155.1/155.4: Update own Calendly URL."""
    url = body.get("calendly_url", "").strip()
    user.calendly_url = url if url else None
    await db.flush()
    await db.commit()
    return {"calendly_url": user.calendly_url or ""}
