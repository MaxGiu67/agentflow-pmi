import { useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  useCrmDeal, useRegisterOrder, useConfirmOrder, useEmailSends,
  useActivityTypes, useCrmActivities, useCreateCrmActivity, useUpdateCrmActivity,
  useDealDocuments, useDeleteDealDocument, useUploadDealDocument,
  useCreatePortalOffer, usePortalStatus,
  usePortalProjectTypes, usePortalLocations, usePortalAccountManagers,
  usePortalProtocolByCustomer, useMyPortalAccountManager,
  useDealProject, useAssignPortalEmployee, usePortalPersons, useDealProgress,
  usePipelineTemplates, useUpdateCrmDeal,
  useDealResources, useAddDealResource, useUpdateDealResource, useRemoveDealResource,
  useDealRequiresResources,
} from '../../api/hooks'
import { formatCurrency } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import SendEmailModal from '../../components/email/SendEmailModal'
import {
  ArrowLeft, FileCheck, CheckCircle, AlertCircle, Mail, Eye, MousePointer,
  Plus, Phone, Video, Calendar, MessageSquare, Activity, Pencil, Building2,
  FileText, Trash2, Send, Loader2, Upload, Users, X, Download, Save, ChevronUp,
} from 'lucide-react'

const ORDER_TYPES = [
  { value: 'po', label: 'Purchase Order (PO)' },
  { value: 'email', label: 'Conferma via Email' },
  { value: 'firma_word', label: 'Firma su documento Word' },
  { value: 'portale', label: 'Accettazione da portale' },
]

const STATUS_ICONS: Record<string, { icon: typeof Mail; color: string; label: string }> = {
  sent: { icon: Mail, color: 'text-gray-400', label: 'Inviata' },
  delivered: { icon: CheckCircle, color: 'text-blue-400', label: 'Consegnata' },
  opened: { icon: Eye, color: 'text-green-500', label: 'Letta' },
  clicked: { icon: MousePointer, color: 'text-purple-500', label: 'Cliccata' },
  bounced: { icon: AlertCircle, color: 'text-red-500', label: 'Rimbalzata' },
}

const ACTIVITY_ICONS: Record<string, typeof Phone> = {
  call: Phone, video_call: Video, meeting: Calendar, email: Mail, note: MessageSquare, task: Activity,
}

