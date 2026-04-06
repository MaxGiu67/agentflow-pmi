#!/bin/bash
# E2E Test Suite against Railway production
# Tests: Companies, Contacts, Deals, Stage moves, Activities, Orders, Pipeline Templates

API="https://api-production-15cd.up.railway.app/api/v1"
PASS=0
FAIL=0
TOTAL=0

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

check() {
    TOTAL=$((TOTAL+1))
    local desc="$1"
    local condition="$2"
    if [ "$condition" = "true" ]; then
        PASS=$((PASS+1))
        echo -e "  ${GREEN}PASS${NC} $TOTAL. $desc"
    else
        FAIL=$((FAIL+1))
        echo -e "  ${RED}FAIL${NC} $TOTAL. $desc"
    fi
}

echo "=== E2E TEST SUITE — Railway Production ==="
echo "API: $API"
echo ""

# ── LOGIN ──
echo "--- Login ---"
LOGIN=$(curl -s "$API/auth/login" -H "Content-Type: application/json" \
    -d '{"email":"mgiurelli@taal.it","password":"zyjdez-zedwi8-mexpeS"}')
TOKEN=$(echo "$LOGIN" | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
AUTH="Authorization: Bearer $TOKEN"
check "Login OK" "$([ -n "$TOKEN" ] && [ "$TOKEN" != "" ] && echo true || echo false)"

# ── A. COMPANIES ──
echo ""
echo "--- A. Companies ---"

# Cleanup: delete test companies if they exist
# Create company
C1=$(curl -s -X POST "$API/crm/companies" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"name":"E2E Test Company SRL","vat":"99988877766","city":"Roma","sector":"IT"}')
C1_ID=$(echo "$C1" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
C1_NAME=$(echo "$C1" | python3 -c "import sys,json; print(json.load(sys.stdin).get('name',''))" 2>/dev/null)
check "Create company" "$([ "$C1_NAME" = "E2E Test Company SRL" ] && echo true || echo false)"

# List companies
COMPANIES=$(curl -s "$API/crm/companies" -H "$AUTH")
C_TOTAL=$(echo "$COMPANIES" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null)
check "List companies (total >= 1)" "$([ "$C_TOTAL" -ge 1 ] && echo true || echo false)"

# Search company
SEARCH=$(curl -s "$API/crm/companies?search=E2E" -H "$AUTH")
S_TOTAL=$(echo "$SEARCH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null)
check "Search company 'E2E'" "$([ "$S_TOTAL" -ge 1 ] && echo true || echo false)"

# Get company by ID
C1_GET=$(curl -s "$API/crm/companies/$C1_ID" -H "$AUTH")
C1_GET_NAME=$(echo "$C1_GET" | python3 -c "import sys,json; print(json.load(sys.stdin).get('name',''))" 2>/dev/null)
check "Get company by ID" "$([ "$C1_GET_NAME" = "E2E Test Company SRL" ] && echo true || echo false)"

# Update company
C1_UPD=$(curl -s -X PATCH "$API/crm/companies/$C1_ID" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"city":"Milano","sector":"Finance"}')
C1_UPD_CITY=$(echo "$C1_UPD" | python3 -c "import sys,json; print(json.load(sys.stdin).get('city',''))" 2>/dev/null)
check "Update company city=Milano" "$([ "$C1_UPD_CITY" = "Milano" ] && echo true || echo false)"

# ── B. CONTACTS ──
echo ""
echo "--- B. Contacts ---"

# Create contact with company
CT1=$(curl -s -X POST "$API/crm/contacts" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"name\":\"E2E Test Company SRL\",\"company_id\":\"$C1_ID\",\"contact_name\":\"Mario E2E\",\"contact_role\":\"CTO\",\"email\":\"mario.e2e@test.it\",\"phone\":\"+39 333 1234567\"}")
CT1_ID=$(echo "$CT1" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
CT1_CN=$(echo "$CT1" | python3 -c "import sys,json; print(json.load(sys.stdin).get('contact_name',''))" 2>/dev/null)
check "Create contact with company" "$([ "$CT1_CN" = "Mario E2E" ] && echo true || echo false)"

# Create second contact same company
CT2=$(curl -s -X POST "$API/crm/contacts" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"name\":\"E2E Test Company SRL\",\"company_id\":\"$C1_ID\",\"contact_name\":\"Luca E2E\",\"contact_role\":\"Sales\",\"email\":\"luca.e2e@test.it\"}")
CT2_ID=$(echo "$CT2" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
check "Create second contact same company" "$([ -n "$CT2_ID" ] && echo true || echo false)"

# Create contact without company
CT3=$(curl -s -X POST "$API/crm/contacts" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"name":"Orphan Contact","contact_name":"Anna Orphan","email":"anna@orphan.it"}')
CT3_ID=$(echo "$CT3" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
check "Create contact without company" "$([ -n "$CT3_ID" ] && echo true || echo false)"

# List contacts
CONTACTS=$(curl -s "$API/crm/contacts" -H "$AUTH")
CT_TOTAL=$(echo "$CONTACTS" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null)
check "List contacts (total >= 3)" "$([ "$CT_TOTAL" -ge 3 ] && echo true || echo false)"

# Verify company_id is returned for contact 1
CT1_CID=$(echo "$CONTACTS" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for c in d.get('contacts',[]):
    if c.get('contact_name')=='Mario E2E':
        print(c.get('company_id',''))
        break
" 2>/dev/null)
check "Contact has company_id" "$([ "$CT1_CID" = "$C1_ID" ] && echo true || echo false)"

# Update contact
CT1_UPD=$(curl -s -X PATCH "$API/crm/contacts/$CT1_ID" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"email":"mario.updated@test.it"}')
CT1_UPD_EMAIL=$(echo "$CT1_UPD" | python3 -c "import sys,json; print(json.load(sys.stdin).get('email',''))" 2>/dev/null)
check "Update contact email" "$([ "$CT1_UPD_EMAIL" = "mario.updated@test.it" ] && echo true || echo false)"

# ── C. PIPELINE TEMPLATES ──
echo ""
echo "--- C. Pipeline Templates ---"

TEMPLATES=$(curl -s "$API/pipeline-templates" -H "$AUTH")
T_COUNT=$(echo "$TEMPLATES" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null)
check "Pipeline templates (3)" "$([ "$T_COUNT" = "3" ] && echo true || echo false)"

VD_ID=$(echo "$TEMPLATES" | python3 -c "
import sys,json
for t in json.load(sys.stdin):
    if t['code']=='vendita_diretta':
        print(t['id'])
        break
" 2>/dev/null)
check "Vendita Diretta template exists" "$([ -n "$VD_ID" ] && echo true || echo false)"

PC_ID=$(echo "$TEMPLATES" | python3 -c "
import sys,json
for t in json.load(sys.stdin):
    if t['code']=='progetto_corpo':
        print(t['id'])
        break
" 2>/dev/null)

SS_ID=$(echo "$TEMPLATES" | python3 -c "
import sys,json
for t in json.load(sys.stdin):
    if t['code']=='social_selling':
        print(t['id'])
        break
" 2>/dev/null)
check "Social Selling template exists" "$([ -n "$SS_ID" ] && echo true || echo false)"

# ── D. DEALS ──
echo ""
echo "--- D. Deals ---"

# Create deal T&M (Consulenza)
D1=$(curl -s -X POST "$API/crm/deals" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"name\":\"E2E Consulenza Java\",\"deal_type\":\"T&M\",\"expected_revenue\":30000,\"daily_rate\":500,\"estimated_days\":60,\"contact_id\":\"$CT1_ID\",\"company_id\":\"$C1_ID\",\"pipeline_template_id\":\"$VD_ID\",\"technology\":\"Java, Spring\"}")
D1_ID=$(echo "$D1" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
D1_TYPE=$(echo "$D1" | python3 -c "import sys,json; print(json.load(sys.stdin).get('deal_type',''))" 2>/dev/null)
D1_REV=$(echo "$D1" | python3 -c "import sys,json; print(json.load(sys.stdin).get('expected_revenue',0))" 2>/dev/null)
D1_PTID=$(echo "$D1" | python3 -c "import sys,json; print(json.load(sys.stdin).get('pipeline_template_id',''))" 2>/dev/null)
check "Create deal T&M" "$([ "$D1_TYPE" = "T&M" ] && echo true || echo false)"
check "Deal revenue = 30000" "$([ "$D1_REV" = "30000" ] && echo true || echo false)"
check "Deal pipeline_template_id saved" "$([ "$D1_PTID" = "$VD_ID" ] && echo true || echo false)"
check "Deal company_id saved" "$(echo "$D1" | python3 -c "import sys,json; print(json.load(sys.stdin).get('company_id',''))" 2>/dev/null | grep -q "$C1_ID" && echo true || echo false)"

# Create deal Corpo
D2=$(curl -s -X POST "$API/crm/deals" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"name\":\"E2E Progetto Gestionale\",\"deal_type\":\"fixed\",\"expected_revenue\":50000,\"pipeline_template_id\":\"$PC_ID\"}")
D2_ID=$(echo "$D2" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
D2_TYPE=$(echo "$D2" | python3 -c "import sys,json; print(json.load(sys.stdin).get('deal_type',''))" 2>/dev/null)
check "Create deal Corpo" "$([ "$D2_TYPE" = "fixed" ] && echo true || echo false)"

# Create deal Elevia
D3=$(curl -s -X POST "$API/crm/deals" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"name\":\"E2E Elevia Metallurgia\",\"deal_type\":\"spot\",\"expected_revenue\":15000,\"pipeline_template_id\":\"$SS_ID\"}")
D3_ID=$(echo "$D3" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
D3_PTID=$(echo "$D3" | python3 -c "import sys,json; print(json.load(sys.stdin).get('pipeline_template_id',''))" 2>/dev/null)
check "Create deal Elevia" "$([ -n "$D3_ID" ] && echo true || echo false)"
check "Elevia pipeline_template = social_selling" "$([ "$D3_PTID" = "$SS_ID" ] && echo true || echo false)"

# List deals
DEALS=$(curl -s "$API/crm/deals" -H "$AUTH")
D_TOTAL=$(echo "$DEALS" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null)
check "List deals (total >= 3)" "$([ "$D_TOTAL" -ge 3 ] && echo true || echo false)"

# Get deal by ID
D1_GET=$(curl -s "$API/crm/deals/$D1_ID" -H "$AUTH")
D1_GET_NAME=$(echo "$D1_GET" | python3 -c "import sys,json; print(json.load(sys.stdin).get('name',''))" 2>/dev/null)
check "Get deal by ID" "$([ "$D1_GET_NAME" = "E2E Consulenza Java" ] && echo true || echo false)"

# Update deal
D1_UPD=$(curl -s -X PATCH "$API/crm/deals/$D1_ID" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"expected_revenue":35000,"technology":"Java, Spring, Angular"}')
D1_UPD_REV=$(echo "$D1_UPD" | python3 -c "import sys,json; print(json.load(sys.stdin).get('expected_revenue',0))" 2>/dev/null)
check "Update deal revenue" "$([ "$D1_UPD_REV" = "35000" ] && echo true || echo false)"

# ── E. STAGE MOVES ──
echo ""
echo "--- E. Stage Moves ---"

STAGES=$(curl -s "$API/crm/pipeline/stages" -H "$AUTH")
STAGE2_ID=$(echo "$STAGES" | python3 -c "import sys,json; s=json.load(sys.stdin); print(s[1]['id'] if len(s)>1 else '')" 2>/dev/null)
STAGE2_NAME=$(echo "$STAGES" | python3 -c "import sys,json; s=json.load(sys.stdin); print(s[1]['name'] if len(s)>1 else '')" 2>/dev/null)

# Move deal to stage 2
D1_MOVE=$(curl -s -X PATCH "$API/crm/deals/$D1_ID" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"stage_id\":\"$STAGE2_ID\"}")
D1_MOVE_STAGE=$(echo "$D1_MOVE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('stage',''))" 2>/dev/null)
check "Move deal to $STAGE2_NAME" "$([ "$D1_MOVE_STAGE" = "$STAGE2_NAME" ] && echo true || echo false)"

# Check activity was auto-created
sleep 1
ACTS=$(curl -s "$API/crm/activities?deal_id=$D1_ID" -H "$AUTH")
ACT_COUNT=$(echo "$ACTS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d) if isinstance(d,list) else d.get('total',0))" 2>/dev/null)
check "Stage move created activity log" "$([ "$ACT_COUNT" -ge 1 ] && echo true || echo false)"

# ── F. ACTIVITIES ──
echo ""
echo "--- F. Activities ---"

# Create call activity
A1=$(curl -s -X POST "$API/crm/activities" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"deal_id\":\"$D1_ID\",\"contact_id\":\"$CT1_ID\",\"type\":\"call\",\"subject\":\"E2E Chiamata qualifica\",\"description\":\"Budget 30k, timeline 6 mesi\",\"status\":\"completed\"}")
A1_ID=$(echo "$A1" | python3 -c "import sys,json; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
A1_TYPE=$(echo "$A1" | python3 -c "import sys,json; print(json.load(sys.stdin).get('type',''))" 2>/dev/null)
check "Create call activity" "$([ "$A1_TYPE" = "call" ] && echo true || echo false)"

# Create meeting
A2=$(curl -s -X POST "$API/crm/activities" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"deal_id\":\"$D1_ID\",\"type\":\"meeting\",\"subject\":\"E2E Demo prodotto\",\"description\":\"Presentazione AgentFlow\",\"status\":\"completed\"}")
A2_TYPE=$(echo "$A2" | python3 -c "import sys,json; print(json.load(sys.stdin).get('type',''))" 2>/dev/null)
check "Create meeting activity" "$([ "$A2_TYPE" = "meeting" ] && echo true || echo false)"

# Create note
A3=$(curl -s -X POST "$API/crm/activities" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"deal_id\":\"$D1_ID\",\"type\":\"note\",\"subject\":\"E2E Nota interna\",\"description\":\"Il cliente ha documentazione dispersa — segnale cross-sell Elevia\"}")
check "Create note activity" "$(echo "$A3" | python3 -c "import sys,json; print(json.load(sys.stdin).get('type',''))" 2>/dev/null | grep -q note && echo true || echo false)"

# Create email activity
A4=$(curl -s -X POST "$API/crm/activities" -H "$AUTH" -H "Content-Type: application/json" \
    -d "{\"deal_id\":\"$D1_ID\",\"type\":\"email\",\"subject\":\"E2E Follow-up email\",\"status\":\"completed\"}")
check "Create email activity" "$(echo "$A4" | python3 -c "import sys,json; print(json.load(sys.stdin).get('type',''))" 2>/dev/null | grep -q email && echo true || echo false)"

# List activities for deal
DEAL_ACTS=$(curl -s "$API/crm/activities?deal_id=$D1_ID" -H "$AUTH")
DEAL_ACT_COUNT=$(echo "$DEAL_ACTS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d) if isinstance(d,list) else 0)" 2>/dev/null)
check "List activities for deal (>= 4)" "$([ "$DEAL_ACT_COUNT" -ge 4 ] && echo true || echo false)"

# ── G. ORDERS ──
echo ""
echo "--- G. Orders ---"

# Register order on deal 2
ORD=$(curl -s -X POST "$API/crm/deals/$D2_ID/order" -H "$AUTH" -H "Content-Type: application/json" \
    -d '{"order_type":"po","order_reference":"PO-E2E-001","order_notes":"Test order"}')
ORD_STATUS=$(echo "$ORD" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('order_type','') or d.get('status',''))" 2>/dev/null)
check "Register order" "$([ -n "$ORD_STATUS" ] && echo true || echo false)"

# Confirm order
CONF=$(curl -s -X POST "$API/crm/deals/$D2_ID/order/confirm" -H "$AUTH" -H "Content-Type: application/json")
check "Confirm order" "$(echo "$CONF" | python3 -c "import sys,json; print('error' not in json.load(sys.stdin))" 2>/dev/null | grep -q True && echo true || echo false)"

# ── H. PIPELINE ANALYTICS ──
echo ""
echo "--- H. Pipeline Analytics ---"

SUMMARY=$(curl -s "$API/crm/pipeline/summary" -H "$AUTH")
check "Pipeline summary" "$(echo "$SUMMARY" | python3 -c "import sys,json; print('total_deals' in json.load(sys.stdin))" 2>/dev/null | grep -q True && echo true || echo false)"

ANALYTICS=$(curl -s "$API/crm/pipeline/analytics" -H "$AUTH")
check "Pipeline analytics" "$(echo "$ANALYTICS" | python3 -c "import sys,json; print('weighted_pipeline_value' in json.load(sys.stdin))" 2>/dev/null | grep -q True && echo true || echo false)"

# ── CLEANUP ──
echo ""
echo "--- Cleanup E2E test data ---"

# Delete test contacts
curl -s -X DELETE "$API/crm/contacts/$CT1_ID" -H "$AUTH" > /dev/null 2>&1
curl -s -X DELETE "$API/crm/contacts/$CT2_ID" -H "$AUTH" > /dev/null 2>&1
curl -s -X DELETE "$API/crm/contacts/$CT3_ID" -H "$AUTH" > /dev/null 2>&1
echo "  Deleted test contacts"

# ── SUMMARY ──
echo ""
echo "=========================================="
echo -e "  TOTAL: $TOTAL  ${GREEN}PASS: $PASS${NC}  ${RED}FAIL: $FAIL${NC}"
echo "=========================================="
