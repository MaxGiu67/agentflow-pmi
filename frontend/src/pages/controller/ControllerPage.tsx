import { useState } from 'react'
import {
  TrendingUp,
  TrendingDown,
  BarChart3,
  Sparkles,
  CheckCircle2,
} from 'lucide-react'
import {
  useBudgetGenerate,
  useBudgetVsActual,
  useControllerSummary,
} from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'
import { formatCurrency } from '../../lib/utils'

interface BudgetLine {
  category: string
  budget: number
  actual: number
  scostamento: number
  scostamento_pct: number
}

interface SummaryKPI {
  ricavi: number
  costi: number
  margine: number
  margine_pct: number
  trend: 'up' | 'down' | 'flat'
  ricavi_prev: number
}

const currentYear = new Date().getFullYear()
const currentMonth = new Date().getMonth() + 1

export default function ControllerPage() {
  const [budgetYear, setBudgetYear] = useState(currentYear)
  const [growthRate, setGrowthRate] = useState(5)
  const [selectedMonth, setSelectedMonth] = useState(currentMonth)
  const [selectedYear, setSelectedYear] = useState(currentYear)
  const [budgetProposal, setBudgetProposal] = useState<Record<string, unknown>[] | null>(null)
  const [budgetSaved, setBudgetSaved] = useState(false)

  const budgetGenerate = useBudgetGenerate()
  const { data: vsActualData, isLoading: vsActualLoading } = useBudgetVsActual(selectedYear, selectedMonth)
  const { data: summaryData, isLoading: summaryLoading } = useControllerSummary(selectedYear, selectedMonth)

  const vsActual = (vsActualData as { lines?: BudgetLine[] })?.lines ?? []
  const summary = summaryData as SummaryKPI | undefined

  const handleGenerateBudget = async () => {
    setBudgetSaved(false)
    try {
      const result = await budgetGenerate.mutateAsync({ year: budgetYear, growth_rate: growthRate / 100 })
      const lines = (result as { lines?: Record<string, unknown>[] })?.lines ?? []
      setBudgetProposal(lines)
    } catch {
      // Error handled by React Query
    }
  }

  const scostamentoColor = (pct: number) => {
    const abs = Math.abs(pct)
    if (abs <= 5) return 'text-green-600 bg-green-50'
    if (abs <= 15) return 'text-amber-600 bg-amber-50'
    return 'text-red-600 bg-red-50'
  }

  const months = [
    'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
    'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre',
  ]

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <PageHeader
        title="Controller"
        subtitle="Budget e andamento aziendale a colpo d'occhio"
      />

      {/* KPI Summary */}
      {summaryLoading ? (
        <LoadingSpinner className="py-8" />
      ) : summary ? (
        <div className="grid gap-4 sm:grid-cols-4">
          <Card>
            <p className="text-sm text-gray-500">Ricavi</p>
            <p className="text-2xl font-bold text-gray-900">{formatCurrency(summary.ricavi)}</p>
            {summary.trend === 'up' ? (
              <p className="mt-1 flex items-center gap-1 text-sm text-green-600">
                <TrendingUp className="h-4 w-4" /> In crescita
              </p>
            ) : summary.trend === 'down' ? (
              <p className="mt-1 flex items-center gap-1 text-sm text-red-600">
                <TrendingDown className="h-4 w-4" /> In calo
              </p>
            ) : null}
          </Card>
          <Card>
            <p className="text-sm text-gray-500">Costi</p>
            <p className="text-2xl font-bold text-gray-900">{formatCurrency(summary.costi)}</p>
          </Card>
          <Card>
            <p className="text-sm text-gray-500">Margine</p>
            <p className="text-2xl font-bold text-gray-900">{formatCurrency(summary.margine)}</p>
          </Card>
          <Card>
            <p className="text-sm text-gray-500">Margine %</p>
            <p className={`text-2xl font-bold ${summary.margine_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {summary.margine_pct.toFixed(1)}%
            </p>
          </Card>
        </div>
      ) : null}

      {/* Budget generation section */}
      <Card>
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Budget</h2>
        <p className="mb-4 text-sm text-gray-600">
          Genera una proposta di budget basata sui dati storici. Puoi modificarla prima di salvarla.
        </p>
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Anno</label>
            <select
              value={budgetYear}
              onChange={(e) => setBudgetYear(Number(e.target.value))}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {[currentYear, currentYear + 1].map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Crescita prevista</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={growthRate}
                onChange={(e) => setGrowthRate(Number(e.target.value))}
                min={-50}
                max={100}
                className="w-20 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-500">%</span>
            </div>
          </div>
          <button
            onClick={handleGenerateBudget}
            disabled={budgetGenerate.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            <Sparkles className="h-4 w-4" />
            {budgetGenerate.isPending ? 'Generazione...' : `Genera budget ${budgetYear}`}
          </button>
        </div>

        {budgetGenerate.error && (
          <p className="mt-3 text-sm text-red-600">
            Errore nella generazione del budget. Verifica di avere dati storici sufficienti.
          </p>
        )}

        {budgetSaved && (
          <div className="mt-4 flex items-center gap-2 rounded-lg bg-green-50 p-3 text-sm text-green-700">
            <CheckCircle2 className="h-4 w-4" /> Budget salvato correttamente.
          </div>
        )}

        {budgetProposal && budgetProposal.length > 0 && (
          <div className="mt-6">
            <h3 className="mb-2 font-medium text-gray-900">Proposta budget {budgetYear}</h3>
            <div className="overflow-x-auto rounded-lg border border-gray-200">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    {Object.keys(budgetProposal[0]).map((key) => (
                      <th key={key} className="px-3 py-2 text-left font-medium text-gray-600">
                        {key}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {budgetProposal.map((row, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      {Object.values(row).map((val, j) => (
                        <td key={j} className="px-3 py-2 text-gray-700">
                          {typeof val === 'number' ? formatCurrency(val) : String(val ?? '')}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-4 flex gap-3">
              <button
                onClick={() => {
                  setBudgetProposal(null)
                  setBudgetSaved(true)
                }}
                className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
              >
                Salva budget
              </button>
              <button
                onClick={() => setBudgetProposal(null)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Annulla
              </button>
            </div>
          </div>
        )}
      </Card>

      {/* Budget vs Actual section */}
      <Card>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-4">
          <h2 className="text-lg font-semibold text-gray-900">Come sta andando?</h2>
          <div className="flex gap-3">
            <select
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(Number(e.target.value))}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {months.map((m, i) => (
                <option key={i} value={i + 1}>{m}</option>
              ))}
            </select>
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(Number(e.target.value))}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {[currentYear - 1, currentYear, currentYear + 1].map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>
        </div>

        {vsActualLoading ? (
          <LoadingSpinner className="py-8" />
        ) : vsActual.length > 0 ? (
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2.5 text-left font-medium text-gray-600">Categoria</th>
                  <th className="px-4 py-2.5 text-right font-medium text-gray-600">Budget</th>
                  <th className="px-4 py-2.5 text-right font-medium text-gray-600">Consuntivo</th>
                  <th className="px-4 py-2.5 text-right font-medium text-gray-600">Scostamento</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {vsActual.map((line, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-2.5 font-medium text-gray-900">{line.category}</td>
                    <td className="px-4 py-2.5 text-right text-gray-700">{formatCurrency(line.budget)}</td>
                    <td className="px-4 py-2.5 text-right text-gray-700">{formatCurrency(line.actual)}</td>
                    <td className="px-4 py-2.5 text-right">
                      <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${scostamentoColor(line.scostamento_pct)}`}>
                        {line.scostamento_pct > 0 ? '+' : ''}{line.scostamento_pct.toFixed(1)}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={<BarChart3 className="h-12 w-12" />}
            title="Nessun dato disponibile"
            description="Genera un budget per iniziare a confrontare le previsioni con i risultati effettivi."
          />
        )}
      </Card>
    </div>
  )
}
