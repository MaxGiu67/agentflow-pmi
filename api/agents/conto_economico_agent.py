"""ContoEconomicoAgent: personalizes the income statement (conto economico)
based on ATECO code, existing invoices, and user interview answers.

Architecture:
  1. Read ATECO code -> select base template (deterministic)
  2. Read existing invoices -> detect categories (DB query)
  3. Ask user 5-6 questions -> Claude API chat
  4. Personalize piano conti -> merge template + answers
  5. User confirms -> save
"""

import json
import logging
import os
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import ChartAccount, Invoice

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ATECO Templates
# ---------------------------------------------------------------------------

ATECO_TEMPLATES: dict[str, dict] = {
    "62": {
        "name": "Software e Consulenza IT",
        "ricavi": [
            "Sviluppo software",
            "Consulenza IT",
            "Manutenzione e assistenza",
            "Licenze e SaaS",
        ],
        "costi": [
            "Personale",
            "Servizi cloud e hosting",
            "Consulenze esterne",
            "Hardware e attrezzature",
            "Affitto ufficio",
            "Formazione",
            "Marketing",
        ],
        "domande": [
            "Hai dipendenti? Se si, quanti?",
            "Lavori da un ufficio o da remoto?",
            "Utilizzi servizi cloud (AWS, Azure, hosting)? Quanto spendi circa al mese?",
            "Hai collaboratori esterni o freelance?",
            "Vendi prodotti (licenze software) o servizi (consulenza, sviluppo)?",
        ],
    },
    "46": {
        "name": "Commercio all'ingrosso",
        "ricavi": ["Vendita merci", "Provvigioni", "Servizi logistici"],
        "costi": [
            "Acquisto merci",
            "Trasporto e logistica",
            "Personale",
            "Magazzino",
            "Affitto",
            "Marketing",
        ],
        "domande": [
            "Quanti dipendenti hai?",
            "Hai un magazzino proprio o utilizzi un deposito esterno?",
            "Che tipo di merci vendi?",
            "Hai una flotta di veicoli per le consegne?",
            "Vendi online o solo a clienti diretti?",
        ],
    },
    "41": {
        "name": "Costruzioni e edilizia",
        "ricavi": ["Lavori edili", "Ristrutturazioni", "Subappalti", "Progettazione"],
        "costi": [
            "Materiali edili",
            "Subappaltatori",
            "Personale",
            "Noleggio attrezzature",
            "Trasporti",
            "Sicurezza",
        ],
        "domande": [
            "Quanti dipendenti e operai hai?",
            "Utilizzi subappaltatori?",
            "Hai attrezzature di proprieta o a noleggio?",
            "Che tipo di lavori fai principalmente (nuove costruzioni, ristrutturazioni)?",
            "Lavori per privati o pubblica amministrazione?",
        ],
    },
    "56": {
        "name": "Ristorazione",
        "ricavi": [
            "Somministrazione cibi e bevande",
            "Catering",
            "Delivery",
            "Asporto",
        ],
        "costi": [
            "Materie prime alimentari",
            "Personale",
            "Affitto locale",
            "Utenze",
            "Attrezzature cucina",
            "Marketing",
        ],
        "domande": [
            "Che tipo di locale hai (ristorante, bar, pizzeria)?",
            "Quanti dipendenti hai?",
            "Fai delivery o asporto?",
            "Il locale e di proprieta o in affitto?",
            "Hai un servizio di catering?",
        ],
    },
    "69": {
        "name": "Servizi professionali",
        "ricavi": ["Consulenze", "Compensi professionali", "Formazione"],
        "costi": [
            "Personale",
            "Affitto studio",
            "Software e abbonamenti",
            "Formazione continua",
            "Assicurazione professionale",
        ],
        "domande": [
            "Sei un libero professionista o hai uno studio associato?",
            "Hai dipendenti o collaboratori?",
            "Hai un ufficio/studio o lavori da casa?",
            "Quali software professionali utilizzi?",
            "Hai costi significativi di formazione/aggiornamento?",
        ],
    },
    # ---- Additional ATECO sections ----
    "01": {
        "name": "Agricoltura",
        "ricavi": ["Vendita prodotti agricoli", "Contributi PAC", "Agriturismo"],
        "costi": [
            "Sementi e fertilizzanti",
            "Personale stagionale",
            "Carburante e macchinari",
            "Affitto terreni",
            "Assicurazioni",
        ],
        "domande": [
            "Che tipo di colture o allevamento pratichi?",
            "Hai personale stagionale?",
            "Possiedi i terreni o li affitti?",
        ],
    },
    "02": {
        "name": "Silvicoltura",
        "ricavi": ["Vendita legname", "Servizi forestali", "Biomasse"],
        "costi": [
            "Personale",
            "Macchinari forestali",
            "Trasporti",
            "Assicurazioni",
        ],
        "domande": [
            "Che tipo di attivita forestale svolgi?",
            "Hai macchinari di proprieta?",
            "Vendi legname o biomasse?",
        ],
    },
    "03": {
        "name": "Pesca e acquacoltura",
        "ricavi": ["Vendita pesce", "Acquacoltura", "Lavorazione prodotti ittici"],
        "costi": [
            "Carburante",
            "Personale",
            "Manutenzione imbarcazioni",
            "Attrezzature",
            "Assicurazioni",
        ],
        "domande": [
            "Pratichi pesca o acquacoltura?",
            "Quante imbarcazioni possiedi?",
            "Vendi a grossisti o al dettaglio?",
        ],
    },
    "10": {
        "name": "Manifatturiero",
        "ricavi": [
            "Vendita prodotti finiti",
            "Lavorazione conto terzi",
            "Esportazioni",
        ],
        "costi": [
            "Materie prime",
            "Personale",
            "Energia",
            "Macchinari e manutenzione",
            "Trasporti",
            "Affitto capannone",
            "Ammortamenti",
        ],
        "domande": [
            "Che tipo di prodotti manifatturi?",
            "Quanti dipendenti hai?",
            "Esporti all'estero?",
        ],
    },
    "45": {
        "name": "Commercio e riparazione veicoli",
        "ricavi": [
            "Vendita veicoli",
            "Riparazioni e manutenzione",
            "Vendita ricambi",
        ],
        "costi": [
            "Acquisto veicoli",
            "Ricambi",
            "Personale",
            "Affitto",
            "Attrezzature officina",
        ],
        "domande": [
            "Vendi veicoli nuovi o usati?",
            "Hai un'officina di riparazione?",
            "Quanti dipendenti hai?",
        ],
    },
    "47": {
        "name": "Commercio al dettaglio",
        "ricavi": [
            "Vendita al dettaglio",
            "Vendite online",
            "Servizi post-vendita",
        ],
        "costi": [
            "Acquisto merci",
            "Personale",
            "Affitto negozio",
            "Utenze",
            "Marketing",
        ],
        "domande": [
            "Hai un negozio fisico o vendi solo online?",
            "Quanti dipendenti hai?",
            "Che tipo di merci vendi?",
        ],
    },
    "49": {
        "name": "Trasporto e logistica",
        "ricavi": [
            "Trasporto merci",
            "Trasporto persone",
            "Servizi logistici",
        ],
        "costi": [
            "Carburante",
            "Personale autisti",
            "Manutenzione veicoli",
            "Pedaggi e assicurazioni",
            "Leasing veicoli",
        ],
        "domande": [
            "Che tipo di trasporto effettui (merci, persone)?",
            "Quanti veicoli hai nella flotta?",
            "I veicoli sono di proprieta o in leasing?",
        ],
    },
    "50": {
        "name": "Trasporto marittimo",
        "ricavi": ["Trasporto merci via mare", "Trasporto passeggeri", "Noleggio"],
        "costi": [
            "Carburante navale",
            "Personale di bordo",
            "Manutenzione navi",
            "Assicurazioni",
            "Diritti portuali",
        ],
        "domande": [
            "Che tipo di trasporto marittimo effettui?",
            "Quante imbarcazioni possiedi?",
            "Operi in acque nazionali o internazionali?",
        ],
    },
    "51": {
        "name": "Trasporto aereo",
        "ricavi": ["Trasporto merci aereo", "Trasporto passeggeri", "Charter"],
        "costi": [
            "Carburante",
            "Personale di volo",
            "Manutenzione aeromobili",
            "Diritti aeroportuali",
            "Assicurazioni",
        ],
        "domande": [
            "Che tipo di servizio aereo offri?",
            "Quanti aeromobili possiedi?",
            "Operi voli nazionali o internazionali?",
        ],
    },
    "52": {
        "name": "Magazzinaggio e supporto trasporti",
        "ricavi": [
            "Servizi di magazzinaggio",
            "Movimentazione merci",
            "Servizi doganali",
        ],
        "costi": [
            "Affitto magazzini",
            "Personale",
            "Attrezzature movimentazione",
            "Sistemi informatici",
            "Assicurazioni",
        ],
        "domande": [
            "Che tipo di servizi logistici offri?",
            "Hai magazzini di proprieta o in affitto?",
            "Gestisci merci pericolose o refrigerate?",
        ],
    },
    "53": {
        "name": "Servizi postali e corriere",
        "ricavi": ["Servizi di spedizione", "Corriere espresso", "Servizi postali"],
        "costi": [
            "Veicoli e carburante",
            "Personale",
            "Centri di smistamento",
            "Tecnologia tracking",
            "Assicurazioni",
        ],
        "domande": [
            "Che tipo di servizi di spedizione offri?",
            "Quanti veicoli hai?",
            "Operi a livello locale o nazionale?",
        ],
    },
    "68": {
        "name": "Immobiliare",
        "ricavi": [
            "Affitti attivi",
            "Compravendita immobili",
            "Intermediazione",
        ],
        "costi": [
            "Manutenzione immobili",
            "IMU e tasse immobiliari",
            "Assicurazioni",
            "Personale",
            "Spese condominiali",
        ],
        "domande": [
            "Fai compravendita, affitti o intermediazione?",
            "Quanti immobili gestisci?",
            "Hai personale o collaboratori?",
        ],
    },
    "70": {
        "name": "Consulenza gestionale",
        "ricavi": ["Consulenza aziendale", "Formazione", "Progetti"],
        "costi": [
            "Personale",
            "Affitto ufficio",
            "Viaggi e trasferte",
            "Software",
            "Marketing",
        ],
        "domande": [
            "Che tipo di consulenza offri?",
            "Hai dipendenti o collaboratori?",
            "Lavori principalmente con PMI o grandi aziende?",
        ],
    },
    "71": {
        "name": "Studi di architettura e ingegneria",
        "ricavi": ["Progettazione", "Direzione lavori", "Consulenze tecniche"],
        "costi": [
            "Personale",
            "Software CAD/BIM",
            "Affitto studio",
            "Assicurazione professionale",
            "Formazione",
        ],
        "domande": [
            "Sei un libero professionista o hai uno studio?",
            "Che tipo di progettazione fai?",
            "Hai collaboratori o dipendenti?",
        ],
    },
    "72": {
        "name": "Ricerca e sviluppo",
        "ricavi": ["Contratti di ricerca", "Brevetti e licenze", "Contributi R&S"],
        "costi": [
            "Personale ricercatori",
            "Materiali e reagenti",
            "Attrezzature laboratorio",
            "Brevetti",
            "Pubblicazioni",
        ],
        "domande": [
            "In che settore fai ricerca?",
            "Hai un laboratorio?",
            "Ricevi contributi pubblici per R&S?",
        ],
    },
    "73": {
        "name": "Pubblicita e ricerche di mercato",
        "ricavi": ["Campagne pubblicitarie", "Ricerche di mercato", "Consulenza marketing"],
        "costi": [
            "Personale creativo",
            "Acquisto spazi pubblicitari",
            "Software e strumenti",
            "Affitto ufficio",
            "Fornitori esterni",
        ],
        "domande": [
            "Fai pubblicita tradizionale o digitale?",
            "Hai dipendenti o collaboratori?",
            "Quali sono i tuoi principali clienti?",
        ],
    },
    "74": {
        "name": "Altre attivita professionali",
        "ricavi": ["Consulenze specialistiche", "Servizi professionali", "Perizie"],
        "costi": [
            "Personale",
            "Affitto studio",
            "Attrezzature",
            "Assicurazione professionale",
            "Formazione",
        ],
        "domande": [
            "Che tipo di attivita professionale svolgi?",
            "Sei un libero professionista o hai uno studio?",
            "Hai costi significativi di attrezzature?",
        ],
    },
    "85": {
        "name": "Istruzione",
        "ricavi": ["Rette scolastiche", "Corsi di formazione", "Contributi"],
        "costi": [
            "Personale docente",
            "Affitto locali",
            "Materiale didattico",
            "Utenze",
            "Assicurazioni",
        ],
        "domande": [
            "Che tipo di istruzione/formazione offri?",
            "Hai docenti dipendenti o collaboratori?",
            "Hai una sede fisica?",
        ],
    },
    "86": {
        "name": "Sanita",
        "ricavi": [
            "Prestazioni sanitarie",
            "Visite specialistiche",
            "Convenzioni SSN",
        ],
        "costi": [
            "Personale sanitario",
            "Attrezzature mediche",
            "Affitto ambulatorio",
            "Assicurazione professionale",
            "Materiale sanitario",
        ],
        "domande": [
            "Che tipo di prestazioni sanitarie offri?",
            "Hai dipendenti o collaboratori sanitari?",
            "Lavori in convenzione con il SSN?",
        ],
    },
    "87": {
        "name": "Assistenza sociale residenziale",
        "ricavi": [
            "Rette residenziali",
            "Contributi pubblici",
            "Servizi accessori",
        ],
        "costi": [
            "Personale assistenziale",
            "Vitto e alloggio",
            "Affitto struttura",
            "Utenze",
            "Assicurazioni",
        ],
        "domande": [
            "Che tipo di struttura residenziale gestisci?",
            "Quanti ospiti puoi accogliere?",
            "Ricevi contributi pubblici?",
        ],
    },
    "88": {
        "name": "Assistenza sociale non residenziale",
        "ricavi": ["Servizi assistenziali", "Contributi pubblici", "Convenzioni"],
        "costi": [
            "Personale assistenziale",
            "Trasporti",
            "Materiale",
            "Affitto locali",
            "Assicurazioni",
        ],
        "domande": [
            "Che tipo di servizi assistenziali offri?",
            "Hai personale dipendente?",
            "Lavori in convenzione con enti pubblici?",
        ],
    },
}

