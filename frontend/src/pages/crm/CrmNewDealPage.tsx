import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCrmContacts, useCreateCrmDeal, useCreateCrmContact, useCrmStages, useActivityTypes, useCreateCrmActivity, useProducts, usePipelineTemplates } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import PageMeta from '../../components/ui/PageMeta'
import { ArrowLeft, Plus, Search } from 'lucide-react'

const DEAL_TYPES = [
  { value: 'T&M', label: 'Time & Material', desc: 'Tariffa giornaliera x giorni' },
  { value: 'fixed', label: 'Progetto fisso', desc: 'Importo a corpo' },
  { value: 'spot', label: 'Spot / Una tantum', desc: 'Consulenza breve' },
  { value: 'hardware', label: 'Hardware / Licenze', desc: 'Vendita prodotti' },
]

export default function CrmNewDealPage() {
  const navigate = useNavigate()
  const { data: contactsData } = useCrmContacts('')
  const createDeal = useCreateCrmDeal()
  const createContact = useCreateCrmContact()
  const { data: stages } = useCrmStages()
  const { data: activityTypes } = useActivityTypes(true)
  const createActivity = useCreateCrmActivity()
  const { data: products } = useProducts(true)
  const { data: pipelineTemplates } = usePipelineTemplates()

  const [step, setStep] = useState(1)
  const [contactSearch, setContactSearch] = useState('')
  const [selectedContactId, setSelectedContactId] = useState('')
  const [selectedContactName, setSelectedContactName] = useState('')
  const [showNewContact, setShowNewContact] = useState(false)
  const [newContact, setNewContact] = useState({ name: '', email: '', vat: '', phone: '' })

  const [name, setName] = useState('')
  const [dealType, setDealType] = useState('T&M')
  const [expectedRevenue, setExpectedRevenue] = useState('')
  const [dailyRate, setDailyRate] = useState('')
  const [estimatedDays, setEstimatedDays] = useState('')
  const [technology, setTechnology] = useState('')

  const [productId, setProductId] = useState('')
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

  const filteredContacts = contactsData?.contacts?.filter((c: any) =>
    c.name.toLowerCase().includes(contactSearch.toLowerCase()) ||
    (c.vat && c.vat.includes(contactSearch))
  ) || []

  const handleCreateContact = async () => {
    if (!newContact.name) return
    const result = await createContact.mutateAsync(newContact)
    setSelectedContactId(result.id)
    setSelectedContactName(result.name)
    setShowNewContact(false)
    setStep(2)
  }

  const handleSubmit = async () => {
    setError('')
    if (!name.trim()) { setError('Il nome dell\'opportunita e obbligatorio'); return }

    try {
      const selectedProduct = products?.find((p: any) => p.id === productId)
      const deal = await createDeal.mutateAsync({
        name,
        contact_id: selectedContactId || undefined,
        deal_type: dealType,
        expected_revenue: parseFloat(expectedRevenue) || 0,
        daily_rate: parseFloat(dailyRate) || 0,
        estimated_days: parseFloat(estimatedDays) || 0,
        technology,
        stage_id: stageId || undefined,
        pipeline_template_id: selectedProduct?.pipeline_template_id || undefined,
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
        /* ── Step 1: Seleziona cliente ── */
        <div className="space-y-4">
          <div className="rounded-2xl border border-gray-200 bg-white p-6 space-y-4">
            <h3 className="font-semibold text-gray-900">Cliente</h3>

            {selectedContactId ? (
              <div className="flex items-center justify-between rounded-lg bg-purple-50 border border-purple-200 p-4">
                <div>
                  <p className="font-medium text-purple-900">{selectedContactName}</p>
                  <p className="text-xs text-purple-500">Cliente selezionato</p>
                </div>
                <button onClick={() => { setSelectedContactId(''); setSelectedContactName('') }}
                  className="text-sm text-purple-600 hover:underline">Cambia</button>
              </div>
            ) : (
              <>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                  <input value={contactSearch} onChange={(e) => setContactSearch(e.target.value)}
                    placeholder="Cerca cliente per nome o P.IVA..."
                    className="w-full rounded-lg border border-gray-300 pl-10 pr-4 py-2.5 text-sm focus:border-purple-500 focus:ring-1 focus:ring-purple-500 focus:outline-none" />
                </div>

                <div className="max-h-48 overflow-y-auto space-y-1">
                  {filteredContacts.map((c: any) => (
                    <button key={c.id} onClick={() => { setSelectedContactId(c.id); setSelectedContactName(c.name); setStep(2) }}
                      className="w-full flex items-center justify-between rounded-lg border border-gray-200 px-4 py-2.5 text-left text-sm hover:bg-gray-50 transition-colors">
                      <div>
                        <p className="font-medium text-gray-900">{c.name}</p>
                        {c.vat && <p className="text-xs text-gray-400">P.IVA: {c.vat}</p>}
                      </div>
                      <span className="text-xs text-gray-400">{c.type}</span>
                    </button>
                  ))}
                  {filteredContacts.length === 0 && contactSearch && (
                    <p className="py-4 text-center text-sm text-gray-400">Nessun cliente trovato</p>
                  )}
                </div>

                <div className="border-t border-gray-100 pt-4">
                  {showNewContact ? (
                    <div className="space-y-3">
                      <h4 className="text-sm font-medium text-gray-700">Nuovo cliente</h4>
                      <div className="grid gap-3 sm:grid-cols-2">
                        <input value={newContact.name} onChange={(e) => setNewContact({ ...newContact, name: e.target.value })}
                          placeholder="Ragione sociale *" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                        <input value={newContact.vat} onChange={(e) => setNewContact({ ...newContact, vat: e.target.value })}
                          placeholder="P.IVA" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                        <input value={newContact.email} onChange={(e) => setNewContact({ ...newContact, email: e.target.value })}
                          placeholder="Email" type="email" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                        <input value={newContact.phone} onChange={(e) => setNewContact({ ...newContact, phone: e.target.value })}
                          placeholder="Telefono" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                      </div>
                      <div className="flex gap-2">
                        <button onClick={handleCreateContact} disabled={!newContact.name}
                          className="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">Crea e continua</button>
                        <button onClick={() => setShowNewContact(false)}
                          className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600">Annulla</button>
                      </div>
                    </div>
                  ) : (
                    <button onClick={() => setShowNewContact(true)}
                      className="inline-flex items-center gap-2 text-sm font-medium text-purple-600 hover:text-purple-700">
                      <Plus className="h-4 w-4" /> Crea nuovo cliente
                    </button>
                  )}
                </div>
              </>
            )}
          </div>

          {selectedContactId && (
            <button onClick={() => setStep(2)}
              className="w-full rounded-lg bg-purple-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-purple-700">
              Continua
            </button>
          )}

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

            {/* Prodotto → Pipeline (US-201) */}
            {products && products.length > 0 && (
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Prodotto (determina la pipeline)</label>
                <select value={productId}
                  onChange={(e) => {
                    setProductId(e.target.value)
                    const prod = products.find((p: any) => p.id === e.target.value)
                    if (prod?.pipeline_template_id && pipelineTemplates) {
                      const tmpl = pipelineTemplates.find((t: any) => t.id === prod.pipeline_template_id)
                      setSelectedPipeline(tmpl || null)
                    } else {
                      setSelectedPipeline(null)
                    }
                  }}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm">
                  <option value="">— Seleziona prodotto (opzionale) —</option>
                  {products.map((p: any) => (
                    <option key={p.id} value={p.id}>{p.name} ({p.pricing_model})</option>
                  ))}
                </select>
                {selectedPipeline && (
                  <p className="mt-1 text-xs text-purple-600">
                    Pipeline: {selectedPipeline.name} ({selectedPipeline.stage_count} stati)
                  </p>
                )}
              </div>
            )}

            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700">Tipo</label>
              <div className="grid gap-2 sm:grid-cols-2">
                {DEAL_TYPES.map((t) => (
                  <button key={t.value} onClick={() => setDealType(t.value)}
                    className={`rounded-lg border p-3 text-left transition-colors ${
                      dealType === t.value ? 'border-purple-500 bg-purple-50 ring-1 ring-purple-200' : 'border-gray-200 hover:bg-gray-50'
                    }`}>
                    <p className="text-sm font-medium text-gray-900">{t.label}</p>
                    <p className="text-xs text-gray-400">{t.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            {dealType === 'T&M' && (
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Tariffa giornaliera (EUR)</label>
                  <input type="number" value={dailyRate} onChange={(e) => setDailyRate(e.target.value)}
                    placeholder="500" className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm" />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Giorni stimati</label>
                  <input type="number" value={estimatedDays} onChange={(e) => setEstimatedDays(e.target.value)}
                    placeholder="60" className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm" />
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
