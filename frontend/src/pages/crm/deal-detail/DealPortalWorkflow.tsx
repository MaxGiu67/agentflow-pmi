import { useState } from 'react'
import {
  useCreatePortalOffer, usePortalProjectTypes, usePortalLocations,
  usePortalAccountManagers, useMyPortalAccountManager,
  usePortalProtocolByCustomer, useDealProject,
  useApproveOffer, usePortalActivityTypes, useCreatePortalActivityOnProject,
  useAssignEmployeeToActivity, usePortalOffer, usePortalPersons,
} from '../../../api/hooks'
import { useUIHighlights, AIHighlightTooltip } from '../../../context/UIHighlightContext'
import { Send, Loader2, CheckCircle, Plus, X } from 'lucide-react'

interface DealPortalWorkflowProps {
  deal: any
  dealId: string
  portalEnabled: boolean
  accountManagers: any[] | undefined
}

export default function DealPortalWorkflow({ deal, dealId, portalEnabled, accountManagers: _parentAM }: DealPortalWorkflowProps) {
  const createPortalOffer = useCreatePortalOffer()
  const { data: projectTypes } = usePortalProjectTypes()
  const { data: locations } = usePortalLocations()
  const { data: accountManagers } = usePortalAccountManagers()
  const { data: myAccountManager } = useMyPortalAccountManager()
  const { data: autoProtocol } = usePortalProtocolByCustomer(deal?.portal_customer_id || undefined)
  const { data: dealProject } = useDealProject(dealId, deal?.portal_project_id || undefined)

  const approveOffer = useApproveOffer()
  const { data: portalActivityTypes } = usePortalActivityTypes()
  const createPortalActivity = useCreatePortalActivityOnProject()
  const assignEmployeeToActivity = useAssignEmployeeToActivity()
  const { data: portalOfferData } = usePortalOffer(deal?.portal_offer_id || undefined)

  const { getHighlight, clearHighlights } = useUIHighlights()
  const offerSectionHL = getHighlight('section', 'offer')
  const createOfferBtnHL = getHighlight('button', 'create-offer')

  const [showOfferForm, setShowOfferForm] = useState(false)
  const [offerForm, setOfferForm] = useState({
    title: '', billing_type: 'Daily', rate: '', days: '', amount: '', description: '',
    project_type_id: '', location_id: '', accountManager_id: '', protocol: '',
    outcome_type: 'W', deadline_date: '', noCollective: false,
  })

  const [showApproveForm, setShowApproveForm] = useState(false)
  const [approveForm, setApproveForm] = useState({ start_date: '', end_date: '', orderNum: '' })

  const [showPortalActivityForm, setShowPortalActivityForm] = useState(false)
  const [portalActivityForm, setPortalActivityForm] = useState({
    description: '', activity_type_id: '9', accountManager_id: '',
    start_date: '', end_date: '', allowance: false,
  })

  const [showPortalAssignForm, setShowPortalAssignForm] = useState<number | null>(null)
  const [portalAssignForm, setPortalAssignForm] = useState({
    person_id: '', person_name: '', start_date: '', end_date: '', expectedDays: '',
  })
  const [portalPersonSearch, setPortalPersonSearch] = useState('')
  const { data: portalSearchedPersons } = usePortalPersons(portalPersonSearch)

  if (!portalEnabled) return null

  return (
    <div className={`rounded-2xl border border-indigo-200 bg-indigo-50/30 p-6 space-y-5 ${offerSectionHL ? (offerSectionHL.style === 'glow' ? 'ai-highlight-glow' : 'ai-highlight-pulse') : ''}`}
      style={offerSectionHL ? { '--ai-color': offerSectionHL.color } as React.CSSProperties : undefined}>
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold uppercase text-indigo-500">Operativo Portal</h3>
          <p className="text-xs text-gray-400 mt-0.5">Flusso: Offerta &rarr; Commessa &rarr; Attivita &rarr; Dipendente</p>
        </div>
      </div>

      {/* ── Step 1: Create Offer ── */}
      {!deal.portal_offer_id && !showOfferForm && deal.portal_customer_id && (
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700">1</span>
              <span className="text-sm font-medium text-gray-700">Crea Offerta su Portal</span>
            </div>
            <button onClick={() => {
              setOfferForm({
                title: deal.name,
                billing_type: deal.deal_type === 'T&M' ? 'Daily' : 'LumpSum',
                rate: String(deal.daily_rate || ''),
                days: String(deal.estimated_days || ''),
                amount: String(deal.expected_revenue || ''),
                description: `Deal AgentFlow: ${deal.name}`,
                project_type_id: '',
                location_id: locations?.[0]?.id ? String(locations[0].id) : '',
                accountManager_id: myAccountManager?.id ? String(myAccountManager.id) : '',
                protocol: autoProtocol || '',
                outcome_type: 'W', deadline_date: '', noCollective: false,
              })
              setShowOfferForm(true)
            }}
              className={`inline-flex items-center gap-1 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 ${createOfferBtnHL ? 'ai-highlight-glow' : ''}`}
              style={createOfferBtnHL ? { '--ai-color': createOfferBtnHL.color } as React.CSSProperties : undefined}>
              <Send className="h-3 w-3" /> Crea Offerta
            </button>
            {createOfferBtnHL && <AIHighlightTooltip highlight={createOfferBtnHL} onDismiss={clearHighlights} />}
          </div>
        </div>
      )}

      {!deal.portal_customer_id && !deal.portal_offer_id && (
        <p className="text-xs text-amber-600 bg-amber-50 rounded-lg px-3 py-2">Seleziona un cliente da Portal nel deal per creare l'offerta</p>
      )}

      {/* Offer creation form */}
      {showOfferForm && (
        <div className="rounded-lg border border-indigo-200 bg-white p-4 space-y-3">
          <p className="text-xs font-medium text-indigo-700">Conferma dati offerta per Portal</p>
          <div className="rounded-lg bg-indigo-50 px-3 py-2">
            <p className="text-[10px] uppercase text-indigo-400 font-medium">Protocollo (auto)</p>
            <p className="text-sm font-mono text-indigo-700">{offerForm.protocol || autoProtocol || 'Caricamento...'}</p>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            <input type="text" value={offerForm.title} onChange={(e) => setOfferForm({ ...offerForm, title: e.target.value })}
              placeholder="Titolo offerta *" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <select value={offerForm.billing_type} onChange={(e) => setOfferForm({ ...offerForm, billing_type: e.target.value })}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              <option value="Daily">Giornaliera (T&M)</option>
              <option value="LumpSum">A corpo (Fixed)</option>
              <option value="None">Nessuna</option>
            </select>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            <select value={offerForm.project_type_id} onChange={(e) => setOfferForm({ ...offerForm, project_type_id: e.target.value })}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              <option value="">Tipo offerta *</option>
              {(projectTypes || []).map((pt: any) => (
                <option key={pt.id} value={pt.id}>{pt.description || pt.code}</option>
              ))}
            </select>
            <select value={offerForm.location_id} onChange={(e) => setOfferForm({ ...offerForm, location_id: e.target.value })}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              <option value="">Sede *</option>
              {(locations || []).map((loc: any) => (
                <option key={loc.id} value={loc.id}>{loc.description || loc.code}</option>
              ))}
            </select>
          </div>
          <div>
            <select value={offerForm.accountManager_id} onChange={(e) => setOfferForm({ ...offerForm, accountManager_id: e.target.value })}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
              <option value="">Commerciale di riferimento *</option>
              {(accountManagers || []).map((am: any) => (
                <option key={am.id} value={am.id}>{am.name || am.email}</option>
              ))}
            </select>
            {myAccountManager?.id && offerForm.accountManager_id === String(myAccountManager.id) && (
              <p className="text-[10px] text-green-600 mt-1">Auto-assegnato: {myAccountManager.name} ({myAccountManager.email})</p>
            )}
          </div>
          {offerForm.billing_type === 'Daily' && (
            <div className="grid gap-2 sm:grid-cols-2">
              <input type="number" value={offerForm.rate} onChange={(e) => setOfferForm({ ...offerForm, rate: e.target.value })}
                placeholder="Tariffa giornaliera (EUR)" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              <input type="number" value={offerForm.days} onChange={(e) => setOfferForm({ ...offerForm, days: e.target.value })}
                placeholder="Giorni offerti" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
          )}
          {offerForm.billing_type === 'LumpSum' && (
            <input type="number" value={offerForm.amount} onChange={(e) => setOfferForm({ ...offerForm, amount: e.target.value })}
              placeholder="Importo fisso (EUR)" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          )}
          <textarea value={offerForm.description} onChange={(e) => setOfferForm({ ...offerForm, description: e.target.value })}
            placeholder="Descrizione / Note" rows={2} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          <div className="flex gap-2">
            <button onClick={async () => {
              const protocol = offerForm.protocol || autoProtocol || ''
              const payload: Record<string, unknown> = {
                project_code: protocol, name: offerForm.title, other_details: offerForm.description,
                billing_type: offerForm.billing_type, customer_id: deal.portal_customer_id,
                accountManager_id: parseInt(offerForm.accountManager_id),
                project_type_id: parseInt(offerForm.project_type_id),
                location_id: parseInt(offerForm.location_id),
                rate: offerForm.rate ? parseFloat(offerForm.rate) : undefined,
                days: offerForm.days ? parseInt(offerForm.days) : undefined,
                amount: offerForm.amount ? parseFloat(offerForm.amount) : undefined,
                OutcomeType: 'W', year: new Date().getFullYear(),
              }
              await createPortalOffer.mutateAsync(payload)
              setShowOfferForm(false)
            }} disabled={!offerForm.title.trim() || !offerForm.project_type_id || !offerForm.location_id || !offerForm.accountManager_id || createPortalOffer.isPending}
              className="inline-flex items-center gap-1 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
              {createPortalOffer.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
              Crea Offerta
            </button>
            <button onClick={() => setShowOfferForm(false)}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600">Annulla</button>
          </div>
          {createPortalOffer.isError && (
            <p className="text-xs text-red-600">Errore: {String((createPortalOffer.error as any)?.message || 'Errore creazione offerta')}</p>
          )}
        </div>
      )}

      {/* ── Offerta esistente ── */}
      {deal.portal_offer_id && (
        <div className="rounded-lg border border-indigo-100 bg-white p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700">1</span>
              <span className="text-sm font-medium text-gray-800">
                Offerta #{deal.portal_offer_id}
                {portalOfferData?.name ? ` "${portalOfferData.name}"` : ''}
              </span>
              <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                (portalOfferData?.OutcomeType || 'W') === 'P' ? 'bg-green-100 text-green-700' :
                (portalOfferData?.OutcomeType || 'W') === 'W' ? 'bg-yellow-100 text-yellow-700' :
                (portalOfferData?.OutcomeType || 'W') === 'N' ? 'bg-red-100 text-red-700' :
                'bg-gray-100 text-gray-600'
              }`}>
                {(portalOfferData?.OutcomeType || 'W') === 'W' ? 'In Attesa' :
                 (portalOfferData?.OutcomeType) === 'P' ? 'Positivo' :
                 (portalOfferData?.OutcomeType) === 'N' ? 'Negativo' :
                 (portalOfferData?.OutcomeType) || 'In Attesa'}
              </span>
            </div>
            {deal.portal_offer_id && !deal.portal_project_id && (
              <button onClick={() => {
                setApproveForm({ start_date: '', end_date: '', orderNum: '' })
                setShowApproveForm(true)
              }}
                className="inline-flex items-center gap-1 rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700">
                <CheckCircle className="h-3 w-3" /> Approva &rarr; Crea Commessa
              </button>
            )}
          </div>

          {/* Approve Offer Dialog */}
          {showApproveForm && (
            <div className="rounded-lg border border-green-200 bg-green-50/50 p-4 space-y-3">
              <p className="text-xs font-medium text-green-800">Approva l'offerta e crea la commessa su Portal</p>
              <p className="text-[10px] text-green-600">L'offerta passera da "In Attesa" (W) a "Positivo" (P), generando automaticamente una commessa.</p>
              <div className="grid gap-2 sm:grid-cols-3">
                <div>
                  <label className="block text-[10px] text-gray-400 mb-0.5">Data inizio *</label>
                  <input type="date" value={approveForm.start_date}
                    onChange={(e) => setApproveForm({ ...approveForm, start_date: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-[10px] text-gray-400 mb-0.5">Data fine *</label>
                  <input type="date" value={approveForm.end_date}
                    onChange={(e) => setApproveForm({ ...approveForm, end_date: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-[10px] text-gray-400 mb-0.5">Numero ordine</label>
                  <input type="text" value={approveForm.orderNum}
                    onChange={(e) => setApproveForm({ ...approveForm, orderNum: e.target.value })}
                    placeholder="es. PO-2026-001" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                </div>
              </div>
              <div className="flex gap-2">
                <button onClick={async () => {
                  if (!approveForm.start_date || !approveForm.end_date) return
                  await approveOffer.mutateAsync({
                    offerId: deal.portal_offer_id!,
                    start_date: approveForm.start_date + 'T00:00:00.000Z',
                    end_date: approveForm.end_date + 'T00:00:00.000Z',
                    orderNum: approveForm.orderNum || undefined,
                    deal_id: deal.id,
                  })
                  setShowApproveForm(false)
                }} disabled={!approveForm.start_date || !approveForm.end_date || approveOffer.isPending}
                  className="inline-flex items-center gap-1 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
                  {approveOffer.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
                  Approva e Crea Commessa
                </button>
                <button onClick={() => setShowApproveForm(false)}
                  className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600">Annulla</button>
              </div>
              {approveOffer.isError && (
                <p className="text-xs text-red-600">Errore: {String((approveOffer.error as any)?.message || 'Errore approvazione')}</p>
              )}
              {approveOffer.isSuccess && (
                <p className="text-xs text-green-600">Offerta approvata! Commessa creata su Portal.</p>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Step 2: Commessa (Project) ── */}
      {deal.portal_project_id && (
        <div className="rounded-lg border border-emerald-200 bg-white p-4 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100 text-xs font-bold text-emerald-700">2</span>
              <span className="text-sm font-medium text-gray-800">Commessa #{deal.portal_project_id}</span>
              <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold text-emerald-700 uppercase">Attiva</span>
            </div>
            <button onClick={() => {
              setPortalActivityForm({
                description: '', activity_type_id: '9',
                accountManager_id: myAccountManager?.id ? String(myAccountManager.id) : '',
                start_date: '', end_date: '', allowance: false,
              })
              setShowPortalActivityForm(true)
            }}
              className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700">
              <Plus className="h-3 w-3" /> Crea Attivita
            </button>
          </div>

          {/* Project details */}
          {dealProject?.project && (
            <div className="grid gap-2 sm:grid-cols-3">
              <div className="rounded-lg bg-emerald-50/50 border border-emerald-100 px-3 py-2">
                <p className="text-[10px] uppercase text-gray-400">Codice</p>
                <p className="text-sm font-mono font-medium">{dealProject.project.project_code || dealProject.project.name || '-'}</p>
              </div>
              <div className="rounded-lg bg-emerald-50/50 border border-emerald-100 px-3 py-2">
                <p className="text-[10px] uppercase text-gray-400">Tipo Fatturazione</p>
                <p className="text-sm">{dealProject.project.billing_type || '-'}</p>
              </div>
              <div className="rounded-lg bg-emerald-50/50 border border-emerald-100 px-3 py-2">
                <p className="text-[10px] uppercase text-gray-400">Importo</p>
                <p className="text-sm font-medium">{dealProject.project.amount ? `${Number(dealProject.project.amount).toLocaleString('it-IT')} EUR` : '-'}</p>
              </div>
            </div>
          )}

          {/* Create Portal Activity Form */}
          {showPortalActivityForm && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50/30 p-4 space-y-3">
              <p className="text-xs font-medium text-emerald-800">Nuova Attivita sulla Commessa #{deal.portal_project_id}</p>
              <div>
                <label className="block text-[10px] text-gray-400 mb-0.5">Descrizione *</label>
                <input type="text" value={portalActivityForm.description}
                  onChange={(e) => setPortalActivityForm({ ...portalActivityForm, description: e.target.value })}
                  placeholder="es. Sviluppo Backend Java" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                <div>
                  <label className="block text-[10px] text-gray-400 mb-0.5">Tipo attivita</label>
                  <select value={portalActivityForm.activity_type_id}
                    onChange={(e) => setPortalActivityForm({ ...portalActivityForm, activity_type_id: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
                    {(() => {
                      const types = Array.isArray(portalActivityTypes) ? portalActivityTypes :
                        (portalActivityTypes?.data || [])
                      return types.length > 0 ? types.map((t: any) => (
                        <option key={t.id} value={t.id}>{t.description || t.code || `Tipo #${t.id}`}</option>
                      )) : <option value="9">Attivita produttiva</option>
                    })()}
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] text-gray-400 mb-0.5">Responsabile</label>
                  <select value={portalActivityForm.accountManager_id}
                    onChange={(e) => setPortalActivityForm({ ...portalActivityForm, accountManager_id: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
                    <option value="">Seleziona responsabile</option>
                    {(accountManagers || []).map((am: any) => (
                      <option key={am.id} value={am.id}>{am.name || am.email}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                <div>
                  <label className="block text-[10px] text-gray-400 mb-0.5">Data inizio *</label>
                  <input type="date" value={portalActivityForm.start_date}
                    onChange={(e) => setPortalActivityForm({ ...portalActivityForm, start_date: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-[10px] text-gray-400 mb-0.5">Data fine *</label>
                  <input type="date" value={portalActivityForm.end_date}
                    onChange={(e) => setPortalActivityForm({ ...portalActivityForm, end_date: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                </div>
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={portalActivityForm.allowance}
                  onChange={(e) => setPortalActivityForm({ ...portalActivityForm, allowance: e.target.checked })} />
                Indennita reperibilita
              </label>
              <div className="flex gap-2">
                <button onClick={async () => {
                  if (!portalActivityForm.description.trim() || !portalActivityForm.start_date || !portalActivityForm.end_date) return
                  await createPortalActivity.mutateAsync({
                    project_id: deal.portal_project_id,
                    description: portalActivityForm.description,
                    activity_type_id: parseInt(portalActivityForm.activity_type_id) || 9,
                    accountManager_id: portalActivityForm.accountManager_id ? parseInt(portalActivityForm.accountManager_id) : undefined,
                    start_date: portalActivityForm.start_date + 'T00:00:00.000Z',
                    end_date: portalActivityForm.end_date + 'T00:00:00.000Z',
                    allowance: portalActivityForm.allowance,
                  })
                  setShowPortalActivityForm(false)
                }} disabled={!portalActivityForm.description.trim() || !portalActivityForm.start_date || !portalActivityForm.end_date || createPortalActivity.isPending}
                  className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
                  {createPortalActivity.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
                  Crea Attivita
                </button>
                <button onClick={() => setShowPortalActivityForm(false)}
                  className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600">Annulla</button>
              </div>
              {createPortalActivity.isError && (
                <p className="text-xs text-red-600">Errore: {String((createPortalActivity.error as any)?.message || 'Errore creazione attivita')}</p>
              )}
            </div>
          )}

          {/* ── Step 3: Activities list with assigned employees ── */}
          {dealProject?.activities && (() => {
            const activityList = dealProject.activities.data || dealProject.activities || []
            return activityList.length > 0 ? (
              <div className="space-y-3">
                {activityList.map((act: any) => {
                  const startDate = act.start_date || act.startDate
                  const endDate = act.end_date || act.endDate
                  const actType = act.ActivityType?.description || act.activityType?.description || ''
                  return (
                    <div key={act.id} className="rounded-lg border border-emerald-100 bg-white p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="flex h-5 w-5 items-center justify-center rounded bg-emerald-50 text-[10px] font-bold text-emerald-600">3</span>
                          <p className="text-sm font-medium text-gray-800">{act.name || act.description || `Attivita #${act.id}`}</p>
                          {actType && <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] text-gray-500">{actType}</span>}
                        </div>
                        <div className="flex items-center gap-2">
                          {startDate && endDate && (
                            <span className="text-[10px] text-gray-400">
                              {new Date(startDate).toLocaleDateString('it-IT')} - {new Date(endDate).toLocaleDateString('it-IT')}
                            </span>
                          )}
                          <button onClick={() => {
                            setShowPortalAssignForm(showPortalAssignForm === act.id ? null : act.id)
                            setPortalAssignForm({ person_id: '', person_name: '', start_date: '', end_date: '', expectedDays: '' })
                            setPortalPersonSearch('')
                          }}
                            className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-600 hover:text-emerald-800">
                            <Plus className="h-3 w-3" /> Assegna Dipendente
                          </button>
                        </div>
                      </div>

                      {/* Assigned persons */}
                      {act.PersonActivities && act.PersonActivities.length > 0 && (
                        <div className="ml-7 space-y-1">
                          {act.PersonActivities.map((pa: any) => {
                            const person = pa.Person || {}
                            const paStart = pa.start_date || pa.startDate
                            const paEnd = pa.end_date || pa.endDate
                            const days = pa.expectedDays || pa.expected_days
                            return (
                              <div key={pa.id} className="flex items-center gap-2 rounded bg-emerald-50/50 px-3 py-1.5">
                                <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-200 text-[10px] font-bold text-emerald-800 shrink-0">
                                  {(person.firstName || '?').charAt(0)}
                                </div>
                                <div className="flex items-center gap-2 flex-wrap">
                                  <span className="text-xs font-medium text-gray-800">
                                    {person.firstName && person.lastName ? `${person.firstName} ${person.lastName}` : `Persona #${pa.person_id}`}
                                  </span>
                                  {days && <span className="text-[10px] text-gray-400">({days}gg)</span>}
                                  {paStart && paEnd && (
                                    <span className="text-[10px] text-gray-400">
                                      {new Date(paStart).toLocaleDateString('it-IT')} - {new Date(paEnd).toLocaleDateString('it-IT')}
                                    </span>
                                  )}
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      )}

                      {/* Assign Employee Form */}
                      {showPortalAssignForm === act.id && (
                        <div className="ml-7 rounded-lg border border-emerald-200 bg-emerald-50/30 p-3 space-y-2">
                          <p className="text-[10px] font-medium text-emerald-700">Assegna dipendente a: {act.name || act.description || `Attivita #${act.id}`}</p>
                          <div>
                            <input type="text" value={portalPersonSearch}
                              onChange={(e) => setPortalPersonSearch(e.target.value)}
                              placeholder="Cerca persona per nome..."
                              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                            {portalPersonSearch.length >= 2 && portalSearchedPersons?.persons && portalSearchedPersons.persons.length > 0 && !portalAssignForm.person_id && (
                              <div className="mt-1 max-h-40 overflow-y-auto rounded-lg border border-gray-200 bg-white">
                                {portalSearchedPersons.persons.map((p: any) => (
                                  <button key={p.portal_id} onClick={() => {
                                    setPortalAssignForm({
                                      ...portalAssignForm,
                                      person_id: String(p.portal_id),
                                      person_name: p.full_name || `${p.first_name || ''} ${p.last_name || ''}`.trim(),
                                    })
                                    setPortalPersonSearch('')
                                  }}
                                    className="w-full text-left px-3 py-2 text-sm hover:bg-emerald-50 border-b border-gray-100 last:border-0">
                                    <span className="font-medium">{p.full_name || `${p.first_name || ''} ${p.last_name || ''}`.trim()}</span>
                                    {p.seniority && (
                                      <span className="text-xs text-gray-400 ml-2">
                                        {typeof p.seniority === 'object' ? p.seniority.description : p.seniority}
                                      </span>
                                    )}
                                    {p.skills?.length > 0 && (
                                      <span className="text-xs text-gray-400 ml-2">({p.skills.map((s: any) => s.name).join(', ')})</span>
                                    )}
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                          {portalAssignForm.person_id && (
                            <div className="flex items-center gap-2 rounded-lg bg-emerald-100 px-3 py-2">
                              <span className="text-sm font-medium text-emerald-800">{portalAssignForm.person_name}</span>
                              <button onClick={() => setPortalAssignForm({ ...portalAssignForm, person_id: '', person_name: '' })}
                                className="text-emerald-400 hover:text-red-500"><X className="h-3.5 w-3.5" /></button>
                            </div>
                          )}
                          <div className="grid gap-2 sm:grid-cols-3">
                            <div>
                              <label className="block text-[10px] text-gray-400 mb-0.5">Data inizio *</label>
                              <input type="date" value={portalAssignForm.start_date}
                                onChange={(e) => setPortalAssignForm({ ...portalAssignForm, start_date: e.target.value })}
                                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                            </div>
                            <div>
                              <label className="block text-[10px] text-gray-400 mb-0.5">Data fine *</label>
                              <input type="date" value={portalAssignForm.end_date}
                                onChange={(e) => setPortalAssignForm({ ...portalAssignForm, end_date: e.target.value })}
                                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                            </div>
                            <div>
                              <label className="block text-[10px] text-gray-400 mb-0.5">Giorni stimati</label>
                              <input type="number" value={portalAssignForm.expectedDays}
                                onChange={(e) => setPortalAssignForm({ ...portalAssignForm, expectedDays: e.target.value })}
                                placeholder="es. 60" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                            </div>
                          </div>
                          <div className="flex gap-2">
                            <button onClick={async () => {
                              if (!portalAssignForm.person_id || !portalAssignForm.start_date || !portalAssignForm.end_date) return
                              await assignEmployeeToActivity.mutateAsync({
                                activity_id: act.id,
                                person_id: parseInt(portalAssignForm.person_id),
                                start_date: portalAssignForm.start_date + 'T00:00:00.000Z',
                                end_date: portalAssignForm.end_date + 'T00:00:00.000Z',
                                expectedDays: portalAssignForm.expectedDays ? parseInt(portalAssignForm.expectedDays) : undefined,
                              })
                              setPortalAssignForm({ person_id: '', person_name: '', start_date: '', end_date: '', expectedDays: '' })
                              setShowPortalAssignForm(null)
                              setPortalPersonSearch('')
                            }} disabled={!portalAssignForm.person_id || !portalAssignForm.start_date || !portalAssignForm.end_date || assignEmployeeToActivity.isPending}
                              className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50">
                              {assignEmployeeToActivity.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
                              Assegna
                            </button>
                            <button onClick={() => { setShowPortalAssignForm(null); setPortalPersonSearch('') }}
                              className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-600">Annulla</button>
                          </div>
                          {assignEmployeeToActivity.isError && (
                            <p className="text-xs text-red-600">Errore: {String((assignEmployeeToActivity.error as any)?.message || 'Errore assegnazione')}</p>
                          )}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            ) : (
              <p className="text-xs text-gray-400 text-center py-2">Nessuna attivita sulla commessa. Clicca "Crea Attivita" per iniziare.</p>
            )
          })()}
        </div>
      )}

      {/* Portal customer info */}
      {deal.portal_customer_id && !deal.portal_offer_id && !showOfferForm && (
        <p className="text-xs text-gray-400">Cliente Portal: {deal.portal_customer_name || `ID ${deal.portal_customer_id}`}</p>
      )}
    </div>
  )
}
