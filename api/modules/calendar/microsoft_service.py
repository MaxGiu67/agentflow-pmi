"""Microsoft 365 Calendar integration — OAuth2 + Graph API push (US-153, US-154).

One-way push: AgentFlow → Outlook Calendar. No two-way sync.
Token stored encrypted (JSON) in User.microsoft_token.
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CrmActivity, User

logger = logging.getLogger(__name__)

# Microsoft OAuth2 config — set in .env
MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "")
MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "")
MICROSOFT_REDIRECT_URI = os.getenv("MICROSOFT_REDIRECT_URI", "")
MICROSOFT_TENANT_ID = os.getenv("MICROSOFT_TENANT_ID", "common")  # "common" for multi-tenant

AUTHORITY = f"https://login.microsoftonline.com/{MICROSOFT_TENANT_ID}"
SCOPES = ["Calendars.ReadWrite", "User.Read", "offline_access"]
GRAPH_API = "https://graph.microsoft.com/v1.0"


class MicrosoftCalendarService:
    """Microsoft 365 Calendar push service."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── US-153: OAuth flow ──────────────────────────────

    def get_auth_url(self, state: str = "") -> str:
        """AC-153.1: Generate Microsoft OAuth2 authorization URL."""
        params = {
            "client_id": MICROSOFT_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": MICROSOFT_REDIRECT_URI,
            "scope": " ".join(SCOPES),
            "response_mode": "query",
            "state": state,
        }
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{AUTHORITY}/oauth2/v2.0/authorize?{qs}"

    async def exchange_code(self, code: str, user: User) -> dict:
        """AC-153.1: Exchange authorization code for tokens."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{AUTHORITY}/oauth2/v2.0/token",
                data={
                    "client_id": MICROSOFT_CLIENT_ID,
                    "client_secret": MICROSOFT_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": MICROSOFT_REDIRECT_URI,
                    "grant_type": "authorization_code",
                    "scope": " ".join(SCOPES),
                },
            )

        if resp.status_code != 200:
            logger.error("Microsoft token exchange failed: %s", resp.text)
            return {"error": "Token exchange failed", "detail": resp.text}

        data = resp.json()
        token_data = {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600))).isoformat(),
        }

        # Save token to user
        user.microsoft_token = json.dumps(token_data)
        await self.db.flush()

        logger.info("Microsoft 365 connected for user %s", user.email)
        return {"status": "connected", "email": user.email}

    async def disconnect(self, user: User) -> dict:
        """AC-153.4: Remove Microsoft token."""
        user.microsoft_token = None
        await self.db.flush()
        return {"status": "disconnected"}

    def is_connected(self, user: User) -> bool:
        """Check if user has Microsoft 365 connected."""
        return bool(user.microsoft_token)

    # ── US-153.3: Token refresh ─────────────────────────

    async def _get_valid_token(self, user: User) -> str | None:
        """AC-153.3: Get valid access token, refresh if expired."""
        if not user.microsoft_token:
            return None

        try:
            token_data = json.loads(user.microsoft_token)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Invalid microsoft_token JSON for user %s — keeping token", user.email)
            return None

        expires_at = datetime.fromisoformat(token_data["expires_at"])
        now = datetime.now(timezone.utc)

        if now < expires_at - timedelta(minutes=5):
            return token_data["access_token"]

        # Token expired — try refresh
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            logger.warning("No refresh token for user %s — token expired but NOT cleared (reconnect needed)", user.email)
            return None  # Don't clear — user can still reconnect

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{AUTHORITY}/oauth2/v2.0/token",
                    data={
                        "client_id": MICROSOFT_CLIENT_ID,
                        "client_secret": MICROSOFT_CLIENT_SECRET,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                        "scope": " ".join(SCOPES),
                    },
                )
        except Exception as e:
            logger.error("Token refresh HTTP error for %s: %s — keeping existing token", user.email, e)
            return None  # Network error — don't clear, retry next time

        if resp.status_code != 200:
            logger.error("Token refresh failed for %s (HTTP %s): %s — keeping existing token", user.email, resp.status_code, resp.text[:200])
            return None  # Don't clear — might be temporary Microsoft outage

        data = resp.json()
        new_token_data = {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token", refresh_token),
            "expires_at": (now + timedelta(seconds=data.get("expires_in", 3600))).isoformat(),
        }
        user.microsoft_token = json.dumps(new_token_data)
        await self.db.flush()

        logger.info("Microsoft token refreshed for user %s", user.email)
        return data["access_token"]

    # ── US-154: Push events to Outlook ──────────────────

    async def push_activity(self, user: User, activity: CrmActivity, contact_name: str = "", deal_name: str = "") -> dict:
        """AC-154.1: Push planned activity to Outlook Calendar."""
        token = await self._get_valid_token(user)
        if not token:
            return {"pushed": False, "reason": "not_connected"}

        if not activity.scheduled_at:
            return {"pushed": False, "reason": "no_scheduled_at"}

        start = activity.scheduled_at
        # Default duration: 30min for calls, 60min for meetings
        duration_min = 60 if activity.type == "meeting" else 30
        end = start + timedelta(minutes=duration_min)

        body_lines = []
        if activity.description:
            body_lines.append(activity.description)
        if contact_name:
            body_lines.append(f"Contatto: {contact_name}")
        if deal_name:
            body_lines.append(f"Deal: {deal_name}")
        body_lines.append("\n---\nCreato da AgentFlow PMI")

        event_payload = {
            "subject": activity.subject,
            "body": {
                "contentType": "text",
                "content": "\n".join(body_lines),
            },
            "start": {
                "dateTime": start.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": "Europe/Rome",
            },
            "end": {
                "dateTime": end.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": "Europe/Rome",
            },
            "reminderMinutesBeforeStart": 15,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{GRAPH_API}/me/events",
                json=event_payload,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )

        if resp.status_code in (200, 201):
            event_id = resp.json().get("id", "")
            activity.outlook_event_id = event_id
            await self.db.flush()
            logger.info("Pushed activity %s to Outlook (event %s)", activity.id, event_id)
            return {"pushed": True, "outlook_event_id": event_id}

        logger.error("Outlook push failed for activity %s: %s %s", activity.id, resp.status_code, resp.text)
        return {"pushed": False, "reason": "api_error", "status": resp.status_code}

    async def update_activity(self, user: User, activity: CrmActivity, contact_name: str = "", deal_name: str = "") -> dict:
        """AC-154.2: Update existing Outlook event when activity changes."""
        if not activity.outlook_event_id:
            return await self.push_activity(user, activity, contact_name, deal_name)

        token = await self._get_valid_token(user)
        if not token:
            return {"pushed": False, "reason": "not_connected"}

        if not activity.scheduled_at:
            return {"pushed": False, "reason": "no_scheduled_at"}

        start = activity.scheduled_at
        duration_min = 60 if activity.type == "meeting" else 30
        end = start + timedelta(minutes=duration_min)

        patch_payload = {
            "subject": activity.subject,
            "start": {
                "dateTime": start.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": "Europe/Rome",
            },
            "end": {
                "dateTime": end.strftime("%Y-%m-%dT%H:%M:%S"),
                "timeZone": "Europe/Rome",
            },
        }

        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                f"{GRAPH_API}/me/events/{activity.outlook_event_id}",
                json=patch_payload,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )

        if resp.status_code == 200:
            return {"pushed": True, "updated": True}

        logger.warning("Outlook update failed, status %s", resp.status_code)
        return {"pushed": False, "reason": "update_failed"}
