"""State snapshot endpoints — viste aggregate denormalizzate per agenti AI.

Ogni endpoint qui ritorna un dict piatto/strutturato che un singolo tool LLM
può leggere in 1 chiamata invece di N tool call sparse. Scopo: ridurre cost +
latenza chatbot e dare ad agenti "tutto sotto controllo" del dominio.

Design:
- Nessuna scrittura, solo lettura
- Tenant-isolated (sempre filtra per current user.tenant_id)
- Aggregazioni precalcolate (ultimi 30/60/90gg, top counterparts, anomalie)
- Compatibile multi-tenant (TAAL, Qubika, Nexa Data, ecc.)
"""
