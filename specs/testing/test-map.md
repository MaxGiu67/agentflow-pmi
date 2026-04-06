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
**Totale Cumulativo (Sprint 1-3):** 92 test | **PASS:** 92 | **FAIL:** 0

---

## Sprint 28-32: Social Selling + User Management (Pivot 8)

### US-130: Admin definisce origine contact custom

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-130 | US-130 | test_social_selling_origins_api.py | test_ac_130_list_origins_seeds_defaults | Integration | PASS | 2026-04-05 |
| AC-130 | US-130 | test_social_selling_origins_api.py | test_ac_130_list_origins_active_only | Integration | PASS | 2026-04-05 |
| AC-130.1 | US-130 | test_social_selling_origins_api.py | test_ac_130_1_create_origin | Integration | PASS | 2026-04-05 |
| AC-130.2 | US-130 | test_social_selling_origins_api.py | test_ac_130_2_duplicate_code_rejected | Integration | PASS | 2026-04-05 |
| AC-130 | US-130 | test_social_selling_origins_api.py | test_ac_130_viewer_cannot_create | Integration | PASS | 2026-04-05 |

### US-131: Admin modifica/disattiva origine

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-131.1 | US-131 | test_social_selling_origins_api.py | test_ac_131_1_update_label | Integration | PASS | 2026-04-05 |
| AC-131.3 | US-131 | test_social_selling_origins_api.py | test_ac_131_3_code_immutable | Integration | PASS | 2026-04-05 |
| AC-131.2 | US-131 | test_social_selling_origins_api.py | test_ac_131_deactivate | Integration | PASS | 2026-04-05 |
| AC-131.4 | US-131 | test_social_selling_origins_api.py | test_ac_131_4_delete_free_origin | Integration | PASS | 2026-04-05 |
| AC-131.4 | US-131 | test_social_selling_origins_api.py | test_ac_131_4_delete_blocked_if_contacts | Integration | PASS | 2026-04-05 |
| AC-131 | US-131 | test_social_selling_origins_api.py | test_ac_131_update_nonexistent | Integration | PASS | 2026-04-05 |
| AC-131 | US-131 | test_social_selling_origins_api.py | test_ac_131_delete_nonexistent | Integration | PASS | 2026-04-05 |

### US-132: Migrare campo source a origine FK

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-132.1 | US-132 | test_social_selling_origins_api.py | test_ac_132_1_migrate_creates_origin | Integration | PASS | 2026-04-05 |
| AC-132.2 | US-132 | test_social_selling_origins_api.py | test_ac_132_2_migrate_idempotent | Integration | PASS | 2026-04-05 |
| AC-132 | US-132 | test_social_selling_origins_api.py | test_ac_132_viewer_cannot_migrate | Integration | PASS | 2026-04-05 |

### US-133: Filtro contatti per origine

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-133 | US-133 | test_social_selling_origins_api.py | test_ac_133_assign_origin | Integration | PASS | 2026-04-05 |
| AC-133 | US-133 | test_social_selling_origins_api.py | test_ac_133_assign_inactive_origin_rejected | Integration | PASS | 2026-04-05 |
| AC-133 | US-133 | test_social_selling_origins_api.py | test_ac_133_assign_nonexistent_contact | Integration | PASS | 2026-04-05 |

### US-134: Admin definisce tipi attivita custom

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-134.1 | US-134 | test_social_selling_epic2_api.py | test_ac_134_1_create_activity_type | Integration | PASS | 2026-04-05 |
| AC-134.2 | US-134 | test_social_selling_epic2_api.py | test_ac_134_2_duplicate_code_rejected | Integration | PASS | 2026-04-05 |
| AC-134.4 | US-134 | test_social_selling_epic2_api.py | test_ac_134_4_invalid_category | Integration | PASS | 2026-04-05 |
| AC-134 | US-134 | test_social_selling_epic2_api.py | test_ac_134_viewer_cannot_create | Integration | PASS | 2026-04-05 |
| AC-134 | US-134 | test_social_selling_epic2_api.py | test_ac_134_list_seeds_defaults | Integration | PASS | 2026-04-05 |
| AC-134 | US-134 | test_social_selling_epic2_api.py | test_ac_134_filter_active_only | Integration | PASS | 2026-04-05 |
| AC-134 | US-134 | test_social_selling_epic2_api.py | test_ac_134_filter_category | Integration | PASS | 2026-04-05 |

