import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Pencil, Plus } from 'lucide-react'
import { useBudget } from '../../api/hooks'
import { formatCurrency } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'
import { cn } from '../../lib/utils'

interface MonthValue {
  month: number
  label: string
  budget: number
  actual: number
}

interface BudgetEntry {
  category: string
  label: string
  monthly: MonthValue[]
  total_budget: number
  total_actual: number
  variance: number
  variance_pct: number
}

function fmtK(n: number): string {
  if (Math.abs(n) >= 1000) return `${(n / 1000).toFixed(1)}k`
  return n.toFixed(0)
}

function fmtCur(n: number): string {
  return formatCurrency(n)
}

export default function BudgetPage() {
  const navigate = useNavigate()
  const currentYear = new Date().getFullYear()
  const [year, setYear] = useState(currentYear)
  const [viewMode, setViewMode] = useState<'budget' | 'actual' | 'variance'>('budget')
  const { data: budget, isLoading } = useBudget(year)

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const entries: BudgetEntry[] = budget?.entries ?? []
  const monthLabels: string[] = budget?.month_labels ?? ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu', 'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic']

  // Split into revenue and cost entries
  const revenueEntries = entries.filter((e) => e.category.startsWith('ricavi'))
  const costEntries = entries.filter((e) => !e.category.startsWith('ricavi'))

  function getCellValue(entry: BudgetEntry, monthIndex: number): number {
    const mv = entry.monthly?.[monthIndex]
    if (!mv) return 0
    if (viewMode === 'budget') return mv.budget
    if (viewMode === 'actual') return mv.actual
    return mv.actual - mv.budget
  }

  function getCellColor(entry: BudgetEntry, monthIndex: number): string {
    if (viewMode !== 'variance') return ''
    const val = getCellValue(entry, monthIndex)
    const isRevenue = entry.category.startsWith('ricavi')
    // For revenue: positive variance = good. For costs: negative variance = good
    if (val === 0) return ''
    if (isRevenue) return val > 0 ? 'text-green-600' : 'text-red-600'
    return val < 0 ? 'text-green-600' : 'text-red-600'
  }

  function renderSection(title: string, sectionEntries: BudgetEntry[], bgClass: string) {
    if (sectionEntries.length === 0) return null
    const sectionTotal = sectionEntries.reduce((s, e) =>
      viewMode === 'budget' ? s + e.total_budget :
      viewMode === 'actual' ? s + e.total_actual :
      s + e.variance, 0)

    return (
      <>
        <tr className={cn('border-t-2 border-slate-300', bgClass)}>
          <td className="sticky left-0 z-10 px-3 py-2 text-xs font-bold uppercase tracking-wider text-slate-500" style={{ background: 'inherit' }}>
            {title}
          </td>
          {monthLabels.map((_, i) => <td key={i} />)}
          <td className="px-3 py-2 text-right text-xs font-bold text-slate-700">{fmtCur(sectionTotal)}</td>
        </tr>
        {sectionEntries.map((entry) => (
          <tr key={entry.category} className="border-t border-slate-100 hover:bg-slate-50">
            <td className="sticky left-0 z-10 whitespace-nowrap bg-white px-3 py-2 text-sm font-medium text-slate-700">
              {entry.label}
            </td>
            {monthLabels.map((_, i) => {
              const val = getCellValue(entry, i)
              return (
                <td key={i} className={cn('px-2 py-2 text-right text-xs tabular-nums', getCellColor(entry, i))}>
                  {val !== 0 ? fmtK(val) : <span className="text-slate-300">-</span>}
                </td>
              )
            })}
            <td className={cn(
              'px-3 py-2 text-right text-sm font-semibold tabular-nums',
              viewMode === 'variance' ? (
                entry.category.startsWith('ricavi')
                  ? (entry.variance >= 0 ? 'text-green-600' : 'text-red-600')
                  : (entry.variance <= 0 ? 'text-green-600' : 'text-red-600')
              ) : 'text-slate-800',
            )}>
              {viewMode === 'budget' ? fmtCur(entry.total_budget) :
               viewMode === 'actual' ? fmtCur(entry.total_actual) :
               fmtCur(entry.variance)}
            </td>
          </tr>
        ))}
      </>
    )
  }

  // EBITDA per month
  const ebitdaMonthly = monthLabels.map((_, i) => {
    const rev = revenueEntries.reduce((s, e) => s + getCellValue(e, i), 0)
    const cost = costEntries.reduce((s, e) => s + getCellValue(e, i), 0)
    return rev - cost
  })
  const ebitdaTotal = ebitdaMonthly.reduce((s, v) => s + v, 0)

  return (
    <div>
      <PageHeader
        title={`Budget ${year}`}
        subtitle="Piano economico mensile — budget, consuntivo e scostamenti"
        actions={
          <div className="flex items-center gap-3">
            <select
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              {Array.from({ length: 5 }, (_, i) => currentYear + 1 - i).map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
            <button
              onClick={() => navigate(`/budget/wizard?edit=true&year=${year}`)}
              className="inline-flex items-center gap-2 rounded-lg border border-blue-300 px-4 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50"
            >
              <Pencil className="h-4 w-4" />
              Modifica
            </button>
          </div>
        }
      />

      {entries.length === 0 ? (
        <div className="flex flex-col items-center py-20">
          <EmptyState
            title="Nessun budget definito"
            description={`Crea il budget ${year} per confrontare previsioni e dati reali.`}
          />
          <button
            onClick={() => navigate(`/budget/wizard?year=${year}`)}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-700"
          >
            <Plus className="h-5 w-5" />
            Crea budget {year}
          </button>
        </div>
      ) : (
        <>
          {/* View mode toggle */}
          <div className="mb-4 flex gap-1 rounded-lg border border-slate-200 bg-slate-50 p-1 w-fit">
            {([
              { key: 'budget' as const, label: 'Budget' },
              { key: 'actual' as const, label: 'Consuntivo' },
              { key: 'variance' as const, label: 'Scostamento' },
            ]).map((m) => (
              <button
                key={m.key}
                onClick={() => setViewMode(m.key)}
                className={cn(
                  'rounded-md px-4 py-1.5 text-xs font-semibold transition-all',
                  viewMode === m.key ? 'bg-white text-blue-700 shadow-sm' : 'text-slate-500 hover:text-slate-700',
                )}
              >
                {m.label}
              </button>
            ))}
          </div>

          {/* Monthly grid table */}
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="w-full min-w-[900px]">
              <thead>
                <tr className="bg-slate-50">
                  <th className="sticky left-0 z-10 bg-slate-50 px-3 py-2.5 text-left text-xs font-semibold text-slate-600">
                    Voce
                  </th>
                  {monthLabels.map((ml) => (
                    <th key={ml} className="px-2 py-2.5 text-right text-xs font-semibold text-slate-500">
                      {ml}
                    </th>
                  ))}
                  <th className="px-3 py-2.5 text-right text-xs font-semibold text-slate-700">
                    Totale
                  </th>
                </tr>
              </thead>
              <tbody>
                {renderSection('Ricavi', revenueEntries, 'bg-green-50/50')}
                {renderSection('Costi', costEntries, 'bg-red-50/30')}

                {/* EBITDA row */}
                <tr className="border-t-2 border-slate-400 bg-slate-100 font-bold">
                  <td className="sticky left-0 z-10 bg-slate-100 px-3 py-2.5 text-sm text-slate-800">
                    EBITDA
                  </td>
                  {ebitdaMonthly.map((val, i) => (
                    <td key={i} className={cn('px-2 py-2.5 text-right text-xs tabular-nums', val >= 0 ? 'text-green-700' : 'text-red-700')}>
                      {fmtK(val)}
                    </td>
                  ))}
                  <td className={cn('px-3 py-2.5 text-right text-sm tabular-nums', ebitdaTotal >= 0 ? 'text-green-700' : 'text-red-700')}>
                    {fmtCur(ebitdaTotal)}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Legend */}
          <p className="mt-3 text-xs text-slate-400">
            {viewMode === 'budget' && 'Importi budget previsti per mese.'}
            {viewMode === 'actual' && 'Importi consuntivo reali per mese.'}
            {viewMode === 'variance' && 'Scostamento: consuntivo - budget. Verde = favorevole, Rosso = sfavorevole.'}
            {' '}I valori sono in migliaia (k = x1.000).
          </p>
        </>
      )}
    </div>
  )
}
