import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useCrmDeal, useRegisterOrder, useConfirmOrder, useEmailSends } from '../../api/hooks'
import { formatCurrency } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import SendEmailModal from '../../components/email/SendEmailModal'
import { ArrowLeft, FileCheck, CheckCircle, AlertCircle, Mail, Eye, MousePointer } from 'lucide-react'

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

export default function CrmDealDetailPage() {
  const { dealId } = useParams()
  const navigate = useNavigate()
  const id = dealId || '0'

  const { data: deal, isLoading } = useCrmDeal(parseInt(id, 10))
  const registerOrder = useRegisterOrder()
  const confirmOrder = useConfirmOrder()
  const { data: emailHistory } = useEmailSends(deal?.client_id || undefined)

  const [showOrderForm, setShowOrderForm] = useState(false)
  const [orderType, setOrderType] = useState('po')
  const [orderRef, setOrderRef] = useState('')
  const [orderNotes, setOrderNotes] = useState('')
  const [showEmailModal, setShowEmailModal] = useState(false)

  if (isLoading) return <LoadingSpinner />
  if (!deal) return <div className="p-8 text-center text-gray-500">Deal non trovato</div>

  const hasOrder = !!deal.order_type
  const isConfirmed = deal.probability === 100

  const handleRegisterOrder = async () => {
    await registerOrder.mutateAsync({
      dealId: parseInt(id, 10),
      order_type: orderType,
      order_reference: orderRef,
      order_notes: orderNotes,
    })
    setShowOrderForm(false)
  }

  const handleConfirm = async () => {
    await confirmOrder.mutateAsync(id)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={deal.name}
        subtitle={`${deal.client_name} - ${deal.stage}`}
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowEmailModal(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700"
            >
              <Mail className="h-4 w-4" />
              Invia email
            </button>
            <button
              onClick={() => navigate('/crm')}
              className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
            >
              <ArrowLeft className="h-4 w-4" />
              Pipeline
            </button>
          </div>
        }
      />

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Deal Info Card */}
        <div className="rounded-xl border border-gray-200 bg-white p-6 space-y-4">
          <h3 className="text-sm font-semibold uppercase text-gray-400">Dettagli Deal</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-gray-400">Cliente</p>
              <p className="font-medium text-gray-900">{deal.client_name}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400">Fase</p>
              <p className="font-medium text-gray-900">{deal.stage}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400">Tipo</p>
              <p className="font-medium text-gray-900">{deal.deal_type || '-'}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400">Probabilita</p>
              <p className="font-medium text-gray-900">{deal.probability}%</p>
            </div>
            <div>
              <p className="text-xs text-gray-400">Valore</p>
              <p className="font-medium text-gray-900">{formatCurrency(deal.expected_revenue)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400">Responsabile</p>
              <p className="font-medium text-gray-900">{deal.user_name || deal.assigned_to || '-'}</p>
            </div>
            {deal.daily_rate > 0 && (
              <>
                <div>
                  <p className="text-xs text-gray-400">Tariffa giornaliera</p>
                  <p className="font-medium text-gray-900">{formatCurrency(deal.daily_rate)}/gg</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400">Giorni stimati</p>
                  <p className="font-medium text-gray-900">{deal.estimated_days}</p>
                </div>
              </>
            )}
            {deal.technology && (
              <div className="col-span-2">
                <p className="text-xs text-gray-400">Tecnologia</p>
                <p className="font-medium text-gray-900">{deal.technology}</p>
              </div>
            )}
          </div>
        </div>

        {/* Order Card */}
        <div className="rounded-xl border border-gray-200 bg-white p-6 space-y-4">
          <h3 className="text-sm font-semibold uppercase text-gray-400">Ordine Cliente</h3>

          {isConfirmed ? (
            <div className="flex items-start gap-3 rounded-lg bg-green-50 p-4">
              <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
              <div>
                <p className="font-medium text-green-800">Ordine confermato</p>
                <p className="text-sm text-green-600">
                  Tipo: {deal.order_type} | Rif: {deal.order_reference || '-'}
                </p>
                {deal.order_notes && (
                  <p className="mt-1 text-sm text-green-600">{deal.order_notes}</p>
                )}
              </div>
            </div>
          ) : hasOrder ? (
            <div className="space-y-4">
              <div className="flex items-start gap-3 rounded-lg bg-yellow-50 p-4">
                <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
                <div>
                  <p className="font-medium text-yellow-800">Ordine registrato — in attesa di conferma</p>
                  <p className="text-sm text-yellow-600">
                    Tipo: {deal.order_type} | Rif: {deal.order_reference || '-'}
                  </p>
                </div>
              </div>
              <button
                onClick={handleConfirm}
                disabled={confirmOrder.isPending}
                className="w-full rounded-lg bg-green-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
              >
                {confirmOrder.isPending ? 'Conferma in corso...' : 'Conferma Ordine'}
              </button>
            </div>
          ) : showOrderForm ? (
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Tipo accettazione</label>
                <select
                  value={orderType}
                  onChange={(e) => setOrderType(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                >
                  {ORDER_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Riferimento ordine</label>
                <input
                  type="text"
                  value={orderRef}
                  onChange={(e) => setOrderRef(e.target.value)}
                  placeholder="Numero PO, ODA..."
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Note</label>
                <textarea
                  value={orderNotes}
                  onChange={(e) => setOrderNotes(e.target.value)}
                  rows={2}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleRegisterOrder}
                  disabled={registerOrder.isPending}
                  className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {registerOrder.isPending ? 'Salvataggio...' : 'Registra Ordine'}
                </button>
                <button
                  onClick={() => setShowOrderForm(false)}
                  className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
                >
                  Annulla
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setShowOrderForm(true)}
              className="w-full inline-flex items-center justify-center gap-2 rounded-lg border-2 border-dashed border-gray-300 px-4 py-4 text-sm font-medium text-gray-500 hover:border-blue-400 hover:text-blue-600 transition-colors"
            >
              <FileCheck className="h-5 w-5" />
              Registra ordine cliente
            </button>
          )}
        </div>
      </div>

      {/* Email History */}
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
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={`text-xs font-medium ${st.color}`}>{st.label}</span>
                    {email.open_count > 0 && <span className="text-[10px] text-gray-400">{email.open_count}x aperta</span>}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Send Email Modal */}
      <SendEmailModal
        open={showEmailModal}
        onClose={() => setShowEmailModal(false)}
        toEmail={deal.client_name ? '' : ''}
        toName={deal.client_name}
        contactId={deal.client_id}
        defaultParams={{ deal_name: deal.name, deal_value: String(deal.expected_revenue) }}
      />
    </div>
  )
}
