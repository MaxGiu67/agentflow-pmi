<!-- Generato da /dev-sprint fase 5 — 2026-03-22 -->
# CLAUDE.md

## Project Overview
- **Nome**: AgentFlow PMI (MVP: ContaBot)
- **Vision**: Primo agente contabile AI per PMI italiane — sincronizza fatture dal cassetto fiscale, categorizza con learning, registra in partita doppia, prevede il cash flow. Da ContaBot a piattaforma multi-agente SaaS.
- **Stack**: Python 3.12 + FastAPI, React + TypeScript + Tailwind, Odoo CE 18 + OCA l10n-italy, PostgreSQL 16, Redis, Celery
- **Database**: PostgreSQL applicativo (FastAPI, 18 tabelle) + PostgreSQL Odoo per tenant (multi-database)
- **Deploy**: AWS eu-south-1 (Milano), Docker Compose, GitHub Actions CI/CD

## Architecture Decisions
- ADR-001: Python over Node.js — ecosistema OCR/ML + compatibilità Odoo
- ADR-002: Odoo headless come engine contabile — 80+ moduli IT già testati, partita doppia pronta
- ADR-003: No LLM API per categorizzazione — hybrid rules + scikit-learn (costi, privacy)
- ADR-004: FiscoAPI + A-Cube per integrazioni fiscali — cassetto fiscale + SDI + Open Banking
- ADR-005: Multi-database per multi-tenancy — isolamento GDPR totale
- ADR-006: A-Cube provider unico SDI + Open Banking — un contratto, REST OpenAPI 3.0

## Coding Conventions
- **File naming**: snake_case per Python, kebab-case per config
- **Component naming**: PascalCase per React, snake_case per Python modules
- **Variable naming**: snake_case Python, camelCase TypeScript
- **DB naming**: snake_case per tabelle e colonne
- **API naming**: /api/v1/kebab-case (es. /expenses, /bank-accounts, /withholding-taxes)
- **Test naming**: test_nome.py per unit, test_nome_integration.py per integration

## Patterns to Follow
- Repository Pattern per accesso DB (SQLAlchemy)
- Service Layer per business logic (modules/*/service.py)
- Adapter Pattern per servizi esterni (adapters/*.py — FiscoAPI, A-Cube, Odoo, OCR)
- Event-Driven Agent Pattern (Redis pub/sub: invoice.downloaded → parsed → categorized → journal.entry.created)
- Pydantic Models per validazione input/output (modules/*/schemas.py)
- Middleware per auth JWT, tenant resolution, rate limiting

## Forbidden Patterns
- NO direct DB access da router (delega a service)
- NO console.log/print in produzione (usa structured logging)
- NO `Any` in Python type hints (usa tipi espliciti)
- NO password/secret/token in codice sorgente (usa env vars + AES-256)
- NO query SQL inline (usa SQLAlchemy ORM)
- NO business logic nei router (delega a service)
- NO cache per dati critici (scritture contabili, saldi Odoo, F24, CU)

## Test Patterns
- **Framework**: pytest 8.x + pytest-asyncio + httpx (TestClient) + factory-boy + Playwright
- **Directory**: `api/modules/*/\_\_tests\_\_/` per unit, `tests/integration/` per API, `tests/e2e/` per Playwright
- **Naming**: `test_[modulo].py` per unit, `test_[modulo]_integration.py` per integration
- **Factory**: `tests/factories/` con factory-boy + Faker(it_IT)
- **Coverage target**: unit 80% (CI gate 70%), integration 60% (CI gate 50%), E2E critical paths
- **AC mapping**: ogni AC (DATO-QUANDO-ALLORA) ha almeno 1 test case
- **Fixtures chiave**: db_session, redis_client, tenant, owner_user, auth_client, sample_invoice, odoo_mock

## Sprint Context
- **Sprint corrente**: Sprint 1 — Autenticazione e Contabilità Base
- **Objective**: Registrazione, login, SPID/CIE, piano dei conti personalizzato
- **Stories in sprint**: US-01, US-02, US-03, US-12
- **SP Sprint**: 24 / 24
- **Comando**: `/dev-implement US-01`

## Key Specs References
- Vision: `specs/01-vision.md`
- PRD: `specs/02-prd.md`
- Stories: `specs/03-user-stories.md`
- Tech Spec: `specs/04-tech-spec.md`
- Sprint Plan: `specs/05-sprint-plan.md`
- DB Schema: `specs/database/schema.md`
- Wireframes: `specs/ux/wireframes.md`
- Test Strategy: `specs/testing/test-strategy.md`

## MCP Server (Debug & Test)
- Server MCP locale: `mcp-server/server.py` — auto-generato, espone DB + 111 endpoint + chatbot test
- Generatore: `python3 mcp-server/generate_mcp.py` — legge modelli SQLAlchemy + router FastAPI
- **REGOLA**: Dopo aver aggiunto/modificato endpoint o modelli DB, eseguire il generatore
- Configurato in Claude Code settings come `agentflow-db`

## Rules
1. Implementa una story alla volta
2. Ogni AC deve avere almeno 1 test
3. Formato AC: DATO-QUANDO-ALLORA
4. Non procedere alla story successiva finche tutti i test della corrente non passano
5. Aggiorna `specs/_status.md` dopo ogni story completata
6. Segui i pattern sopra — se devi deviare, documenta il motivo
7. Dopo modifiche a modelli DB o endpoint API, eseguire `python3 mcp-server/generate_mcp.py`