### US-135: Admin modifica/disattiva tipo attivita

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-135.1 | US-135 | test_social_selling_epic2_api.py | test_ac_135_1_update_label | Integration | PASS | 2026-04-05 |
| AC-135.2 | US-135 | test_social_selling_epic2_api.py | test_ac_135_2_deactivate | Integration | PASS | 2026-04-05 |
| AC-135.3 | US-135 | test_social_selling_epic2_api.py | test_ac_135_3_hard_delete_returns_409 | Integration | PASS | 2026-04-05 |
| AC-135 | US-135 | test_social_selling_epic2_api.py | test_ac_135_update_nonexistent | Integration | PASS | 2026-04-05 |

### US-136: Pipeline stages + pre-funnel

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-136.1 | US-136 | test_social_selling_epic2_api.py | test_ac_136_1_create_pre_funnel_stage | Integration | PASS | 2026-04-05 |
| AC-136.2 | US-136 | test_social_selling_epic2_api.py | test_ac_136_2_stages_ordered_by_sequence | Integration | PASS | 2026-04-05 |
| AC-136.3 | US-136 | test_social_selling_epic2_api.py | test_ac_136_3_pre_funnel_auto_reorder | Integration | PASS | 2026-04-05 |
| AC-136 | US-136 | test_social_selling_epic2_api.py | test_ac_136_update_stage | Integration | PASS | 2026-04-05 |
| AC-136 | US-136 | test_social_selling_epic2_api.py | test_ac_136_reorder_stages | Integration | PASS | 2026-04-05 |
| AC-136 | US-136 | test_social_selling_epic2_api.py | test_ac_136_viewer_cannot_create | Integration | PASS | 2026-04-05 |

### US-137: Attivita con tipo custom + last_contact

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-137.1 | US-137 | test_social_selling_epic2_api.py | test_ac_137_1_create_activity_with_type | Integration | PASS | 2026-04-05 |
| AC-137.2 | US-137 | test_social_selling_epic2_api.py | test_ac_137_2_last_contact_updated | Integration | PASS | 2026-04-05 |
| AC-137.3 | US-137 | test_social_selling_epic2_api.py | test_ac_137_3_missing_subject_rejected | Integration | PASS | 2026-04-05 |

### US-138: Ruoli CRM custom con matrice permessi

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-138.1 | US-138 | test_social_selling_epic3_api.py | test_ac_138_1_create_role_with_permissions | Integration | PASS | 2026-04-05 |
| AC-138.2 | US-138 | test_social_selling_epic3_api.py | test_ac_138_2_default_roles_seeded | Integration | PASS | 2026-04-05 |
| AC-138 | US-138 | test_social_selling_epic3_api.py | test_ac_138_duplicate_name_rejected | Integration | PASS | 2026-04-05 |
| AC-138 | US-138 | test_social_selling_epic3_api.py | test_ac_138_viewer_cannot_manage_roles | Integration | PASS | 2026-04-05 |
| AC-138 | US-138 | test_social_selling_epic3_api.py | test_ac_138_delete_custom_role | Integration | PASS | 2026-04-05 |
| AC-138 | US-138 | test_social_selling_epic3_api.py | test_ac_138_cannot_delete_system_role | Integration | PASS | 2026-04-05 |
| AC-138 | US-138 | test_social_selling_epic3_api.py | test_ac_138_cannot_delete_role_with_users | Integration | PASS | 2026-04-05 |

