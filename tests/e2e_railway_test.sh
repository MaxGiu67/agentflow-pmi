#!/bin/bash
# ============================================================================
# E2E Test Suite MASSIVO against Railway production
# 200+ tests: Companies, Contacts, Deals, Stage moves, Activities, Orders,
#             Pipeline Templates, Analytics — ogni write verificato con GET
# ============================================================================

API="https://api-production-15cd.up.railway.app/api/v1"
PASS=0
FAIL=0
TOTAL=0
ERRORS=""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

check() {
    TOTAL=$((TOTAL+1))
    local desc="$1"
    local condition="$2"
    if [ "$condition" = "true" ]; then
        PASS=$((PASS+1))
        echo -e "  ${GREEN}✓${NC} $TOTAL. $desc"
    else
        FAIL=$((FAIL+1))
        echo -e "  ${RED}✗${NC} $TOTAL. $desc"
        ERRORS="$ERRORS\n  $TOTAL. $desc"
    fi
}

jq_val() {
    echo "$1" | python3 -c "import sys,json; d=json.load(sys.stdin); print($2)" 2>/dev/null
}

echo "============================================================"
echo "  E2E TEST SUITE MASSIVO — Railway Production"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "  API: $API"
echo "============================================================"
echo ""

# ═══════════════════════════════════════════════════════════════════
# 1. LOGIN
# ═══════════════════════════════════════════════════════════════════
echo "━━━ 1. LOGIN ━━━"
LOGIN=$(curl -s "$API/auth/login" -H "Content-Type: application/json" \
    -d '{"email":"mgiurelli@taal.it","password":"zyjdez-zedwi8-mexpeS"}')
TOKEN=$(jq_val "$LOGIN" "d.get('access_token','')")
AUTH="Authorization: Bearer $TOKEN"
check "Login restituisce token" "$([ -n "$TOKEN" ] && [ ${#TOKEN} -gt 20 ] && echo true || echo false)"

# Verify token works by calling an endpoint that requires auth
ME_TEST=$(curl -s -o /dev/null -w "%{http_code}" "$API/crm/deals?limit=1" -H "$AUTH")
check "Token valido (GET /crm/deals)" "$([ "$ME_TEST" = "200" ] && echo true || echo false)"

# Invalid login
BAD_LOGIN=$(curl -s -o /dev/null -w "%{http_code}" "$API/auth/login" -H "Content-Type: application/json" \
    -d '{"email":"fake@fake.it","password":"wrong"}')
check "Login errato → 401" "$([ "$BAD_LOGIN" = "401" ] && echo true || echo false)"

echo ""

# ═══════════════════════════════════════════════════════════════════
# 2. COMPANIES — CRUD + verifica
# ═══════════════════════════════════════════════════════════════════
echo "━━━ 2. COMPANIES ━━━"

# 2.1 Create company A
C1=$(curl -s -X POST "$API/crm/companies" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"name":"E2E Acme SRL","vat":"11122233344","city":"Roma","sector":"IT","website":"https://acme.it"}')
C1_ID=$(jq_val "$C1" "d.get('id','')")
C1_NAME=$(jq_val "$C1" "d.get('name','')")
check "Create company A (Acme)" "$([ "$C1_NAME" = "E2E Acme SRL" ] && echo true || echo false)"

# 2.2 Verify company A via GET by ID
C1_GET=$(curl -s "$API/crm/companies/$C1_ID" -H "$AUTH")
C1_GET_NAME=$(jq_val "$C1_GET" "d.get('name','')")
C1_GET_VAT=$(jq_val "$C1_GET" "d.get('vat','')")
C1_GET_CITY=$(jq_val "$C1_GET" "d.get('city','')")
C1_GET_SECTOR=$(jq_val "$C1_GET" "d.get('sector','')")
check "GET company A: name OK" "$([ "$C1_GET_NAME" = "E2E Acme SRL" ] && echo true || echo false)"
check "GET company A: vat OK" "$([ "$C1_GET_VAT" = "11122233344" ] && echo true || echo false)"
check "GET company A: city OK" "$([ "$C1_GET_CITY" = "Roma" ] && echo true || echo false)"
check "GET company A: sector OK" "$([ "$C1_GET_SECTOR" = "IT" ] && echo true || echo false)"

# 2.3 Create company B
C2=$(curl -s -X POST "$API/crm/companies" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"name":"E2E Beta Corp","vat":"55566677788","city":"Milano","sector":"Finance"}')
C2_ID=$(jq_val "$C2" "d.get('id','')")
C2_NAME=$(jq_val "$C2" "d.get('name','')")
check "Create company B (Beta)" "$([ "$C2_NAME" = "E2E Beta Corp" ] && echo true || echo false)"

# 2.4 Create company C (minimal data)
C3=$(curl -s -X POST "$API/crm/companies" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"name":"E2E Gamma Minimal"}')
C3_ID=$(jq_val "$C3" "d.get('id','')")
check "Create company C (minimal)" "$([ -n "$C3_ID" ] && echo true || echo false)"

# 2.5 List companies
COMPANIES=$(curl -s "$API/crm/companies" -H "$AUTH")
C_TOTAL=$(jq_val "$COMPANIES" "d.get('total',0)")
check "List companies (total >= 3)" "$([ "$C_TOTAL" -ge 3 ] 2>/dev/null && echo true || echo false)"

# 2.6 Search company by name
SEARCH=$(curl -s "$API/crm/companies?search=E2E%20Acme" -H "$AUTH")
S_TOTAL=$(jq_val "$SEARCH" "d.get('total',0)")
check "Search 'E2E Acme' → trova risultati" "$([ "$S_TOTAL" -ge 1 ] 2>/dev/null && echo true || echo false)"

# 2.7 Search non-existent company
SEARCH_EMPTY=$(curl -s "$API/crm/companies?search=ZZZZZZNOTEXIST" -H "$AUTH")
SE_TOTAL=$(jq_val "$SEARCH_EMPTY" "d.get('total',0)")
check "Search inesistente → 0 risultati" "$([ "$SE_TOTAL" = "0" ] && echo true || echo false)"

# 2.8 Update company A
C1_UPD=$(curl -s -X PATCH "$API/crm/companies/$C1_ID" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"city":"Firenze","sector":"Software"}')
C1_UPD_CITY=$(jq_val "$C1_UPD" "d.get('city','')")
C1_UPD_SECTOR=$(jq_val "$C1_UPD" "d.get('sector','')")
check "Update company A city → Firenze" "$([ "$C1_UPD_CITY" = "Firenze" ] && echo true || echo false)"
check "Update company A sector → Software" "$([ "$C1_UPD_SECTOR" = "Software" ] && echo true || echo false)"

# 2.9 Verify update persists via GET
C1_VERIFY=$(curl -s "$API/crm/companies/$C1_ID" -H "$AUTH")
C1_V_CITY=$(jq_val "$C1_VERIFY" "d.get('city','')")
check "Verify update persists (GET)" "$([ "$C1_V_CITY" = "Firenze" ] && echo true || echo false)"

# 2.10 Update company name
C2_UPD=$(curl -s -X PATCH "$API/crm/companies/$C2_ID" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"name":"E2E Beta Corp Updated"}')
C2_UPD_NAME=$(jq_val "$C2_UPD" "d.get('name','')")
check "Update company B name" "$([ "$C2_UPD_NAME" = "E2E Beta Corp Updated" ] && echo true || echo false)"

echo ""

# ═══════════════════════════════════════════════════════════════════
# 3. CONTACTS — CRUD + company association
# ═══════════════════════════════════════════════════════════════════
echo "━━━ 3. CONTACTS ━━━"

# 3.1 Create contact with company A
CT1=$(curl -s -X POST "$API/crm/contacts" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"name\":\"E2E Acme SRL\",\"company_id\":\"$C1_ID\",\"contact_name\":\"Marco Rossi\",\"contact_role\":\"CTO\",\"email\":\"marco.rossi@acme.it\",\"phone\":\"+39 333 1111111\"}")
CT1_ID=$(jq_val "$CT1" "d.get('id','')")
CT1_CN=$(jq_val "$CT1" "d.get('contact_name','')")
CT1_CR=$(jq_val "$CT1" "d.get('contact_role','')")
CT1_CID=$(jq_val "$CT1" "d.get('company_id','')")
CT1_EMAIL=$(jq_val "$CT1" "d.get('email','')")
check "Create contact 1 (Marco)" "$([ -n "$CT1_ID" ] && echo true || echo false)"
check "Contact 1 contact_name saved" "$([ "$CT1_CN" = "Marco Rossi" ] && echo true || echo false)"
check "Contact 1 contact_role saved" "$([ "$CT1_CR" = "CTO" ] && echo true || echo false)"
check "Contact 1 company_id saved" "$([ "$CT1_CID" = "$C1_ID" ] && echo true || echo false)"
check "Contact 1 email saved" "$([ "$CT1_EMAIL" = "marco.rossi@acme.it" ] && echo true || echo false)"

