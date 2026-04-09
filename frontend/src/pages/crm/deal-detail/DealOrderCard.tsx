import { useState } from 'react'
import { useRegisterOrder, useConfirmOrder } from '../../../api/hooks'
import { FileCheck, CheckCircle, AlertCircle } from 'lucide-react'

const ORDER_TYPES = [
  { value: 'po', label: 'Purchase Order (PO)' },
  { value: 'email', label: 'Conferma via Email' },
  { value: 'firma_word', label: 'Firma su documento Word' },
  { value: 'portale', label: 'Accettazione da portale' },
]

interface DealOrderCardProps {
  deal: any
  dealId: string
}

export default function DealOrderCard({ deal, dealId }: DealOrderCardProps) {
  const registerOrder = useRegisterOrder()
  const confirmOrder = useConfirmOrder()

  const [showOrderForm, setShowOrderForm] = useState(false)
  const [orderType, setOrderType] = useState('po')
  const [orderRef, setOrderRef] = useState('')
  const [orderNotes, setOrderNotes] = useState('')

  const hasOrder = !!deal.order_type
  const isConfirmed = deal.probability === 100

  const handleRegisterOrder = async () => {
    await registerOrder.mutateAsync({
      dealId,
      order_type: orderType, order_reference: orderRef, order_notes: orderNotes,
    })
    setShowOrderForm(false)
  }

  return (
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
          <button onClick={() => confirmOrder.mutateAsync(dealId)} disabled={confirmOrder.isPending}
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
  )
}