DEFAULT_TEMPLATE: dict = {
    "name": "Attivita generica",
    "ricavi": ["Vendite", "Prestazioni di servizi", "Altri ricavi"],
    "costi": [
        "Acquisti",
        "Servizi",
        "Personale",
        "Affitto",
        "Utenze",
        "Ammortamenti",
        "Oneri diversi",
    ],
    "domande": [
        "Che tipo di attivita svolgi?",
        "Hai dipendenti? Se si, quanti?",
        "Hai un ufficio/locale o lavori da casa?",
        "Quali sono le tue principali voci di spesa?",
        "Vendi prodotti, servizi o entrambi?",
    ],
}

# ATECO ranges where one key covers multiple sections
_ATECO_RANGES: list[tuple[range, str]] = [
    (range(10, 34), "10"),  # Manifatturiero 10-33
    (range(49, 54), "49"),  # Trasporto 49-53 (use 49 template)
    (range(86, 89), "86"),  # Sanita 86-88 (use 86 as base, but 87/88 have own)
]


class ContoEconomicoAgent:
    """Agent that personalizes the conto economico (income statement)
    based on ATECO code, invoice history, and user answers."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Template selection
    # ------------------------------------------------------------------

    def get_template_for_ateco(self, codice_ateco: str) -> dict:
        """Get the appropriate template based on ATECO code (first 2 digits).

        Matching priority:
          1. Exact 2-digit match in ATECO_TEMPLATES
          2. Range match (e.g. 10-33 -> Manifatturiero)
          3. DEFAULT_TEMPLATE
        """
        section = codice_ateco[:2] if codice_ateco else ""

        # 1. Exact match
        if section in ATECO_TEMPLATES:
            return ATECO_TEMPLATES[section]

        # 2. Range match
        try:
            section_int = int(section)
        except (ValueError, TypeError):
            return DEFAULT_TEMPLATE

        for r, key in _ATECO_RANGES:
            if section_int in r:
                # Check if there's a more specific template first
                if section in ATECO_TEMPLATES:
                    return ATECO_TEMPLATES[section]
                return ATECO_TEMPLATES[key]

        return DEFAULT_TEMPLATE

    # ------------------------------------------------------------------
    # Invoice analysis
    # ------------------------------------------------------------------

    async def analyze_existing_invoices(self, tenant_id: uuid.UUID) -> dict:
        """Analyze existing invoices to detect spending patterns.

        Returns:
            dict with categories_found, top_expenses, total_ricavi, total_costi
        """
        # Aggregate categories from invoices
        result = await self.db.execute(
            select(Invoice.category, func.count(Invoice.id), func.sum(Invoice.importo_totale))
            .where(Invoice.tenant_id == tenant_id, Invoice.category.is_not(None))
            .group_by(Invoice.category)
            .order_by(func.sum(Invoice.importo_totale).desc())
        )
        rows = result.all()

        categories_found: list[str] = []
        top_expenses: list[dict] = []
        total_costi = 0.0

        for cat, count, total in rows:
            if cat:
                categories_found.append(cat)
                total_amount = float(total or 0)
                top_expenses.append({
                    "category": cat,
                    "count": count,
                    "total": total_amount,
                })
                total_costi += total_amount

        # Sum total ricavi from active invoices
        result_ricavi = await self.db.execute(
            select(func.sum(Invoice.importo_totale))
            .where(Invoice.tenant_id == tenant_id, Invoice.type == "attiva")
        )
        total_ricavi = float(result_ricavi.scalar_one_or_none() or 0)

        return {
            "categories_found": categories_found,
            "top_expenses": top_expenses[:10],
            "total_ricavi": total_ricavi,
            "total_costi": total_costi,
        }

    # ------------------------------------------------------------------
    # Question generation
    # ------------------------------------------------------------------

    async def generate_questions(
        self, codice_ateco: str, tenant_id: uuid.UUID,
    ) -> dict:
        """Generate personalized questions based on ATECO + existing data."""
        template = self.get_template_for_ateco(codice_ateco)
        invoice_analysis = await self.analyze_existing_invoices(tenant_id)

        questions: list[dict] = []
        for i, q in enumerate(template["domande"]):
            questions.append({
                "id": i + 1,
                "question": q,
                "type": "text",
            })

        return {
            "template_name": template["name"],
            "questions": questions,
            "ricavi_suggeriti": template["ricavi"],
            "costi_suggeriti": template["costi"],
            "invoice_analysis": invoice_analysis,
        }

    # ------------------------------------------------------------------
    # Answer processing
    # ------------------------------------------------------------------

    async def process_answers(
        self,
        codice_ateco: str,
        answers: list[dict],
        tenant_id: uuid.UUID,
    ) -> dict:
        """Process user answers and create personalized conto economico structure.

        Uses Claude API to interpret free-text answers and map to accounting
        categories. Falls back to rule-based logic when the API key is not set.
        """
        template = self.get_template_for_ateco(codice_ateco)

        # Build prompt for Claude
        prompt = self._build_personalization_prompt(template, answers)

        # Call Claude API (or fall back to rule-based if no API key)
        try:
            personalized = await self._call_claude(prompt)
        except Exception as exc:
            logger.info(
                "Claude API not available (%s), using rule-based fallback", exc,
            )
            personalized = self._rule_based_personalization(template, answers)

        return personalized

    # ------------------------------------------------------------------
    # Claude API integration
    # ------------------------------------------------------------------

    async def _call_claude(self, prompt: str) -> dict:
        """Call Claude API to interpret answers and personalize the plan."""
        import httpx

        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30,
            )
            resp.raise_for_status()
            content = resp.json()["content"][0]["text"]
            return json.loads(content)

    def _build_personalization_prompt(self, template: dict, answers: list[dict]) -> str:
        """Build prompt for Claude to personalize the conto economico."""
        answers_text = "\n".join(
            [f"D: {a['question']}\nR: {a['answer']}" for a in answers]
        )

        return (
            "Sei un commercialista esperto italiano. Basandoti sulle risposte dell'utente, "
            "personalizza il piano dei conti (conto economico) per la sua azienda.\n\n"
            f"Settore: {template['name']}\n"
            f"Voci ricavi suggerite: {', '.join(template['ricavi'])}\n"
            f"Voci costi suggerite: {', '.join(template['costi'])}\n\n"
            f"Risposte dell'utente:\n{answers_text}\n\n"
            "Rispondi SOLO con un JSON valido (nessun altro testo) con questa struttura:\n"
            "{\n"
            '    "ricavi": ["voce1", "voce2", ...],\n'
            '    "costi": ["voce1", "voce2", ...],\n'
            '    "note": "breve nota per l\'utente su cosa e stato personalizzato",\n'
            '    "has_dipendenti": true/false,\n'
            '    "has_affitto": true/false,\n'
            '    "regime_suggerito": "ordinario" o "forfettario" o "semplificato"\n'
            "}"
        )

    # ------------------------------------------------------------------
    # Rule-based fallback
    # ------------------------------------------------------------------

    def _rule_based_personalization(self, template: dict, answers: list[dict]) -> dict:
        """Fallback: personalize without LLM using simple rules."""
        ricavi = list(template["ricavi"])
        costi = list(template["costi"])
        has_dipendenti = False
        has_affitto = False

        for a in answers:
            answer_lower = a.get("answer", "").lower()

            # Detect employees
            if any(
                w in a.get("question", "").lower()
                for w in ["dipendenti", "collaboratori", "personale", "operai"]
            ):
                if any(
                    w in answer_lower
                    for w in ["no", "nessuno", "solo io", "nessun"]
                ):
                    if "Personale" in costi:
                        costi.remove("Personale")
                else:
                    has_dipendenti = True

            # Detect office / remote work
            if any(
                w in a.get("question", "").lower()
                for w in ["ufficio", "remoto", "locale", "casa", "studio", "sede"]
            ):
                if any(
                    w in answer_lower
                    for w in ["remoto", "casa", "smart working", "da remoto"]
                ):
                    for label in ["Affitto ufficio", "Affitto", "Affitto locale", "Affitto studio"]:
                        if label in costi:
                            costi.remove(label)
                elif any(
                    w in answer_lower
                    for w in ["ufficio", "locale", "negozio", "studio", "sede", "affitto"]
                ):
                    has_affitto = True

            # Detect online sales
            if "online" in answer_lower and "Vendite online" not in ricavi:
                if any(w in a.get("question", "").lower() for w in ["vend", "online"]):
                    ricavi.append("Vendite online")

            # Detect delivery
            if any(w in answer_lower for w in ["delivery", "consegn", "asporto"]):
                if "Delivery" not in ricavi and "delivery" in a.get("question", "").lower():
                    ricavi.append("Delivery")

            # Detect cloud/hosting expenses
            if any(w in answer_lower for w in ["aws", "azure", "cloud", "hosting"]):
                if "Servizi cloud e hosting" not in costi:
                    costi.append("Servizi cloud e hosting")

            # Detect subcontractors
            if any(w in answer_lower for w in ["subappalt", "freelance", "esterni"]):
                if "Consulenze esterne" not in costi and "Subappaltatori" not in costi:
                    costi.append("Consulenze esterne")

        return {
            "ricavi": ricavi,
            "costi": costi,
            "note": f"Piano personalizzato per {template['name']}",
            "has_dipendenti": has_dipendenti,
            "has_affitto": has_affitto,
            "regime_suggerito": "ordinario",
        }

    # ------------------------------------------------------------------
    # Chart of accounts creation
    # ------------------------------------------------------------------

    async def create_personalized_chart(
        self,
        tenant_id: uuid.UUID,
        personalized: dict,
    ) -> dict:
        """Create the actual ChartAccount entries from personalized plan.

        Deletes any existing chart accounts for the tenant and creates new ones
        based on the personalized plan.
        """
        accounts: list[dict] = []

        # Standard accounts (always present)
        standard = [
            ("1010", "Cassa", "asset", "C.IV.3", "Disponibilita liquide"),
            ("1020", "Banca c/c", "asset", "C.IV.1", "Depositi bancari"),
            ("1110", "Crediti verso clienti", "asset", "C.II.1", "Crediti clienti"),
            ("2010", "Debiti verso fornitori", "liability", "D.7", "Debiti fornitori"),
            ("2110", "IVA a debito", "liability", "D.12", "Debiti tributari"),
            ("2212", "IVA a credito", "asset", "C.II.5-bis", "Crediti tributari"),
            ("3010", "Capitale", "equity", "A.I", "Capitale"),
        ]

        for code, name, atype, cee_code, cee_name in standard:
            accounts.append({
                "code": code,
                "name": name,
                "account_type": atype,
                "cee_code": cee_code,
                "cee_name": cee_name,
            })

        # Ricavi accounts
        for i, voce in enumerate(personalized["ricavi"]):
            code = str(4010 + i * 10)
            accounts.append({
                "code": code,
                "name": voce,
                "account_type": "income",
                "cee_code": "A.1",
                "cee_name": "Ricavi",
            })

        # Costi accounts
        for i, voce in enumerate(personalized["costi"]):
            code = str(5010 + i * 10)
            cee = (
                "B.9"
                if "personal" in voce.lower() or "dipendent" in voce.lower()
                else "B.7"
            )
            accounts.append({
                "code": code,
                "name": voce,
                "account_type": "expense",
                "cee_code": cee,
                "cee_name": "Costi",
            })

        # Delete existing chart accounts for tenant then insert new ones
        await self.db.execute(
            delete(ChartAccount).where(ChartAccount.tenant_id == tenant_id)
        )

        for acc in accounts:
            chart_acc = ChartAccount(
                tenant_id=tenant_id,
                code=acc["code"],
                name=acc["name"],
                account_type=acc["account_type"],
                cee_code=acc.get("cee_code"),
                cee_name=acc.get("cee_name"),
            )
            self.db.add(chart_acc)

        await self.db.flush()

        return {
            "accounts": accounts,
            "total": len(accounts),
            "ricavi_count": len(personalized["ricavi"]),
            "costi_count": len(personalized["costi"]),
            "note": personalized.get("note", ""),
        }
