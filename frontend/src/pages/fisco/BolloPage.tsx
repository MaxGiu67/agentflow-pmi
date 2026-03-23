import { useState } from 'react'
import { Stamp } from 'lucide-react'
import { useStampDuties } from '../../api/hooks'
import { formatCurrency, formatDate } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'

export default function BolloPage() {
  const currentYear = new Date().getFullYear()
  const currentQuarter = Math.ceil((new Date().getMonth() + 1) / 3)
  const [year, setYear] = useState(currentYear)
  const [quarter, setQuarter] = useState(currentQuarter)

  const { data, isLoading, error } = useStampDuties(year, quarter)

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  return (
    <div>
      <PageHeader
        title="Imposta di Bollo"
        subtitle="Riepilogo trimestrale bollo su fatture esenti"
        actions={
          <div className="flex gap-2">
            <select
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              {Array.from({ length: 3 }, (_, i) => currentYear - i).map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
            <select
              value={quarter}
              onChange={(e) => setQuarter(Number(e.target.value))}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              {[1, 2, 3, 4].map((q) => (
                <option key={q} value={q}>Q{q}</option>
              ))}
            </select>
          </div>
        }
      />

      {error ? (
        <EmptyState
          title="Nessun dato disponibile"
          description={`Non ci sono dati per Q${quarter} ${year}`}
          icon={<Stamp className="h-12 w-12" />}
        />
      ) : data ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <h2 className="mb-4 text-lg font-semibold text-gray-900">
              Riepilogo Q{quarter} {year}
            </h2>
            <dl className="space-y-3">
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Fatture con bollo</dt>
                <dd className="text-sm font-medium text-gray-900">{data.invoice_count ?? 0}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Importo unitario</dt>
                <dd className="text-sm font-medium text-gray-900">{formatCurrency(2)}</dd>
              </div>
              <div className="flex justify-between border-t border-gray-200 pt-3">
                <dt className="text-sm font-bold text-gray-900">Totale bollo</dt>
                <dd className="text-lg font-bold text-gray-900">
                  {formatCurrency(data.total_amount ?? 0)}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Scadenza versamento</dt>
                <dd className="text-sm font-medium text-gray-900">
                  {data.deadline ? formatDate(data.deadline) : '-'}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Codice tributo F24</dt>
                <dd className="text-sm font-mono font-medium text-gray-900">{data.codice_tributo ?? '2501'}</dd>
              </div>
            </dl>
          </Card>
        </div>
      ) : null}
    </div>
  )
}
