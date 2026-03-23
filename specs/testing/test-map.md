# Test Map — AgentFlow PMI

**Aggiornato:** 2026-03-22

---

## US-01: Registrazione e login utente

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-01.1 | US-01 | test_auth_api.py | test_ac_011_registrazione_con_dati_validi | Integration | PASS | 2026-03-22 |
| AC-01.1 | US-01 | test_auth_api.py | test_ac_011_verifica_email_e_accesso_dashboard | Integration | PASS | 2026-03-22 |
| AC-01.1 | US-01 | test_auth_api.py | test_ac_011_password_troppo_corta | Integration | PASS | 2026-03-22 |
| AC-01.1 | US-01 | test_auth_api.py | test_ac_011_password_senza_maiuscola | Integration | PASS | 2026-03-22 |
| AC-01.1 | US-01 | test_auth_api.py | test_ac_011_password_senza_numero | Integration | PASS | 2026-03-22 |
| AC-01.2 | US-01 | test_auth_api.py | test_ac_012_login_con_credenziali_valide | Integration | PASS | 2026-03-22 |
| AC-01.2 | US-01 | test_auth_api.py | test_ac_012_refresh_token | Integration | PASS | 2026-03-22 |
| AC-01.2 | US-01 | test_auth_api.py | test_ac_012_login_email_non_verificata | Integration | PASS | 2026-03-22 |
| AC-01.3 | US-01 | test_auth_api.py | test_ac_013_email_gia_registrata | Integration | PASS | 2026-03-22 |
| AC-01.3 | US-01 | test_auth_api.py | test_ac_013_email_diversa_accettata | Integration | PASS | 2026-03-22 |
| AC-01.4 | US-01 | test_auth_api.py | test_ac_014_richiesta_reset_password | Integration | PASS | 2026-03-22 |
| AC-01.4 | US-01 | test_auth_api.py | test_ac_014_reset_password_email_inesistente | Integration | PASS | 2026-03-22 |
| AC-01.4 | US-01 | test_auth_api.py | test_ac_014_conferma_reset_password | Integration | PASS | 2026-03-22 |
| AC-01.4 | US-01 | test_auth_api.py | test_ac_014_reset_token_invalido | Integration | PASS | 2026-03-22 |
| AC-01.5 | US-01 | test_auth_api.py | test_ac_015_lockout_dopo_5_tentativi | Integration | PASS | 2026-03-22 |
| AC-01.5 | US-01 | test_auth_api.py | test_ac_015_dopo_lockout_tentativi_bloccati | Integration | PASS | 2026-03-22 |
| AC-01.5 | US-01 | test_auth_api.py | test_ac_015_login_corretto_resetta_contatore | Integration | PASS | 2026-03-22 |

## US-02: Profilo utente e configurazione azienda

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-02.1 | US-02 | test_profile_api.py | test_ac_021_get_profilo_autenticato | Integration | PASS | 2026-03-22 |
| AC-02.1 | US-02 | test_profile_api.py | test_ac_021_aggiorna_profilo_completo | Integration | PASS | 2026-03-22 |
| AC-02.1 | US-02 | test_profile_api.py | test_ac_021_setup_profilo_nuovo_utente | Integration | PASS | 2026-03-22 |
| AC-02.1 | US-02 | test_profile_api.py | test_ac_021_accesso_non_autenticato_rifiutato | Integration | PASS | 2026-03-22 |
| AC-02.2 | US-02 | test_profile_api.py | test_ac_022_piva_non_11_cifre | Integration | PASS | 2026-03-22 |
| AC-02.2 | US-02 | test_profile_api.py | test_ac_022_piva_con_lettere | Integration | PASS | 2026-03-22 |
| AC-02.2 | US-02 | test_profile_api.py | test_ac_022_piva_checksum_invalido | Integration | PASS | 2026-03-22 |
| AC-02.3 | US-02 | test_profile_api.py | test_ac_023_ateco_formato_errato | Integration | PASS | 2026-03-22 |
| AC-02.3 | US-02 | test_profile_api.py | test_ac_023_ateco_sezione_inesistente | Integration | PASS | 2026-03-22 |
| AC-02.3 | US-02 | test_profile_api.py | test_ac_023_ateco_valido_accettato | Integration | PASS | 2026-03-22 |
| AC-02.4 | US-02 | test_profile_api.py | test_ac_024_cambio_tipo_azienda_con_piano_conti | Integration | PASS | 2026-03-22 |
| AC-02.4 | US-02 | test_profile_api.py | test_ac_024_cambio_confermato_accettato | Integration | PASS | 2026-03-22 |

