"""Elevia Use Case Engine — ATECO scoring, bundles, ROI (US-208→US-210, US-220, US-221).

Manages Elevia AI use cases with ATECO sector fit scoring.
Provides prospect scoring, use case bundles, ROI estimation, discovery briefs,
demo prep, onboarding plans, and adoption monitoring.
"""

import logging
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import EleviaUseCase, AtecoUseCaseMatrix

logger = logging.getLogger(__name__)

# ── Seed data ──────────────────────────────────────────

SEED_USE_CASES = [
    {"code": "UC01", "name": "FAQ interno tecnico-commerciale", "description": "Chatbot FAQ per risposte rapide a domande tecniche e commerciali ricorrenti"},
    {"code": "UC02", "name": "Knowledge Navigator", "description": "Navigazione intelligente documentazione tecnica dispersa"},
    {"code": "UC03", "name": "Supporto redazione offerte", "description": "Assistenza AI per composizione offerte e schede tecniche"},
    {"code": "UC04", "name": "Report automatici produzione", "description": "Generazione automatica report da dati di produzione"},
    {"code": "UC05", "name": "Classificazione email/PEC", "description": "Smistamento automatico comunicazioni in ingresso"},
    {"code": "UC06", "name": "Generazione documenti", "description": "Creazione automatica documenti da template e dati"},
    {"code": "UC07", "name": "Estrazione dati da documenti", "description": "OCR + AI per estrarre dati strutturati da documenti"},
    {"code": "UC09", "name": "FAQ manutentive/operatori", "description": "Assistente AI per operatori e manutentori in stabilimento"},
    {"code": "UC13", "name": "Classificazione richieste", "description": "Categorizzazione automatica richieste clienti/fornitori"},
    {"code": "UC14", "name": "Predizione guasti", "description": "Analisi anomalie testuali per predizione guasti impianti"},
    {"code": "UC15", "name": "Motore ricerca interno", "description": "Search engine intelligente per documentazione aziendale"},
]

# ATECO fit scores: {use_case_code: {ateco_prefix: score}}
ATECO_MATRIX = {
    "UC01": {"24": 70, "25": 75, "46": 85, "20": 70},
    "UC02": {"24": 90, "25": 90, "46": 80, "20": 85},
    "UC03": {"24": 60, "25": 65, "46": 85, "20": 60},
    "UC04": {"24": 90, "25": 85, "46": 50, "20": 80},
    "UC05": {"24": 60, "25": 60, "46": 75, "20": 65},
    "UC06": {"24": 65, "25": 65, "46": 70, "20": 70},
    "UC07": {"24": 70, "25": 70, "46": 60, "20": 75},
    "UC09": {"24": 85, "25": 80, "46": 40, "20": 70},
    "UC13": {"24": 65, "25": 65, "46": 80, "20": 70},
    "UC14": {"24": 80, "25": 75, "46": 30, "20": 65},
    "UC15": {"24": 75, "25": 75, "46": 70, "20": 75},
}

SECTOR_BUNDLES = {
    "metallurgia": {"name": "Metallurgia Standard", "ateco_prefixes": ["24", "25"], "use_cases": ["UC02", "UC04", "UC13", "UC14"]},
    "commercio": {"name": "Commercio Standard", "ateco_prefixes": ["46"], "use_cases": ["UC01", "UC03", "UC05", "UC06", "UC15"]},
    "chimica": {"name": "Chimica Standard", "ateco_prefixes": ["20"], "use_cases": ["UC02", "UC04", "UC07", "UC09"]},
}

# ATECO priority: P1 sectors (100), P2 (70), off-target (10)
ATECO_PRIORITY = {"24": 100, "25": 100, "46": 100, "20": 70}


