import { useState } from 'react'
import { useMonthlyCompensation, useCalculateCompensation, useConfirmCompensation, useMarkPaidCompensation } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import { formatCurrency } from '../../lib/utils'
import { Calculator, CheckCircle, CreditCard, AlertCircle } from 'lucide-react'

const STATUS_MAP: Record<string, { label: string; color: string; icon: typeof CheckCircle }> = {
  draft: { label: 'Bozza', color: 'bg-yellow-50 text-yellow-700', icon: AlertCircle },
  confirmed: { label: 'Confermato', color: 'bg-blue-50 text-blue-700', icon: CheckCircle },
  paid: { label: 'Pagato', color: 'bg-green-50 text-green-700', icon: CreditCard },
  error: { label: 'Errore', color: 'bg-red-50 text-red-700', icon: AlertCircle },
}

export default function CompensationPage() {
  const today = new Date()
  const [month, setMonth] = useState(`${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-01`)
  const { data: entries, isLoading } = useMonthlyCompensation(month)
  const calculate = useCalculateCompensation()
  const confirm = useConfirmCompensation()
  const markPaid = useMarkPaidCompensation()

  return (
    <div className="space-y-6">
      <PageHeader title="Compensi Mensili" subtitle="Calcolo e gestione provvigioni del team commerciale"
        actions={
          <button onClick={() => calculate.mutate(month)} disabled={calculate.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
            <Calculator className="h-4 w-4" /> {calculate.isPending ? 'Calcolo...' : 'Calcola Mese'}
          </button>
        } />

      <div className="flex items-center gap-3">
        <input type="month" value={month.slice(0, 7)}
          onChange={(e) => setMonth(e.target.value + '-01')}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
      </div>

      {isLoading ? <LoadingSpinner /> : !entries?.length ? (
        <div className="rounded-xl border-2 border-dashed border-gray-200 p-12 text-center text-gray-400">
          <Calculator className="mx-auto h-12 w-12 mb-3" />
          <p>Nessun compenso per questo mese. Clicca "Calcola Mese" per generare.</p>
        </div>
      ) : (
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs font-semibold uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3">Collaboratore</th>
                <th className="px-4 py-3">Mese</th>
                <th className="px-4 py-3">Deal</th>
                <th className="px-4 py-3">Revenue</th>
                <th className="px-4 py-3">Compenso Lordo</th>
                <th className="px-4 py-3">Stato</th>
                <th className="px-4 py-3">Azioni</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {entries.map((e: any) => {
                const st = STATUS_MAP[e.status] || STATUS_MAP.draft
                const Icon = st.icon
                return (
                  <tr key={e.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{e.user_id.slice(0, 8)}...</td>
                    <td className="px-4 py-3 text-gray-500">{e.month}</td>
                    <td className="px-4 py-3">{e.deal_contributions?.deal_count || 0}</td>
                    <td className="px-4 py-3">{formatCurrency(e.deal_contributions?.total_revenue || 0)}</td>
                    <td className="px-4 py-3 font-semibold text-gray-900">{formatCurrency(e.amount_gross)}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${st.color}`}>
                        <Icon className="h-3 w-3" /> {st.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 space-x-1">
                      {e.status === 'draft' && (
                        <button onClick={() => confirm.mutate(e.id)}
                          className="rounded bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100">Conferma</button>
                      )}
                      {e.status === 'confirmed' && (
                        <button onClick={() => markPaid.mutate(e.id)}
                          className="rounded bg-green-50 px-2 py-1 text-xs font-medium text-green-700 hover:bg-green-100">Segna Pagato</button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {entries?.length > 0 && (
        <div className="rounded-xl bg-gray-50 p-4 text-sm text-gray-600">
          <strong>Regole applicate:</strong>{' '}
          {entries[0]?.rules_applied?.map((r: any) => `${r.rule_name} (${formatCurrency(r.amount)})`).join(' + ') || '-'}
        </div>
      )}
    </div>
  )
}
