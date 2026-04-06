import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCrmContacts, useCreateCrmDeal, useCreateCrmContact, useCrmStages, useActivityTypes, useCreateCrmActivity, usePipelineTemplates, useCrmCompanies, useCreateCrmCompany } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import PageMeta from '../../components/ui/PageMeta'
import { ArrowLeft, Search, Building, PlusCircle } from 'lucide-react'

export default function CrmNewDealPage() {
  const navigate = useNavigate()
  const { data: contactsData } = useCrmContacts('')
  const createDeal = useCreateCrmDeal()
  const createContact = useCreateCrmContact()
  const { data: stages } = useCrmStages()
  const { data: activityTypes } = useActivityTypes(true)
  const createActivity = useCreateCrmActivity()
  const { data: pipelineTemplates } = usePipelineTemplates()

  const [step, setStep] = useState(1)

  // Company autocomplete
  const [companySearch, setCompanySearch] = useState('')
  const [selectedCompanyId, setSelectedCompanyId] = useState('')
  const [selectedCompanyName, setSelectedCompanyName] = useState('')
  const [showCompanyDropdown, setShowCompanyDropdown] = useState(false)
  const [showNewCompany, setShowNewCompany] = useState(false)
  const [newCompanyForm, setNewCompanyForm] = useState({ name: '', vat: '', sector: '', city: '' })

  // Referente
  const [contactSearch, setContactSearch] = useState('')
  const [selectedContactId, setSelectedContactId] = useState('')
  const [selectedContactName, setSelectedContactName] = useState('')
  const [showNewContact, setShowNewContact] = useState(false)
  const [newContact, setNewContact] = useState({ name: '', email: '', phone: '', contact_role: '' })

  // Company hooks — load ALL companies, filter client-side
  const { data: companiesData } = useCrmCompanies('')
  const createCompany = useCreateCrmCompany()
  const allCompanies = (companiesData?.companies || []).sort((a: any, b: any) => a.name.localeCompare(b.name))
  const filteredCompanies = companySearch.length >= 3
    ? allCompanies.filter((c: any) => c.name.toLowerCase().includes(companySearch.toLowerCase()))
    : allCompanies
  const showCompanyAutocomplete = showCompanyDropdown && !selectedCompanyId

  const [name, setName] = useState('')
  const [dealType, setDealType] = useState('T&M')
  const [expectedRevenue, setExpectedRevenue] = useState('')
  const [dailyRate, setDailyRate] = useState('')
  const [estimatedDays, setEstimatedDays] = useState('')
  const [technology, setTechnology] = useState('')

  const [selectedPipeline, setSelectedPipeline] = useState<any>(null)
  const [stageId, setStageId] = useState('')
  const [actSubject, setActSubject] = useState('')
  const [actType, setActType] = useState('call')
  const [actTypeId, setActTypeId] = useState('')
  const [error, setError] = useState('')

  // Auto-calc revenue for T&M
  useEffect(() => {
    if (dealType === 'T&M' && dailyRate && estimatedDays) {
      setExpectedRevenue(String(parseFloat(dailyRate) * parseFloat(estimatedDays)))
    }
  }, [dealType, dailyRate, estimatedDays])

  const filteredContacts = (contactsData?.contacts || []).filter((c: any) => {
    // Se azienda selezionata, mostra solo referenti di quell'azienda
    if (selectedCompanyId && c.company_id && c.company_id !== selectedCompanyId) return false
    // Se azienda selezionata e no search, mostra tutti i referenti dell'azienda
    if (selectedCompanyId && !contactSearch) return true
    // Search
    if (contactSearch.length >= 2) {
      const q = contactSearch.toLowerCase()
      return (c.contact_name || c.name || '').toLowerCase().includes(q) || (c.email || '').toLowerCase().includes(q)
    }
    return selectedCompanyId ? true : false
  })

  const handleSubmit = async () => {
    setError('')
    if (!name.trim()) { setError('Il nome dell\'opportunita e obbligatorio'); return }

    try {
      const deal = await createDeal.mutateAsync({
        name,
        contact_id: selectedContactId || undefined,
        company_id: selectedCompanyId || undefined,
        deal_type: dealType,
        expected_revenue: parseFloat(expectedRevenue) || 0,
        daily_rate: parseFloat(dailyRate) || 0,
        estimated_days: parseFloat(estimatedDays) || 0,
        technology,
        stage_id: stageId || undefined,
        pipeline_template_id: selectedPipeline?.id || undefined,
      })

      // Create initial activity if provided
      if (actSubject.trim()) {
        await createActivity.mutateAsync({
          deal_id: deal.id,
          contact_id: selectedContactId || undefined,
          type: actType,
          activity_type_id: actTypeId || undefined,
          subject: actSubject,
          status: 'completed',
        })
      }

      navigate(`/crm/deals/${deal.id}`)
    } catch {
      setError('Errore nella creazione. Riprova.')
    }
  }

  return (
    <div className="space-y-6">
      <PageMeta title="Nuova opportunita" />
      <PageHeader
        title="Nuova opportunita"
        subtitle={step === 1 ? 'Seleziona o crea il cliente' : 'Dettagli del deal'}
        actions={
          <button onClick={() => navigate('/crm')} className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700">
            <ArrowLeft className="h-4 w-4" /> Torna alla pipeline
          </button>
        }
      />

      {/* Step indicator */}
      <div className="flex gap-2">
        <div className={`h-1.5 flex-1 rounded-full ${step >= 1 ? 'bg-purple-600' : 'bg-gray-200'}`} />
        <div className={`h-1.5 flex-1 rounded-full ${step >= 2 ? 'bg-purple-600' : 'bg-gray-200'}`} />
      </div>

      {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      {step === 1 ? (
        /* ── Step 1: Azienda + Referente (come pagina Contatti) ── */
        <div className="space-y-4">
          <div className="rounded-2xl border border-gray-200 bg-white p-6 space-y-5">

            {/* 1. Azienda (autocomplete) */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">1. Azienda</h3>
              {selectedCompanyId ? (
                <div className="flex items-center justify-between rounded-lg bg-blue-50 border border-blue-200 p-3">
                  <div className="flex items-center gap-2">
                    <Building className="h-4 w-4 text-blue-600" />
                    <span className="font-medium text-blue-900">{selectedCompanyName}</span>
                  </div>
                  <button onClick={() => { setSelectedCompanyId(''); setSelectedCompanyName(''); setCompanySearch('') }}
                    className="text-xs text-blue-600 hover:underline">Cambia</button>
                </div>
              ) : showNewCompany ? (
                <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 space-y-2">
                  <p className="text-xs font-medium text-gray-500">Nuova azienda</p>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <input value={newCompanyForm.name} onChange={(e) => setNewCompanyForm({ ...newCompanyForm, name: e.target.value })}
                      placeholder="Ragione sociale *" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                    <input value={newCompanyForm.vat} onChange={(e) => setNewCompanyForm({ ...newCompanyForm, vat: e.target.value })}
                      placeholder="P.IVA" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                    <input value={newCompanyForm.sector} onChange={(e) => setNewCompanyForm({ ...newCompanyForm, sector: e.target.value })}
                      placeholder="Settore" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                    <input value={newCompanyForm.city} onChange={(e) => setNewCompanyForm({ ...newCompanyForm, city: e.target.value })}
                      placeholder="Citta" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                  </div>
                  <div className="flex gap-2">
                    <button onClick={async () => {
                      if (!newCompanyForm.name) return
                      const c = await createCompany.mutateAsync(newCompanyForm)
                      setSelectedCompanyId(c.id); setSelectedCompanyName(c.name)
                      setShowNewCompany(false); setNewCompanyForm({ name: '', vat: '', sector: '', city: '' })
                    }} disabled={!newCompanyForm.name}
                      className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50">Crea azienda</button>
                    <button onClick={() => setShowNewCompany(false)}
                      className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-600">Annulla</button>
                  </div>
                </div>
              ) : (
                <div className="relative">
                  <input value={companySearch}
                    onChange={(e) => { setCompanySearch(e.target.value); setShowCompanyDropdown(true) }}
                    onFocus={() => setShowCompanyDropdown(true)}
                    placeholder="Clicca per vedere tutte — o digita 3+ caratteri per cercare..."
                    className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm" />
                  {showCompanyAutocomplete && (
                    <div className="absolute z-10 mt-1 w-full rounded-lg border border-gray-200 bg-white shadow-lg max-h-48 overflow-y-auto">
                      {filteredCompanies.map((c: any) => (
                        <button key={c.id} onClick={() => {
                          setSelectedCompanyId(c.id); setSelectedCompanyName(c.name)
                          setCompanySearch(c.name); setShowCompanyDropdown(false)
                        }}
                          className="w-full flex items-center gap-2 px-3 py-2.5 text-left text-sm hover:bg-blue-50 border-b border-gray-100 last:border-0">
                          <Building className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
                          <span className="font-medium">{c.name}</span>
                          {c.city && <span className="text-xs text-gray-400">— {c.city}</span>}
                        </button>
                      ))}
                    </div>
                  )}
                  {companySearch.length >= 3 && filteredCompanies.length === 0 && showCompanyDropdown && (
                    <div className="absolute z-10 mt-1 w-full rounded-lg border border-gray-200 bg-white shadow-lg p-3">
                      <p className="text-xs text-gray-500 mb-2">Nessuna azienda trovata</p>
                      <button onClick={() => { setShowNewCompany(true); setShowCompanyDropdown(false); setNewCompanyForm({ ...newCompanyForm, name: companySearch }) }}
                        className="inline-flex items-center gap-1 text-xs font-medium text-blue-600">
                        <PlusCircle className="h-3.5 w-3.5" /> Crea "{companySearch}"
                      </button>
                    </div>
                  )}
                  <button onClick={() => setShowNewCompany(true)}
                    className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-blue-600">
                    <PlusCircle className="h-3.5 w-3.5" /> Crea nuova azienda
                  </button>
                </div>
              )}
            </div>

            {/* 2. Referente (come pagina Contatti) */}
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">2. Referente</h3>

              {selectedContactId ? (
                <div className="flex items-center justify-between rounded-lg bg-purple-50 border border-purple-200 p-3">
                  <div>
                    <p className="font-medium text-purple-900">{selectedContactName}</p>
                    <p className="text-xs text-purple-500">Referente selezionato</p>
                  </div>
                  <button onClick={() => { setSelectedContactId(''); setSelectedContactName('') }}
                    className="text-xs text-purple-600 hover:underline">Cambia</button>
                </div>
              ) : (
                <>
                  {/* Cerca referente esistente */}
                  <div className="relative mb-2">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                    <input value={contactSearch} onChange={(e) => setContactSearch(e.target.value)}
                      placeholder={selectedCompanyId ? `Cerca referente di ${selectedCompanyName}...` : "Seleziona prima un'azienda"}
                      className="w-full rounded-lg border border-gray-300 pl-10 pr-4 py-2 text-sm" />
                  </div>

                  {/* Mostra referenti dell'azienda selezionata (o risultati ricerca) */}
                  {filteredContacts.length > 0 && (
                    <div className="max-h-36 overflow-y-auto space-y-1 mb-2">
                      {filteredContacts.map((c: any) => (
                        <button key={c.id} onClick={() => { setSelectedContactId(c.id); setSelectedContactName(c.contact_name || c.name) }}
                          className="w-full flex items-center justify-between rounded-lg border border-gray-200 px-3 py-2 text-left text-sm hover:bg-gray-50">
                          <div>
                            <p className="font-medium text-gray-900">{c.contact_name || c.name}</p>
                            {c.contact_role && <span className="text-xs text-gray-500"> — {c.contact_role}</span>}
                            <p className="text-xs text-gray-400">{c.name}{c.email ? ` · ${c.email}` : ''}</p>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                  {selectedCompanyId && filteredContacts.length === 0 && !contactSearch && (
                    <p className="text-xs text-gray-400 mb-2">Nessun referente per {selectedCompanyName}. Creane uno nuovo.</p>
                  )}

                  {/* Crea nuovo referente */}
                  {showNewContact ? (
                    <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 space-y-2">
                      <p className="text-xs font-medium text-gray-500">Nuovo referente</p>
                      <div className="grid gap-2 sm:grid-cols-2">
                        <input value={newContact.name} onChange={(e) => setNewContact({ ...newContact, name: e.target.value })}
                          placeholder="Nome e cognome *" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                        <input value={newContact.contact_role} onChange={(e) => setNewContact({ ...newContact, contact_role: e.target.value })}
                          placeholder="Ruolo (es. CEO, CTO)" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                        <input value={newContact.email} onChange={(e) => setNewContact({ ...newContact, email: e.target.value })}
                          placeholder="Email" type="email" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                        <input value={newContact.phone} onChange={(e) => setNewContact({ ...newContact, phone: e.target.value })}
                          placeholder="Telefono" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                      </div>
                      <div className="flex gap-2">
                        <button onClick={async () => {
                          if (!newContact.name) return
                          const result = await createContact.mutateAsync({
                            name: selectedCompanyName || newContact.name,
                            company_id: selectedCompanyId || undefined,
                            contact_name: newContact.name,
                            contact_role: newContact.contact_role,
                            email: newContact.email,
                            phone: newContact.phone,
                          })
                          setSelectedContactId(result.id)
                          setSelectedContactName(newContact.name)
                          setShowNewContact(false)
                          setNewContact({ name: '', email: '', phone: '', contact_role: '' })
                        }} disabled={!newContact.name}
                          className="rounded-lg bg-purple-600 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50">Crea referente</button>
                        <button onClick={() => setShowNewContact(false)}
                          className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-600">Annulla</button>
                      </div>
                    </div>
                  ) : (
                    <button onClick={() => setShowNewContact(true)}
                      className="inline-flex items-center gap-1 text-xs font-medium text-purple-600">
                      <PlusCircle className="h-3.5 w-3.5" /> Crea nuovo referente
                    </button>
                  )}
                </>
              )}
            </div>
          </div>

          <button onClick={() => setStep(2)}
            className="w-full rounded-lg bg-purple-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-purple-700">
            Continua
          </button>

          <button onClick={() => setStep(2)} className="w-full text-center text-sm text-gray-400 hover:text-gray-600">
            Salta — crea deal senza cliente
          </button>
        </div>
      ) : (
        /* ── Step 2: Dettagli deal ── */
        <div className="space-y-4">
          <div className="rounded-2xl border border-gray-200 bg-white p-6 space-y-4">
            <h3 className="font-semibold text-gray-900">Dettagli opportunita</h3>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Nome opportunita *</label>
              <input value={name} onChange={(e) => setName(e.target.value)}
                placeholder="es. Migrazione SAP S/4HANA per Acme SPA"
                className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-purple-500 focus:ring-1 focus:ring-purple-500 focus:outline-none" />
            </div>

            {/* Cosa vendi? — 3 bottoni grandi + Altro */}
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Cosa vendi?</label>
              <div className="grid gap-3 sm:grid-cols-4">
                <button onClick={() => { setDealType('T&M'); setSelectedPipeline(pipelineTemplates?.find((t: any) => t.code === 'vendita_diretta') || null) }}
                  className={`rounded-xl border-2 p-4 text-left transition-all ${
                    dealType === 'T&M' ? 'border-purple-500 bg-purple-50 ring-2 ring-purple-200' : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                  }`}>
                  <p className="text-2xl mb-1">🤝</p>
                  <p className="text-sm font-semibold text-gray-900">Consulenza</p>
                  <p className="text-xs text-gray-500 mt-0.5">T&M, staff augmentation, servizi</p>
                  <p className="text-[10px] text-purple-600 mt-2 font-medium">Pipeline: Vendita Diretta</p>
                </button>

                <button onClick={() => { setDealType('fixed'); setSelectedPipeline(pipelineTemplates?.find((t: any) => t.code === 'progetto_corpo') || null) }}
                  className={`rounded-xl border-2 p-4 text-left transition-all ${
                    dealType === 'fixed' ? 'border-purple-500 bg-purple-50 ring-2 ring-purple-200' : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                  }`}>
                  <p className="text-2xl mb-1">📋</p>
                  <p className="text-sm font-semibold text-gray-900">Progetto a corpo</p>
                  <p className="text-xs text-gray-500 mt-0.5">Prezzo fisso, specifiche, milestone</p>
                  <p className="text-[10px] text-purple-600 mt-2 font-medium">Pipeline: Progetto a Corpo</p>
                </button>

                <button onClick={() => { setDealType('spot'); setSelectedPipeline(pipelineTemplates?.find((t: any) => t.code === 'social_selling') || null) }}
                  className={`rounded-xl border-2 p-4 text-left transition-all ${
                    dealType === 'spot' ? 'border-purple-500 bg-purple-50 ring-2 ring-purple-200' : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                  }`}>
                  <p className="text-2xl mb-1">🤖</p>
                  <p className="text-sm font-semibold text-gray-900">Elevia / Prodotto</p>
                  <p className="text-xs text-gray-500 mt-0.5">Prodotto AI, licenze, SaaS</p>
                  <p className="text-[10px] text-purple-600 mt-2 font-medium">Pipeline: Social Selling</p>
                </button>

                <button onClick={() => { setDealType('hardware'); setSelectedPipeline(pipelineTemplates?.find((t: any) => t.code === 'vendita_diretta') || null) }}
                  className={`rounded-xl border-2 p-4 text-left transition-all ${
                    dealType === 'hardware' ? 'border-purple-500 bg-purple-50 ring-2 ring-purple-200' : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                  }`}>
                  <p className="text-2xl mb-1">📦</p>
                  <p className="text-sm font-semibold text-gray-900">Altro</p>
                  <p className="text-xs text-gray-500 mt-0.5">Hardware, licenze, una tantum</p>
                  <p className="text-[10px] text-purple-600 mt-2 font-medium">Pipeline: Vendita Diretta</p>
                </button>
              </div>

            </div>

            {/* Campi specifici per Consulenza T&M */}
            {dealType === 'T&M' && (
              <div className="rounded-lg border border-purple-100 bg-purple-50/30 p-3 space-y-3">
                <p className="text-xs font-medium text-purple-700">Dettagli consulenza</p>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className="mb-1 block text-xs text-gray-600">Tariffa giornaliera (EUR)</label>
                    <input type="number" value={dailyRate} onChange={(e) => setDailyRate(e.target.value)}
                      placeholder="500" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-gray-600">Giorni stimati</label>
                    <input type="number" value={estimatedDays} onChange={(e) => setEstimatedDays(e.target.value)}
                      placeholder="60" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                  </div>
                </div>
              </div>
            )}

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Valore atteso (EUR) {dealType === 'T&M' && dailyRate && estimatedDays ? '(calcolato)' : ''}
              </label>
              <input type="number" value={expectedRevenue} onChange={(e) => setExpectedRevenue(e.target.value)}
                placeholder="30000" className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm" />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Tecnologia / Stack</label>
              <input value={technology} onChange={(e) => setTechnology(e.target.value)}
                placeholder="es. Java, SAP, .NET, React..."
                className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm" />
            </div>

            {/* Stage selector */}
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Fase pipeline</label>
              <select value={stageId} onChange={(e) => setStageId(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm">
                <option value="">Nuovo Lead (default)</option>
                {stages?.map((s: any) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.probability}%){s.stage_type === 'pre_funnel' ? ' — pre-funnel' : ''}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-gray-400">Scegli "Prospect" se e un contatto freddo, "Nuovo Lead" se ha gia mostrato interesse</p>
            </div>
          </div>

          {/* Initial activity (optional) */}
          <div className="rounded-2xl border border-gray-200 bg-white p-6 space-y-4">
            <div>
              <h3 className="font-semibold text-gray-900">Prima attivita (opzionale)</h3>
              <p className="text-xs text-gray-400 mt-0.5">Come hai conosciuto questo contatto? Registra la prima interazione.</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <select value={actType} onChange={(e) => setActType(e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2.5 text-sm">
                <option value="call">Chiamata</option>
                <option value="meeting">Incontro</option>
                <option value="email">Email</option>
                <option value="note">Nota</option>
              </select>
              <select value={actTypeId} onChange={(e) => setActTypeId(e.target.value)}
                className="rounded-lg border border-gray-300 px-3 py-2.5 text-sm">
                <option value="">-- Tipo specifico --</option>
                {activityTypes?.map((t: any) => (
                  <option key={t.id} value={t.id}>{t.label}</option>
                ))}
              </select>
            </div>
            <input value={actSubject} onChange={(e) => setActSubject(e.target.value)}
              placeholder="es. Incontro a SMAU Milano — interesse per gestionale"
              className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm" />
          </div>

          <div className="flex gap-3">
            <button onClick={() => setStep(1)}
              className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-50">
              Indietro
            </button>
            <button onClick={handleSubmit} disabled={createDeal.isPending || !name.trim()}
              className="flex-1 rounded-lg bg-purple-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50">
              {createDeal.isPending ? 'Creazione...' : 'Crea opportunita'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