# 3.2 Create contact 2 same company
CT2=$(curl -s -X POST "$API/crm/contacts" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"name\":\"E2E Acme SRL\",\"company_id\":\"$C1_ID\",\"contact_name\":\"Luca Bianchi\",\"contact_role\":\"Sales Director\",\"email\":\"luca@acme.it\"}")
CT2_ID=$(jq_val "$CT2" "d.get('id','')")
CT2_CID=$(jq_val "$CT2" "d.get('company_id','')")
check "Create contact 2 (Luca) same company" "$([ -n "$CT2_ID" ] && echo true || echo false)"
check "Contact 2 company_id = company A" "$([ "$CT2_CID" = "$C1_ID" ] && echo true || echo false)"

# 3.3 Create contact with company B
CT3=$(curl -s -X POST "$API/crm/contacts" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"name\":\"E2E Beta Corp Updated\",\"company_id\":\"$C2_ID\",\"contact_name\":\"Anna Verdi\",\"contact_role\":\"CEO\",\"email\":\"anna@beta.it\"}")
CT3_ID=$(jq_val "$CT3" "d.get('id','')")
CT3_CID=$(jq_val "$CT3" "d.get('company_id','')")
check "Create contact 3 (Anna) company B" "$([ -n "$CT3_ID" ] && echo true || echo false)"
check "Contact 3 company_id = company B" "$([ "$CT3_CID" = "$C2_ID" ] && echo true || echo false)"

# 3.4 Create contact without company
CT4=$(curl -s -X POST "$API/crm/contacts" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"name":"E2E Freelancer","contact_name":"Paolo Neri","email":"paolo@freelance.it","type":"prospect"}')
CT4_ID=$(jq_val "$CT4" "d.get('id','')")
CT4_CID=$(jq_val "$CT4" "d.get('company_id','')")
CT4_TYPE=$(jq_val "$CT4" "d.get('type','')")
check "Create contact 4 (no company)" "$([ -n "$CT4_ID" ] && echo true || echo false)"
check "Contact 4 company_id = None" "$([ "$CT4_CID" = "None" ] && echo true || echo false)"
check "Contact 4 type = prospect" "$([ "$CT4_TYPE" = "prospect" ] && echo true || echo false)"

# 3.5 Create contact 5 with phone only
CT5=$(curl -s -X POST "$API/crm/contacts" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"name\":\"E2E Phone Only\",\"company_id\":\"$C1_ID\",\"contact_name\":\"Sara Gialli\",\"phone\":\"+39 346 9999999\"}")
CT5_ID=$(jq_val "$CT5" "d.get('id','')")
check "Create contact 5 (phone only)" "$([ -n "$CT5_ID" ] && echo true || echo false)"

# 3.6 List all contacts
CONTACTS=$(curl -s "$API/crm/contacts" -H "$AUTH")
CT_TOTAL=$(jq_val "$CONTACTS" "d.get('total',0)")
check "List contacts (>= 5)" "$([ "$CT_TOTAL" -ge 5 ] 2>/dev/null && echo true || echo false)"

