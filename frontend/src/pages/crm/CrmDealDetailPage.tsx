import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  useCrmDeal, useRegisterOrder, useConfirmOrder, useEmailSends,
  useDealProducts, useAddDealProduct, useRemoveDealProduct,
  useProducts, useActivityTypes, useCrmActivities, useCreateCrmActivity,
} from '../../api/hooks'
import { formatCurrency } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import SendEmailModal from '../../components/email/SendEmailModal'
import {
  ArrowLeft, FileCheck, CheckCircle, AlertCircle, Mail, Eye, MousePointer,
  Package, Plus, Trash2, Phone, Calendar, MessageSquare, Activity, Pencil,
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
  call: Phone, meeting: Calendar, email: Mail, note: MessageSquare, task: Activity,
}

export default function CrmDealDetailPage() {
  const { dealId } = useParams()
  const navigate = useNavigate()
  const id = dealId || ''

  const { data: deal, isLoading } = useCrmDeal(id)
  const registerOrder = useRegisterOrder()
  const confirmOrder = useConfirmOrder()
  const { data: emailHistory } = useEmailSends(deal?.client_id || undefined)

  // Products
  const { data: dealProducts } = useDealProducts(deal?.id || '')
  const { data: catalogProducts } = useProducts(true)
  const addProduct = useAddDealProduct()
  const removeProduct = useRemoveDealProduct()

  // Activities
  const { data: activityTypes } = useActivityTypes(true)
  const { data: activities } = useCrmActivities(undefined, deal?.id)
  const createActivity = useCreateCrmActivity()

  const [showOrderForm, setShowOrderForm] = useState(false)
  const [orderType, setOrderType] = useState('po')
  const [orderRef, setOrderRef] = useState('')
  const [orderNotes, setOrderNotes] = useState('')
  const [showEmailModal, setShowEmailModal] = useState(false)
  const [showAddProduct, setShowAddProduct] = useState(false)
  const [prodForm, setProdForm] = useState({ product_id: '', quantity: '1', price_override: '' })
  const [showActivityForm, setShowActivityForm] = useState(false)
  const [actForm, setActForm] = useState({ type: 'call', activity_type_id: '', subject: '', description: '', status: 'completed', scheduled_at: '' })

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

  const handleAddProduct = async () => {
    if (!prodForm.product_id) return
    await addProduct.mutateAsync({
      dealId: deal.id,
      product_id: prodForm.product_id,
      quantity: Number(prodForm.quantity) || 1,
      price_override: prodForm.price_override ? Number(prodForm.price_override) : undefined,
    })
    setProdForm({ product_id: '', quantity: '1', price_override: '' })
    setShowAddProduct(false)
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
        subtitle={`${deal.client_name} - ${deal.stage}`}
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

      <div className="grid gap-6 lg:grid-cols-2">
        {/* ── Deal Info ── */}
        <div className="rounded-xl border border-gray-200 bg-white p-6 space-y-4">
          <h3 className="text-sm font-semibold uppercase text-gray-400">Dettagli Deal</h3>
          <div className="grid grid-cols-2 gap-4">
            <Info label="Cliente" value={deal.client_name} />
            <Info label="Fase" value={deal.stage} />
            <Info label="Tipo" value={deal.deal_type || '-'} />
            <Info label="Probabilita" value={`${deal.probability}%`} />
            <Info label="Valore" value={formatCurrency(deal.expected_revenue)} />
            <Info label="Responsabile" value={deal.user_name || deal.assigned_to || '-'} />
            {deal.daily_rate > 0 && <Info label="Tariffa" value={`${formatCurrency(deal.daily_rate)}/gg`} />}
            {deal.estimated_days > 0 && <Info label="Giorni" value={String(deal.estimated_days)} />}
            {deal.technology && <Info label="Tecnologia" value={deal.technology} className="col-span-2" />}
          </div>
        </div>

        {/* ── Order ── */}
        <div className="rounded-xl border border-gray-200 bg-white p-6 space-y-4">
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

      {/* ── Products ── */}
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold uppercase text-gray-400">Prodotti / Servizi</h3>
          <button onClick={() => setShowAddProduct(!showAddProduct)}
            className="inline-flex items-center gap-1 rounded-lg bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-100">
            <Plus className="h-3 w-3" /> Aggiungi
          </button>
        </div>

        {showAddProduct && (
          <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50/30 p-3 space-y-2">
            <div className="grid gap-2 sm:grid-cols-3">
              <select value={prodForm.product_id} onChange={(e) => setProdForm({ ...prodForm, product_id: e.target.value })}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                <option value="">-- Seleziona prodotto --</option>
                {catalogProducts?.map((p: any) => (
                  <option key={p.id} value={p.id}>{p.name} ({formatCurrency(p.base_price || 0)})</option>
                ))}
              </select>
              <input type="number" value={prodForm.quantity} onChange={(e) => setProdForm({ ...prodForm, quantity: e.target.value })}
                placeholder="Quantita" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              <input type="number" value={prodForm.price_override} onChange={(e) => setProdForm({ ...prodForm, price_override: e.target.value })}
                placeholder="Prezzo override (opz.)" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <div className="flex gap-2">
              <button onClick={handleAddProduct} disabled={!prodForm.product_id}
                className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50">Aggiungi</button>
              <button onClick={() => setShowAddProduct(false)} className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-600">Annulla</button>
            </div>
          </div>
        )}

        {dealProducts && dealProducts.length > 0 ? (
          <div className="space-y-2">
            {dealProducts.map((dp: any) => (
              <div key={dp.id} className="flex items-center justify-between rounded-lg border border-gray-100 px-4 py-2.5">
                <div className="flex items-center gap-3 min-w-0">
                  <Package className="h-4 w-4 text-blue-500 shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900">{dp.product_name}</p>
                    <p className="text-xs text-gray-400">qty {dp.quantity} x {formatCurrency(dp.unit_price || 0)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="text-sm font-semibold text-gray-900">{formatCurrency(dp.line_total || 0)}</span>
                  <button onClick={() => removeProduct.mutate({ dealId: deal.id, lineId: dp.id })}
                    className="text-gray-300 hover:text-red-500"><Trash2 className="h-3.5 w-3.5" /></button>
                </div>
              </div>
            ))}
            <div className="flex justify-end pt-2 border-t border-gray-100">
              <span className="text-sm font-bold text-gray-900">
                Totale: {formatCurrency(dealProducts.reduce((s: number, dp: any) => s + (dp.line_total || 0), 0))}
              </span>
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-400 text-center py-4">Nessun prodotto associato</p>
        )}
      </div>

      {/* ── Activities ── */}
      <div className="rounded-xl border border-gray-200 bg-white p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold uppercase text-gray-400">Attivita</h3>
          <button onClick={() => setShowActivityForm(!showActivityForm)}
            className="inline-flex items-center gap-1 rounded-lg bg-green-50 px-3 py-1.5 text-xs font-medium text-green-700 hover:bg-green-100">
            <Plus className="h-3 w-3" /> Nuova Attivita
          </button>
        </div>

        {showActivityForm && (
          <div className="mb-4 rounded-lg border border-green-200 bg-green-50/30 p-3 space-y-2">
            <div className="grid gap-2 sm:grid-cols-2">
              <select value={actForm.type} onChange={(e) => setActForm({ ...actForm, type: e.target.value })}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                <option value="call">Chiamata</option>
                <option value="meeting">Incontro</option>
                <option value="email">Email</option>
                <option value="note">Nota</option>
                <option value="task">Task</option>
              </select>
              <select value={actForm.activity_type_id} onChange={(e) => setActForm({ ...actForm, activity_type_id: e.target.value })}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                <option value="">-- Tipo custom (opz.) --</option>
                {activityTypes?.map((t: any) => (
                  <option key={t.id} value={t.id}>{t.label} ({t.category})</option>
                ))}
              </select>
            </div>
            <input type="text" value={actForm.subject} onChange={(e) => setActForm({ ...actForm, subject: e.target.value })}
              placeholder="Oggetto attivita *" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <textarea value={actForm.description} onChange={(e) => setActForm({ ...actForm, description: e.target.value })}
              placeholder="Descrizione / note" rows={2} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <div className="flex flex-wrap items-center gap-3">
              <select value={actForm.status} onChange={(e) => setActForm({ ...actForm, status: e.target.value })}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                <option value="completed">Completata</option>
                <option value="planned">Pianificata</option>
              </select>
              {actForm.status === 'planned' && (
                <input type="datetime-local" value={actForm.scheduled_at}
                  onChange={(e) => setActForm({ ...actForm, scheduled_at: e.target.value })}
                  className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              )}
              <button onClick={handleCreateActivity} disabled={!actForm.subject.trim() || createActivity.isPending}
                className="rounded-lg bg-green-600 px-3 py-2 text-xs font-medium text-white disabled:opacity-50">
                {createActivity.isPending ? 'Salvataggio...' : actForm.status === 'planned' ? 'Pianifica' : 'Salva Attivita'}
              </button>
              <button onClick={() => setShowActivityForm(false)} className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-600">Annulla</button>
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
        <div className="rounded-xl border border-gray-200 bg-white p-6">
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
