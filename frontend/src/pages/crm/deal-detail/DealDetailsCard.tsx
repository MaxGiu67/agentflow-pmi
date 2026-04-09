import { useState } from 'react'
import { useUpdateCrmDeal } from '../../../api/hooks'
import { formatCurrency } from '../../../lib/utils'

function Info({ label, value, className = '' }: { label: string; value: string; className?: string }) {
  return (
    <div className={className}>
      <p className="text-xs text-gray-400">{label}</p>
      <p className="font-medium text-gray-900">{value}</p>
    </div>
  )
}

interface DealDetailsCardProps {
  deal: any
  dealId: string
  editMode: boolean
  setEditMode: (v: boolean) => void
}

export default function DealDetailsCard({ deal, dealId, editMode, setEditMode }: DealDetailsCardProps) {
  const updateDeal = useUpdateCrmDeal()
  const [editForm, setEditForm] = useState({
    name: deal.name || '',
    expected_revenue: String(deal.expected_revenue || ''),
    daily_rate: String(deal.daily_rate || ''),
    estimated_days: String(deal.estimated_days || ''),
    technology: deal.technology || '',
    probability: String(deal.probability || ''),
  })

  // Sync form when deal changes and edit mode is toggled on
  const syncForm = () => {
    setEditForm({
      name: deal.name || '',
      expected_revenue: String(deal.expected_revenue || ''),
      daily_rate: String(deal.daily_rate || ''),
      estimated_days: String(deal.estimated_days || ''),
      technology: deal.technology || '',
      probability: String(deal.probability || ''),
    })
  }

  // Expose sync via parent toggle
  if (editMode && editForm.name === '' && deal.name) {
    syncForm()
  }

  return (
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
              dealId,
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
  )
}
