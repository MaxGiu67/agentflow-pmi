import { Shield, CheckCircle, Clock, AlertTriangle } from 'lucide-react'
import { usePreservation } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import StatCard from '../../components/ui/StatCard'
import StatusBadge from '../../components/ui/StatusBadge'
import LoadingSpinner from '../../components/ui/LoadingSpinner'

export default function ConservazionePage() {
  const { data, isLoading } = usePreservation()

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const summary = data?.summary ?? { preserved: 0, pending: 0, failed: 0, total: 0 }
  const items = data?.items ?? []

  return (
    <div>
      <PageHeader
        title="Conservazione digitale"
        subtitle="Stato della conservazione a norma dei documenti"
      />

      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Totale documenti"
          value={summary.total}
          icon={<Shield className="h-6 w-6" />}
        />
        <StatCard
          title="Conservati"
          value={summary.preserved}
          icon={<CheckCircle className="h-6 w-6 text-green-500" />}
        />
        <StatCard
          title="In attesa"
          value={summary.pending}
          icon={<Clock className="h-6 w-6 text-amber-500" />}
        />
        <StatCard
          title="Errori"
          value={summary.failed}
          icon={<AlertTriangle className="h-6 w-6 text-red-500" />}
        />
      </div>

      <Card>
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Documenti</h2>
        {items.length === 0 ? (
          <p className="py-8 text-center text-sm text-gray-500">Nessun documento in conservazione</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Documento</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Tipo</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Provider</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Stato</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {items.map((item: Record<string, unknown>, idx: number) => (
                  <tr key={idx}>
                    <td className="px-4 py-3 text-sm text-gray-700">{item.document_ref as string}</td>
                    <td className="px-4 py-3 text-sm text-gray-700">{item.document_type as string}</td>
                    <td className="px-4 py-3 text-sm text-gray-700">{item.provider as string}</td>
                    <td className="px-4 py-3"><StatusBadge status={item.status as string} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