### US-141: Audit trail immutabile

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-141.1 | US-141 | test_social_selling_epic3_api.py | test_ac_141_1_list_audit_log | Integration | PASS | 2026-04-05 |
| AC-141 | US-141 | test_social_selling_epic3_api.py | test_ac_141_filter_by_action | Integration | PASS | 2026-04-05 |
| AC-141.4 | US-141 | test_social_selling_epic3_api.py | test_ac_141_4_export_csv | Integration | PASS | 2026-04-05 |
| AC-141 | US-141 | test_social_selling_epic3_api.py | test_ac_141_viewer_cannot_view_audit | Integration | PASS | 2026-04-05 |
| AC-141 | US-141 | test_social_selling_epic3_api.py | test_ac_141_log_action_service | Integration | PASS | 2026-04-05 |
| AC-141.3 | US-141 | test_social_selling_epic3_api.py | test_ac_141_3_permission_denied_logged | Integration | PASS | 2026-04-05 |

### US-142: Catalogo prodotti/servizi

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-142.1 | US-142 | test_social_selling_epic4_api.py | test_ac_142_1_create_product | Integration | PASS | 2026-04-05 |
| AC-142.3 | US-142 | test_social_selling_epic4_api.py | test_ac_142_3_duplicate_code | Integration | PASS | 2026-04-05 |
| AC-142.4 | US-142 | test_social_selling_epic4_api.py | test_ac_142_4_auto_create_category | Integration | PASS | 2026-04-05 |

### US-143: Modifica/disattiva prodotto

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-143.1 | US-143 | test_social_selling_epic4_api.py | test_ac_143_1_update_product | Integration | PASS | 2026-04-05 |
| AC-143.2 | US-143 | test_social_selling_epic4_api.py | test_ac_143_2_deactivate_product | Integration | PASS | 2026-04-05 |
| AC-143.3 | US-143 | test_social_selling_epic4_api.py | test_ac_143_3_hard_delete_409 | Integration | PASS | 2026-04-05 |

### US-144: Prodotti associati a deal

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-144.1 | US-144 | test_social_selling_epic4_api.py | test_ac_144_1_add_product_to_deal | Integration | PASS | 2026-04-05 |
| AC-144.2 | US-144 | test_social_selling_epic4_api.py | test_ac_144_2_revenue_calculation | Integration | PASS | 2026-04-05 |
| AC-144.3 | US-144 | test_social_selling_epic4_api.py | test_ac_144_3_cannot_remove_last_product | Integration | PASS | 2026-04-05 |
| AC-144.4 | US-144 | test_social_selling_epic4_api.py | test_ac_144_4_duplicate_product_allowed | Integration | PASS | 2026-04-05 |
| AC-144 | US-144 | test_social_selling_epic4_api.py | test_ac_144_list_deal_products | Integration | PASS | 2026-04-05 |

### US-146: Dashboard KPI personalizzabile

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-146.1 | US-146 | test_social_selling_epic5_api.py | test_ac_146_1_create_dashboard | Integration | PASS | 2026-04-05 |
| AC-146.3 | US-146 | test_social_selling_epic5_api.py | test_ac_146_3_missing_period_rejected | Integration | PASS | 2026-04-05 |
| AC-146 | US-146 | test_social_selling_epic5_api.py | test_ac_146_list_dashboards | Integration | PASS | 2026-04-05 |

### US-147: Scorecard performance

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-147.1 | US-147 | test_social_selling_epic5_api.py | test_ac_147_1_scorecard_kpis | Integration | PASS | 2026-04-05 |
| AC-147.3 | US-147 | test_social_selling_epic5_api.py | test_ac_147_3_user_no_data | Integration | PASS | 2026-04-05 |

### US-148: Regole compenso configurabili

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-148.1 | US-148 | test_social_selling_epic5_api.py | test_ac_148_1_create_rule | Integration | PASS | 2026-04-05 |
| AC-148.2 | US-148 | test_social_selling_epic5_api.py | test_ac_148_2_tiered_rule | Integration | PASS | 2026-04-05 |
| AC-148 | US-148 | test_social_selling_epic5_api.py | test_ac_148_invalid_method | Integration | PASS | 2026-04-05 |
| AC-148 | US-148 | test_social_selling_epic5_api.py | test_ac_148_list_rules | Integration | PASS | 2026-04-05 |

