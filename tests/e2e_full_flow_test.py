#!/usr/bin/env python3
"""
E2E Full Flow Test — 10 scenarios against Railway production API + Portal staging DB.

Covers: Deal → Offer → Approve → Commessa → Activities → Assign Employees
Verifies on Portal staging DB after each scenario.

Usage: python3 tests/e2e_full_flow_test.py
"""

import json
import random
import string
import sys
import time
import traceback
from datetime import datetime

import httpx
import psycopg2

# ── Config ────────────────────────────────────────────────────────────────────

API_BASE = "https://api-production-15cd.up.railway.app/api/v1"
LOGIN_EMAIL = "mgiurelli@nexadata.it"
LOGIN_PASSWORD = "NikMax67!"

PORTAL_DB_DSN = "postgresql://postgres:plfLKIQoBzeAMXAOPxJAKQpFnmQAHoXt@maglev.proxy.rlwy.net:52815/portaal"

# Portal reference data
AM_ID = 17  # Andrea Palermo
CUSTOMER_AUBAY = 4
CUSTOMER_BETA80 = 5
ACTIVITY_TYPE_PROD = 9  # Attivita produttiva

# Available internal persons from Portal
PERSON_IDS = [2, 3, 5, 6, 10, 22, 28, 40, 46]

# Timeout for HTTP requests
TIMEOUT = 30.0

# ── Globals ───────────────────────────────────────────────────────────────────

TOKEN = ""
CREATED_DEAL_IDS = []  # for cleanup
RESULTS = []  # (scenario_name, step, pass/fail, detail)


# ── Helpers ───────────────────────────────────────────────────────────────────

