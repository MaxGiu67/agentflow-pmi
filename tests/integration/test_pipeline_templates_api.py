"""Tests for Pipeline Templates — Sprint 35 (US-200, US-201, US-202).

Covers:
- US-200: Seed 3 templates (T&M, Corpo, Elevia), list, get
- US-201: Product → pipeline mapping
- US-202: Create custom template, update
"""

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import CrmProduct, PipelineTemplate, PipelineTemplateStage, Tenant
from api.modules.pipeline_templates.service import PipelineTemplateService
from tests.conftest import get_auth_token


class TestUS200PipelineTemplates:
    """US-200: Pipeline templates from DB with seed."""

    @pytest.mark.anyio
    async def test_ac_200_1_seed_creates_3_templates(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """AC-200.1: Seed creates T&M, Corpo, Elevia templates."""
        svc = PipelineTemplateService(db_session)
        await svc.ensure_defaults(tenant.id)

        templates = await svc.list_templates(tenant.id)
        codes = [t["code"] for t in templates]
        assert "vendita_diretta" in codes
        assert "progetto_corpo" in codes
        assert "social_selling" in codes
        assert len(templates) == 3

    @pytest.mark.anyio
    async def test_ac_200_1_tm_has_correct_stages(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """T&M template has correct stages."""
        svc = PipelineTemplateService(db_session)
        tmpl = await svc.get_template_by_code(tenant.id, "vendita_diretta")
        assert tmpl is not None
        assert tmpl["pipeline_type"] == "services"

        stage_codes = [s["code"] for s in tmpl["stages"]]
        assert "lead" in stage_codes
        assert "qualifica" in stage_codes
        assert "match" in stage_codes
        assert "offerta" in stage_codes
        assert "won" in stage_codes

    @pytest.mark.anyio
    async def test_ac_200_1_elevia_has_optional_demo(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """Elevia template has optional Demo stage."""
        svc = PipelineTemplateService(db_session)
        tmpl = await svc.get_template_by_code(tenant.id, "social_selling")
        assert tmpl is not None

        demo = next((s for s in tmpl["stages"] if s["code"] == "demo"), None)
        assert demo is not None
        assert demo["is_optional"] is True

    @pytest.mark.anyio
    async def test_ac_200_2_seed_idempotent(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """Seed is idempotent — calling twice doesn't duplicate."""
        svc = PipelineTemplateService(db_session)
        await svc.ensure_defaults(tenant.id)
        await svc.ensure_defaults(tenant.id)

        templates = await svc.list_templates(tenant.id)
        assert len(templates) == 3

    @pytest.mark.anyio
    async def test_ac_200_3_tenant_isolation(
        self, db_session: AsyncSession,
    ):
        """Different tenants get their own templates."""
        from api.db.models import Tenant as T
        t1 = T(name="Tenant A", type="srl", regime_fiscale="ordinario", piva="11111111111")
        t2 = T(name="Tenant B", type="srl", regime_fiscale="ordinario", piva="22222222222")
        db_session.add_all([t1, t2])
        await db_session.flush()

        svc = PipelineTemplateService(db_session)
        await svc.ensure_defaults(t1.id)
        await svc.ensure_defaults(t2.id)

        t1_templates = await svc.list_templates(t1.id)
        t2_templates = await svc.list_templates(t2.id)

        # Each has 3, but different IDs
        assert len(t1_templates) == 3
        assert len(t2_templates) == 3
        t1_ids = {t["id"] for t in t1_templates}
        t2_ids = {t["id"] for t in t2_templates}
        assert t1_ids.isdisjoint(t2_ids)


class TestUS201ProductPipeline:
    """US-201: Product determines pipeline."""

    @pytest.mark.anyio
    async def test_ac_201_product_has_pipeline_template_id(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """Product can be linked to a pipeline template."""
        svc = PipelineTemplateService(db_session)
        await svc.ensure_defaults(tenant.id)

        tmpl = await svc.get_template_by_code(tenant.id, "vendita_diretta")

        product = CrmProduct(
            tenant_id=tenant.id,
            code="java_senior",
            name="Consulenza Java Senior",
            pricing_model="hourly",
            pipeline_template_id=uuid.UUID(tmpl["id"]),
        )
        db_session.add(product)
        await db_session.flush()

        assert product.pipeline_template_id == uuid.UUID(tmpl["id"])


class TestUS202CustomTemplate:
    """US-202: Admin creates custom template."""

    @pytest.mark.anyio
    async def test_ac_202_create_custom_template(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """Admin can create a custom pipeline template."""
        svc = PipelineTemplateService(db_session)

        result = await svc.create_template(tenant.id, {
            "code": "training",
            "name": "Formazione",
            "pipeline_type": "custom",
            "stages": [
                {"code": "lead", "name": "Lead", "sequence": 10},
                {"code": "analisi", "name": "Analisi bisogni", "sequence": 20},
                {"code": "programma", "name": "Programma", "sequence": 30},
                {"code": "offerta", "name": "Offerta", "sequence": 40},
                {"code": "won", "name": "Won", "sequence": 50, "is_won": True},
            ],
        })

        assert result["code"] == "training"
        assert result["stage_count"] == 5

    @pytest.mark.anyio
    async def test_ac_202_update_template(
        self, db_session: AsyncSession, tenant: Tenant,
    ):
        """Admin can update template name."""
        svc = PipelineTemplateService(db_session)
        await svc.ensure_defaults(tenant.id)

        tmpl = await svc.get_template_by_code(tenant.id, "vendita_diretta")
        updated = await svc.update_template(uuid.UUID(tmpl["id"]), tenant.id, {"name": "T&M Aggiornato"})

        assert updated is not None
        assert updated["name"] == "T&M Aggiornato"


class TestAPIEndpoints:
    """API endpoint tests for pipeline templates."""

    @pytest.mark.anyio
    async def test_api_list_templates(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/pipeline-templates", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 3
        codes = [t["code"] for t in data]
        assert "vendita_diretta" in codes

    @pytest.mark.anyio
    async def test_api_get_template(self, client: AsyncClient, auth_headers: dict):
        # Get list first
        resp = await client.get("/api/v1/pipeline-templates", headers=auth_headers)
        templates = resp.json()
        tm = next(t for t in templates if t["code"] == "vendita_diretta")

        # Get by ID
        resp2 = await client.get(f"/api/v1/pipeline-templates/{tm['id']}", headers=auth_headers)
        assert resp2.status_code == 200
        assert resp2.json()["code"] == "vendita_diretta"
        assert len(resp2.json()["stages"]) >= 6