### US-149: Calcolo compensi mensile

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-149.1 | US-149 | test_social_selling_epic5_api.py | test_ac_149_1_calculate_monthly | Integration | PASS | 2026-04-05 |
| AC-149 | US-149 | test_social_selling_epic5_api.py | test_ac_149_list_monthly | Integration | PASS | 2026-04-05 |

### US-150: Conferma e pagamento compensi

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-150.1 | US-150 | test_social_selling_epic5_api.py | test_ac_150_1_confirm_entry | Integration | PASS | 2026-04-05 |
| AC-150.3 | US-150 | test_social_selling_epic5_api.py | test_ac_150_3_mark_paid | Integration | PASS | 2026-04-05 |
| AC-150 | US-150 | test_social_selling_epic5_api.py | test_ac_150_cannot_pay_draft | Integration | PASS | 2026-04-05 |

### US-109: Gestione utenti con invito

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-109.1 | US-109 | test_sprint32_users_api.py | test_ac_109_1_list_users | Integration | PASS | 2026-04-05 |
| AC-109.2 | US-109 | test_sprint32_users_api.py | test_ac_109_2_invite_user | Integration | PASS | 2026-04-05 |
| AC-109.3 | US-109 | test_sprint32_users_api.py | test_ac_109_3_update_role | Integration | PASS | 2026-04-05 |
| AC-109.4 | US-109 | test_sprint32_users_api.py | test_ac_109_4_toggle_active | Integration | PASS | 2026-04-05 |
| AC-109.5 | US-109 | test_sprint32_users_api.py | test_ac_109_5_only_admin_can_manage | Integration | PASS | 2026-04-05 |
| AC-109 | US-109 | test_sprint32_users_api.py | test_ac_109_cannot_self_modify | Integration | PASS | 2026-04-05 |

### US-110: Row-level security per commerciale

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-110.1 | US-110 | test_sprint32_users_api.py | test_ac_110_1_commerciale_sees_own_deals | Integration | PASS | 2026-04-05 |
| AC-110.2 | US-110 | test_sprint32_users_api.py | test_ac_110_2_commerciale_sees_own_contacts | Integration | PASS | 2026-04-05 |
| AC-110.5 | US-110 | test_sprint32_users_api.py | test_ac_110_5_commerciale_auto_assign | Integration | PASS | 2026-04-05 |

### US-111: Email sender per utente

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| AC-111.1 | US-111 | test_sprint32_users_api.py | test_ac_111_1_sender_per_user | Integration | PASS | 2026-04-05 |
| AC-111.2 | US-111 | test_sprint32_users_api.py | test_ac_111_2_3_sender_fallback | Integration | PASS | 2026-04-05 |

### API Integration (Sprint 32)

| AC ID | Story | Test File | Test Name | Tipo | Status | Last Run |
|-------|-------|-----------|-----------|------|--------|----------|
| — | API | test_sprint32_users_api.py | test_api_list_users | Integration | PASS | 2026-04-05 |
| — | API | test_sprint32_users_api.py | test_api_invite_user | Integration | PASS | 2026-04-05 |
| — | API | test_sprint32_users_api.py | test_api_my_permissions | Integration | PASS | 2026-04-05 |

---

**Totale Sprint 28-32 (Pivot 8):** 87 test | **PASS:** 87 | **FAIL:** 0
**Totale Cumulativo:** 179 test mappati (92 Sprint 1-3 + 87 Pivot 8) | **PASS:** 179 | **FAIL:** 0

> **Nota**: I test di Sprint 4-27 (583 test) sono eseguiti e passano ma non sono ancora dettagliati nel test-map.
> Totale test reali nel progetto: **775 test** tutti PASS.
