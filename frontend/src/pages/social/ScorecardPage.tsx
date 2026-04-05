import { useState } from 'react'
import { useScorecard, useTeamUsers } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import { formatCurrency } from '../../lib/utils'
import { TrendingUp, Target, Award, Activity, Users } from 'lucide-react'

export default function ScorecardPage() {
  const { data: users } = useTeamUsers()
  const [selectedUser, setSelectedUser] = useState('')
  const today = new Date()
  const monthStart = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-01`
  const monthEnd = today.toISOString().split('T')[0]

  const { data: scorecard, isLoading } = useScorecard(selectedUser, monthStart, monthEnd)

  const kpis = scorecard?.kpis

  return (
    <div className="space-y-6">
      <PageHeader title="Scorecard Collaboratori" subtitle="KPI di performance per ogni membro del team commerciale" />

      <div className="flex items-center gap-3">
        <Users className="h-4 w-4 text-gray-400" />
        <select value={selectedUser} onChange={(e) => setSelectedUser(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm min-w-[250px]">
          <option value="">-- Seleziona collaboratore --</option>
          {users?.map((u: any) => (
            <option key={u.id} value={u.id}>{u.name} ({u.role})</option>
          ))}
        </select>
      </div>

      {!selectedUser ? (
        <div className="rounded-xl border-2 border-dashed border-gray-200 p-12 text-center text-gray-400">
          <Users className="mx-auto h-12 w-12 mb-3" />
          <p>Seleziona un collaboratore per visualizzare la scorecard</p>
        </div>
      ) : isLoading ? <LoadingSpinner /> : !kpis ? (
        <div className="rounded-xl border border-gray-200 bg-white p-8 text-center text-gray-400">
          Nessun dato disponibile per questo periodo
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <KpiCard icon={Target} label="Deal Creati" value={String(kpis.deal_count)} color="blue" />
          <KpiCard icon={Award} label="Deal Vinti" value={String(kpis.won_count)} color="green" />
          <KpiCard icon={TrendingUp} label="Revenue Chiusa" value={formatCurrency(kpis.revenue_closed)} color="emerald" />
          <KpiCard icon={Target} label="Win Rate" value={`${kpis.win_rate}%`} color="purple" />
          <KpiCard icon={Activity} label="Attivita" value={String(kpis.activity_count)} color="amber" />
        </div>
      )}
    </div>
  )
}

function KpiCard({ icon: Icon, label, value, color }: { icon: typeof Target; label: string; value: string; color: string }) {
  const bg: Record<string, string> = { blue: 'bg-blue-50', green: 'bg-green-50', emerald: 'bg-emerald-50', purple: 'bg-purple-50', amber: 'bg-amber-50' }
  const text: Record<string, string> = { blue: 'text-blue-600', green: 'text-green-600', emerald: 'text-emerald-600', purple: 'text-purple-600', amber: 'text-amber-600' }
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <div className={`inline-flex rounded-lg p-2 ${bg[color]}`}>
        <Icon className={`h-5 w-5 ${text[color]}`} />
      </div>
      <p className="mt-3 text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-xs text-gray-500">{label}</p>
    </div>
  )
}