export default function CrmDealDetailPage() {
  const { dealId } = useParams()
  const navigate = useNavigate()
  const id = dealId || ''

  const { data: deal, isLoading } = useCrmDeal(id)
  const registerOrder = useRegisterOrder()
  const confirmOrder = useConfirmOrder()
  const { data: emailHistory } = useEmailSends(deal?.client_id || undefined)

  // Documents
  const { data: documents } = useDealDocuments(id)
  const deleteDocument = useDeleteDealDocument()
  const uploadDocument = useUploadDealDocument()

  // Portal integration
  const { data: portalStatus } = usePortalStatus()
  const { data: pipelineTemplates } = usePipelineTemplates()
  const createPortalOffer = useCreatePortalOffer()
  const { data: projectTypes } = usePortalProjectTypes()
  const { data: locations } = usePortalLocations()
  const { data: accountManagers } = usePortalAccountManagers()
  const { data: myAccountManager } = useMyPortalAccountManager()
  const { data: autoProtocol } = usePortalProtocolByCustomer(deal?.portal_customer_id || undefined)
  const { data: dealProject } = useDealProject(id, deal?.portal_project_id || undefined)
  const assignEmployee = useAssignPortalEmployee()
  const { data: portalPersons } = usePortalPersons('')
  const { data: dealProgressData } = useDealProgress(id, deal?.portal_project_id || undefined)

  // Activities
  const { data: activityTypes } = useActivityTypes(true)
  const { data: activities } = useCrmActivities(undefined, deal?.id)
  const createActivity = useCreateCrmActivity()
  const updateActivity = useUpdateCrmActivity()

  // Resources
  const { data: dealResources } = useDealResources(id)
  const { data: requiresResourcesData } = useDealRequiresResources(id)
  const addDealResource = useAddDealResource()
  const updateDealResource = useUpdateDealResource()
  const removeDealResource = useRemoveDealResource()
  const [personSearch, setPersonSearch] = useState('')
  const { data: searchedPersons } = usePortalPersons(personSearch)

  const [showOrderForm, setShowOrderForm] = useState(false)
  const [orderType, setOrderType] = useState('po')
  const [orderRef, setOrderRef] = useState('')
  const [orderNotes, setOrderNotes] = useState('')
  const [showEmailModal, setShowEmailModal] = useState(false)
  const [showActivityForm, setShowActivityForm] = useState(false)
  const [actForm, setActForm] = useState({ type: 'call', activity_type_id: '', subject: '', description: '', status: 'completed', scheduled_at: '' })
  const [showDocForm, setShowDocForm] = useState(false)
  const [docForm, setDocForm] = useState({ doc_type: 'offerta', name: '', notes: '' })
  const [docFile, setDocFile] = useState<File | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Activity editing
  const [editingActivityId, setEditingActivityId] = useState<string | null>(null)
  const [editActForm, setEditActForm] = useState({ subject: '', description: '', type: '', status: '' })

  // Resource form
  const [showResourceForm, setShowResourceForm] = useState(false)
  const [resourceForm, setResourceForm] = useState({ portal_person_id: '', person_name: '', role: '', start_date: '', end_date: '' })
  const [editingResourceId, setEditingResourceId] = useState<string | null>(null)
  const [editResForm, setEditResForm] = useState({ role: '', start_date: '', end_date: '', status: '' })
  const [showOfferForm, setShowOfferForm] = useState(false)
  const [offerForm, setOfferForm] = useState({
    title: '', billing_type: 'Daily', rate: '', days: '', amount: '', description: '',
    project_type_id: '', location_id: '', accountManager_id: '', protocol: '',
  })
  const [showAssignForm, setShowAssignForm] = useState(false)
  const [assignForm, setAssignForm] = useState({ activity_id: '', person_id: '' })

  // Edit mode
  const updateDeal = useUpdateCrmDeal()
  const [editMode, setEditMode] = useState(false)
  const [editForm, setEditForm] = useState({ name: '', expected_revenue: '', daily_rate: '', estimated_days: '', technology: '', probability: '' })

  if (isLoading) return <LoadingSpinner />
  if (!deal) return <div className="p-8 text-center text-gray-500">Deal non trovato</div>

  const hasOrder = !!deal.order_type
  const isConfirmed = deal.probability === 100

  const handleRegisterOrder = async () => {
    await registerOrder.mutateAsync({
      dealId: id,
      order_type: orderType, order_reference: orderRef, order_notes: orderNotes,
    })
    setShowOrderForm(false)
  }

  const handleCreateActivity = async () => {
    if (!actForm.subject.trim()) return
    await createActivity.mutateAsync({
      deal_id: deal.id,
      contact_id: deal.client_id || undefined,
      type: actForm.type,
      activity_type_id: actForm.activity_type_id || undefined,
      subject: actForm.subject,
      description: actForm.description || undefined,
      status: actForm.status,
      scheduled_at: actForm.scheduled_at || undefined,
    })
    setActForm({ type: 'call', activity_type_id: '', subject: '', description: '', status: 'completed', scheduled_at: '' })
    setShowActivityForm(false)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={deal.name}
        subtitle={`${deal.client_name} · ${deal.stage}`}
        actions={
          <div className="flex items-center gap-2">
            <button onClick={() => setShowEmailModal(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700">
              <Mail className="h-4 w-4" /> Invia email
            </button>
            <button onClick={() => {
              if (!editMode) {
                setEditForm({
                  name: deal.name || '', expected_revenue: String(deal.expected_revenue || ''),
                  daily_rate: String(deal.daily_rate || ''), estimated_days: String(deal.estimated_days || ''),
                  technology: deal.technology || '', probability: String(deal.probability || ''),
                })
              }
              setEditMode(!editMode)
            }}
              className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm ${editMode ? 'border-purple-300 bg-purple-50 text-purple-700' : 'border-gray-300 text-gray-600 hover:bg-gray-50'}`}>
              <Pencil className="h-4 w-4" /> {editMode ? 'Annulla' : 'Modifica'}
            </button>
            <button onClick={() => navigate('/crm')}
              className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900">
              <ArrowLeft className="h-4 w-4" /> Pipeline
            </button>
          </div>
        }
      />

      {/* Badge tipo vendita + pipeline + commerciale */}
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded-full px-3 py-1 text-xs font-medium ${
          deal.deal_type === 'T&M' ? 'bg-purple-100 text-purple-700' :
          deal.deal_type === 'fixed' ? 'bg-blue-100 text-blue-700' :
          deal.deal_type === 'spot' ? 'bg-green-100 text-green-700' :
          'bg-gray-100 text-gray-700'
        }`}>
          {deal.deal_type === 'T&M' ? '🤝 Consulenza' : deal.deal_type === 'fixed' ? '📋 Progetto a corpo' : deal.deal_type === 'spot' ? '🤖 Elevia / Prodotto' : '📦 ' + (deal.deal_type || 'Altro')}
        </span>
        <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600">
          Fase: {deal.stage}
        </span>
        <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600">
          Probabilita: {deal.probability}%
        </span>
        {deal.assigned_to_name && (
          <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-700">
            {deal.assigned_to_name}
          </span>
        )}
        {deal.pipeline_template_id && (() => {
          const tmpl = pipelineTemplates?.find((t: any) => t.id === deal.pipeline_template_id)
          return tmpl ? (
            <span className="rounded-full bg-indigo-100 px-3 py-1 text-xs font-medium text-indigo-700">
              Pipeline: {tmpl.name}
            </span>
          ) : null
        })()}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* ── Azienda + Referente (coerente con creazione deal) ── */}
        <div className="rounded-2xl border border-gray-200 bg-white p-6 space-y-4">
          <h3 className="text-sm font-semibold uppercase text-gray-400">Cliente</h3>
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-600 shrink-0">
                <Building2 className="h-5 w-5" />
              </div>
              <div>
                <p className="font-semibold text-gray-900">{deal.client_name || 'Cliente non specificato'}</p>
                {deal.contact_name && (
                  <p className="text-sm text-gray-600">{deal.contact_name}{deal.contact_role ? ` — ${deal.contact_role}` : ''}</p>
                )}
              </div>
            </div>
            {(deal.client_email || deal.client_phone) && (
              <div className="flex gap-4 text-sm text-gray-500 pl-[52px]">
                {deal.client_email && <span>{deal.client_email}</span>}
                {deal.client_phone && <span>{deal.client_phone}</span>}
              </div>
            )}
          </div>

          {/* Dettagli deal */}
          <div className="border-t border-gray-100 pt-4">
            <h4 className="text-xs font-semibold uppercase text-gray-400 mb-3">Dettagli Opportunita</h4>
            {editMode ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[10px] text-gray-400 mb-0.5">Nome opportunita</label>
                    <input value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                      className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
                  </div>
                  <div>
                    <label className="block text-[10px] text-gray-400 mb-0.5">Valore atteso (EUR)</label>
                    <input type="number" value={editForm.expected_revenue} onChange={(e) => setEditForm({ ...editForm, expected_revenue: e.target.value })}
                      className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
                  </div>
                  <div>
                    <label className="block text-[10px] text-gray-400 mb-0.5">Tariffa giornaliera</label>
                    <input type="number" value={editForm.daily_rate} onChange={(e) => setEditForm({ ...editForm, daily_rate: e.target.value })}
                      className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
                  </div>
                  <div>
                    <label className="block text-[10px] text-gray-400 mb-0.5">Giorni stimati</label>
                    <input type="number" value={editForm.estimated_days} onChange={(e) => setEditForm({ ...editForm, estimated_days: e.target.value })}
                      className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
                  </div>
                  <div>
                    <label className="block text-[10px] text-gray-400 mb-0.5">Tecnologia / Stack</label>
                    <input value={editForm.technology} onChange={(e) => setEditForm({ ...editForm, technology: e.target.value })}
                      className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
                  </div>
                  <div>
                    <label className="block text-[10px] text-gray-400 mb-0.5">Probabilita (%)</label>
                    <input type="number" value={editForm.probability} onChange={(e) => setEditForm({ ...editForm, probability: e.target.value })}
                      className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
                  </div>
                </div>
                <button onClick={async () => {
                  await updateDeal.mutateAsync({
                    dealId: id,
                    name: editForm.name || undefined,
                    expected_revenue: editForm.expected_revenue ? parseFloat(editForm.expected_revenue) : undefined,
                    daily_rate: editForm.daily_rate ? parseFloat(editForm.daily_rate) : undefined,
                    estimated_days: editForm.estimated_days ? parseFloat(editForm.estimated_days) : undefined,
                    technology: editForm.technology || undefined,
                    probability: editForm.probability ? parseFloat(editForm.probability) : undefined,
                  })
                  setEditMode(false)
                }} disabled={updateDeal.isPending}
                  className="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
                  {updateDeal.isPending ? 'Salvataggio...' : 'Salva modifiche'}
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-3">
                <Info label="Valore atteso" value={formatCurrency(deal.expected_revenue)} />
                <Info label="Probabilita" value={`${deal.probability}%`} />
                {deal.daily_rate > 0 && <Info label="Tariffa giornaliera" value={`${formatCurrency(deal.daily_rate)}/gg`} />}
                {deal.estimated_days > 0 && <Info label="Giorni stimati" value={String(deal.estimated_days)} />}
                {deal.technology && <Info label="Tecnologia / Stack" value={deal.technology} className="col-span-2" />}
                <Info label="Responsabile" value={deal.assigned_to_name || deal.assigned_to || '-'} />
                {deal.days_in_stage != null && <Info label="Giorni in questa fase" value={`${deal.days_in_stage} giorni`} />}
              </div>
            )}
          </div>
        </div>

        {/* ── Order ── */}
        <div className="rounded-2xl border border-gray-200 bg-white p-6 space-y-4">
          <h3 className="text-sm font-semibold uppercase text-gray-400">Ordine Cliente</h3>
          {isConfirmed ? (
            <div className="flex items-start gap-3 rounded-lg bg-green-50 p-4">
              <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
              <div>
                <p className="font-medium text-green-800">Ordine confermato</p>
                <p className="text-sm text-green-600">Tipo: {deal.order_type} | Rif: {deal.order_reference || '-'}</p>
              </div>
            </div>
          ) : hasOrder ? (
            <div className="space-y-4">
              <div className="flex items-start gap-3 rounded-lg bg-yellow-50 p-4">
                <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
                <div>
                  <p className="font-medium text-yellow-800">In attesa di conferma</p>
                  <p className="text-sm text-yellow-600">Tipo: {deal.order_type} | Rif: {deal.order_reference || '-'}</p>
                </div>
              </div>
              <button onClick={() => confirmOrder.mutateAsync(id)} disabled={confirmOrder.isPending}
                className="w-full rounded-lg bg-green-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50">
                {confirmOrder.isPending ? 'Conferma...' : 'Conferma Ordine'}
              </button>
            </div>
          ) : showOrderForm ? (
            <div className="space-y-3">
              <select value={orderType} onChange={(e) => setOrderType(e.target.value)} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
                {ORDER_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
              <input type="text" value={orderRef} onChange={(e) => setOrderRef(e.target.value)} placeholder="Riferimento ordine" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              <textarea value={orderNotes} onChange={(e) => setOrderNotes(e.target.value)} rows={2} placeholder="Note" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              <div className="flex gap-2">
                <button onClick={handleRegisterOrder} disabled={registerOrder.isPending}
                  className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">Registra</button>
                <button onClick={() => setShowOrderForm(false)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600">Annulla</button>
              </div>
            </div>
          ) : (
            <button onClick={() => setShowOrderForm(true)}
              className="w-full inline-flex items-center justify-center gap-2 rounded-lg border-2 border-dashed border-gray-300 px-4 py-4 text-sm text-gray-500 hover:border-blue-400 hover:text-blue-600">
              <FileCheck className="h-5 w-5" /> Registra ordine
            </button>
          )}
        </div>
      </div>

      {/* ── RISORSE (Deal Resources) ── */}
      {portalStatus?.enabled && (requiresResourcesData?.requires_resources || (dealResources && dealResources.length > 0)) && (
        <div className="rounded-2xl border border-teal-200 bg-teal-50/20 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-teal-600" />
              <h3 className="text-sm font-semibold uppercase text-teal-600">Risorse</h3>
            </div>
            <button onClick={() => { setShowResourceForm(!showResourceForm); setPersonSearch('') }}
              className="inline-flex items-center gap-1 rounded-lg bg-teal-50 px-3 py-1.5 text-xs font-medium text-teal-700 hover:bg-teal-100">
              <Plus className="h-3 w-3" /> Aggiungi Risorsa
            </button>
          </div>

          {/* Add resource form */}
          {showResourceForm && (
            <div className="mb-4 rounded-lg border border-teal-200 bg-white p-4 space-y-3">
              <div>
                <input type="text" value={personSearch} onChange={(e) => setPersonSearch(e.target.value)}
                  placeholder="Cerca persona per nome..." className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                {personSearch.length >= 2 && searchedPersons?.persons && searchedPersons.persons.length > 0 && (
                  <div className="mt-1 max-h-40 overflow-y-auto rounded-lg border border-gray-200 bg-white">
                    {searchedPersons.persons.map((p: any) => (
                      <button key={p.portal_id} onClick={() => {
                        setResourceForm({
                          ...resourceForm,
                          portal_person_id: String(p.portal_id),
                          person_name: p.full_name || `${p.firstName || ''} ${p.lastName || ''}`.trim(),
                        })
                        setPersonSearch('')
                      }}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-teal-50 border-b border-gray-100 last:border-0">
                        <span className="font-medium">{p.full_name || `${p.firstName || ''} ${p.lastName || ''}`.trim()}</span>
                        {p.seniority && <span className="text-xs text-gray-400 ml-2">{typeof p.seniority === 'object' ? p.seniority.description : p.seniority}</span>}
                        {p.skills?.length > 0 && <span className="text-xs text-gray-400 ml-2">({p.skills.map((s: any) => s.name).join(', ')})</span>}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              {resourceForm.portal_person_id && (
                <div className="flex items-center gap-2 rounded-lg bg-teal-50 px-3 py-2">
                  <span className="text-sm font-medium text-teal-800">{resourceForm.person_name}</span>
                  <button onClick={() => setResourceForm({ ...resourceForm, portal_person_id: '', person_name: '' })}
                    className="text-teal-400 hover:text-red-500"><X className="h-3.5 w-3.5" /></button>
                </div>
              )}
              <input type="text" value={resourceForm.role} onChange={(e) => setResourceForm({ ...resourceForm, role: e.target.value })}
                placeholder="Ruolo (es. Frontend Developer, PM, ...)" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              <div className="grid gap-2 sm:grid-cols-2">
                <div>
                  <label className="block text-[10px] text-gray-400 mb-0.5">Data inizio</label>
                  <input type="date" value={resourceForm.start_date} onChange={(e) => setResourceForm({ ...resourceForm, start_date: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-[10px] text-gray-400 mb-0.5">Data fine</label>
                  <input type="date" value={resourceForm.end_date} onChange={(e) => setResourceForm({ ...resourceForm, end_date: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                </div>
              </div>
              <div className="flex gap-2">
                <button onClick={async () => {
                  if (!resourceForm.portal_person_id) return
                  await addDealResource.mutateAsync({
                    dealId: id,
                    portal_person_id: parseInt(resourceForm.portal_person_id),
                    person_name: resourceForm.person_name,
                    role: resourceForm.role || undefined,
                    start_date: resourceForm.start_date || undefined,
                    end_date: resourceForm.end_date || undefined,
                  })
                  setResourceForm({ portal_person_id: '', person_name: '', role: '', start_date: '', end_date: '' })
                  setShowResourceForm(false)
                }} disabled={!resourceForm.portal_person_id || addDealResource.isPending}
                  className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
                  {addDealResource.isPending ? 'Aggiunta...' : 'Aggiungi'}
                </button>
                <button onClick={() => setShowResourceForm(false)}
                  className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600">Annulla</button>
              </div>
            </div>
          )}

          {/* Resource list */}
          {dealResources && dealResources.length > 0 ? (
            <div className="space-y-2">
              {dealResources.map((res: any) => {
                const isEditingRes = editingResourceId === res.id
                const statusColors: Record<string, string> = {
                  assigned: 'bg-blue-100 text-blue-700',
                  active: 'bg-green-100 text-green-700',
                  released: 'bg-gray-100 text-gray-500',
                }
                return (
                  <div key={res.id} className="rounded-lg border border-teal-100 bg-white px-4 py-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-teal-100 text-teal-600 text-xs font-bold shrink-0">
                          {(res.person_name || '?').charAt(0).toUpperCase()}
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-medium text-gray-900">{res.person_name || `Person #${res.portal_person_id}`}</p>
                            <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${statusColors[res.status] || statusColors.assigned}`}>
                              {res.status === 'assigned' ? 'Assegnato' : res.status === 'active' ? 'Attivo' : 'Rilasciato'}
                            </span>
                          </div>
                          <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-gray-500 mt-0.5">
                            {res.role && <span>{res.role}</span>}
                            {res.seniority && <span>{res.seniority}</span>}
                            {res.daily_cost != null && <span>{formatCurrency(res.daily_cost)}/gg</span>}
                            {res.start_date && <span>dal {new Date(res.start_date).toLocaleDateString('it-IT')}</span>}
                            {res.end_date && <span>al {new Date(res.end_date).toLocaleDateString('it-IT')}</span>}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-1 shrink-0">
                        <button onClick={() => {
                          if (isEditingRes) {
                            setEditingResourceId(null)
                          } else {
                            setEditingResourceId(res.id)
                            setEditResForm({
                              role: res.role || '',
                              start_date: res.start_date || '',
                              end_date: res.end_date || '',
                              status: res.status || 'assigned',
                            })
                          }
                        }}
                          className={`rounded px-2 py-1 text-[10px] font-medium ${isEditingRes ? 'bg-teal-100 text-teal-700' : 'bg-gray-50 text-gray-500 hover:bg-gray-100'}`}>
                          {isEditingRes ? <ChevronUp className="h-3 w-3" /> : <Pencil className="h-3 w-3" />}
                        </button>
                        <button onClick={() => {
                          if (confirm(`Rimuovere ${res.person_name || 'questa risorsa'}?`))
                            removeDealResource.mutate({ dealId: id, resourceId: res.id })
                        }}
                          className="text-gray-300 hover:text-red-500"><Trash2 className="h-3.5 w-3.5" /></button>
                      </div>
                    </div>

                    {/* Inline edit for resource */}
                    {isEditingRes && (
                      <div className="mt-3 space-y-2 border-t border-gray-100 pt-3">
                        <input type="text" value={editResForm.role} onChange={(e) => setEditResForm({ ...editResForm, role: e.target.value })}
                          placeholder="Ruolo" className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
                        <div className="grid gap-2 sm:grid-cols-3">
                          <div>
                            <label className="block text-[10px] text-gray-400 mb-0.5">Data inizio</label>
                            <input type="date" value={editResForm.start_date} onChange={(e) => setEditResForm({ ...editResForm, start_date: e.target.value })}
                              className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
                          </div>
                          <div>
                            <label className="block text-[10px] text-gray-400 mb-0.5">Data fine</label>
                            <input type="date" value={editResForm.end_date} onChange={(e) => setEditResForm({ ...editResForm, end_date: e.target.value })}
                              className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
                          </div>
                          <div>
                            <label className="block text-[10px] text-gray-400 mb-0.5">Stato</label>
                            <select value={editResForm.status} onChange={(e) => setEditResForm({ ...editResForm, status: e.target.value })}
                              className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm">
                              <option value="assigned">Assegnato</option>
                              <option value="active">Attivo</option>
                              <option value="released">Rilasciato</option>
                            </select>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <button onClick={async () => {
                            await updateDealResource.mutateAsync({
                              dealId: id,
                              resourceId: res.id,
                              role: editResForm.role || undefined,
                              start_date: editResForm.start_date || undefined,
                              end_date: editResForm.end_date || undefined,
                              status: editResForm.status,
                            })
                            setEditingResourceId(null)
                          }} disabled={updateDealResource.isPending}
                            className="inline-flex items-center gap-1 rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50">
                            <Save className="h-3 w-3" /> {updateDealResource.isPending ? 'Salvataggio...' : 'Salva'}
                          </button>
                          <button onClick={() => setEditingResourceId(null)}
                            className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-600">Annulla</button>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}

              {/* Total daily cost */}
              {(() => {
                const totalCost = dealResources.reduce((sum: number, r: any) => sum + (r.daily_cost || 0), 0)
                if (totalCost > 0) {
                  return (
                    <div className="flex items-center justify-end gap-2 pt-2 border-t border-teal-100">
                      <span className="text-xs text-gray-400">Costo giornaliero totale:</span>
                      <span className="text-sm font-bold text-teal-700">{formatCurrency(totalCost)}/gg</span>
                    </div>
                  )
                }
                return null
              })()}
            </div>
          ) : (
            <p className="text-sm text-gray-400 text-center py-4">Nessuna risorsa assegnata</p>
          )}
        </div>
      )}

      {/* ── Documents (Offerta, Ordine, Contratto) ── */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold uppercase text-gray-400">Documenti</h3>
          <button onClick={() => setShowDocForm(!showDocForm)}
            className="inline-flex items-center gap-1 rounded-lg bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-100">
            <Plus className="h-3 w-3" /> Aggiungi documento
          </button>
        </div>

        {showDocForm && (
          <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50/30 p-4 space-y-3">
            <div className="grid gap-2 sm:grid-cols-2">
              <select value={docForm.doc_type} onChange={(e) => setDocForm({ ...docForm, doc_type: e.target.value })}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                <option value="offerta">Offerta</option>
                <option value="ordine">Ordine cliente</option>
                <option value="contratto">Contratto</option>
                <option value="specifica">Specifica tecnica</option>
                <option value="altro">Altro</option>
              </select>
              <input type="text" value={docForm.name} onChange={(e) => setDocForm({ ...docForm, name: e.target.value })}
                placeholder="Nome documento (opzionale)" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
            {/* File upload */}
            <div>
              <input ref={fileInputRef} type="file" className="hidden" onChange={(e) => {
                const f = e.target.files?.[0] || null
                setDocFile(f)
                if (f && !docForm.name.trim()) setDocForm({ ...docForm, name: f.name })
              }} />
              <button type="button" onClick={() => fileInputRef.current?.click()}
                className={`w-full flex items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-3 text-sm transition-colors ${
                  docFile ? 'border-green-300 bg-green-50 text-green-700' : 'border-gray-300 text-gray-500 hover:border-blue-400 hover:text-blue-600'
                }`}>
                <Upload className="h-4 w-4" />
                {docFile ? docFile.name : 'Seleziona file da caricare'}
              </button>
              {docFile && (
                <div className="flex items-center gap-2 mt-1.5">
                  <span className="text-xs text-gray-400">{(docFile.size / 1024).toFixed(1)} KB</span>
                  <button onClick={() => { setDocFile(null); if (fileInputRef.current) fileInputRef.current.value = '' }}
                    className="text-xs text-red-500 hover:text-red-700">Rimuovi</button>
                </div>
              )}
            </div>
            <input type="text" value={docForm.notes} onChange={(e) => setDocForm({ ...docForm, notes: e.target.value })}
              placeholder="Note (opzionale)" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <div className="flex gap-2">
              <button onClick={async () => {
                if (!docFile) return
                const formData = new FormData()
                formData.append('file', docFile)
                formData.append('doc_type', docForm.doc_type)
                formData.append('name', docForm.name || docFile.name)
                formData.append('notes', docForm.notes)
                await uploadDocument.mutateAsync({ dealId: deal.id, formData })
                setDocForm({ doc_type: 'offerta', name: '', notes: '' })
                setDocFile(null)
                if (fileInputRef.current) fileInputRef.current.value = ''
                setShowDocForm(false)
              }} disabled={!docFile || uploadDocument.isPending}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
                {uploadDocument.isPending ? 'Caricamento...' : 'Carica'}
              </button>
              <button onClick={() => { setShowDocForm(false); setDocFile(null) }}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600">Annulla</button>
            </div>
          </div>
        )}

        {documents && documents.length > 0 ? (
          <div className="space-y-2">
            {documents.map((doc: any) => {
              const typeLabels: Record<string, { label: string; color: string }> = {
                offerta: { label: 'Offerta', color: 'bg-green-100 text-green-700' },
                ordine: { label: 'Ordine', color: 'bg-blue-100 text-blue-700' },
                contratto: { label: 'Contratto', color: 'bg-purple-100 text-purple-700' },
                specifica: { label: 'Specifica', color: 'bg-yellow-100 text-yellow-700' },
                altro: { label: 'Altro', color: 'bg-gray-100 text-gray-700' },
              }
              const typeInfo = typeLabels[doc.doc_type] || typeLabels.altro
              const isDataUrl = doc.url?.startsWith('data:')
              return (
                <div key={doc.id} className="flex items-center justify-between rounded-lg border border-gray-100 px-4 py-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <FileText className="h-4 w-4 text-gray-400 shrink-0" />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${typeInfo.color}`}>{typeInfo.label}</span>
                        <p className="text-sm font-medium text-gray-900 truncate">{doc.name}</p>
                      </div>
                      {doc.notes && <p className="text-xs text-gray-400 mt-0.5">{doc.notes}</p>}
                      {doc.created_at && <p className="text-[10px] text-gray-300 mt-0.5">{new Date(doc.created_at).toLocaleDateString('it-IT')}</p>}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {doc.url && (
                      <a href={isDataUrl ? doc.url : doc.url} download={isDataUrl ? doc.name : undefined}
                        target={isDataUrl ? undefined : '_blank'} rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 rounded bg-gray-50 px-2 py-1 text-xs text-blue-600 hover:bg-blue-50">
                        <Download className="h-3 w-3" /> {isDataUrl ? 'Scarica' : 'Apri'}
                      </a>
                    )}
                    <button onClick={() => { if (confirm(`Eliminare "${doc.name}"?`)) deleteDocument.mutate(doc.id) }}
                      className="text-gray-300 hover:text-red-500"><Trash2 className="h-3.5 w-3.5" /></button>
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <p className="text-sm text-gray-400 text-center py-4">Nessun documento allegato</p>
        )}
      </div>

      {/* ── Portal: Crea Offerta / Commessa ── */}
      {portalStatus?.enabled && (
        <div className="rounded-2xl border border-indigo-200 bg-indigo-50/30 p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold uppercase text-indigo-500">Operativo Portal</h3>
              <p className="text-xs text-gray-400 mt-0.5">Crea offerta e commessa su PortalJS.be</p>
            </div>
            {!showOfferForm && deal.portal_customer_id && (
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
                })
                setShowOfferForm(true)
              }}
                className="inline-flex items-center gap-1 rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700">
                <Send className="h-3 w-3" /> Crea Offerta su Portal
              </button>
            )}
          </div>

          {showOfferForm && (
            <div className="rounded-lg border border-indigo-200 bg-white p-4 space-y-3">
              <p className="text-xs font-medium text-indigo-700">Conferma dati offerta per Portal</p>

              {/* Protocollo (auto-generated) */}
              <div className="rounded-lg bg-indigo-50 px-3 py-2">
                <p className="text-[10px] uppercase text-indigo-400 font-medium">Protocollo (auto)</p>
                <p className="text-sm font-mono text-indigo-700">{offerForm.protocol || autoProtocol || 'Caricamento...'}</p>
              </div>

              {/* Titolo + Tipo fatturazione */}
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

              {/* Tipo offerta + Sede */}
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

              {/* Commerciale (auto-match per email) */}
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
                {myAccountManager && !myAccountManager.id && (
                  <p className="text-[10px] text-amber-600 mt-1">Nessun account Portal trovato per {myAccountManager.email}</p>
                )}
              </div>

              {/* Rate/Days (Daily) or Amount (LumpSum) */}
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

              {/* Descrizione */}
              <textarea value={offerForm.description} onChange={(e) => setOfferForm({ ...offerForm, description: e.target.value })}
                placeholder="Descrizione" rows={2} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />

              {/* Actions */}
              <div className="flex gap-2">
                <button onClick={async () => {
                  const protocol = offerForm.protocol || autoProtocol || ''
                  const payload: Record<string, unknown> = {
                    project_code: protocol,
                    name: offerForm.title,
                    other_details: offerForm.description,
                    billing_type: offerForm.billing_type,
                    customer_id: deal.portal_customer_id,
                    accountManager_id: parseInt(offerForm.accountManager_id),
                    project_type_id: parseInt(offerForm.project_type_id),
                    location_id: parseInt(offerForm.location_id),
                    rate: offerForm.rate ? parseFloat(offerForm.rate) : undefined,
                    days: offerForm.days ? parseInt(offerForm.days) : undefined,
                    amount: offerForm.amount ? parseFloat(offerForm.amount) : undefined,
                    OutcomeType: 'W',
                    year: new Date().getFullYear(),
                  }
                  await createPortalOffer.mutateAsync(payload)
                  setShowOfferForm(false)
                }} disabled={
                  !offerForm.title.trim() || !offerForm.project_type_id || !offerForm.location_id ||
                  !offerForm.accountManager_id || createPortalOffer.isPending
                }
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
              {createPortalOffer.isSuccess && (
                <p className="text-xs text-green-600">Offerta creata su Portal con successo!</p>
              )}
            </div>
          )}

          {deal.portal_customer_id && !showOfferForm && (
            <p className="text-xs text-gray-400">Cliente Portal: {deal.portal_customer_name || `ID ${deal.portal_customer_id}`}</p>
          )}
          {!deal.portal_customer_id && !showOfferForm && (
            <p className="text-xs text-amber-600">Seleziona un cliente da Portal nel deal per creare l'offerta</p>
          )}
        </div>
      )}

      {/* ── Portal: Commessa + Risorse Assegnate (US-236/237/238) ── */}
      {portalStatus?.enabled && deal.portal_project_id && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50/30 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold uppercase text-emerald-600">Commessa Portal</h3>
              <p className="text-xs text-gray-400 mt-0.5">Progetto #{deal.portal_project_id} su PortalJS.be</p>
            </div>
            <span className="rounded-full bg-emerald-100 px-3 py-1 text-[10px] font-bold text-emerald-700 uppercase">Attiva</span>
          </div>

          {/* Project details */}
          {dealProject?.project && (
            <div className="grid gap-2 sm:grid-cols-3">
              <div className="rounded-lg bg-white border border-emerald-100 px-3 py-2">
                <p className="text-[10px] uppercase text-gray-400">Codice</p>
                <p className="text-sm font-mono font-medium">{dealProject.project.project_code || dealProject.project.name || '-'}</p>
              </div>
              <div className="rounded-lg bg-white border border-emerald-100 px-3 py-2">
                <p className="text-[10px] uppercase text-gray-400">Tipo Fatturazione</p>
                <p className="text-sm">{dealProject.project.billing_type || '-'}</p>
              </div>
              <div className="rounded-lg bg-white border border-emerald-100 px-3 py-2">
                <p className="text-[10px] uppercase text-gray-400">Importo</p>
                <p className="text-sm font-medium">{dealProject.project.amount ? `€ ${Number(dealProject.project.amount).toLocaleString('it-IT')}` : '-'}</p>
              </div>
            </div>
          )}

          {/* Risorse assegnate */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold text-emerald-700">Risorse Assegnate</p>
              <button onClick={() => setShowAssignForm(!showAssignForm)}
                className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-600 hover:text-emerald-800">
                <Plus className="h-3 w-3" /> Assegna risorsa
              </button>
            </div>

            {showAssignForm && (
              <div className="mb-3 rounded-lg border border-emerald-200 bg-white p-3 space-y-2">
                <select value={assignForm.activity_id} onChange={(e) => setAssignForm({ ...assignForm, activity_id: e.target.value })}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
                  <option value="">Seleziona attività *</option>
                  {(dealProject?.activities?.data || dealProject?.activities || []).map((act: any) => (
                    <option key={act.id} value={act.id}>{act.name || act.description || `Attività #${act.id}`}</option>
                  ))}
                </select>
                <select value={assignForm.person_id} onChange={(e) => setAssignForm({ ...assignForm, person_id: e.target.value })}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
                  <option value="">Seleziona persona *</option>
                  {(portalPersons?.persons || []).map((p: any) => (
                    <option key={p.portal_id} value={p.portal_id}>{p.full_name} {p.skills?.length ? `(${p.skills.map((s: any) => s.name).join(', ')})` : ''}</option>
                  ))}
                </select>
                <div className="flex gap-2">
                  <button onClick={async () => {
                    if (!assignForm.activity_id || !assignForm.person_id) return
                    await assignEmployee.mutateAsync({
                      activity_id: parseInt(assignForm.activity_id),
                      person_id: parseInt(assignForm.person_id),
                    })
                    setAssignForm({ activity_id: '', person_id: '' })
                    setShowAssignForm(false)
                  }} disabled={!assignForm.activity_id || !assignForm.person_id || assignEmployee.isPending}
                    className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50">
                    {assignEmployee.isPending ? 'Assegnazione...' : 'Assegna'}
                  </button>
                  <button onClick={() => setShowAssignForm(false)}
                    className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-600">Annulla</button>
                </div>
              </div>
            )}

            {dealProject?.activities && (
              <div className="space-y-2">
                {(dealProject.activities.data || dealProject.activities || []).map((act: any) => (
                  <div key={act.id} className="rounded-lg border border-emerald-100 bg-white px-3 py-2">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-gray-800">{act.name || act.description || `Attività #${act.id}`}</p>
                      <span className="text-[10px] text-gray-400">{act.ActivityType?.description || ''}</span>
                    </div>
                    {act.PersonActivities && act.PersonActivities.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {act.PersonActivities.map((pa: any) => (
                          <span key={pa.id} className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] text-emerald-700">
                            {pa.Person ? `${pa.Person.firstName} ${pa.Person.lastName}` : `Persona #${pa.person_id}`}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Avanzamento Operativo (US-240) ── */}
      {portalStatus?.enabled && deal.portal_project_id && dealProgressData?.progress && (() => {
        const p = dealProgressData.progress
        return (
          <div className="rounded-2xl border border-blue-200 bg-blue-50/30 p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold uppercase text-blue-600">Avanzamento Operativo</h3>
              {p.warning && (
                <span className="rounded-full bg-red-100 px-3 py-1 text-[10px] font-bold text-red-700 uppercase">Margine &lt; 15%</span>
              )}
            </div>

            {/* KPI Cards */}
            <div className="grid gap-2 sm:grid-cols-4">
              <div className="rounded-lg bg-white border border-blue-100 px-3 py-2 text-center">
                <p className="text-[10px] uppercase text-gray-400">Valore Deal</p>
                <p className="text-lg font-bold text-gray-900">€ {Number(p.deal_value).toLocaleString('it-IT')}</p>
              </div>
              <div className="rounded-lg bg-white border border-blue-100 px-3 py-2 text-center">
                <p className="text-[10px] uppercase text-gray-400">Costo Stimato</p>
                <p className="text-lg font-bold text-gray-700">€ {Number(p.estimated_cost).toLocaleString('it-IT')}</p>
              </div>
              <div className={`rounded-lg border px-3 py-2 text-center ${
                p.margin_pct >= 25 ? 'bg-green-50 border-green-200' :
                p.margin_pct >= 15 ? 'bg-yellow-50 border-yellow-200' :
                'bg-red-50 border-red-200'
              }`}>
                <p className="text-[10px] uppercase text-gray-400">Margine</p>
                <p className={`text-lg font-bold ${
                  p.margin_pct >= 25 ? 'text-green-700' : p.margin_pct >= 15 ? 'text-yellow-700' : 'text-red-700'
                }`}>€ {Number(p.margin_eur).toLocaleString('it-IT')} ({p.margin_pct}%)</p>
              </div>
              <div className="rounded-lg bg-white border border-blue-100 px-3 py-2 text-center">
                <p className="text-[10px] uppercase text-gray-400">Risorse</p>
                <p className="text-lg font-bold text-gray-900">{p.assigned_persons}</p>
                <p className="text-[10px] text-gray-400">costo medio €{p.avg_daily_cost}/gg</p>
              </div>
            </div>

            {/* Progress details */}
            <div className="grid gap-2 sm:grid-cols-3 text-xs text-gray-500">
              <p>Giorni pianificati: <span className="font-medium text-gray-700">{p.planned_days}</span></p>
              <p>Tariffa giornaliera: <span className="font-medium text-gray-700">€{p.daily_rate}</span></p>
              <p>Costo giornaliero totale: <span className="font-medium text-gray-700">€{p.total_daily_cost}</span></p>
            </div>
          </div>
        )
      })()}

      {/* ── Activities ── */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold uppercase text-gray-400">Attivita</h3>
          <button onClick={() => setShowActivityForm(!showActivityForm)}
            className="inline-flex items-center gap-1 rounded-lg bg-green-50 px-3 py-1.5 text-xs font-medium text-green-700 hover:bg-green-100">
            <Plus className="h-3 w-3" /> Nuova Attivita
          </button>
        </div>

        {showActivityForm && (
          <div className="mb-4 rounded-lg border border-green-200 bg-green-50/30 p-4 space-y-3">
            {/* Activity type — big buttons */}
            <div className="grid grid-cols-3 sm:grid-cols-6 gap-1.5">
              {[
                { value: 'call', label: 'Chiamata', emoji: '📞' },
                { value: 'video_call', label: 'Video', emoji: '📹' },
                { value: 'meeting', label: 'Riunione', emoji: '🤝' },
                { value: 'email', label: 'Email', emoji: '📧' },
                { value: 'task', label: 'Task', emoji: '✅' },
                { value: 'note', label: 'Nota', emoji: '📝' },
              ].map(({ value, label, emoji }) => (
                <button key={value}
                  onClick={() => setActForm({ ...actForm, type: value, status: value === 'note' ? 'completed' : 'planned' })}
                  className={`flex flex-col items-center gap-0.5 rounded-lg border-2 p-2 text-xs font-medium transition-all ${
                    actForm.type === value ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-600 hover:border-gray-300'
                  }`}>
                  <span className="text-base">{emoji}</span>
                  {label}
                </button>
              ))}
            </div>

            <input type="text" value={actForm.subject} onChange={(e) => setActForm({ ...actForm, subject: e.target.value })}
              placeholder="Oggetto (es. Chiamata qualifica con Mario Rossi) *" className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm" />

            <div className="grid gap-2 sm:grid-cols-3">
              <select value={actForm.status} onChange={(e) => setActForm({ ...actForm, status: e.target.value })}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                <option value="planned">Pianificata</option>
                <option value="completed">Completata</option>
              </select>
              <input type="datetime-local" value={actForm.scheduled_at}
                onChange={(e) => setActForm({ ...actForm, scheduled_at: e.target.value })}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
                placeholder="Data e ora" />
              <select value={actForm.activity_type_id} onChange={(e) => setActForm({ ...actForm, activity_type_id: e.target.value })}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                <option value="">-- Tipo specifico (opz.) --</option>
                {activityTypes?.map((t: any) => (
                  <option key={t.id} value={t.id}>{t.label}</option>
                ))}
              </select>
            </div>

            <textarea value={actForm.description} onChange={(e) => setActForm({ ...actForm, description: e.target.value })}
              placeholder="Note / descrizione" rows={2} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />

            {actForm.status === 'planned' && actForm.scheduled_at && (
              <p className="text-xs text-green-600">Verra sincronizzata automaticamente con Outlook Calendar</p>
            )}

            <div className="flex gap-2">
              <button onClick={handleCreateActivity} disabled={!actForm.subject.trim() || createActivity.isPending}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 hover:bg-blue-700">
                {createActivity.isPending ? 'Salvataggio...' : actForm.status === 'planned' ? 'Pianifica' : 'Salva'}
              </button>
              <button onClick={() => setShowActivityForm(false)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600">Annulla</button>
            </div>
          </div>
        )}

        {activities && activities.length > 0 ? (
          <div className="space-y-2">
            {activities.map((a: any) => {
              const AIcon = ACTIVITY_ICONS[a.type] || Activity
              const isPlanned = a.status === 'planned'
              const isEditing = editingActivityId === a.id
              return (
                <div key={a.id} className={`rounded-lg border px-4 py-2.5 ${isPlanned ? 'border-amber-200 bg-amber-50/50' : 'border-gray-100'}`}>
                  <div className="flex items-start gap-3">
                    <AIcon className={`h-4 w-4 mt-0.5 shrink-0 ${isPlanned ? 'text-amber-500' : 'text-gray-400'}`} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-gray-900">{a.subject}</p>
                        {isPlanned && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700">Pianificata</span>}
                        {a.status === 'cancelled' && <span className="rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-medium text-red-700">Annullata</span>}
                      </div>
                      {a.description && <p className="text-xs text-gray-500 mt-0.5">{a.description}</p>}
                      <p className="text-[10px] text-gray-400 mt-1">
                        {a.type} - {a.status}
                        {a.scheduled_at && ` - ${a.scheduled_at.split('T')[0]} ${a.scheduled_at.split('T')[1]?.slice(0, 5) || ''}`}
                        {!a.scheduled_at && a.created_at && ` - ${a.created_at.split('T')[0]}`}
                      </p>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      {isPlanned && (
                        <button onClick={() => updateActivity.mutateAsync({ activityId: a.id, status: 'completed' })}
                          className="rounded bg-green-50 px-2 py-1 text-[10px] font-medium text-green-700 hover:bg-green-100">
                          Completa
                        </button>
                      )}
                      <button onClick={() => {
                        if (isEditing) {
                          setEditingActivityId(null)
                        } else {
                          setEditingActivityId(a.id)
                          setEditActForm({
                            subject: a.subject || '',
                            description: a.description || '',
                            type: a.type || 'call',
                            status: a.status || 'planned',
                          })
                        }
                      }}
                        className={`rounded px-2 py-1 text-[10px] font-medium ${isEditing ? 'bg-purple-100 text-purple-700' : 'bg-gray-50 text-gray-500 hover:bg-gray-100'}`}>
                        {isEditing ? <ChevronUp className="h-3 w-3" /> : <Pencil className="h-3 w-3" />}
                      </button>
                    </div>
                  </div>

                  {/* Inline edit form */}
                  {isEditing && (
                    <div className="mt-3 ml-7 space-y-2 border-t border-gray-100 pt-3">
                      <input type="text" value={editActForm.subject} onChange={(e) => setEditActForm({ ...editActForm, subject: e.target.value })}
                        placeholder="Oggetto *" className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
                      <textarea value={editActForm.description} onChange={(e) => setEditActForm({ ...editActForm, description: e.target.value })}
                        placeholder="Descrizione" rows={2} className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
                      <div className="grid gap-2 sm:grid-cols-2">
                        <select value={editActForm.type} onChange={(e) => setEditActForm({ ...editActForm, type: e.target.value })}
                          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm">
                          <option value="call">Chiamata</option>
                          <option value="video_call">Video Call</option>
                          <option value="meeting">Riunione</option>
                          <option value="email">Email</option>
                          <option value="task">Task</option>
                          <option value="note">Nota</option>
                        </select>
                        <select value={editActForm.status} onChange={(e) => setEditActForm({ ...editActForm, status: e.target.value })}
                          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm">
                          <option value="planned">Pianificata</option>
                          <option value="completed">Completata</option>
                          <option value="cancelled">Annullata</option>
                        </select>
                      </div>
                      <div className="flex gap-2">
                        <button onClick={async () => {
                          if (!editActForm.subject.trim()) return
                          await updateActivity.mutateAsync({
                            activityId: a.id,
                            subject: editActForm.subject,
                            description: editActForm.description || undefined,
                            type: editActForm.type,
                            status: editActForm.status,
                          })
                          setEditingActivityId(null)
                        }} disabled={!editActForm.subject.trim() || updateActivity.isPending}
                          className="inline-flex items-center gap-1 rounded-lg bg-purple-600 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50">
                          <Save className="h-3 w-3" /> {updateActivity.isPending ? 'Salvataggio...' : 'Salva'}
                        </button>
                        <button onClick={() => setEditingActivityId(null)}
                          className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-600">Annulla</button>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        ) : (
          <p className="text-sm text-gray-400 text-center py-4">Nessuna attivita registrata</p>
        )}
      </div>

      {/* ── Email History ── */}
      {emailHistory && emailHistory.length > 0 && (
        <div className="rounded-2xl border border-gray-200 bg-white p-6">
          <h3 className="text-sm font-semibold uppercase text-gray-400 mb-4">Email inviate</h3>
          <div className="space-y-2">
            {emailHistory.map((email: any) => {
              const st = STATUS_ICONS[email.status] || STATUS_ICONS.sent
              const Icon = st.icon
              return (
                <div key={email.id} className="flex items-center justify-between rounded-lg border border-gray-100 px-4 py-2.5">
                  <div className="flex items-center gap-3 min-w-0">
                    <Icon className={`h-4 w-4 shrink-0 ${st.color}`} />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{email.subject}</p>
                      <p className="text-xs text-gray-400">{email.to_email} — {email.sent_at?.split('T')[0]}</p>
                    </div>
                  </div>
                  <span className={`text-xs font-medium shrink-0 ${st.color}`}>{st.label}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      <SendEmailModal open={showEmailModal} onClose={() => setShowEmailModal(false)}
        toEmail="" toName={deal.client_name} contactId={deal.client_id}
        defaultParams={{ deal_name: deal.name, deal_value: String(deal.expected_revenue) }} />
    </div>
  )
}

function Info({ label, value, className = '' }: { label: string; value: string; className?: string }) {
  return (
    <div className={className}>
      <p className="text-xs text-gray-400">{label}</p>
      <p className="font-medium text-gray-900">{value}</p>
    </div>
  )
}
