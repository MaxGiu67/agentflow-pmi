import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  FileText,
  AlertTriangle,
  TrendingUp,
  Receipt,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  MessageSquare,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { useDashboard, useAgentStatuses, useYearlyStats, useSyncCassetto } from '../api/hooks'
import { formatCurrency } from '../lib/utils'
import PageHeader from '../components/ui/PageHeader'
import Card from '../components/ui/Card'
import StatusBadge from '../components/ui/StatusBadge'
import LoadingSpinner from '../components/ui/LoadingSpinner'

const MONTH_LABELS = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu', 'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic']

interface MonthlyRow {
  mese: number
  label: string
  attive_totale: number
  passive_totale: number
}

interface TopEntityRow {
  nome: string
  piva: string
  totale: number
  count: number
}

function formatTooltipValue(value: unknown): string {
  return formatCurrency(Number(value ?? 0))
}

function formatTooltipLabel(label: unknown): string {
  return `Mese: ${String(label ?? '')}`
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const currentYear = new Date().getFullYear()
  const [selectedYear, setSelectedYear] = useState(currentYear)

  const { data: yearlyData, isLoading: yearlyLoading, error: yearlyError } = useYearlyStats(selectedYear)
  const { data: dashboard, isLoading: dashLoading } = useDashboard()
  const { data: agentsData } = useAgentStatuses()
  const syncCassetto = useSyncCassetto()

  const isLoading = yearlyLoading || dashLoading

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  if (yearlyError) {
    return (
      <div className="mt-20 text-center">
        <AlertTriangle className="mx-auto mb-4 h-12 w-12 text-amber-500" />
        <p className="text-gray-600">Errore nel caricamento della dashboard</p>
      </div>
    )
  }

  const fattureAttive = yearlyData?.fatture_attive ?? { count: 0, totale: 0, imponibile: 0, iva: 0 }
  const fatturePassive = yearlyData?.fatture_passive ?? { count: 0, totale: 0, imponibile: 0, iva: 0 }
  const margineLordo = yearlyData?.margine_lordo ?? 0
  const ivaNetta = (fattureAttive.iva ?? 0) - (fatturePassive.iva ?? 0)
  const topClienti: TopEntityRow[] = yearlyData?.top_clienti ?? []
  const topFornitori: TopEntityRow[] = yearlyData?.top_fornitori ?? []
  const availableYears: number[] = yearlyData?.available_years ?? []

  // Prepare monthly chart data
  const fatturePerMese: MonthlyRow[] = (yearlyData?.fatture_per_mese ?? []).map(
    (m: { mese: number; attive_totale: number; passive_totale: number }) => ({
      ...m,
      label: MONTH_LABELS[m.mese - 1] ?? '',
    })
  )

  // Recent invoices from the summary endpoint (limit 5)
  const recentInvoices = (dashboard?.recent_invoices ?? []).slice(0, 5)
  const agents = agentsData?.agents ?? agentsData ?? []

  // Year navigation
  const yearOptions = availableYears.length > 0 ? availableYears : [currentYear]
  const canGoBack = selectedYear > (yearOptions[0] ?? currentYear - 5)
  const canGoForward = selectedYear < currentYear

  return (
    <div>
      {/* Header */}
      <PageHeader
        title={`Dashboard ${selectedYear}`}
        subtitle="Panoramica annuale fatturazione"
        actions={
          <div className="flex items-center gap-3">
            {/* Year navigation */}
            <div className="flex items-center gap-1 rounded-lg border border-gray-300 px-1 py-1">
              <button
                onClick={() => setSelectedYear((y) => y - 1)}
                disabled={!canGoBack}
                className="rounded p-1 hover:bg-gray-100 disabled:opacity-30"
                aria-label="Anno precedente"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <select
                value={selectedYear}
                onChange={(e) => setSelectedYear(Number(e.target.value))}
                className="appearance-none border-none bg-transparent px-2 py-0.5 text-sm font-medium text-gray-700 focus:outline-none"
              >
                {Array.from(
                  new Set([...yearOptions, currentYear, selectedYear])
                )
                  .sort((a, b) => b - a)
                  .map((y) => (
                    <option key={y} value={y}>
                      {y}
                    </option>
                  ))}
              </select>
              <button
                onClick={() => setSelectedYear((y) => y + 1)}
                disabled={!canGoForward}
                className="rounded p-1 hover:bg-gray-100 disabled:opacity-30"
                aria-label="Anno successivo"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>

            <button
              onClick={() => navigate('/chat')}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              <MessageSquare className="h-4 w-4" />
              Apri Chat
            </button>
            <button
              onClick={() => syncCassetto.mutate({})}
              disabled={syncCassetto.isPending}
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${syncCassetto.isPending ? 'animate-spin' : ''}`} />
              Sincronizza
            </button>
          </div>
        }
      />

      {/* Row 1: Stat cards */}
      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Fatture Emesse */}
        <Card className="flex items-start gap-4 border-l-4 border-l-green-500">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-green-50 text-green-600">
            <FileText className="h-6 w-6" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-gray-500">Fatture Emesse</p>
            <p className="mt-1 text-2xl font-semibold text-gray-900">{fattureAttive.count}</p>
            <p className="mt-0.5 text-sm text-green-600">{formatCurrency(fattureAttive.totale)}</p>
          </div>
        </Card>

        {/* Fatture Ricevute */}
        <Card className="flex items-start gap-4 border-l-4 border-l-orange-500">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-orange-50 text-orange-600">
            <Receipt className="h-6 w-6" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-gray-500">Fatture Ricevute</p>
            <p className="mt-1 text-2xl font-semibold text-gray-900">{fatturePassive.count}</p>
            <p className="mt-0.5 text-sm text-orange-600">{formatCurrency(fatturePassive.totale)}</p>
          </div>
        </Card>

        {/* Margine Lordo */}
        <Card className="flex items-start gap-4 border-l-4 border-l-blue-500">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
            <TrendingUp className="h-6 w-6" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-gray-500">Margine Lordo</p>
            <p className="mt-1 text-2xl font-semibold text-gray-900">{formatCurrency(margineLordo)}</p>
          </div>
        </Card>

        {/* IVA Netta */}
        <Card className="flex items-start gap-4 border-l-4 border-l-gray-400">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-gray-100 text-gray-600">
            <Receipt className="h-6 w-6" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-gray-500">IVA Netta</p>
            <p className="mt-1 text-2xl font-semibold text-gray-900">{formatCurrency(ivaNetta)}</p>
            <p className="mt-0.5 text-xs text-gray-400">debito - credito</p>
          </div>
        </Card>
      </div>

      {/* Row 2: Monthly chart */}
      <Card className="mb-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Fatturazione Mensile {selectedYear}</h2>
        {fatturePerMese.length > 0 ? (
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={fatturePerMese} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="label" />
              <YAxis
                tickFormatter={(v: number) =>
                  v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)
                }
              />
              <Tooltip
                formatter={formatTooltipValue}
                labelFormatter={formatTooltipLabel}
              />
              <Legend />
              <Bar dataKey="attive_totale" name="Emesse" fill="#22c55e" radius={[4, 4, 0, 0]} />
              <Bar dataKey="passive_totale" name="Ricevute" fill="#f97316" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="py-12 text-center text-sm text-gray-500">Nessun dato disponibile per {selectedYear}</p>
        )}
      </Card>

      {/* Row 3: Top clienti + Top fornitori */}
      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        {/* Top 10 Clienti */}
        <Card>
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Top 10 Clienti</h2>
          {topClienti.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead>
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Cliente</th>
                    <th className="px-3 py-2 text-right text-xs font-medium uppercase text-gray-500">Fatture</th>
                    <th className="px-3 py-2 text-right text-xs font-medium uppercase text-gray-500">Totale</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {topClienti.map((c, i) => (
                    <tr key={`${c.piva}-${i}`}>
                      <td className="px-3 py-2 text-sm text-gray-700">
                        <div className="font-medium">{c.nome}</div>
                        {c.piva && <div className="text-xs text-gray-400">{c.piva}</div>}
                      </td>
                      <td className="px-3 py-2 text-right text-sm text-gray-600">{c.count}</td>
                      <td className="px-3 py-2 text-right text-sm font-medium text-gray-900">
                        {formatCurrency(c.totale)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="py-8 text-center text-sm text-gray-500">Nessun cliente per {selectedYear}</p>
          )}
        </Card>

        {/* Top 10 Fornitori */}
        <Card>
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Top 10 Fornitori</h2>
          {topFornitori.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead>
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Fornitore</th>
                    <th className="px-3 py-2 text-right text-xs font-medium uppercase text-gray-500">Fatture</th>
                    <th className="px-3 py-2 text-right text-xs font-medium uppercase text-gray-500">Totale</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {topFornitori.map((f, i) => (
                    <tr key={`${f.piva}-${i}`}>
                      <td className="px-3 py-2 text-sm text-gray-700">
                        <div className="font-medium">{f.nome}</div>
                        {f.piva && <div className="text-xs text-gray-400">{f.piva}</div>}
                      </td>
                      <td className="px-3 py-2 text-right text-sm text-gray-600">{f.count}</td>
                      <td className="px-3 py-2 text-right text-sm font-medium text-gray-900">
                        {formatCurrency(f.totale)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="py-8 text-center text-sm text-gray-500">Nessun fornitore per {selectedYear}</p>
          )}
        </Card>
      </div>

      {/* Row 4: Recent invoices (limit 5) */}
      <Card className="mb-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Fatture recenti</h2>
          <button
            onClick={() => navigate('/fatture')}
            className="text-sm text-blue-600 hover:underline"
          >
            Vedi tutte
          </button>
        </div>
        {recentInvoices.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Numero</th>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Emittente</th>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Tipo</th>
                  <th className="px-4 py-2 text-right text-xs font-medium uppercase text-gray-500">Importo</th>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Stato</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {recentInvoices.map((inv: Record<string, unknown>) => (
                  <tr
                    key={inv.id as string}
                    className="cursor-pointer hover:bg-gray-50"
                    onClick={() => navigate(`/fatture/${inv.id}`)}
                  >
                    <td className="whitespace-nowrap px-4 py-2 text-sm text-gray-700">
                      {inv.numero_fattura as string}
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-700">{inv.emittente_nome as string}</td>
                    <td className="px-4 py-2 text-sm text-gray-500">
                      {(inv.type as string) === 'attiva' ? 'Emessa' : 'Ricevuta'}
                    </td>
                    <td className="whitespace-nowrap px-4 py-2 text-right text-sm font-medium text-gray-900">
                      {formatCurrency(inv.importo_totale as number)}
                    </td>
                    <td className="px-4 py-2">
                      <StatusBadge status={inv.processing_status as string} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="py-8 text-center text-sm text-gray-500">Nessuna fattura recente</p>
        )}
      </Card>

      {/* Row 5: Agent statuses */}
      {Array.isArray(agents) && agents.length > 0 && (
        <Card>
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Stato Agenti</h2>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {agents.map((agent: Record<string, unknown>) => (
              <div
                key={agent.name as string}
                className="flex items-center justify-between rounded-lg border border-gray-200 p-3"
              >
                <span className="text-sm font-medium text-gray-700">{agent.name as string}</span>
                <StatusBadge status={agent.status as string} />
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}