# 3.7 Verify contact 1 in list has correct company_id
CT1_LIST_CID=$(echo "$CONTACTS" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for c in d.get('contacts',[]):
    if c.get('id')=='$CT1_ID':
        print(c.get('company_id',''))
        break
else:
    print('')
" 2>/dev/null)
check "Contact 1 in list has correct company_id" "$([ "$CT1_LIST_CID" = "$C1_ID" ] && echo true || echo false)"

# 3.8 Verify contact 4 in list has null company_id
CT4_LIST_CID=$(jq_val "$CONTACTS" "
next((c.get('company_id') for c in d.get('contacts',[]) if c.get('id')=='$CT4_ID'), 'NOTFOUND')
")
check "Contact 4 in list has null company_id" "$([ "$CT4_LIST_CID" = "None" ] && echo true || echo false)"

# 3.9 Update contact email
CT1_UPD=$(curl -s -X PATCH "$API/crm/contacts/$CT1_ID" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"email":"marco.rossi.new@acme.it","phone":"+39 333 2222222"}')
CT1_UPD_EMAIL=$(jq_val "$CT1_UPD" "d.get('email','')")
CT1_UPD_PHONE=$(jq_val "$CT1_UPD" "d.get('phone','')")
check "Update contact 1 email" "$([ "$CT1_UPD_EMAIL" = "marco.rossi.new@acme.it" ] && echo true || echo false)"
check "Update contact 1 phone" "$([ "$CT1_UPD_PHONE" = "+39 333 2222222" ] && echo true || echo false)"

# 3.10 Update contact role
CT2_UPD=$(curl -s -X PATCH "$API/crm/contacts/$CT2_ID" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"contact_role":"VP Sales"}')
CT2_UPD_ROLE=$(jq_val "$CT2_UPD" "d.get('contact_role','')")
check "Update contact 2 role" "$([ "$CT2_UPD_ROLE" = "VP Sales" ] && echo true || echo false)"

# 3.11 Search contacts
SEARCH_CT=$(curl -s "$API/crm/contacts?search=marco" -H "$AUTH")
SCT_TOTAL=$(jq_val "$SEARCH_CT" "d.get('total',0)")
check "Search contacts 'marco' → risultati" "$([ "$SCT_TOTAL" -ge 1 ] 2>/dev/null && echo true || echo false)"

# 3.12 Delete contact 5
DEL5_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$API/crm/contacts/$CT5_ID" -H "$AUTH")
check "Delete contact 5 → 200" "$([ "$DEL5_STATUS" = "200" ] && echo true || echo false)"

# 3.13 Verify contact 5 deleted from list
CONTACTS_AFTER=$(curl -s "$API/crm/contacts" -H "$AUTH")
CT5_FOUND=$(jq_val "$CONTACTS_AFTER" "
any(c.get('id')=='$CT5_ID' for c in d.get('contacts',[]))
")
check "Contact 5 non in lista dopo delete" "$([ "$CT5_FOUND" = "False" ] && echo true || echo false)"

echo ""

# ═══════════════════════════════════════════════════════════════════
# 4. PIPELINE TEMPLATES
# ═══════════════════════════════════════════════════════════════════
echo "━━━ 4. PIPELINE TEMPLATES ━━━"

TEMPLATES=$(curl -s "$API/pipeline-templates" -H "$AUTH")
T_COUNT=$(jq_val "$TEMPLATES" "len(d)")
check "Pipeline templates count = 3" "$([ "$T_COUNT" = "3" ] && echo true || echo false)"

# Get each template
VD_ID=$(jq_val "$TEMPLATES" "next((t['id'] for t in d if t['code']=='vendita_diretta'), '')")
PC_ID=$(jq_val "$TEMPLATES" "next((t['id'] for t in d if t['code']=='progetto_corpo'), '')")
SS_ID=$(jq_val "$TEMPLATES" "next((t['id'] for t in d if t['code']=='social_selling'), '')")
check "Template Vendita Diretta exists" "$([ -n "$VD_ID" ] && echo true || echo false)"
check "Template Progetto Corpo exists" "$([ -n "$PC_ID" ] && echo true || echo false)"
check "Template Social Selling exists" "$([ -n "$SS_ID" ] && echo true || echo false)"

# Verify template names
VD_NAME=$(jq_val "$TEMPLATES" "next((t['name'] for t in d if t['code']=='vendita_diretta'), '')")
PC_NAME=$(jq_val "$TEMPLATES" "next((t['name'] for t in d if t['code']=='progetto_corpo'), '')")
SS_NAME=$(jq_val "$TEMPLATES" "next((t['name'] for t in d if t['code']=='social_selling'), '')")
check "VD name = Vendita Diretta" "$(echo "$VD_NAME" | grep -qi "vendita" && echo true || echo false)"
check "PC name contains Corpo" "$(echo "$PC_NAME" | grep -qi "corpo" && echo true || echo false)"
check "SS name = Social Selling" "$(echo "$SS_NAME" | grep -qi "social" && echo true || echo false)"

# Verify templates have stages
VD_STAGES=$(jq_val "$TEMPLATES" "len(next((t.get('stages',[]) for t in d if t['code']=='vendita_diretta'), []))")
check "VD template has stages (>= 3)" "$([ "$VD_STAGES" -ge 3 ] 2>/dev/null && echo true || echo false)"

echo ""

# ═══════════════════════════════════════════════════════════════════
# 5. PIPELINE STAGES
# ═══════════════════════════════════════════════════════════════════
echo "━━━ 5. PIPELINE STAGES ━━━"

STAGES=$(curl -s "$API/crm/pipeline/stages" -H "$AUTH")
STAGE_COUNT=$(jq_val "$STAGES" "len(d)")
check "Stages exist (>= 6)" "$([ "$STAGE_COUNT" -ge 6 ] 2>/dev/null && echo true || echo false)"

# Get specific stages for later use
STAGE_FIRST_ID=$(jq_val "$STAGES" "d[0]['id']")
STAGE_FIRST_NAME=$(jq_val "$STAGES" "d[0]['name']")
STAGE_SECOND_ID=$(jq_val "$STAGES" "d[1]['id']")
STAGE_SECOND_NAME=$(jq_val "$STAGES" "d[1]['name']")

# Find won and lost stages
WON_STAGE_ID=$(jq_val "$STAGES" "next((s['id'] for s in d if s.get('is_won')), '')")
LOST_STAGE_ID=$(jq_val "$STAGES" "next((s['id'] for s in d if s.get('is_lost')), '')")
ORDINE_STAGE_ID=$(jq_val "$STAGES" "next((s['id'] for s in d if 'Ordine' in s.get('name','')), '')")
check "Won stage exists" "$([ -n "$WON_STAGE_ID" ] && echo true || echo false)"
check "Lost stage exists" "$([ -n "$LOST_STAGE_ID" ] && echo true || echo false)"
check "Ordine Ricevuto stage exists" "$([ -n "$ORDINE_STAGE_ID" ] && echo true || echo false)"

# Verify stages have probability
FIRST_PROB=$(jq_val "$STAGES" "d[0].get('probability_default',0)")
check "First stage has probability" "$(python3 -c "print('true' if float('$FIRST_PROB') >= 0 else 'false')" 2>/dev/null)"

echo ""

# ═══════════════════════════════════════════════════════════════════
# 6. DEALS — CRUD per ogni tipo
# ═══════════════════════════════════════════════════════════════════
echo "━━━ 6. DEALS — Creazione per tipo ━━━"

# 6.1 Create deal T&M (Consulenza)
D1=$(curl -s -X POST "$API/crm/deals" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"name\":\"E2E Consulenza Java Spring\",\"deal_type\":\"T&M\",\"expected_revenue\":45000,\"daily_rate\":600,\"estimated_days\":75,\"contact_id\":\"$CT1_ID\",\"company_id\":\"$C1_ID\",\"pipeline_template_id\":\"$VD_ID\",\"technology\":\"Java, Spring Boot, Angular\"}")
D1_ID=$(jq_val "$D1" "d.get('id','')")
D1_TYPE=$(jq_val "$D1" "d.get('deal_type','')")
D1_REV=$(jq_val "$D1" "d.get('expected_revenue',0)")
D1_PTID=$(jq_val "$D1" "d.get('pipeline_template_id','')")
D1_CID=$(jq_val "$D1" "d.get('company_id','')")
D1_TECH=$(jq_val "$D1" "d.get('technology','')")
D1_STAGE=$(jq_val "$D1" "d.get('stage','')")
check "Create deal T&M" "$([ "$D1_TYPE" = "T&M" ] && echo true || echo false)"
check "Deal T&M revenue = 45000" "$(python3 -c "print('true' if float('$D1_REV') == 45000 else 'false')" 2>/dev/null)"
check "Deal T&M pipeline_template_id saved" "$([ "$D1_PTID" = "$VD_ID" ] && echo true || echo false)"
check "Deal T&M company_id saved" "$([ "$D1_CID" = "$C1_ID" ] && echo true || echo false)"
check "Deal T&M technology saved" "$(echo "$D1_TECH" | grep -q "Java" && echo true || echo false)"
check "Deal T&M has initial stage" "$([ -n "$D1_STAGE" ] && echo true || echo false)"

# 6.2 Verify deal T&M via GET
D1_GET=$(curl -s "$API/crm/deals/$D1_ID" -H "$AUTH")
D1G_NAME=$(jq_val "$D1_GET" "d.get('name','')")
D1G_TYPE=$(jq_val "$D1_GET" "d.get('deal_type','')")
D1G_REV=$(jq_val "$D1_GET" "d.get('expected_revenue',0)")
D1G_TECH=$(jq_val "$D1_GET" "d.get('technology','')")
D1G_PTID=$(jq_val "$D1_GET" "d.get('pipeline_template_id','')")
D1G_CID=$(jq_val "$D1_GET" "d.get('company_id','')")
check "GET deal T&M: name OK" "$([ "$D1G_NAME" = "E2E Consulenza Java Spring" ] && echo true || echo false)"
check "GET deal T&M: deal_type OK" "$([ "$D1G_TYPE" = "T&M" ] && echo true || echo false)"
check "GET deal T&M: revenue OK" "$(python3 -c "print('true' if float('$D1G_REV') == 45000 else 'false')" 2>/dev/null)"
check "GET deal T&M: technology OK" "$(echo "$D1G_TECH" | grep -q "Spring" && echo true || echo false)"
check "GET deal T&M: pipeline_template_id OK" "$([ "$D1G_PTID" = "$VD_ID" ] && echo true || echo false)"
check "GET deal T&M: company_id OK" "$([ "$D1G_CID" = "$C1_ID" ] && echo true || echo false)"

# 6.3 Create deal Corpo (Fixed price)
D2=$(curl -s -X POST "$API/crm/deals" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"name\":\"E2E Progetto Gestionale ERP\",\"deal_type\":\"fixed\",\"expected_revenue\":80000,\"contact_id\":\"$CT3_ID\",\"company_id\":\"$C2_ID\",\"pipeline_template_id\":\"$PC_ID\",\"technology\":\"Python, React\"}")
D2_ID=$(jq_val "$D2" "d.get('id','')")
D2_TYPE=$(jq_val "$D2" "d.get('deal_type','')")
D2_REV=$(jq_val "$D2" "d.get('expected_revenue',0)")
D2_PTID=$(jq_val "$D2" "d.get('pipeline_template_id','')")
check "Create deal Corpo" "$([ "$D2_TYPE" = "fixed" ] && echo true || echo false)"
check "Deal Corpo revenue = 80000" "$(python3 -c "print('true' if float('$D2_REV') == 80000 else 'false')" 2>/dev/null)"
check "Deal Corpo pipeline_template_id" "$([ "$D2_PTID" = "$PC_ID" ] && echo true || echo false)"

# 6.4 Create deal Elevia (Social Selling)
D3=$(curl -s -X POST "$API/crm/deals" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"name\":\"E2E Elevia AI Metallurgia\",\"deal_type\":\"spot\",\"expected_revenue\":18000,\"pipeline_template_id\":\"$SS_ID\",\"company_id\":\"$C1_ID\"}")
D3_ID=$(jq_val "$D3" "d.get('id','')")
D3_PTID=$(jq_val "$D3" "d.get('pipeline_template_id','')")
D3_CID=$(jq_val "$D3" "d.get('company_id','')")
check "Create deal Elevia" "$([ -n "$D3_ID" ] && echo true || echo false)"
check "Deal Elevia pipeline = social_selling" "$([ "$D3_PTID" = "$SS_ID" ] && echo true || echo false)"
check "Deal Elevia company_id" "$([ "$D3_CID" = "$C1_ID" ] && echo true || echo false)"

# 6.5 Create deal hardware
D4=$(curl -s -X POST "$API/crm/deals" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"name\":\"E2E Server Dell PowerEdge\",\"deal_type\":\"hardware\",\"expected_revenue\":12000,\"company_id\":\"$C2_ID\",\"pipeline_template_id\":\"$VD_ID\"}")
D4_ID=$(jq_val "$D4" "d.get('id','')")
D4_TYPE=$(jq_val "$D4" "d.get('deal_type','')")
check "Create deal hardware" "$([ "$D4_TYPE" = "hardware" ] && echo true || echo false)"

# 6.6 Create deal minimal (no optional fields)
D5=$(curl -s -X POST "$API/crm/deals" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"name":"E2E Deal Minimo"}')
D5_ID=$(jq_val "$D5" "d.get('id','')")
D5_REV=$(jq_val "$D5" "d.get('expected_revenue',0)")
check "Create deal minimal" "$([ -n "$D5_ID" ] && echo true || echo false)"
check "Deal minimal revenue = 0" "$([ "$D5_REV" = "0" ] && echo true || echo false)"

# 6.7 Create deal with daily_rate + estimated_days
D6=$(curl -s -X POST "$API/crm/deals" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"name\":\"E2E Consulenza DevOps\",\"deal_type\":\"T&M\",\"daily_rate\":700,\"estimated_days\":40,\"expected_revenue\":28000,\"contact_id\":\"$CT2_ID\",\"company_id\":\"$C1_ID\",\"pipeline_template_id\":\"$VD_ID\"}")
D6_ID=$(jq_val "$D6" "d.get('id','')")
D6_DR=$(jq_val "$D6" "d.get('daily_rate',0)")
D6_ED=$(jq_val "$D6" "d.get('estimated_days',0)")
check "Create deal DevOps" "$([ -n "$D6_ID" ] && echo true || echo false)"
check "Deal DevOps daily_rate = 700" "$([ "$D6_DR" = "700" ] && echo true || echo false)"
check "Deal DevOps estimated_days = 40" "$([ "$D6_ED" = "40" ] && echo true || echo false)"

echo ""
echo "━━━ 6b. DEALS — List + Filter ━━━"

# 6.8 List all deals
DEALS=$(curl -s "$API/crm/deals" -H "$AUTH")
D_TOTAL=$(jq_val "$DEALS" "d.get('total',0)")
check "List deals (>= 6)" "$([ "$D_TOTAL" -ge 6 ] 2>/dev/null && echo true || echo false)"

# 6.9 Verify deal fields in list
D1_IN_LIST=$(jq_val "$DEALS" "
next((dl for dl in d.get('deals',[]) if dl.get('id')=='$D1_ID'), None) is not None
")
check "Deal T&M found in list" "$([ "$D1_IN_LIST" = "True" ] && echo true || echo false)"

# 6.10 Deal list has client_name
D1_CLIENT=$(jq_val "$DEALS" "
next((dl.get('client_name','') for dl in d.get('deals',[]) if dl.get('id')=='$D1_ID'), '')
")
check "Deal T&M has client_name in list" "$([ -n "$D1_CLIENT" ] && echo true || echo false)"

# 6.11 Filter deals by type T&M
DEALS_TM=$(curl -s "$API/crm/deals?deal_type=T%26M" -H "$AUTH")
DTM_TOTAL=$(jq_val "$DEALS_TM" "d.get('total',0)")
check "Filter deals T&M (>= 2)" "$([ "$DTM_TOTAL" -ge 2 ] 2>/dev/null && echo true || echo false)"

# 6.12 All filtered deals are T&M
ALL_TM=$(jq_val "$DEALS_TM" "all(dl.get('deal_type')=='T&M' for dl in d.get('deals',[]))")
check "All T&M deals have correct type" "$([ "$ALL_TM" = "True" ] && echo true || echo false)"

# 6.13 Filter deals by type fixed
DEALS_FX=$(curl -s "$API/crm/deals?deal_type=fixed" -H "$AUTH")
DFX_TOTAL=$(jq_val "$DEALS_FX" "d.get('total',0)")
check "Filter deals fixed (>= 1)" "$([ "$DFX_TOTAL" -ge 1 ] 2>/dev/null && echo true || echo false)"

echo ""
echo "━━━ 6c. DEALS — Update ━━━"

# 6.14 Update deal revenue
D1_U=$(curl -s -X PATCH "$API/crm/deals/$D1_ID" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"expected_revenue":50000}')
D1U_REV=$(jq_val "$D1_U" "d.get('expected_revenue',0)")
check "Update deal T&M revenue → 50000" "$([ "$D1U_REV" = "50000.0" ] || [ "$D1U_REV" = "50000" ] && echo true || echo false)"

# 6.15 Verify update persists
D1_VERIFY=$(curl -s "$API/crm/deals/$D1_ID" -H "$AUTH")
D1V_REV=$(jq_val "$D1_VERIFY" "d.get('expected_revenue',0)")
check "Verify update persists (GET)" "$(python3 -c "print('true' if float('$D1V_REV') == 50000 else 'false')" 2>/dev/null)"

# 6.16 Update deal name
D2_U=$(curl -s -X PATCH "$API/crm/deals/$D2_ID" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"name":"E2E Progetto ERP v2"}')
D2U_NAME=$(jq_val "$D2_U" "d.get('name','')")
check "Update deal Corpo name" "$([ "$D2U_NAME" = "E2E Progetto ERP v2" ] && echo true || echo false)"

# 6.17 Update deal technology
D1_U2=$(curl -s -X PATCH "$API/crm/deals/$D1_ID" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"technology":"Java, Spring Boot, Angular, Docker"}')
D1U2_TECH=$(jq_val "$D1_U2" "d.get('technology','')")
check "Update deal technology" "$(echo "$D1U2_TECH" | grep -q "Docker" && echo true || echo false)"

# 6.18 Update deal daily_rate
D6_U=$(curl -s -X PATCH "$API/crm/deals/$D6_ID" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"daily_rate":750,"estimated_days":45}')
D6U_DR=$(jq_val "$D6_U" "d.get('daily_rate',0)")
D6U_ED=$(jq_val "$D6_U" "d.get('estimated_days',0)")
check "Update deal daily_rate" "$([ "$D6U_DR" = "750.0" ] || [ "$D6U_DR" = "750" ] && echo true || echo false)"
check "Update deal estimated_days" "$([ "$D6U_ED" = "45.0" ] || [ "$D6U_ED" = "45" ] && echo true || echo false)"

echo ""

# ═══════════════════════════════════════════════════════════════════
# 7. STAGE MOVES — cambio fase + activity log
# ═══════════════════════════════════════════════════════════════════
echo "━━━ 7. STAGE MOVES ━━━"

# 7.1 Move deal D1 from stage 1 to stage 2
D1_MOVE1=$(curl -s -X PATCH "$API/crm/deals/$D1_ID" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"stage_id\":\"$STAGE_SECOND_ID\"}")
D1M1_STAGE=$(jq_val "$D1_MOVE1" "d.get('stage','')")
D1M1_PROB=$(jq_val "$D1_MOVE1" "d.get('probability',0)")
check "Move D1 to $STAGE_SECOND_NAME" "$([ "$D1M1_STAGE" = "$STAGE_SECOND_NAME" ] && echo true || echo false)"
check "Probability auto-updated" "$(python3 -c "print('true' if float('$D1M1_PROB') > 0 else 'false')" 2>/dev/null)"

# 7.2 Verify stage persists
sleep 1
D1_AFTER=$(curl -s "$API/crm/deals/$D1_ID" -H "$AUTH")
D1A_STAGE=$(jq_val "$D1_AFTER" "d.get('stage','')")
check "Stage persists after GET" "$([ "$D1A_STAGE" = "$STAGE_SECOND_NAME" ] && echo true || echo false)"

# 7.3 Verify activity log created for stage move
ACTS_D1=$(curl -s "$API/crm/activities?deal_id=$D1_ID" -H "$AUTH")
ACT1_COUNT=$(jq_val "$ACTS_D1" "len(d) if isinstance(d,list) else len(d.get('activities',d.get('items',[])))")
check "Activity log created for stage move" "$([ "$ACT1_COUNT" -ge 1 ] 2>/dev/null && echo true || echo false)"

# 7.4 Verify activity has correct subject
ACT1_HAS_SPOSTATO=$(echo "$ACTS_D1" | python3 -c "
import sys,json
d=json.load(sys.stdin)
acts = d if isinstance(d,list) else d.get('activities',d.get('items',[]))
found = any('spostato' in a.get('subject','') for a in acts)
print('true' if found else 'false')
" 2>/dev/null)
check "Activity subject contains 'spostato'" "$([ "$ACT1_HAS_SPOSTATO" = "true" ] && echo true || echo false)"

# 7.5 Get Qualificato stage
QUAL_STAGE_ID=$(jq_val "$STAGES" "next((s['id'] for s in d if 'Qualificato' == s.get('name','')), '')")
if [ -n "$QUAL_STAGE_ID" ] && [ "$QUAL_STAGE_ID" != "" ]; then
    # Move to Qualificato
    D1_MOVE2=$(curl -s -X PATCH "$API/crm/deals/$D1_ID" -H "$AUTH" -H "Content-Type: application/json" \
        -d "{\"stage_id\":\"$QUAL_STAGE_ID\"}")
    D1M2_STAGE=$(jq_val "$D1_MOVE2" "d.get('stage','')")
    check "Move D1 to Qualificato" "$([ "$D1M2_STAGE" = "Qualificato" ] && echo true || echo false)"
fi

# 7.6 Get Proposta Inviata stage
PROP_STAGE_ID=$(jq_val "$STAGES" "next((s['id'] for s in d if 'Proposta' in s.get('name','')), '')")
if [ -n "$PROP_STAGE_ID" ] && [ "$PROP_STAGE_ID" != "" ]; then
    D1_MOVE3=$(curl -s -X PATCH "$API/crm/deals/$D1_ID" -H "$AUTH" -H "Content-Type: application/json" \
        -d "{\"stage_id\":\"$PROP_STAGE_ID\"}")
    D1M3_STAGE=$(jq_val "$D1_MOVE3" "d.get('stage','')")
    D1M3_PROB=$(jq_val "$D1_MOVE3" "d.get('probability',0)")
    check "Move D1 to Proposta Inviata" "$(echo "$D1M3_STAGE" | grep -q "Proposta" && echo true || echo false)"
    check "Proposta probability = 50%" "$(python3 -c "print('true' if float('$D1M3_PROB') == 50.0 else 'false')" 2>/dev/null)"
fi

# 7.7 Move deal D4 to Won
D4_WON=$(curl -s -X PATCH "$API/crm/deals/$D4_ID" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"stage_id\":\"$WON_STAGE_ID\"}")
D4W_STAGE=$(jq_val "$D4_WON" "d.get('stage','')")
D4W_PROB=$(jq_val "$D4_WON" "d.get('probability',0)")
check "Move D4 to Won" "$(echo "$D4W_STAGE" | grep -qi "confermato" && echo true || echo false)"
check "Won probability = 100%" "$(python3 -c "print('true' if float('$D4W_PROB') == 100.0 else 'false')" 2>/dev/null)"

# 7.8 Move deal D5 to Lost
D5_LOST=$(curl -s -X PATCH "$API/crm/deals/$D5_ID" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"stage_id\":\"$LOST_STAGE_ID\"}")
D5L_STAGE=$(jq_val "$D5_LOST" "d.get('stage','')")
D5L_PROB=$(jq_val "$D5_LOST" "d.get('probability',0)")
check "Move D5 to Lost" "$(echo "$D5L_STAGE" | grep -qi "perso" && echo true || echo false)"
check "Lost probability = 0%" "$(python3 -c "print('true' if float('$D5L_PROB') == 0.0 else 'false')" 2>/dev/null)"

# 7.9 Count all activity logs for D1 (should have multiple moves)
sleep 1
ACTS_D1_ALL=$(curl -s "$API/crm/activities?deal_id=$D1_ID" -H "$AUTH")
ACT_D1_TOTAL=$(jq_val "$ACTS_D1_ALL" "len(d) if isinstance(d,list) else len(d.get('activities',[]))")
check "D1 has multiple activity logs (>= 2)" "$([ "$ACT_D1_TOTAL" -ge 2 ] 2>/dev/null && echo true || echo false)"

echo ""

# ═══════════════════════════════════════════════════════════════════
# 8. ACTIVITIES — CRUD tutti i tipi
# ═══════════════════════════════════════════════════════════════════
echo "━━━ 8. ACTIVITIES ━━━"

# 8.1 Create call activity
A1=$(curl -s -X POST "$API/crm/activities" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"deal_id\":\"$D1_ID\",\"contact_id\":\"$CT1_ID\",\"type\":\"call\",\"subject\":\"E2E Prima chiamata qualifica\",\"description\":\"Discusso budget 50k, timeline 6 mesi\",\"status\":\"completed\"}")
A1_ID=$(jq_val "$A1" "d.get('id','')")
A1_TYPE=$(jq_val "$A1" "d.get('type','')")
A1_STATUS=$(jq_val "$A1" "d.get('status','')")
check "Create call activity" "$([ "$A1_TYPE" = "call" ] && echo true || echo false)"
check "Call status = completed" "$([ "$A1_STATUS" = "completed" ] && echo true || echo false)"

# 8.2 Create meeting activity
A2=$(curl -s -X POST "$API/crm/activities" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"deal_id\":\"$D1_ID\",\"contact_id\":\"$CT1_ID\",\"type\":\"meeting\",\"subject\":\"E2E Demo prodotto\",\"description\":\"Presentazione AgentFlow PMI\",\"status\":\"completed\"}")
A2_TYPE=$(jq_val "$A2" "d.get('type','')")
check "Create meeting activity" "$([ "$A2_TYPE" = "meeting" ] && echo true || echo false)"

# 8.3 Create note
A3=$(curl -s -X POST "$API/crm/activities" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"deal_id\":\"$D1_ID\",\"type\":\"note\",\"subject\":\"E2E Nota interna\",\"description\":\"Il cliente ha documentazione dispersa — segnale cross-sell Elevia\"}")
A3_TYPE=$(jq_val "$A3" "d.get('type','')")
A3_STATUS=$(jq_val "$A3" "d.get('status','')")
check "Create note activity" "$([ "$A3_TYPE" = "note" ] && echo true || echo false)"
check "Note default status = planned" "$([ "$A3_STATUS" = "planned" ] && echo true || echo false)"

# 8.4 Create email activity
A4=$(curl -s -X POST "$API/crm/activities" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"deal_id\":\"$D1_ID\",\"type\":\"email\",\"subject\":\"E2E Follow-up email proposta\",\"status\":\"completed\"}")
A4_TYPE=$(jq_val "$A4" "d.get('type','')")
check "Create email activity" "$([ "$A4_TYPE" = "email" ] && echo true || echo false)"

# 8.5 Create task activity
A5=$(curl -s -X POST "$API/crm/activities" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"deal_id\":\"$D2_ID\",\"type\":\"task\",\"subject\":\"E2E Preparare offerta tecnica\",\"status\":\"planned\"}")
A5_TYPE=$(jq_val "$A5" "d.get('type','')")
A5_ID=$(jq_val "$A5" "d.get('id','')")
check "Create task activity" "$([ "$A5_TYPE" = "task" ] && echo true || echo false)"

# 8.6 Create activity on different deal
A6=$(curl -s -X POST "$API/crm/activities" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"deal_id\":\"$D3_ID\",\"type\":\"call\",\"subject\":\"E2E Chiamata prospect Elevia\",\"description\":\"Discusso use case AI per metallurgia\",\"status\":\"completed\"}")
A6_TYPE=$(jq_val "$A6" "d.get('type','')")
check "Create activity on deal Elevia" "$([ "$A6_TYPE" = "call" ] && echo true || echo false)"

# 8.7 Create activity with contact only (no deal)
A7=$(curl -s -X POST "$API/crm/activities" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"contact_id\":\"$CT3_ID\",\"type\":\"call\",\"subject\":\"E2E Chiamata cold contact\",\"status\":\"completed\"}")
A7_ID=$(jq_val "$A7" "d.get('id','')")
check "Create activity contact-only" "$([ -n "$A7_ID" ] && echo true || echo false)"

# 8.8 List activities for deal D1
ACTS_LIST=$(curl -s "$API/crm/activities?deal_id=$D1_ID" -H "$AUTH")
ACTS_COUNT=$(jq_val "$ACTS_LIST" "len(d) if isinstance(d,list) else 0")
check "List activities D1 (>= 5)" "$([ "$ACTS_COUNT" -ge 5 ] 2>/dev/null && echo true || echo false)"

# 8.9 List activities for deal D2
ACTS_D2=$(curl -s "$API/crm/activities?deal_id=$D2_ID" -H "$AUTH")
ACTS_D2_COUNT=$(jq_val "$ACTS_D2" "len(d) if isinstance(d,list) else 0")
check "List activities D2 (>= 1)" "$([ "$ACTS_D2_COUNT" -ge 1 ] 2>/dev/null && echo true || echo false)"

# 8.10 List activities for contact
ACTS_CT=$(curl -s "$API/crm/activities?contact_id=$CT3_ID" -H "$AUTH")
ACTS_CT_COUNT=$(jq_val "$ACTS_CT" "len(d) if isinstance(d,list) else 0")
check "List activities contact 3 (>= 1)" "$([ "$ACTS_CT_COUNT" -ge 1 ] 2>/dev/null && echo true || echo false)"

# 8.11 Complete planned task
COMPLETE=$(curl -s -X POST "$API/crm/activities/$A5_ID/complete" -H "$AUTH" -H "Content-Type: application/json")
COMP_STATUS=$(jq_val "$COMPLETE" "d.get('status','')")
COMP_AT=$(jq_val "$COMPLETE" "d.get('completed_at','')")
check "Complete task → status=completed" "$([ "$COMP_STATUS" = "completed" ] && echo true || echo false)"
check "Complete task → completed_at set" "$([ -n "$COMP_AT" ] && [ "$COMP_AT" != "None" ] && echo true || echo false)"

echo ""

# ═══════════════════════════════════════════════════════════════════
# 9. ORDERS — Register + Confirm
# ═══════════════════════════════════════════════════════════════════
echo "━━━ 9. ORDERS ━━━"

# 9.1 Register order on D2 (PO)
ORD1=$(curl -s -X POST "$API/crm/deals/$D2_ID/order" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"order_type":"po","order_reference":"PO-E2E-001","order_notes":"Test order PO"}')
ORD1_STATUS=$(jq_val "$ORD1" "d.get('status','')")
ORD1_OT=$(jq_val "$ORD1" "d.get('order_type','')")
check "Register order PO" "$([ "$ORD1_STATUS" = "registered" ] && echo true || echo false)"
check "Order type = po" "$([ "$ORD1_OT" = "po" ] && echo true || echo false)"

# 9.2 Verify deal moved to "Ordine Ricevuto"
D2_AFTER_ORD=$(curl -s "$API/crm/deals/$D2_ID" -H "$AUTH")
D2AO_STAGE=$(jq_val "$D2_AFTER_ORD" "d.get('stage','')")
D2AO_OT=$(jq_val "$D2_AFTER_ORD" "d.get('order_type','')")
D2AO_OR=$(jq_val "$D2_AFTER_ORD" "d.get('order_reference','')")
check "Deal moved to Ordine Ricevuto" "$(echo "$D2AO_STAGE" | grep -qi "ordine" && echo true || echo false)"
check "Deal order_type saved" "$([ "$D2AO_OT" = "po" ] && echo true || echo false)"
check "Deal order_reference saved" "$([ "$D2AO_OR" = "PO-E2E-001" ] && echo true || echo false)"

# 9.3 List pending orders
PENDING=$(curl -s "$API/crm/orders/pending" -H "$AUTH")
PEND_TOTAL=$(jq_val "$PENDING" "d.get('total',0)")
check "Pending orders (>= 1)" "$([ "$PEND_TOTAL" -ge 1 ] 2>/dev/null && echo true || echo false)"

# 9.4 Confirm order
CONF=$(curl -s -X POST "$API/crm/deals/$D2_ID/order/confirm" -H "$AUTH" -H "Content-Type: application/json")
CONF_STATUS=$(jq_val "$CONF" "d.get('status','')")
check "Confirm order → confirmed" "$([ "$CONF_STATUS" = "confirmed" ] && echo true || echo false)"

# 9.5 Verify deal moved to Won (Confermato)
D2_AFTER_CONF=$(curl -s "$API/crm/deals/$D2_ID" -H "$AUTH")
D2AC_STAGE=$(jq_val "$D2_AFTER_CONF" "d.get('stage','')")
D2AC_PROB=$(jq_val "$D2_AFTER_CONF" "d.get('probability',0)")
check "Deal moved to Confermato (Won)" "$(echo "$D2AC_STAGE" | grep -qi "confermato" && echo true || echo false)"
check "Deal probability = 100%" "$(python3 -c "print('true' if float('$D2AC_PROB') == 100.0 else 'false')" 2>/dev/null)"

# 9.6 Register order on D3 (email type)
ORD2=$(curl -s -X POST "$API/crm/deals/$D3_ID/order" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"order_type":"email","order_reference":"Email conferma 15/03","order_notes":"Confermato via email dal CEO"}')
ORD2_STATUS=$(jq_val "$ORD2" "d.get('status','')")
check "Register order email type" "$([ "$ORD2_STATUS" = "registered" ] && echo true || echo false)"

# 9.7 Order on non-existent deal → 404
ORD_BAD=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/crm/deals/00000000-0000-0000-0000-000000000000/order" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"order_type":"po"}')
check "Order on fake deal → 404" "$([ "$ORD_BAD" = "404" ] && echo true || echo false)"

echo ""

# ═══════════════════════════════════════════════════════════════════
# 10. PIPELINE ANALYTICS
# ═══════════════════════════════════════════════════════════════════
echo "━━━ 10. PIPELINE ANALYTICS ━━━"

# 10.1 Pipeline summary
SUMMARY=$(curl -s "$API/crm/pipeline/summary" -H "$AUTH")
SUM_TOTAL=$(jq_val "$SUMMARY" "d.get('total_deals',0)")
SUM_VALUE=$(jq_val "$SUMMARY" "d.get('total_value',0)")
SUM_STAGES=$(jq_val "$SUMMARY" "len(d.get('by_stage',{}))")
check "Pipeline summary total_deals (>= 6)" "$([ "$SUM_TOTAL" -ge 6 ] 2>/dev/null && echo true || echo false)"
check "Pipeline summary total_value > 0" "$(python3 -c "print('true' if float('$SUM_VALUE') > 0 else 'false')" 2>/dev/null)"
check "Pipeline summary has by_stage" "$([ "$SUM_STAGES" -ge 1 ] 2>/dev/null && echo true || echo false)"

# 10.2 Pipeline analytics
ANALYTICS=$(curl -s "$API/crm/pipeline/analytics" -H "$AUTH")
AN_WEIGHTED=$(jq_val "$ANALYTICS" "d.get('weighted_pipeline_value',0)")
AN_WON=$(jq_val "$ANALYTICS" "d.get('won_count',0)")
AN_LOST=$(jq_val "$ANALYTICS" "d.get('lost_count',0)")
AN_TOTAL=$(jq_val "$ANALYTICS" "d.get('total_deals',0)")
AN_CONV=$(jq_val "$ANALYTICS" "len(d.get('conversion_by_stage',[]))")
check "Analytics weighted_pipeline_value" "$(python3 -c "print('true' if float('$AN_WEIGHTED') >= 0 else 'false')" 2>/dev/null)"
check "Analytics won_count (>= 1)" "$([ "$AN_WON" -ge 1 ] 2>/dev/null && echo true || echo false)"
check "Analytics lost_count (>= 1)" "$([ "$AN_LOST" -ge 1 ] 2>/dev/null && echo true || echo false)"
check "Analytics total_deals (>= 6)" "$([ "$AN_TOTAL" -ge 6 ] 2>/dev/null && echo true || echo false)"
check "Analytics conversion_by_stage" "$([ "$AN_CONV" -ge 1 ] 2>/dev/null && echo true || echo false)"

# 10.3 Won deals list
WON_DEALS=$(curl -s "$API/crm/deals/won" -H "$AUTH")
WON_TOTAL=$(jq_val "$WON_DEALS" "d.get('total',0)")
check "Won deals list (>= 1)" "$([ "$WON_TOTAL" -ge 1 ] 2>/dev/null && echo true || echo false)"

echo ""

# ═══════════════════════════════════════════════════════════════════
# 11. CROSS-VALIDATION — dati coerenti tra endpoint
# ═══════════════════════════════════════════════════════════════════
echo "━━━ 11. CROSS-VALIDATION ━━━"

# 11.1 Deal count in summary = deal count in list
LIST_TOTAL=$(jq_val "$(curl -s "$API/crm/deals?limit=500" -H "$AUTH")" "d.get('total',0)")
SUM_TOTAL2=$(jq_val "$(curl -s "$API/crm/pipeline/summary" -H "$AUTH")" "d.get('total_deals',0)")
check "Deal count: list == summary" "$([ "$LIST_TOTAL" = "$SUM_TOTAL2" ] && echo true || echo false)"

# 11.2 Company GET includes contacts
C1_WITH_CT=$(curl -s "$API/crm/companies/$C1_ID" -H "$AUTH")
C1_CT_COUNT=$(jq_val "$C1_WITH_CT" "len(d.get('contacts',[]))")
check "Company GET includes contacts (>= 2)" "$([ "$C1_CT_COUNT" -ge 2 ] 2>/dev/null && echo true || echo false)"

# 11.3 Deal GET has correct stage after moves
D1_FINAL=$(curl -s "$API/crm/deals/$D1_ID" -H "$AUTH")
D1F_STAGE_ID=$(jq_val "$D1_FINAL" "d.get('stage_id','')")
check "Deal D1 stage_id is set" "$([ -n "$D1F_STAGE_ID" ] && echo true || echo false)"

# 11.4 Activities count for D1 matches expectation (stage moves + manual)
ACTS_D1_FINAL=$(curl -s "$API/crm/activities?deal_id=$D1_ID" -H "$AUTH")
ACTS_D1_FINAL_COUNT=$(jq_val "$ACTS_D1_FINAL" "len(d) if isinstance(d,list) else 0")
check "D1 total activities (>= 7)" "$([ "$ACTS_D1_FINAL_COUNT" -ge 7 ] 2>/dev/null && echo true || echo false)"

# 11.5 Won deal D4 has 100% probability
D4_FINAL=$(curl -s "$API/crm/deals/$D4_ID" -H "$AUTH")
D4F_PROB=$(jq_val "$D4_FINAL" "d.get('probability',0)")
check "Won deal D4 probability = 100%" "$(python3 -c "print('true' if float('$D4F_PROB') == 100.0 else 'false')" 2>/dev/null)"

# 11.6 Lost deal D5 has 0% probability
D5_FINAL=$(curl -s "$API/crm/deals/$D5_ID" -H "$AUTH")
D5F_PROB=$(jq_val "$D5_FINAL" "d.get('probability',0)")
check "Lost deal D5 probability = 0%" "$(python3 -c "print('true' if float('$D5F_PROB') == 0.0 else 'false')" 2>/dev/null)"

# 11.7 Deal D2 has order fields after registration
D2_FINAL=$(curl -s "$API/crm/deals/$D2_ID" -H "$AUTH")
D2F_OT=$(jq_val "$D2_FINAL" "d.get('order_type','')")
D2F_OR=$(jq_val "$D2_FINAL" "d.get('order_reference','')")
D2F_OD=$(jq_val "$D2_FINAL" "d.get('order_date','')")
check "D2 order_type persists" "$([ "$D2F_OT" = "po" ] && echo true || echo false)"
check "D2 order_reference persists" "$([ "$D2F_OR" = "PO-E2E-001" ] && echo true || echo false)"
check "D2 order_date set" "$([ -n "$D2F_OD" ] && [ "$D2F_OD" != "" ] && echo true || echo false)"

echo ""

# ═══════════════════════════════════════════════════════════════════
# 12. ADDITIONAL DEAL SCENARIOS
# ═══════════════════════════════════════════════════════════════════
echo "━━━ 12. ADDITIONAL DEAL SCENARIOS ━━━"

# 12.1 Create multiple deals same company
DA=$(curl -s -X POST "$API/crm/deals" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"name\":\"E2E Multi Deal A\",\"deal_type\":\"T&M\",\"expected_revenue\":10000,\"company_id\":\"$C1_ID\"}")
DA_ID=$(jq_val "$DA" "d.get('id','')")
DB=$(curl -s -X POST "$API/crm/deals" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"name\":\"E2E Multi Deal B\",\"deal_type\":\"fixed\",\"expected_revenue\":20000,\"company_id\":\"$C1_ID\"}")
DB_ID=$(jq_val "$DB" "d.get('id','')")
DC=$(curl -s -X POST "$API/crm/deals" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"name\":\"E2E Multi Deal C\",\"deal_type\":\"spot\",\"expected_revenue\":5000,\"company_id\":\"$C1_ID\"}")
DC_ID=$(jq_val "$DC" "d.get('id','')")
check "Create 3 deals same company" "$([ -n "$DA_ID" ] && [ -n "$DB_ID" ] && [ -n "$DC_ID" ] && echo true || echo false)"

# 12.2 Verify all 3 are different IDs
check "3 deals have unique IDs" "$([ "$DA_ID" != "$DB_ID" ] && [ "$DB_ID" != "$DC_ID" ] && [ "$DA_ID" != "$DC_ID" ] && echo true || echo false)"

# 12.3 Move them through stages
DA_M=$(curl -s -X PATCH "$API/crm/deals/$DA_ID" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"stage_id\":\"$STAGE_SECOND_ID\"}")
check "Move multi-deal A to stage 2" "$(jq_val "$DA_M" "d.get('stage','')=='$STAGE_SECOND_NAME'" | grep -q "True" && echo true || echo false)"

DB_M=$(curl -s -X PATCH "$API/crm/deals/$DB_ID" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"stage_id\":\"$WON_STAGE_ID\"}")
check "Move multi-deal B to Won" "$(echo "$(jq_val "$DB_M" "d.get('stage','')")" | grep -qi "confermato" && echo true || echo false)"

DC_M=$(curl -s -X PATCH "$API/crm/deals/$DC_ID" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"stage_id\":\"$LOST_STAGE_ID\"}")
check "Move multi-deal C to Lost" "$(echo "$(jq_val "$DC_M" "d.get('stage','')")" | grep -qi "perso" && echo true || echo false)"

# 12.4 Create deal with all fields
D_FULL=$(curl -s -X POST "$API/crm/deals" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"name\":\"E2E Full Deal\",\"deal_type\":\"T&M\",\"expected_revenue\":100000,\"daily_rate\":800,\"estimated_days\":125,\"contact_id\":\"$CT1_ID\",\"company_id\":\"$C1_ID\",\"pipeline_template_id\":\"$VD_ID\",\"technology\":\"Java, Spring, Kubernetes, AWS\"}")
DF_ID=$(jq_val "$D_FULL" "d.get('id','')")
DF_DR=$(jq_val "$D_FULL" "d.get('daily_rate',0)")
DF_ED=$(jq_val "$D_FULL" "d.get('estimated_days',0)")
DF_CID=$(jq_val "$D_FULL" "d.get('company_id','')")
DF_CT=$(jq_val "$D_FULL" "d.get('client_id','')")
check "Create full deal" "$([ -n "$DF_ID" ] && echo true || echo false)"
check "Full deal daily_rate" "$([ "$DF_DR" = "800" ] && echo true || echo false)"
check "Full deal estimated_days" "$([ "$DF_ED" = "125" ] && echo true || echo false)"
check "Full deal company_id" "$([ "$DF_CID" = "$C1_ID" ] && echo true || echo false)"
check "Full deal contact_id (client_id)" "$([ "$DF_CT" = "$CT1_ID" ] && echo true || echo false)"

# 12.5 Verify full deal via GET
DF_GET=$(curl -s "$API/crm/deals/$DF_ID" -H "$AUTH")
DFG_NAME=$(jq_val "$DF_GET" "d.get('name','')")
DFG_TYPE=$(jq_val "$DF_GET" "d.get('deal_type','')")
DFG_REV=$(jq_val "$DF_GET" "d.get('expected_revenue',0)")
DFG_PTID=$(jq_val "$DF_GET" "d.get('pipeline_template_id','')")
check "GET full deal name" "$([ "$DFG_NAME" = "E2E Full Deal" ] && echo true || echo false)"
check "GET full deal type" "$([ "$DFG_TYPE" = "T&M" ] && echo true || echo false)"
check "GET full deal revenue" "$(python3 -c "print('true' if float('$DFG_REV') == 100000 else 'false')" 2>/dev/null)"
check "GET full deal pipeline_template_id" "$([ "$DFG_PTID" = "$VD_ID" ] && echo true || echo false)"

echo ""

# ═══════════════════════════════════════════════════════════════════
# 13. ACTIVITY SCENARIOS AVANZATI
# ═══════════════════════════════════════════════════════════════════
echo "━━━ 13. ACTIVITY SCENARIOS AVANZATI ━━━"

# 13.1 Create multiple activities on same deal
for i in 1 2 3 4 5; do
    curl -s -X POST "$API/crm/activities" -H "$AUTH" -H "Content-Type: application/json" \
        -d "{\"deal_id\":\"$D6_ID\",\"type\":\"call\",\"subject\":\"E2E Chiamata followup #$i\",\"status\":\"completed\"}" > /dev/null
done
ACTS_D6=$(curl -s "$API/crm/activities?deal_id=$D6_ID" -H "$AUTH")
ACTS_D6_COUNT=$(jq_val "$ACTS_D6" "len(d) if isinstance(d,list) else 0")
check "5 activities created on D6 (>= 5)" "$([ "$ACTS_D6_COUNT" -ge 5 ] 2>/dev/null && echo true || echo false)"

# 13.2 Create planned activity then complete it
A_PLAN=$(curl -s -X POST "$API/crm/activities" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"deal_id\":\"$D1_ID\",\"type\":\"meeting\",\"subject\":\"E2E Planned meeting\",\"status\":\"planned\"}")
AP_ID=$(jq_val "$A_PLAN" "d.get('id','')")
AP_STATUS=$(jq_val "$A_PLAN" "d.get('status','')")
check "Create planned activity" "$([ "$AP_STATUS" = "planned" ] && echo true || echo false)"

AP_COMPLETE=$(curl -s -X POST "$API/crm/activities/$AP_ID/complete" -H "$AUTH" -H "Content-Type: application/json")
APC_STATUS=$(jq_val "$AP_COMPLETE" "d.get('status','')")
APC_AT=$(jq_val "$AP_COMPLETE" "d.get('completed_at','')")
check "Complete planned → completed" "$([ "$APC_STATUS" = "completed" ] && echo true || echo false)"
check "completed_at timestamp set" "$([ -n "$APC_AT" ] && [ "$APC_AT" != "None" ] && echo true || echo false)"

# 13.3 Activity types mix
for type in call email meeting note task; do
    A_MIX=$(curl -s -X POST "$API/crm/activities" -H "$AUTH" -H "Content-Type: application/json" \
        -d "{\"deal_id\":\"$DF_ID\",\"type\":\"$type\",\"subject\":\"E2E Type test $type\",\"status\":\"completed\"}")
    MIX_TYPE=$(jq_val "$A_MIX" "d.get('type','')")
    check "Activity type $type OK" "$([ "$MIX_TYPE" = "$type" ] && echo true || echo false)"
done

echo ""

# ═══════════════════════════════════════════════════════════════════
# 14. EDGE CASES + ERROR HANDLING
# ═══════════════════════════════════════════════════════════════════
echo "━━━ 14. EDGE CASES ━━━"

# 14.1 Get non-existent deal → 404
FAKE_DEAL=$(curl -s -o /dev/null -w "%{http_code}" "$API/crm/deals/00000000-0000-0000-0000-000000000000" -H "$AUTH")
check "GET fake deal → 404" "$([ "$FAKE_DEAL" = "404" ] && echo true || echo false)"

# 14.2 GET without auth → 401/403
NO_AUTH=$(curl -s -o /dev/null -w "%{http_code}" "$API/crm/deals")
check "GET deals no auth → 401/403" "$([ "$NO_AUTH" = "401" ] || [ "$NO_AUTH" = "403" ] || [ "$NO_AUTH" = "422" ] && echo true || echo false)"

# 14.3 PATCH fake deal → 404
FAKE_PATCH=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH "$API/crm/deals/00000000-0000-0000-0000-000000000000" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"name":"nope"}')
check "PATCH fake deal → 404" "$([ "$FAKE_PATCH" = "404" ] && echo true || echo false)"

# 14.4 Delete fake contact → 404
FAKE_DEL=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$API/crm/contacts/00000000-0000-0000-0000-000000000000" -H "$AUTH")
check "DELETE fake contact → 404" "$([ "$FAKE_DEL" = "404" ] && echo true || echo false)"

# 14.5 PATCH fake company → 404
FAKE_COMP=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH "$API/crm/companies/00000000-0000-0000-0000-000000000000" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"name":"nope"}')
check "PATCH fake company → 404" "$([ "$FAKE_COMP" = "404" ] && echo true || echo false)"

# 14.6 Complete fake activity → 404
FAKE_ACT=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/crm/activities/00000000-0000-0000-0000-000000000000/complete" -H "$AUTH")
check "Complete fake activity → 404" "$([ "$FAKE_ACT" = "404" ] && echo true || echo false)"

# 14.7 Create deal without required name → 422
BAD_DEAL=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/crm/deals" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{}')
check "Create deal no name → error" "$([ "$BAD_DEAL" = "422" ] || [ "$BAD_DEAL" = "500" ] && echo true || echo false)"

echo ""

# ═══════════════════════════════════════════════════════════════════
# 15. BULK VERIFICATION — rileggere tutto e verificare coerenza
# ═══════════════════════════════════════════════════════════════════
echo "━━━ 15. BULK VERIFICATION ━━━"

# 15.1 All test companies exist
ALL_COMP=$(curl -s "$API/crm/companies?search=E2E" -H "$AUTH")
E2E_COMP_COUNT=$(jq_val "$ALL_COMP" "d.get('total',0)")
check "All E2E companies exist (>= 3)" "$([ "$E2E_COMP_COUNT" -ge 3 ] 2>/dev/null && echo true || echo false)"

# 15.2 All test contacts exist
ALL_CONT=$(curl -s "$API/crm/contacts?search=E2E" -H "$AUTH")
E2E_CONT_COUNT=$(jq_val "$ALL_CONT" "d.get('total',0)")
check "E2E contacts exist (>= 3)" "$([ "$E2E_CONT_COUNT" -ge 3 ] 2>/dev/null && echo true || echo false)"

# 15.3 Verify each deal type exists in list
DEALS_FINAL=$(curl -s "$API/crm/deals?limit=500" -H "$AUTH")
HAS_TM=$(jq_val "$DEALS_FINAL" "any(dl.get('deal_type')=='T&M' for dl in d.get('deals',[]))")
HAS_FX=$(jq_val "$DEALS_FINAL" "any(dl.get('deal_type')=='fixed' for dl in d.get('deals',[]))")
HAS_SP=$(jq_val "$DEALS_FINAL" "any(dl.get('deal_type')=='spot' for dl in d.get('deals',[]))")
HAS_HW=$(jq_val "$DEALS_FINAL" "any(dl.get('deal_type')=='hardware' for dl in d.get('deals',[]))")
check "T&M deals in list" "$([ "$HAS_TM" = "True" ] && echo true || echo false)"
check "Fixed deals in list" "$([ "$HAS_FX" = "True" ] && echo true || echo false)"
check "Spot deals in list" "$([ "$HAS_SP" = "True" ] && echo true || echo false)"
check "Hardware deals in list" "$([ "$HAS_HW" = "True" ] && echo true || echo false)"

# 15.4 Pipeline summary value >= sum of our E2E deals
SUM_FINAL=$(curl -s "$API/crm/pipeline/summary" -H "$AUTH")
SUM_VALUE_F=$(jq_val "$SUM_FINAL" "d.get('total_value',0)")
check "Pipeline value > 0" "$(python3 -c "print('true' if float('$SUM_VALUE_F') > 0 else 'false')" 2>/dev/null)"

# 15.5 Won/lost ratio is reasonable
AN_FINAL=$(curl -s "$API/crm/pipeline/analytics" -H "$AUTH")
WLR=$(jq_val "$AN_FINAL" "d.get('won_lost_ratio',0)")
check "Won/lost ratio calculated" "$(python3 -c "print('true' if float('$WLR') >= 0 else 'false')" 2>/dev/null)"

echo ""

# ═══════════════════════════════════════════════════════════════════
# 16. CLEANUP E2E TEST DATA
# ═══════════════════════════════════════════════════════════════════
echo "━━━ 16. CLEANUP ━━━"

# Delete test contacts (that still exist)
for CT_ID in $CT1_ID $CT2_ID $CT3_ID $CT4_ID; do
    curl -s -X DELETE "$API/crm/contacts/$CT_ID" -H "$AUTH" > /dev/null 2>&1
done
echo "  Deleted test contacts"

# Note: deals and companies cannot be deleted via API (no DELETE endpoint)
# They stay in DB but are identifiable by "E2E" prefix
echo "  Note: deals/companies with 'E2E' prefix remain (no DELETE endpoint)"

echo ""

# ═══════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════
echo "============================================================"
if [ $FAIL -eq 0 ]; then
    echo -e "  ${GREEN}ALL PASS!${NC}  TOTAL: $TOTAL  ${GREEN}PASS: $PASS${NC}"
else
    echo -e "  TOTAL: $TOTAL  ${GREEN}PASS: $PASS${NC}  ${RED}FAIL: $FAIL${NC}"
    echo ""
    echo -e "  Failed tests:${ERRORS}"
fi
echo "============================================================"
