import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  useCrmDeal, useRegisterOrder, useConfirmOrder, useEmailSends,
  useActivityTypes, useCrmActivities, useCreateCrmActivity,
  useDealDocuments, useAddDealDocument, useDeleteDealDocument,
  useCreatePortalOffer, usePortalStatus,
} from '../../api/hooks'
import { formatCurrency } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import SendEmailModal from '../../components/email/SendEmailModal'
import {
  ArrowLeft, FileCheck, CheckCircle, AlertCircle, Mail, Eye, MousePointer,
  Plus, Phone, Video, Calendar, MessageSquare, Activity, Pencil, Building2,
  FileText, Link2, Trash2, Send, Loader2,
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
  const addDocument = useAddDealDocument()
  const deleteDocument = useDeleteDealDocument()

  // Portal integration
  const { data: portalStatus } = usePortalStatus()
  const createPortalOffer = useCreatePortalOffer()

  // Activities
  const { data: activityTypes } = useActivityTypes(true)
  const { data: activities } = useCrmActivities(undefined, deal?.id)
  const createActivity = useCreateCrmActivity()

  const [showOrderForm, setShowOrderForm] = useState(false)
  const [orderType, setOrderType] = useState('po')
  const [orderRef, setOrderRef] = useState('')
  const [orderNotes, setOrderNotes] = useState('')
  const [showEmailModal, setShowEmailModal] = useState(false)
  const [showActivityForm, setShowActivityForm] = useState(false)
  const [actForm, setActForm] = useState({ type: 'call', activity_type_id: '', subject: '', description: '', status: 'completed', scheduled_at: '' })
  const [showDocForm, setShowDocForm] = useState(false)
  const [docForm, setDocForm] = useState({ doc_type: 'offerta', name: '', url: '', notes: '' })
  const [showOfferForm, setShowOfferForm] = useState(false)
  const [offerForm, setOfferForm] = useState({ title: '', billing_type: 'Daily', rate: '', days: '', amount: '', description: '' })

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
            <button onClick={() => navigate(`/crm/deals/${id}/edit`)}
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50">
              <Pencil className="h-4 w-4" /> Modifica
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
        {deal.pipeline_template_id && (
          <span className="rounded-full bg-indigo-100 px-3 py-1 text-xs font-medium text-indigo-700">
            Pipeline: {deal.pipeline_template_id.slice(0, 8)}...
          </span>
        )}
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
            <div className="grid grid-cols-2 gap-3">
              <Info label="Valore atteso" value={formatCurrency(deal.expected_revenue)} />
              <Info label="Probabilita" value={`${deal.probability}%`} />
              {deal.daily_rate > 0 && <Info label="Tariffa giornaliera" value={`${formatCurrency(deal.daily_rate)}/gg`} />}
              {deal.estimated_days > 0 && <Info label="Giorni stimati" value={String(deal.estimated_days)} />}
              {deal.technology && <Info label="Tecnologia / Stack" value={deal.technology} className="col-span-2" />}
              <Info label="Responsabile" value={deal.assigned_to_name || deal.assigned_to || '-'} />
              {deal.days_in_stage != null && <Info label="Giorni in questa fase" value={`${deal.days_in_stage} giorni`} />}
            </div>
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
                placeholder="Nome documento *" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <input type="url" value={docForm.url} onChange={(e) => setDocForm({ ...docForm, url: e.target.value })}
              placeholder="Link (Google Drive, SharePoint, Dropbox...)" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <input type="text" value={docForm.notes} onChange={(e) => setDocForm({ ...docForm, notes: e.target.value })}
              placeholder="Note (opzionale)" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <div className="flex gap-2">
              <button onClick={async () => {
                if (!docForm.name.trim()) return
                await addDocument.mutateAsync({ dealId: deal.id, ...docForm })
                setDocForm({ doc_type: 'offerta', name: '', url: '', notes: '' })
                setShowDocForm(false)
              }} disabled={!docForm.name.trim() || addDocument.isPending}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
                {addDocument.isPending ? 'Salvataggio...' : 'Salva'}
              </button>
              <button onClick={() => setShowDocForm(false)}
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
                      <a href={doc.url} target="_blank" rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 rounded bg-gray-50 px-2 py-1 text-xs text-blue-600 hover:bg-blue-50">
                        <Link2 className="h-3 w-3" /> Apri
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
            {!showOfferForm && (
              <button onClick={() => {
                setOfferForm({
                  title: deal.name,
                  billing_type: deal.deal_type === 'T&M' ? 'Daily' : 'LumpSum',
                  rate: String(deal.daily_rate || ''),
                  days: String(deal.estimated_days || ''),
                  amount: String(deal.expected_revenue || ''),
                  description: `Deal AgentFlow: ${deal.name}`,
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
                placeholder="Descrizione" rows={2} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />

              <div className="flex gap-2">
                <button onClick={async () => {
                  const payload: Record<string, unknown> = {
                    title: offerForm.title,
                    description: offerForm.description,
                    billing_type: offerForm.billing_type,
                    customer_id: deal.portal_customer_id,
                    rate: offerForm.rate ? parseInt(offerForm.rate) : undefined,
                    days: offerForm.days ? parseInt(offerForm.days) : undefined,
                    amount: offerForm.amount ? parseInt(offerForm.amount) : undefined,
                    outcome_type: 'W',
                  }
                  await createPortalOffer.mutateAsync(payload)
                  setShowOfferForm(false)
                }} disabled={!offerForm.title.trim() || createPortalOffer.isPending}
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
              return (
                <div key={a.id} className={`flex items-start gap-3 rounded-lg border px-4 py-2.5 ${isPlanned ? 'border-amber-200 bg-amber-50/50' : 'border-gray-100'}`}>
                  <AIcon className={`h-4 w-4 mt-0.5 shrink-0 ${isPlanned ? 'text-amber-500' : 'text-gray-400'}`} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-gray-900">{a.subject}</p>
                      {isPlanned && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700">Pianificata</span>}
                    </div>
                    {a.description && <p className="text-xs text-gray-500 mt-0.5">{a.description}</p>}
                    <p className="text-[10px] text-gray-400 mt-1">
                      {a.type} - {a.status}
                      {a.scheduled_at && ` - ${a.scheduled_at.split('T')[0]} ${a.scheduled_at.split('T')[1]?.slice(0, 5) || ''}`}
                      {!a.scheduled_at && a.created_at && ` - ${a.created_at.split('T')[0]}`}
                    </p>
                  </div>
                  {isPlanned && (
                    <button onClick={() => createActivity.mutateAsync({
                      deal_id: deal.id, contact_id: deal.client_id || undefined,
                      type: a.type, subject: `${a.subject} (completata)`, status: 'completed',
                    })}
                      className="shrink-0 rounded bg-green-50 px-2 py-1 text-[10px] font-medium text-green-700 hover:bg-green-100">
                      Completa
                    </button>
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
