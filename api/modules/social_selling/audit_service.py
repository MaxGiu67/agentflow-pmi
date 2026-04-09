"""Service for audit trail — immutable log (US-141)."""

import csv
import hashlib
import io
import logging
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CrmAuditLog

logger = logging.getLogger(__name__)


class AuditService:
    """Read-only audit trail (logs are written by other services)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log_action(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID | None = None,
        entity_name: str | None = None,
        change_details: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        status: str = "success",
        error_message: str | None = None,
    ) -> dict:
        """Write audit log entry."""
        entry = CrmAuditLog(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            change_details=change_details,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            error_message=error_message,
        )
        self.db.add(entry)
        await self.db.flush()
        return self._to_dict(entry)

    async def list_logs(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """AC-141.1: List audit logs with filters."""
        query = select(CrmAuditLog).where(CrmAuditLog.tenant_id == tenant_id)

        if user_id:
            query = query.where(CrmAuditLog.user_id == user_id)
        if action:
            query = query.where(CrmAuditLog.action == action)
        if entity_type:
            query = query.where(CrmAuditLog.entity_type == entity_type)
        if start_date:
            query = query.where(CrmAuditLog.created_at >= start_date)
        if end_date:
            query = query.where(CrmAuditLog.created_at <= end_date)

        # Count
        count_query = select(func.count(CrmAuditLog.id)).where(CrmAuditLog.tenant_id == tenant_id)
        if user_id:
            count_query = count_query.where(CrmAuditLog.user_id == user_id)
        total = await self.db.scalar(count_query) or 0

        query = query.order_by(CrmAuditLog.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)

        return {
            "data": [self._to_dict(log) for log in result.scalars().all()],
            "meta": {"total": total, "limit": limit, "offset": offset},
        }

    async def export_csv(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[str, str]:
        """AC-141.4: Export audit log as CSV with SHA256 hash."""
        logs = await self.list_logs(
            tenant_id, user_id=user_id, action=action,
            entity_type=entity_type, start_date=start_date, end_date=end_date,
            limit=10000, offset=0,
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["timestamp", "user_id", "action", "entity_type", "entity_id", "entity_name", "status", "ip_address"])
        for log in logs["data"]:
            writer.writerow([
                log["created_at"], log["user_id"], log["action"],
                log["entity_type"], log.get("entity_id", ""),
                log.get("entity_name", ""), log["status"],
                log.get("ip_address", ""),
            ])

        csv_content = output.getvalue()
        sha256 = hashlib.sha256(csv_content.encode()).hexdigest()
        return csv_content, sha256

    def _to_dict(self, log: CrmAuditLog) -> dict:
        return {
            "id": str(log.id),
            "tenant_id": str(log.tenant_id),
            "user_id": str(log.user_id),
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": str(log.entity_id) if log.entity_id else None,
            "entity_name": log.entity_name,
            "change_details": log.change_details,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "status": log.status,
            "error_message": log.error_message,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
