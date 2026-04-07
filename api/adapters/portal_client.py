"""PortalJS.be async client — JWT auto-generated, no login/password (ADR-011).

Reads: Customer, Person, EmploymentContract, Project, Activity, Timesheet.
Writes: Project (create commessa), Activity (assign resource) — with human confirmation.

Connection: JWT signed with shared JWTSECRET (HS256), auto-refreshed every 4 min.
"""

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import jwt

logger = logging.getLogger(__name__)

PORTAL_API_URL = os.getenv("PORTAL_API_URL", "")
PORTAL_JWT_SECRET = os.getenv("PORTAL_JWT_SECRET", "")
PORTAL_TENANT = os.getenv("PORTAL_TENANT", "NEXA")

# In-memory cache: key → (data, expires_at)
_cache: dict[str, tuple[Any, float]] = {}
CACHE_TTL = 300  # 5 minutes


class PortalClient:
    """Async client for PortalJS.be REST API."""

    def __init__(self) -> None:
        self.base_url = PORTAL_API_URL.rstrip("/") if PORTAL_API_URL else ""
        self.secret = PORTAL_JWT_SECRET
        self.tenant = PORTAL_TENANT
        self._token: str | None = None
        self._token_expires: float = 0
        self.enabled = bool(self.base_url and self.secret)

        if not self.enabled:
            logger.warning("PortalClient disabled — PORTAL_API_URL or PORTAL_JWT_SECRET not set")

    # ── JWT ──────────────────────────────────────────────

    def _generate_token(self) -> str:
        """Generate JWT signed with shared secret (AC-230.1)."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": 1,
            "email": "agentflow@iridia.tech",
            "username": "agentflow@iridia.tech",
            "roles": [{"id": 1, "role": "AMMI", "description": "AgentFlow Service"}],
            "tenant": self.tenant,
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "iat": int(now.timestamp()),
        }
        return jwt.encode(payload, self.secret, algorithm="HS256")

    def _get_token(self) -> str:
        """Get valid token, regenerate if expired."""
        now = time.time()
        if not self._token or now >= self._token_expires:
            self._token = self._generate_token()
            self._token_expires = now + 240  # Refresh every 4 min (token valid 5 min)
            logger.debug("Portal JWT token regenerated")
        return self._token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }

    # ── HTTP helpers ─────────────────────────────────────

    async def _get(self, path: str, params: dict | None = None, use_cache: bool = True) -> Any:
        """GET with cache and error handling (AC-230.4)."""
        if not self.enabled:
            logger.warning("PortalClient disabled — returning empty result")
            return {"data": [], "total": 0}

        cache_key = f"{path}:{params}" if params else path
        if use_cache and cache_key in _cache:
            data, expires = _cache[cache_key]
            if time.time() < expires:
                return data

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{self.base_url}{path}",
                    params=params,
                    headers=self._headers(),
                )
            if resp.status_code == 200:
                data = resp.json()
                if use_cache:
                    _cache[cache_key] = (data, time.time() + CACHE_TTL)
                return data
            logger.error("Portal GET %s → HTTP %s: %s", path, resp.status_code, resp.text[:200])
            return {"data": [], "total": 0, "error": f"HTTP {resp.status_code}"}
        except httpx.ConnectError as e:
            logger.error("Portal non raggiungibile: %s — %s", self.base_url, e)
            return {"data": [], "total": 0, "error": f"Portal non raggiungibile: {self.base_url}"}
        except Exception as e:
            logger.error("Portal GET %s error: %s", path, e)
            return {"data": [], "total": 0, "error": str(e)}

    async def _post(self, path: str, body: dict) -> Any:
        """POST — for creating resources on Portal."""
        if not self.enabled:
            return {"error": "PortalClient disabled"}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self.base_url}{path}",
                    json=body,
                    headers=self._headers(),
                )
            if resp.status_code in (200, 201):
                return resp.json()
            logger.error("Portal POST %s → HTTP %s: %s", path, resp.status_code, resp.text[:200])
            return {"error": f"HTTP {resp.status_code}", "detail": resp.text[:200]}
        except Exception as e:
            logger.error("Portal POST %s error: %s", path, e)
            return {"error": str(e)}

    # ── Customers (AC-230.2) ─────────────────────────────

    async def get_customers(self, search: str = "", page: int = 1, page_size: int = 100) -> dict:
        """Read customers from Portal."""
        params: dict[str, Any] = {"pageNum": page, "pageSize": page_size}
        if search:
            params["term"] = search
        return await self._get("/crud/Customer", params)

    async def get_customer(self, customer_id: int) -> dict:
        """Read single customer."""
        return await self._get(f"/crud/Customer/{customer_id}", use_cache=False)

    # ── Persons (AC-230.3) ───────────────────────────────

    async def get_persons(self, search: str = "", page: int = 1, page_size: int = 50) -> dict:
        """Read persons from Portal."""
        params: dict[str, Any] = {"pageNum": page, "pageSize": page_size, "include": "true"}
        if search:
            params["term"] = search
        return await self._get("/crud/Person", params)

    async def get_person(self, person_id: int) -> dict:
        """Read single person with contracts."""
        return await self._get(f"/crud/Person/{person_id}", {"include": "true"}, use_cache=False)

    # ── Employment Contracts ─────────────────────────────

    async def get_employment_contracts(self, person_id: int | None = None) -> dict:
        """Read employment contracts, optionally filtered by person."""
        params: dict[str, Any] = {"pageNum": 0, "pageSize": 100, "include": "true"}
        # Note: filtering by person_id may need POST with filter body
        return await self._get("/crud/EmploymentContract", params)

    # ── Projects (Commesse) ──────────────────────────────

    async def get_projects(self, search: str = "", page: int = 1, page_size: int = 50) -> dict:
        """Read projects from Portal."""
        params: dict[str, Any] = {"pageNum": page, "pageSize": page_size, "include": "true"}
        if search:
            params["term"] = search
        return await self._get("/crud/Project", params)

    async def get_project(self, project_id: int) -> dict:
        """Read single project with activities."""
        return await self._get(f"/crud/Project/{project_id}", {"include": "true"}, use_cache=False)

    async def create_project(self, data: dict) -> dict:
        """Create project on Portal (requires human confirmation)."""
        return await self._post("/projects/create", data)

    # ── Activities (Assignments) ─────────────────────────

    async def get_activities(self, project_id: int | None = None) -> dict:
        """Read activities (assignments)."""
        params: dict[str, Any] = {"pageNum": 0, "pageSize": 200, "include": "true"}
        return await self._get("/crud/Activity", params)

    async def create_activity(self, data: dict) -> dict:
        """Create activity (assignment) on Portal."""
        return await self._post("/activities/create", data)

    # ── Timesheets ───────────────────────────────────────

    async def get_timesheets(self, year: int | None = None, month: int | None = None) -> dict:
        """Read timesheets."""
        params: dict[str, Any] = {"pageNum": 0, "pageSize": 200, "include": "true"}
        return await self._get("/crud/Timesheet", params)

    async def get_timesheet_details(self, timesheet_id: int) -> dict:
        """Read timesheet details (daily hours)."""
        return await self._get(f"/crud/TimesheetDetail", {"pageNum": 0, "pageSize": 500})

    # ── Cache management ─────────────────────────────────

    def clear_cache(self) -> None:
        """Clear all cached data."""
        _cache.clear()

    def is_enabled(self) -> bool:
        return self.enabled


# Singleton instance
portal_client = PortalClient()