## US-03: Autenticazione SPID/CIE per cassetto fiscale

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-03.1 | US-03 | test_spid_api.py | test_ac_031_init_spid_auth | Integration | PASS | 2026-03-22 |
| AC-03.1 | US-03 | test_spid_api.py | test_ac_031_spid_callback_successo | Integration | PASS | 2026-03-22 |
| AC-03.1 | US-03 | test_spid_api.py | test_ac_031_cassetto_status_dopo_collegamento | Integration | PASS | 2026-03-22 |
| AC-03.2 | US-03 | test_spid_api.py | test_ac_032_spid_annullata | Integration | PASS | 2026-03-22 |
| AC-03.2 | US-03 | test_spid_api.py | test_ac_032_spid_errore | Integration | PASS | 2026-03-22 |
| AC-03.3 | US-03 | test_spid_api.py | test_ac_033_token_scaduto_status | Integration | PASS | 2026-03-22 |
| AC-03.4 | US-03 | test_spid_api.py | test_ac_034_info_senza_spid | Integration | PASS | 2026-03-22 |
| AC-03.4 | US-03 | test_spid_api.py | test_ac_034_status_non_collegato | Integration | PASS | 2026-03-22 |
| AC-03.5 | US-03 | test_spid_api.py | test_ac_035_init_delega | Integration | PASS | 2026-03-22 |

## US-12: Setup piano dei conti personalizzato

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-12.1 | US-12 | test_accounting_api.py | test_ac_121_crea_piano_conti_srl_ordinario | Integration | PASS | 2026-03-22 |
| AC-12.1 | US-12 | test_accounting_api.py | test_ac_121_get_piano_conti_dopo_creazione | Integration | PASS | 2026-03-22 |
| AC-12.2 | US-12 | test_accounting_api.py | test_ac_122_crea_piano_conti_forfettario | Integration | PASS | 2026-03-22 |
| AC-12.3 | US-12 | test_accounting_api.py | test_ac_123_odoo_non_raggiungibile | Integration | PASS | 2026-03-22 |
| AC-12.4 | US-12 | test_accounting_api.py | test_ac_124_piano_generico_con_nota | Integration | PASS | 2026-03-22 |
| AC-12.4 | US-12 | test_accounting_api.py | test_ac_124_piano_non_duplicato | Integration | PASS | 2026-03-22 |
| AC-12.4 | US-12 | test_accounting_api.py | test_ac_124_piano_ricreato_con_force | Integration | PASS | 2026-03-22 |
| AC-12.4 | US-12 | test_accounting_api.py | test_ac_124_profilo_non_configurato | Integration | PASS | 2026-03-22 |

---

**Totale Sprint 1:** 46 test | **PASS:** 46 | **FAIL:** 0

---

## US-04: Sync fatture dal cassetto fiscale AdE

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-04.1 | US-04 | test_invoices_api.py | test_ac_041_primo_sync_cassetto | Integration | PASS | 2026-03-22 |
| AC-04.1 | US-04 | test_invoices_api.py | test_ac_041_sync_senza_spid | Integration | PASS | 2026-03-22 |
| AC-04.2 | US-04 | test_invoices_api.py | test_ac_042_sync_incrementale | Integration | PASS | 2026-03-22 |
| AC-04.3 | US-04 | test_invoices_api.py | test_ac_043_fiscoapi_non_disponibile | Integration | PASS | 2026-03-22 |
| AC-04.4 | US-04 | test_invoices_api.py | test_ac_044_fattura_duplicata | Integration | PASS | 2026-03-22 |
| AC-04.5 | US-04 | test_invoices_api.py | test_ac_045_cassetto_vuoto | Integration | PASS | 2026-03-22 |

## US-05: Parsing XML FatturaPA

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-05.1 | US-05 | test_parser_api.py | test_ac_051_parsing_xml_fatturapa | Integration | PASS | 2026-03-22 |
| AC-05.2 | US-05 | test_parser_api.py | test_ac_052_nota_credito_td04 | Integration | PASS | 2026-03-22 |
| AC-05.3 | US-05 | test_parser_api.py | test_ac_053_xml_malformato | Integration | PASS | 2026-03-22 |
| AC-05.4 | US-05 | test_parser_api.py | test_ac_054_fattura_200_righe | Integration | PASS | 2026-03-22 |

## US-10: Categorizzazione automatica con learning

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-10.1 | US-10 | test_categorization_api.py | test_ac_101_categorizzazione_rules | Integration | PASS | 2026-03-22 |
| AC-10.2 | US-10 | test_categorization_api.py | test_ac_102_learning_migliora | Integration | PASS | 2026-03-22 |
| AC-10.3 | US-10 | test_categorization_api.py | test_ac_103_nessuna_regola | Integration | PASS | 2026-03-22 |
| AC-10.4 | US-10 | test_categorization_api.py | test_ac_104_dead_letter_queue | Integration | PASS | 2026-03-22 |
| AC-10.5 | US-10 | test_categorization_api.py | test_ac_105_fornitore_cambia_nome | Integration | PASS | 2026-03-22 |