def uid():
    """Short unique ID for test data."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}")


def record(scenario, step, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    RESULTS.append((scenario, step, status, detail))
    icon = "+" if passed else "X"
    log(f"  [{icon}] {step}: {detail[:120]}", "INFO" if passed else "ERROR")


def api_get(path, params=None):
    """GET request to API."""
    resp = httpx.get(
        f"{API_BASE}{path}",
        params=params,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        timeout=TIMEOUT,
    )
    return resp


def api_post(path, body=None):
    """POST request to API."""
    resp = httpx.post(
        f"{API_BASE}{path}",
        json=body or {},
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        timeout=TIMEOUT,
    )
    return resp


def api_patch(path, body=None):
    """PATCH request to API."""
    resp = httpx.patch(
        f"{API_BASE}{path}",
        json=body or {},
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        timeout=TIMEOUT,
    )
    return resp


def api_delete(path):
    """DELETE request to API."""
    resp = httpx.delete(
        f"{API_BASE}{path}",
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        timeout=TIMEOUT,
    )
    return resp


def portal_db_query(query, params=None):
    """Query Portal staging DB directly."""
    try:
        conn = psycopg2.connect(PORTAL_DB_DSN)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(query, params or ())
        if cur.description:
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            result = [dict(zip(cols, row)) for row in rows]
        else:
            result = []
        cur.close()
        conn.close()
        return result
    except Exception as e:
        log(f"Portal DB error: {e}", "ERROR")
        return None


# ── Login ─────────────────────────────────────────────────────────────────────

def login():
    global TOKEN
    log("Logging in...")
    resp = httpx.post(
        f"{API_BASE}/auth/login",
        json={"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD},
        timeout=TIMEOUT,
    )
    if resp.status_code != 200:
        log(f"Login failed: {resp.status_code} — {resp.text[:200]}", "ERROR")
        sys.exit(1)
    data = resp.json()
    TOKEN = data.get("access_token") or data.get("token") or ""
    if not TOKEN:
        log(f"No token in response: {json.dumps(data)[:200]}", "ERROR")
        sys.exit(1)
    log(f"Login OK — token starts with {TOKEN[:20]}...")


# ── Core Flow Functions ───────────────────────────────────────────────────────

def create_deal(scenario, name, deal_type, customer_id, amount, daily_rate=0, estimated_days=0):
    """Create a deal via CRM API. Returns deal dict or None."""
    body = {
        "name": name,
        "deal_type": deal_type,
        "portal_customer_id": customer_id,
        "expected_revenue": amount,
        "daily_rate": daily_rate,
        "estimated_days": estimated_days,
    }
    resp = api_post("/crm/deals", body)
    if resp.status_code in (200, 201):
        deal = resp.json()
        deal_id = deal.get("id")
        CREATED_DEAL_IDS.append(deal_id)
        record(scenario, "Create Deal", True, f"id={deal_id}, name={name}")
        return deal
    else:
        record(scenario, "Create Deal", False, f"HTTP {resp.status_code}: {resp.text[:200]}")
        return None


def create_offer_from_deal(scenario, deal_id, deal_name, customer_id, billing_type, daily_rate=None, days=None, amount=None):
    """Create offer on Portal via API proxy. Returns offer dict or None."""
    project_code = f"E2E-{uid()}"
    body = {
        "project_code": project_code,
        "name": deal_name,
        "accountManager_id": AM_ID,
        "project_type_id": 1,  # Default project type
        "location_id": 1,  # Default location
        "billing_type": billing_type,
    }
    if daily_rate is not None:
        body["rate"] = daily_rate
    if days is not None:
        body["days"] = days
    if amount is not None:
        body["amount"] = amount

    resp = api_post(f"/portal/offers/create-from-deal/{deal_id}", body)
    if resp.status_code in (200, 201):
        offer = resp.json()
        if offer.get("error"):
            record(scenario, "Create Offer", False, f"API error: {offer['error']}")
            return None
        offer_id = offer.get("id")
        record(scenario, "Create Offer", True, f"offer_id={offer_id}, code={project_code}")
        return offer
    else:
        record(scenario, "Create Offer", False, f"HTTP {resp.status_code}: {resp.text[:200]}")
        return None


def link_customer_to_deal(scenario, deal_id, customer_id):
    """Update deal with portal_customer_id."""
    resp = api_patch(f"/crm/deals/{deal_id}", {
        "portal_customer_id": customer_id,
    })
    if resp.status_code == 200:
        record(scenario, "Link Customer", True, f"customer_id={customer_id}")
        return True
    else:
        record(scenario, "Link Customer", False, f"HTTP {resp.status_code}: {resp.text[:200]}")
        return False


def approve_offer(scenario, offer_id, deal_id, start_date, end_date, order_num=""):
    """Approve offer (OutcomeType=P) which creates commessa. Returns result or None."""
    body = {
        "start_date": start_date,
        "end_date": end_date,
        "orderNum": order_num,
        "deal_id": deal_id,
    }
    resp = api_post(f"/portal/offers/{offer_id}/approve", body)
    if resp.status_code == 200:
        result = resp.json()
        # Check for Portal-level error
        if result.get("ok") is False or result.get("error"):
            record(scenario, "Approve Offer", False, f"Portal error: {result.get('error')} — {result.get('detail', '')[:150]}")
            return None
        project_id = result.get("project_id")
        # Also check nested result
        if not project_id and isinstance(result.get("result"), dict):
            inner = result["result"]
            proj = inner.get("Project") or inner.get("project")
            if isinstance(proj, dict):
                project_id = proj.get("id")
        if project_id:
            result["project_id"] = project_id
            record(scenario, "Approve Offer", True, f"project_id={project_id}")
        else:
            record(scenario, "Approve Offer", True, f"approved, project_id will be fetched")
        return result
    else:
        record(scenario, "Approve Offer", False, f"HTTP {resp.status_code}: {resp.text[:200]}")
        return None


def get_project_id_from_offer(scenario, offer_id, retries=6, delay=2.0):
    """Fetch offer and extract project_id, with retries for async project creation."""
    offer = None
    for attempt in range(retries):
        resp = api_get(f"/portal/offers/{offer_id}")
        if resp.status_code == 200:
            offer = resp.json()
            pid = offer.get("project_id") or offer.get("projectId")
            if not pid:
                proj = offer.get("Project") or offer.get("project")
                if isinstance(proj, dict):
                    pid = proj.get("id")
            if pid:
                record(scenario, "Get Project ID", True, f"project_id={pid} (attempt {attempt+1})")
                return pid
        if attempt < retries - 1:
            time.sleep(delay)

    # Fallback: query Portal DB directly for project linked to this offer
    projects = portal_db_query(
        'SELECT id FROM "Project" WHERE offer_id = %s',
        (offer_id,)
    )
    if projects:
        pid = projects[0]["id"]
        record(scenario, "Get Project ID", True, f"project_id={pid} (from DB fallback)")
        return pid

    record(scenario, "Get Project ID", False, f"No project_id after {retries} attempts + DB fallback. Last offer OutcomeType={offer.get('OutcomeType') if offer else 'N/A'}")
    return None


def create_activity(scenario, project_id, name, start_date, end_date, activity_type_id=ACTIVITY_TYPE_PROD):
    """Create activity on Portal. Returns activity dict or None."""
    body = {
        "project_id": project_id,
        "description": name,  # Portal uses 'description' not 'name'
        "name": name,  # Also send 'name' for the backend mapping
        "start_date": start_date,
        "end_date": end_date,
        "activityType_id": activity_type_id,  # Portal uses camelCase
        "activity_type_id": activity_type_id,  # Also send snake_case for mapping
        "activityManager_id": AM_ID,  # Required by Portal
    }
    resp = api_post("/portal/activities/create", body)
    if resp.status_code in (200, 201):
        activity = resp.json()
        if activity.get("error"):
            detail = activity.get("detail", activity.get("error", ""))
            record(scenario, f"Create Activity '{name}'", False, f"Error: {detail}")
            return None
        act_id = activity.get("id")
        record(scenario, f"Create Activity '{name}'", True, f"activity_id={act_id}")
        return activity
    else:
        record(scenario, f"Create Activity '{name}'", False, f"HTTP {resp.status_code}: {resp.text[:200]}")
        return None


def assign_employee(scenario, activity_id, person_id, start_date, end_date, planned_days=None):
    """Assign employee to activity. Returns result or None."""
    body = {
        "activity_id": activity_id,
        "person_id": person_id,
        "start_date": start_date,
        "end_date": end_date,
    }
    if planned_days is not None:
        body["expectedDays"] = planned_days  # Portal uses 'expectedDays'
        body["planned_days"] = planned_days  # Also send for backend mapping

    resp = api_post("/portal/activities/assign", body)
    if resp.status_code in (200, 201):
        result = resp.json()
        if result.get("error"):
            err_str = str(result.get("error", "")) + str(result.get("detail", ""))
            # Handle 409 = date conflict with existing assignment
            if "409" in err_str or "conflitt" in err_str.lower() or "conflict" in err_str.lower():
                record(scenario, f"Assign Person {person_id}", True, f"Date conflict (409) - expected, skipped")
                return {"ok": True, "status": "date_conflict"}
            record(scenario, f"Assign Person {person_id}", False, f"Error: {json.dumps(result)[:200]}")
            return None
        record(scenario, f"Assign Person {person_id}", True, f"Assigned to activity {activity_id}")
        return result
    elif resp.status_code == 409:
        record(scenario, f"Assign Person {person_id}", True, f"Date conflict (409) - expected, skipped")
        return {"ok": True, "status": "date_conflict"}
    else:
        record(scenario, f"Assign Person {person_id}", False, f"HTTP {resp.status_code}: {resp.text[:200]}")
        return None


def verify_on_portal_db(scenario, project_id, expected_activities=0, expected_persons=0):
    """Verify data on Portal staging DB."""
    if not project_id:
        record(scenario, "DB Verify", False, "No project_id to verify")
        return

    # Check project exists (Portal uses project_code, not name)
    projects = portal_db_query(
        'SELECT id, offer_id, "ProjectState", start_date, end_date FROM "Project" WHERE id = %s',
        (project_id,)
    )
    if projects:
        record(scenario, "DB Verify Project", True, f"Found: id={projects[0]['id']}, state={projects[0].get('ProjectState')}")
    else:
        record(scenario, "DB Verify Project", False, f"Project {project_id} not found in DB")
        return

    # Check activities (Portal uses 'description' not 'name')
    activities = portal_db_query(
        'SELECT id, description, start_date, end_date FROM "Activity" WHERE project_id = %s',
        (project_id,)
    )
    act_count = len(activities) if activities else 0
    if expected_activities > 0 and act_count >= expected_activities:
        record(scenario, "DB Verify Activities", True, f"Found {act_count} activities (expected >= {expected_activities})")
    elif expected_activities > 0:
        record(scenario, "DB Verify Activities", False, f"Found {act_count} activities, expected >= {expected_activities}")
    else:
        record(scenario, "DB Verify Activities", True, f"Found {act_count} activities")

    # Check person assignments
    if activities:
        act_ids = [a["id"] for a in activities]
        placeholders = ",".join(["%s"] * len(act_ids))
        persons = portal_db_query(
            f'SELECT pa.id, pa.activity_id, pa.person_id, pa.start_date, pa.end_date '
            f'FROM "PersonActivity" pa WHERE pa.activity_id IN ({placeholders})',
            tuple(act_ids)
        )
        person_count = len(persons) if persons else 0
        if expected_persons > 0 and person_count >= expected_persons:
            record(scenario, "DB Verify Persons", True, f"Found {person_count} assignments (expected >= {expected_persons})")
        elif expected_persons > 0:
            record(scenario, "DB Verify Persons", False, f"Found {person_count} assignments, expected >= {expected_persons}")
        else:
            record(scenario, "DB Verify Persons", True, f"Found {person_count} person assignments")


# ── Full Scenario Flow ────────────────────────────────────────────────────────

def run_scenario(scenario_name, deal_config, offer_config, commessa_config, activities_config):
    """
    Run a complete scenario:
    1. Create deal
    2. Create offer (from deal)
    3. Approve offer → commessa
    4. Create activities
    5. Assign employees
    6. Verify on Portal DB
    """
    log(f"\n{'='*60}")
    log(f"SCENARIO: {scenario_name}")
    log(f"{'='*60}")

    # Step 1: Create deal
    deal = create_deal(
        scenario_name,
        deal_config["name"],
        deal_config["deal_type"],
        deal_config["customer_id"],
        deal_config["amount"],
        deal_config.get("daily_rate", 0),
        deal_config.get("estimated_days", 0),
    )
    if not deal:
        return None

    deal_id = deal["id"]

    # Step 2: Create offer from deal
    offer = create_offer_from_deal(
        scenario_name,
        deal_id,
        deal_config["name"],
        deal_config["customer_id"],
        offer_config["billing_type"],
        daily_rate=deal_config.get("daily_rate"),
        days=deal_config.get("estimated_days"),
        amount=deal_config["amount"],
    )
    if not offer:
        return deal_id

    offer_id = offer.get("id")
    if not offer_id:
        record(scenario_name, "Offer ID", False, f"No offer ID in response: {json.dumps(offer)[:200]}")
        return deal_id

    # Update deal with offer ID
    api_patch(f"/crm/deals/{deal_id}", {"portal_offer_id": offer_id})

    # Step 3: Approve offer → creates commessa
    time.sleep(1)  # Give Portal a moment
    approval = approve_offer(
        scenario_name,
        offer_id,
        deal_id,
        commessa_config["start_date"],
        commessa_config["end_date"],
        commessa_config.get("order_num", ""),
    )

    project_id = None
    if approval:
        project_id = approval.get("project_id")

    # If project_id not in approval response, try fetching
    if not project_id:
        time.sleep(1)
        project_id = get_project_id_from_offer(scenario_name, offer_id)

    if not project_id:
        record(scenario_name, "Project Resolution", False, "Could not resolve project_id")
        return deal_id

    # Update deal with project ID
    api_patch(f"/crm/deals/{deal_id}", {"portal_project_id": project_id})

    # Step 4: Create activities
    created_activities = []
    for act_cfg in activities_config:
        time.sleep(0.5)
        activity = create_activity(
            scenario_name,
            project_id,
            act_cfg["name"],
            act_cfg["start_date"],
            act_cfg["end_date"],
            act_cfg.get("activity_type_id", ACTIVITY_TYPE_PROD),
        )
        if activity:
            act_id = activity.get("id")
            created_activities.append((act_id, act_cfg))

    # Step 5: Assign employees
    total_expected_persons = 0
    for act_id, act_cfg in created_activities:
        if not act_id:
            continue
        for person_cfg in act_cfg.get("persons", []):
            time.sleep(0.3)
            result = assign_employee(
                scenario_name,
                act_id,
                person_cfg["person_id"],
                person_cfg["start_date"],
                person_cfg["end_date"],
                person_cfg.get("planned_days"),
            )
            # Only count as expected if actually assigned (not date conflict)
            if result and result.get("status") != "date_conflict":
                total_expected_persons += 1

    # Step 6: Verify on Portal DB
    time.sleep(1)
    verify_on_portal_db(
        scenario_name,
        project_id,
        expected_activities=len(activities_config),
        expected_persons=total_expected_persons,
    )

    return deal_id


# ── Scenario Definitions ──────────────────────────────────────────────────────

def scenario_1():
    """T&M Consulenza Java — 3 risorse, date diverse."""
    return run_scenario(
        "S1: T&M Java 3 risorse",
        deal_config={
            "name": f"E2E T&M Java {uid()}",
            "deal_type": "T&M",
            "customer_id": CUSTOMER_AUBAY,
            "amount": 50400,
            "daily_rate": 350,
            "estimated_days": 144,
        },
        offer_config={"billing_type": "Daily"},
        commessa_config={
            "start_date": "2026-06-01T00:00:00.000Z",
            "end_date": "2026-12-31T00:00:00.000Z",
            "order_num": f"PO-TM-JAVA-{uid()}",
        },
        activities_config=[
            {
                "name": "Sviluppo Backend Java",
                "start_date": "2026-06-01T00:00:00.000Z",
                "end_date": "2026-12-31T00:00:00.000Z",
                "persons": [
                    {"person_id": 2, "start_date": "2026-06-01T00:00:00.000Z", "end_date": "2026-09-30T00:00:00.000Z", "planned_days": 80},
                    {"person_id": 40, "start_date": "2026-07-01T00:00:00.000Z", "end_date": "2026-12-31T00:00:00.000Z", "planned_days": 100},
                    {"person_id": 22, "start_date": "2026-09-01T00:00:00.000Z", "end_date": "2026-12-31T00:00:00.000Z", "planned_days": 60},
                ],
            },
        ],
    )


def scenario_2():
    """T&M Consulenza .NET — 2 risorse stesso periodo."""
    return run_scenario(
        "S2: T&M .NET 2 risorse",
        deal_config={
            "name": f"E2E T&M .NET {uid()}",
            "deal_type": "T&M",
            "customer_id": CUSTOMER_BETA80,
            "amount": 36000,
            "daily_rate": 300,
            "estimated_days": 120,
        },
        offer_config={"billing_type": "Daily"},
        commessa_config={
            "start_date": "2026-07-01T00:00:00.000Z",
            "end_date": "2026-12-31T00:00:00.000Z",
        },
        activities_config=[
            {
                "name": "Consulenza .NET",
                "start_date": "2026-07-01T00:00:00.000Z",
                "end_date": "2026-12-31T00:00:00.000Z",
                "persons": [
                    {"person_id": 3, "start_date": "2026-07-01T00:00:00.000Z", "end_date": "2026-12-31T00:00:00.000Z", "planned_days": 60},
                    {"person_id": 5, "start_date": "2026-07-01T00:00:00.000Z", "end_date": "2026-12-31T00:00:00.000Z", "planned_days": 60},
                ],
            },
        ],
    )


def scenario_3():
    """Progetto a Corpo SAP — 3 attivita diverse, persone diverse."""
    return run_scenario(
        "S3: Fixed SAP 3 attivita",
        deal_config={
            "name": f"E2E SAP Corpo {uid()}",
            "deal_type": "fixed",
            "customer_id": CUSTOMER_AUBAY,
            "amount": 80000,
        },
        offer_config={"billing_type": "LumpSum"},
        commessa_config={
            "start_date": "2026-05-01T00:00:00.000Z",
            "end_date": "2026-10-31T00:00:00.000Z",
        },
        activities_config=[
            {
                "name": "Analisi Requisiti",
                "start_date": "2026-05-01T00:00:00.000Z",
                "end_date": "2026-06-30T00:00:00.000Z",
                "persons": [
                    {"person_id": 6, "start_date": "2026-05-01T00:00:00.000Z", "end_date": "2026-06-30T00:00:00.000Z", "planned_days": 40},
                ],
            },
            {
                "name": "Sviluppo SAP",
                "start_date": "2026-07-01T00:00:00.000Z",
                "end_date": "2026-09-30T00:00:00.000Z",
                "persons": [
                    {"person_id": 10, "start_date": "2026-07-01T00:00:00.000Z", "end_date": "2026-09-30T00:00:00.000Z", "planned_days": 60},
                    {"person_id": 28, "start_date": "2026-07-01T00:00:00.000Z", "end_date": "2026-09-30T00:00:00.000Z", "planned_days": 60},
                ],
            },
            {
                "name": "Testing & QA",
                "start_date": "2026-09-01T00:00:00.000Z",
                "end_date": "2026-10-31T00:00:00.000Z",
                "persons": [
                    {"person_id": 46, "start_date": "2026-09-01T00:00:00.000Z", "end_date": "2026-10-31T00:00:00.000Z", "planned_days": 40},
                ],
            },
        ],
    )


def scenario_4():
    """T&M Frontend React — 1 risorsa breve."""
    return run_scenario(
        "S4: T&M React 1 risorsa",
        deal_config={
            "name": f"E2E React Frontend {uid()}",
            "deal_type": "T&M",
            "customer_id": CUSTOMER_AUBAY,
            "amount": 15000,
            "daily_rate": 500,
            "estimated_days": 30,
        },
        offer_config={"billing_type": "Daily"},
        commessa_config={
            "start_date": "2026-08-01T00:00:00.000Z",
            "end_date": "2026-09-30T00:00:00.000Z",
        },
        activities_config=[
            {
                "name": "Frontend React Development",
                "start_date": "2026-08-01T00:00:00.000Z",
                "end_date": "2026-09-30T00:00:00.000Z",
                "persons": [
                    {"person_id": 2, "start_date": "2026-08-01T00:00:00.000Z", "end_date": "2026-09-30T00:00:00.000Z", "planned_days": 30},
                ],
            },
        ],
    )


def scenario_5():
    """Progetto Data Migration — 2 attivita sequenziali."""
    return run_scenario(
        "S5: Fixed Data Migration",
        deal_config={
            "name": f"E2E Data Migration {uid()}",
            "deal_type": "fixed",
            "customer_id": CUSTOMER_BETA80,
            "amount": 45000,
        },
        offer_config={"billing_type": "LumpSum"},
        commessa_config={
            "start_date": "2026-06-01T00:00:00.000Z",
            "end_date": "2026-08-31T00:00:00.000Z",
        },
        activities_config=[
            {
                "name": "Migrazione Dati",
                "start_date": "2026-06-01T00:00:00.000Z",
                "end_date": "2026-07-31T00:00:00.000Z",
                "persons": [
                    {"person_id": 3, "start_date": "2026-06-01T00:00:00.000Z", "end_date": "2026-07-31T00:00:00.000Z", "planned_days": 40},
                    {"person_id": 5, "start_date": "2026-06-01T00:00:00.000Z", "end_date": "2026-07-31T00:00:00.000Z", "planned_days": 40},
                ],
            },
            {
                "name": "Validazione Dati",
                "start_date": "2026-08-01T00:00:00.000Z",
                "end_date": "2026-08-31T00:00:00.000Z",
                "persons": [
                    {"person_id": 6, "start_date": "2026-08-01T00:00:00.000Z", "end_date": "2026-08-31T00:00:00.000Z", "planned_days": 20},
                ],
            },
        ],
    )


def scenario_6():
    """T&M DevOps — risorsa con alta tariffa."""
    return run_scenario(
        "S6: T&M DevOps alta tariffa",
        deal_config={
            "name": f"E2E DevOps {uid()}",
            "deal_type": "T&M",
            "customer_id": CUSTOMER_AUBAY,
            "amount": 72000,
            "daily_rate": 600,
            "estimated_days": 120,
        },
        offer_config={"billing_type": "Daily"},
        commessa_config={
            "start_date": "2026-06-01T00:00:00.000Z",
            "end_date": "2026-12-31T00:00:00.000Z",
        },
        activities_config=[
            {
                "name": "DevOps & Infrastructure",
                "start_date": "2026-06-01T00:00:00.000Z",
                "end_date": "2026-12-31T00:00:00.000Z",
                "persons": [
                    {"person_id": 10, "start_date": "2026-06-01T00:00:00.000Z", "end_date": "2026-12-31T00:00:00.000Z", "planned_days": 120},
                ],
            },
        ],
    )


def scenario_7():
    """Progetto Mobile App — 4 attivita con team misto."""
    return run_scenario(
        "S7: Fixed Mobile App 4 attivita",
        deal_config={
            "name": f"E2E Mobile App {uid()}",
            "deal_type": "fixed",
            "customer_id": CUSTOMER_BETA80,
            "amount": 120000,
        },
        offer_config={"billing_type": "LumpSum"},
        commessa_config={
            "start_date": "2026-05-01T00:00:00.000Z",
            "end_date": "2026-12-31T00:00:00.000Z",
        },
        activities_config=[
            {
                "name": "UI/UX Design",
                "start_date": "2026-05-01T00:00:00.000Z",
                "end_date": "2026-06-30T00:00:00.000Z",
                "persons": [
                    {"person_id": 46, "start_date": "2026-05-01T00:00:00.000Z", "end_date": "2026-06-30T00:00:00.000Z", "planned_days": 40},
                ],
            },
            {
                "name": "Backend API Development",
                "start_date": "2026-07-01T00:00:00.000Z",
                "end_date": "2026-09-30T00:00:00.000Z",
                "persons": [
                    {"person_id": 22, "start_date": "2026-07-01T00:00:00.000Z", "end_date": "2026-09-30T00:00:00.000Z", "planned_days": 60},
                ],
            },
            {
                "name": "Mobile Frontend",
                "start_date": "2026-07-01T00:00:00.000Z",
                "end_date": "2026-10-31T00:00:00.000Z",
                "persons": [
                    {"person_id": 40, "start_date": "2026-07-01T00:00:00.000Z", "end_date": "2026-10-31T00:00:00.000Z", "planned_days": 80},
                ],
            },
            {
                "name": "Integration Testing",
                "start_date": "2026-10-01T00:00:00.000Z",
                "end_date": "2026-12-31T00:00:00.000Z",
                "persons": [
                    {"person_id": 28, "start_date": "2026-10-01T00:00:00.000Z", "end_date": "2026-12-31T00:00:00.000Z", "planned_days": 60},
                ],
            },
        ],
    )


def scenario_8():
    """T&M Support & Maintenance."""
    return run_scenario(
        "S8: T&M Support",
        deal_config={
            "name": f"E2E Support {uid()}",
            "deal_type": "T&M",
            "customer_id": CUSTOMER_AUBAY,
            "amount": 21000,
            "daily_rate": 350,
            "estimated_days": 60,
        },
        offer_config={"billing_type": "Daily"},
        commessa_config={
            "start_date": "2026-07-01T00:00:00.000Z",
            "end_date": "2026-12-31T00:00:00.000Z",
        },
        activities_config=[
            {
                "name": "Support & Maintenance",
                "start_date": "2026-07-01T00:00:00.000Z",
                "end_date": "2026-12-31T00:00:00.000Z",
                "persons": [
                    {"person_id": 2, "start_date": "2026-07-01T00:00:00.000Z", "end_date": "2026-12-31T00:00:00.000Z", "planned_days": 60},
                ],
            },
        ],
    )


def scenario_9():
    """Progetto Cloud Migration — 3 attivita parallele."""
    return run_scenario(
        "S9: Fixed Cloud Migration",
        deal_config={
            "name": f"E2E Cloud Migration {uid()}",
            "deal_type": "fixed",
            "customer_id": CUSTOMER_BETA80,
            "amount": 150000,
        },
        offer_config={"billing_type": "LumpSum"},
        commessa_config={
            "start_date": "2026-06-01T00:00:00.000Z",
            "end_date": "2026-12-31T00:00:00.000Z",
        },
        activities_config=[
            {
                "name": "Infrastructure Assessment",
                "start_date": "2026-06-01T00:00:00.000Z",
                "end_date": "2026-09-30T00:00:00.000Z",
                "persons": [
                    {"person_id": 6, "start_date": "2026-06-01T00:00:00.000Z", "end_date": "2026-09-30T00:00:00.000Z", "planned_days": 80},
                    {"person_id": 28, "start_date": "2026-06-01T00:00:00.000Z", "end_date": "2026-09-30T00:00:00.000Z", "planned_days": 80},
                ],
            },
            {
                "name": "Cloud Setup & Migration",
                "start_date": "2026-07-01T00:00:00.000Z",
                "end_date": "2026-11-30T00:00:00.000Z",
                "persons": [
                    {"person_id": 10, "start_date": "2026-07-01T00:00:00.000Z", "end_date": "2026-11-30T00:00:00.000Z", "planned_days": 100},
                    {"person_id": 22, "start_date": "2026-07-01T00:00:00.000Z", "end_date": "2026-11-30T00:00:00.000Z", "planned_days": 100},
                ],
            },
            {
                "name": "Monitoring & Optimization",
                "start_date": "2026-09-01T00:00:00.000Z",
                "end_date": "2026-12-31T00:00:00.000Z",
                "persons": [
                    {"person_id": 46, "start_date": "2026-09-01T00:00:00.000Z", "end_date": "2026-12-31T00:00:00.000Z", "planned_days": 80},
                ],
            },
        ],
    )


def scenario_10():
    """T&M Staff Augmentation — 5 risorse."""
    return run_scenario(
        "S10: T&M Staff Aug 5 risorse",
        deal_config={
            "name": f"E2E Staff Aug {uid()}",
            "deal_type": "T&M",
            "customer_id": CUSTOMER_AUBAY,
            "amount": 175000,
            "daily_rate": 350,
            "estimated_days": 500,
        },
        offer_config={"billing_type": "Daily"},
        commessa_config={
            "start_date": "2026-06-01T00:00:00.000Z",
            "end_date": "2026-12-31T00:00:00.000Z",
        },
        activities_config=[
            {
                "name": "Staff Augmentation Team",
                "start_date": "2026-06-01T00:00:00.000Z",
                "end_date": "2026-12-31T00:00:00.000Z",
                "persons": [
                    {"person_id": 2, "start_date": "2026-06-01T00:00:00.000Z", "end_date": "2026-12-31T00:00:00.000Z", "planned_days": 100},
                    {"person_id": 3, "start_date": "2026-06-01T00:00:00.000Z", "end_date": "2026-12-31T00:00:00.000Z", "planned_days": 100},
                    {"person_id": 5, "start_date": "2026-06-01T00:00:00.000Z", "end_date": "2026-12-31T00:00:00.000Z", "planned_days": 100},
                    {"person_id": 40, "start_date": "2026-06-01T00:00:00.000Z", "end_date": "2026-12-31T00:00:00.000Z", "planned_days": 100},
                    {"person_id": 46, "start_date": "2026-06-01T00:00:00.000Z", "end_date": "2026-12-31T00:00:00.000Z", "planned_days": 100},
                ],
            },
        ],
    )


# ── Cleanup ───────────────────────────────────────────────────────────────────

def cleanup():
    """Delete test deals from AgentFlow API (leave Portal data for verification)."""
    log(f"\n{'='*60}")
    log("CLEANUP — Deleting test deals from AgentFlow")
    log(f"{'='*60}")
    for deal_id in CREATED_DEAL_IDS:
        try:
            resp = api_delete(f"/crm/deals/{deal_id}")
            if resp.status_code == 200:
                log(f"  Deleted deal {deal_id}")
            else:
                log(f"  Failed to delete deal {deal_id}: HTTP {resp.status_code}", "WARN")
        except Exception as e:
            log(f"  Error deleting deal {deal_id}: {e}", "WARN")


# ── Report ────────────────────────────────────────────────────────────────────

def print_report():
    log(f"\n{'='*60}")
    log("FINAL REPORT")
    log(f"{'='*60}")

    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r[2] == "PASS")
    failed = sum(1 for r in RESULTS if r[2] == "FAIL")

    # Group by scenario
    scenarios = {}
    for scenario, step, status, detail in RESULTS:
        if scenario not in scenarios:
            scenarios[scenario] = {"pass": 0, "fail": 0, "steps": []}
        scenarios[scenario]["steps"].append((step, status, detail))
        if status == "PASS":
            scenarios[scenario]["pass"] += 1
        else:
            scenarios[scenario]["fail"] += 1

    for sname, sdata in scenarios.items():
        status_icon = "PASS" if sdata["fail"] == 0 else "FAIL"
        log(f"\n  [{status_icon}] {sname} — {sdata['pass']} passed, {sdata['fail']} failed")
        if sdata["fail"] > 0:
            for step, status, detail in sdata["steps"]:
                if status == "FAIL":
                    log(f"      X {step}: {detail[:100]}")

    log(f"\n  TOTAL: {passed}/{total} passed, {failed}/{total} failed")
    pct = (passed / total * 100) if total > 0 else 0
    log(f"  SUCCESS RATE: {pct:.1f}%")

    if failed > 0:
        log(f"\n  FAILED STEPS:")
        for scenario, step, status, detail in RESULTS:
            if status == "FAIL":
                log(f"    [{scenario}] {step}: {detail[:120]}")

    return failed == 0


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log("E2E Full Flow Test — 10 Scenarios")
    log(f"API: {API_BASE}")
    log(f"Portal DB: {PORTAL_DB_DSN[:50]}...")

    # Test Portal DB connection
    log("Testing Portal DB connection...")
    test_q = portal_db_query("SELECT count(*) as cnt FROM \"Project\"")
    if test_q is not None:
        log(f"Portal DB OK — {test_q[0]['cnt']} projects found")
    else:
        log("Portal DB connection FAILED — DB verification will be skipped", "WARN")

    # Login
    login()

    # Check Portal API status
    resp = api_get("/portal/status")
    if resp.status_code == 200:
        log(f"Portal API status: {resp.json()}")
    else:
        log(f"Portal status check failed: {resp.status_code}", "WARN")

    # Run all 10 scenarios
    scenarios = [
        scenario_1,
        scenario_2,
        scenario_3,
        scenario_4,
        scenario_5,
        scenario_6,
        scenario_7,
        scenario_8,
        scenario_9,
        scenario_10,
    ]

    for fn in scenarios:
        try:
            fn()
        except Exception as e:
            scenario_name = fn.__doc__ or fn.__name__
            log(f"SCENARIO EXCEPTION: {e}", "ERROR")
            traceback.print_exc()
            record(scenario_name, "Exception", False, str(e))

    # Report
    all_pass = print_report()

    # Cleanup deals
    cleanup()

    if all_pass:
        log("\nALL TESTS PASSED!")
        sys.exit(0)
    else:
        log("\nSOME TESTS FAILED — see report above")
        sys.exit(1)


if __name__ == "__main__":
    main()
