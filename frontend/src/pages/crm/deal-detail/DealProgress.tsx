import { useDealProgress } from '../../../api/hooks'

interface DealProgressProps {
  deal: any
  dealId: string
  portalEnabled: boolean
}

export default function DealProgress({ deal, dealId, portalEnabled }: DealProgressProps) {
  const { data: dealProgressData } = useDealProgress(dealId, deal?.portal_project_id || undefined)

  if (!portalEnabled || !deal.portal_project_id || !dealProgressData?.progress) return null

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
          <p className="text-lg font-bold text-gray-900">&euro; {Number(p.deal_value).toLocaleString('it-IT')}</p>
        </div>
        <div className="rounded-lg bg-white border border-blue-100 px-3 py-2 text-center">
          <p className="text-[10px] uppercase text-gray-400">Costo Stimato</p>
          <p className="text-lg font-bold text-gray-700">&euro; {Number(p.estimated_cost).toLocaleString('it-IT')}</p>
        </div>
        <div className={`rounded-lg border px-3 py-2 text-center ${
          p.margin_pct >= 25 ? 'bg-green-50 border-green-200' :
          p.margin_pct >= 15 ? 'bg-yellow-50 border-yellow-200' :
          'bg-red-50 border-red-200'
        }`}>
          <p className="text-[10px] uppercase text-gray-400">Margine</p>
          <p className={`text-lg font-bold ${
            p.margin_pct >= 25 ? 'text-green-700' : p.margin_pct >= 15 ? 'text-yellow-700' : 'text-red-700'
          }`}>&euro; {Number(p.margin_eur).toLocaleString('it-IT')} ({p.margin_pct}%)</p>
        </div>
        <div className="rounded-lg bg-white border border-blue-100 px-3 py-2 text-center">
          <p className="text-[10px] uppercase text-gray-400">Risorse</p>
          <p className="text-lg font-bold text-gray-900">{p.assigned_persons}</p>
          <p className="text-[10px] text-gray-400">costo medio &euro;{p.avg_daily_cost}/gg</p>
        </div>
      </div>

      {/* Progress details */}
      <div className="grid gap-2 sm:grid-cols-3 text-xs text-gray-500">
        <p>Giorni pianificati: <span className="font-medium text-gray-700">{p.planned_days}</span></p>
        <p>Tariffa giornaliera: <span className="font-medium text-gray-700">&euro;{p.daily_rate}</span></p>
        <p>Costo giornaliero totale: <span className="font-medium text-gray-700">&euro;{p.total_daily_cost}</span></p>
      </div>
    </div>
  )
}