## US-14: Dashboard fatture e stato agenti

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-14.1 | US-14 | test_dashboard_api.py | test_ac_141_vista_completa | Integration | PASS | 2026-03-22 |
| AC-14.1 | US-14 | test_dashboard_api.py | test_ac_141_agent_status | Integration | PASS | 2026-03-22 |
| AC-14.2 | US-14 | test_dashboard_api.py | test_ac_142_filtri_e_ricerca | Integration | PASS | 2026-03-22 |
| AC-14.3 | US-14 | test_dashboard_api.py | test_ac_143_empty_state | Integration | PASS | 2026-03-22 |
| AC-14.4 | US-14 | test_dashboard_api.py | test_ac_144_paginazione | Integration | PASS | 2026-03-22 |
| AC-14.4 | US-14 | test_dashboard_api.py | test_ac_144_paginazione_page2 | Integration | PASS | 2026-03-22 |

---

**Totale Sprint 2:** 21 test | **PASS:** 21 | **FAIL:** 0

---

## US-11: Verifica e correzione categoria

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-11.1 | US-11 | test_verify_api.py | test_ac_111_conferma_categoria | Integration | PASS | 2026-03-22 |
| AC-11.2 | US-11 | test_verify_api.py | test_ac_112_correzione_categoria | Integration | PASS | 2026-03-22 |
| AC-11.3 | US-11 | test_verify_api.py | test_ac_113_categoria_suggerita | Integration | PASS | 2026-03-22 |
| AC-11.3 | US-11 | test_verify_api.py | test_ac_113_suggest_no_matches | Integration | PASS | 2026-03-22 |
| AC-11.4 | US-11 | test_verify_api.py | test_ac_114_lista_da_verificare | Integration | PASS | 2026-03-22 |
| AC-11.4 | US-11 | test_verify_api.py | test_ac_114_lista_vuota | Integration | PASS | 2026-03-22 |
| AC-11.5 | US-11 | test_verify_api.py | test_ac_115_verifica_concorrente | Integration | PASS | 2026-03-22 |

## US-13: Registrazione automatica scritture partita doppia

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-13.1 | US-13 | test_journal_api.py | test_ac_131_registrazione_fattura_passiva | Integration | PASS | 2026-03-22 |
| AC-13.2 | US-13 | test_journal_api.py | test_ac_132_reverse_charge | Integration | PASS | 2026-03-22 |
| AC-13.3 | US-13 | test_journal_api.py | test_ac_133_conto_mancante | Integration | PASS | 2026-03-22 |
| AC-13.4 | US-13 | test_journal_api.py | test_ac_134_sbilanciamento | Integration | PASS | 2026-03-22 |
| AC-13.5 | US-13 | test_journal_api.py | test_ac_135_multi_aliquota | Integration | PASS | 2026-03-22 |
| AC-13.6 | US-13 | test_journal_api.py | test_ac_136_registrazione_concorrente | Integration | PASS | 2026-03-22 |
| AC-13.6 | US-13 | test_journal_api.py | test_ac_136_idempotency | Integration | PASS | 2026-03-22 |

## US-15: Dashboard scritture contabili

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-15.1 | US-15 | test_journal_dashboard_api.py | test_ac_151_lista_scritture | Integration | PASS | 2026-03-22 |
| AC-15.2 | US-15 | test_journal_dashboard_api.py | test_ac_152_quadratura | Integration | PASS | 2026-03-22 |
| AC-15.3 | US-15 | test_journal_dashboard_api.py | test_ac_153_errore_odoo | Integration | PASS | 2026-03-22 |
| AC-15.4 | US-15 | test_journal_dashboard_api.py | test_ac_154_empty_state | Integration | PASS | 2026-03-22 |
| AC-15.5 | US-15 | test_journal_dashboard_api.py | test_ac_155_filtro_periodo | Integration | PASS | 2026-03-22 |
| AC-15.5 | US-15 | test_journal_dashboard_api.py | test_ac_155_filtro_periodo_vuoto | Integration | PASS | 2026-03-22 |

## US-16: Onboarding guidato

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-16.1 | US-16 | test_onboarding_api.py | test_ac_161_onboarding_wizard | Integration | PASS | 2026-03-22 |
| AC-16.2 | US-16 | test_onboarding_api.py | test_ac_162_time_to_value | Integration | PASS | 2026-03-22 |
| AC-16.3 | US-16 | test_onboarding_api.py | test_ac_163_abbandonato | Integration | PASS | 2026-03-22 |
| AC-16.4 | US-16 | test_onboarding_api.py | test_ac_164_spid_fallisce | Integration | PASS | 2026-03-22 |
| AC-16.5 | US-16 | test_onboarding_api.py | test_ac_165_tipo_altro | Integration | PASS | 2026-03-22 |

---

**Totale Sprint 3:** 25 test | **PASS:** 25 | **FAIL:** 0
**Totale Cumulativo:** 92 test | **PASS:** 92 | **FAIL:** 0
