import { useNavigate } from 'react-router-dom'
import { FileText, AlertTriangle, CalendarClock, RefreshCw, MessageSquare } from 'lucide-react'
import { useDashboard, useAgentStatuses, useSyncCassetto } from '../api/hooks'
import { formatCurrency, formatDate } from '../lib/utils'
import PageHeader from '../components/ui/PageHeader'
import StatCard from '../components/ui/StatCard'
import StatusBadge from '../components/ui/StatusBadge'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import Card from '../components/ui/Card'

export default function DashboardPage() {
  const navigate = useNavigate()
  const { data: dashboard, isLoading, error } = useDashboard()
  const { data: agentsData } = useAgentStatuses()
  const syncCassetto = useSyncCassetto()

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  if (error) {
    return (
      <div className="mt-20 text-center">
        <AlertTriangle className="mx-auto mb-4 h-12 w-12 text-amber-500" />
        <p className="text-gray-600">Errore nel caricamento della dashboard</p>
      </div>
    )
  }

  const counters = dashboard?.counters ?? { total: 0, pending: 0, categorized: 0, registered: 0, error: 0 }
  const recentInvoices = dashboard?.recent_invoices ?? []
  const agents = agentsData?.agents ?? agentsData ?? []

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle="Panoramica della tua contabilita"
        actions={
          <div className="flex items-center gap-3">
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

      {/* Stat cards */}
      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Fatture totali"
          value={counters.total}
          icon={<FileText className="h-6 w-6" />}
        />
        <StatCard
          title="In attesa"
          value={counters.pending}
          icon={<AlertTriangle className="h-6 w-6" />}
          subtitle={counters.pending > 0 ? 'Da elaborare' : ''}
        />
        <StatCard
          title="Categorizzate"
          value={counters.categorized}
          icon={<FileText className="h-6 w-6" />}
        />
        <StatCard
          title="Registrate"
          value={counters.registered}
          icon={<CalendarClock className="h-6 w-6" />}
        />
      </div>

      {/* Recent invoices */}
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
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Data</th>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Numero</th>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Emittente</th>
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
                      {formatDate(inv.data_fattura as string)}
                    </td>
                    <td className="whitespace-nowrap px-4 py-2 text-sm text-gray-700">
                      {inv.numero_fattura as string}
                    </td>
                    <td className="px-4 py-2 text-sm text-gray-700">
                      {inv.emittente_nome as string}
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

      {/* Agent statuses */}
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
