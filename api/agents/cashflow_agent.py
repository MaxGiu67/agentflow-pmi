"""CashFlowAgent: Monitors cash flow and generates alerts (US-25)."""

import logging
import uuid

from api.agents.base_agent import BaseAgent
from api.modules.cashflow.service import CashFlowService

logger = logging.getLogger(__name__)


class CashFlowAgent(BaseAgent):
    """Agent that monitors cash flow and generates predictive alerts."""

    agent_name = "cashflow_agent"

    async def analyze(self, tenant_id: uuid.UUID) -> dict:
        """Run cash flow analysis and publish alerts.

        Returns prediction summary and any alerts generated.
        """
        service = CashFlowService(self.db)

        # Generate prediction
        prediction = await service.predict(tenant_id=tenant_id)

        # Generate alerts
        alerts_result = await service.get_alerts(tenant_id=tenant_id)

        # Publish events for critical alerts
        for alert in alerts_result["alerts"]:
            if alert["severity"] == "critical":
                await self.publish_event(
                    "cashflow.alert.critical",
                    {
                        "type": alert["type"],
                        "message": alert["message"],
                        "amount": alert.get("amount"),
                    },
                    tenant_id,
                )
            elif alert["type"] == "late_payment":
                await self.publish_event(
                    "cashflow.alert.late_payment",
                    {
                        "message": alert["message"],
                        "amount": alert.get("amount"),
                        "scenario_optimistic": alert.get("scenario_optimistic"),
                        "scenario_pessimistic": alert.get("scenario_pessimistic"),
                    },
                    tenant_id,
                )

        return {
            "prediction_days": prediction["giorni"],
            "saldo_attuale": prediction["saldo_attuale"],
            "saldo_proiettato": prediction["saldo_finale_proiettato"],
            "alerts_count": alerts_result["total"],
            "data_source": prediction["data_source"],
        }