class EleviaService:
    """Elevia Use Case Engine."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── US-208: Seed + CRUD ────────────────────────────

    async def ensure_defaults(self, tenant_id: uuid.UUID) -> None:
        count = await self.db.scalar(
            select(func.count(EleviaUseCase.id)).where(EleviaUseCase.tenant_id == tenant_id)
        )
        if count and count > 0:
            return

        for uc in SEED_USE_CASES:
            use_case = EleviaUseCase(
                tenant_id=tenant_id, code=uc["code"], name=uc["name"], description=uc["description"],
            )
            self.db.add(use_case)
            await self.db.flush()

            # Seed ATECO matrix for this use case
            for ateco, score in ATECO_MATRIX.get(uc["code"], {}).items():
                self.db.add(AtecoUseCaseMatrix(
                    use_case_id=use_case.id, ateco_code=ateco, fit_score=score,
                ))

        await self.db.flush()
        logger.info("Seeded %d Elevia use cases for tenant %s", len(SEED_USE_CASES), tenant_id)

    async def list_use_cases(self, tenant_id: uuid.UUID) -> list[dict]:
        await self.ensure_defaults(tenant_id)
        result = await self.db.execute(
            select(EleviaUseCase).where(
                EleviaUseCase.tenant_id == tenant_id, EleviaUseCase.is_active.is_(True),
            ).order_by(EleviaUseCase.code)
        )
        cases = []
        for uc in result.scalars().all():
            matrix = await self._get_matrix(uc.id)
            cases.append(self._uc_to_dict(uc, matrix))
        return cases

    # ── US-209: Score prospect ─────────────────────────

    async def score_prospect(
        self, tenant_id: uuid.UUID,
        ateco_code: str, employee_count: int = 0,
        has_decision_maker: bool = False, engagement_level: str = "low",
    ) -> dict:
        """Composite fit score: ATECO (30%) + size (15%) + use cases (25%) + engagement (20%) + DM (10%)."""
        await self.ensure_defaults(tenant_id)

        ateco_prefix = ateco_code[:2] if ateco_code else ""

        # ATECO priority (30%)
        ateco_score = ATECO_PRIORITY.get(ateco_prefix, 10)

        # Company size (15%) — sweet spot 50-200
        if 50 <= employee_count <= 200:
            size_score = 100
        elif employee_count < 50:
            size_score = 60
        elif employee_count > 200:
            size_score = 80
        else:
            size_score = 50

        # Use case count (25%) — how many UCs score > 50 for this ATECO
        applicable_ucs = []
        for uc_code, ateco_scores in ATECO_MATRIX.items():
            score = ateco_scores.get(ateco_prefix, 0)
            if score > 50:
                applicable_ucs.append({"code": uc_code, "fit_score": score})

        if len(applicable_ucs) >= 5:
            uc_score = 100
        elif len(applicable_ucs) >= 3:
            uc_score = 70
        elif len(applicable_ucs) >= 1:
            uc_score = 40
        else:
            uc_score = 10

        # Engagement (20%)
        eng_map = {"high": 100, "medium": 60, "low": 20}
        eng_score = eng_map.get(engagement_level, 20)

        # Decision maker (10%)
        dm_score = 100 if has_decision_maker else 30

        total = round(
            ateco_score * 0.30 + size_score * 0.15 + uc_score * 0.25 + eng_score * 0.20 + dm_score * 0.10
        )

        # Suggest bundle
        bundle = self._suggest_bundle(ateco_prefix)

        return {
            "total_score": total,
            "threshold_qualified": 60,
            "threshold_hot": 80,
            "is_qualified": total >= 60,
            "is_hot": total >= 80,
            "breakdown": {
                "ateco_priority": ateco_score,
                "company_size": size_score,
                "use_case_fit": uc_score,
                "engagement": eng_score,
                "decision_maker": dm_score,
            },
            "applicable_use_cases": sorted(applicable_ucs, key=lambda x: x["fit_score"], reverse=True),
            "suggested_bundle": bundle,
        }

    def _suggest_bundle(self, ateco_prefix: str) -> dict | None:
        for bundle_key, bundle in SECTOR_BUNDLES.items():
            if ateco_prefix in bundle["ateco_prefixes"]:
                return {"name": bundle["name"], "use_cases": bundle["use_cases"]}
        return None

    # ── US-210: ROI calculator ─────────────────────────

    def calc_roi(
        self, use_case_count: int, avg_hours_saved_per_uc: float = 8,
        hourly_cost: float = 35, elevia_annual_cost: float = 6000,
    ) -> dict:
        monthly_savings = use_case_count * avg_hours_saved_per_uc * hourly_cost
        annual_savings = monthly_savings * 12
        roi_pct = ((annual_savings - elevia_annual_cost) / elevia_annual_cost * 100) if elevia_annual_cost > 0 else 0
        payback_months = round(elevia_annual_cost / monthly_savings) if monthly_savings > 0 else 0

        return {
            "use_case_count": use_case_count,
            "monthly_savings_eur": round(monthly_savings),
            "annual_savings_eur": round(annual_savings),
            "elevia_annual_cost_eur": elevia_annual_cost,
            "net_benefit_eur": round(annual_savings - elevia_annual_cost),
            "roi_pct": round(roi_pct, 1),
            "payback_months": payback_months,
        }

    # ── US-220: Discovery brief ────────────────────────

    def get_discovery_brief(self, ateco_prefix: str) -> dict:
        """Pre-fill discovery brief with sector pain points and candidate use cases."""
        pain_points = {
            "24": ["Know-how tecnico disperso tra operatori", "Report produzione manuali e lenti", "Documentazione tecnica non trovabile", "Comunicazioni non classificate"],
            "25": ["Know-how tecnico disperso tra operatori", "Report produzione manuali", "Offerte tecniche laboriose", "FAQ manutentive ripetitive"],
            "46": ["Catalogo prodotti complesso", "Offerte commerciali lente", "Email e PEC non classificate", "Documentazione dispersa tra sedi"],
            "20": ["Normativa stringente e documentazione complessa", "Report produzione obbligatori", "Estrazione dati da certificati", "FAQ manutentive per operatori"],
        }
        discovery_questions = [
            "Come gestite oggi la documentazione tecnica interna?",
            "Quanto tempo dedicate alla generazione di report?",
            "Come smistare le comunicazioni in ingresso (email, PEC)?",
            "Quali processi ripetitivi occupano piu tempo al team?",
            "Avete gia provato soluzioni AI? Se si, con quali risultati?",
        ]

        applicable = []
        for uc_code, scores in ATECO_MATRIX.items():
            score = scores.get(ateco_prefix, 0)
            if score > 50:
                uc = next((u for u in SEED_USE_CASES if u["code"] == uc_code), None)
                if uc:
                    applicable.append({"code": uc_code, "name": uc["name"], "fit_score": score})

        return {
            "pain_points": pain_points.get(ateco_prefix, ["Pain point da esplorare durante la call"]),
            "candidate_use_cases": sorted(applicable, key=lambda x: x["fit_score"], reverse=True),
            "discovery_questions": discovery_questions,
            "suggested_bundle": self._suggest_bundle(ateco_prefix),
        }

    # ── Helpers ────────────────────────────────────────

    async def _get_matrix(self, use_case_id: uuid.UUID) -> list[dict]:
        result = await self.db.execute(
            select(AtecoUseCaseMatrix).where(AtecoUseCaseMatrix.use_case_id == use_case_id)
        )
        return [{"ateco_code": m.ateco_code, "fit_score": m.fit_score} for m in result.scalars().all()]

    def _uc_to_dict(self, uc: EleviaUseCase, matrix: list[dict]) -> dict:
        return {
            "id": str(uc.id),
            "code": uc.code,
            "name": uc.name,
            "description": uc.description,
            "is_active": uc.is_active,
            "ateco_matrix": matrix,
        }
