import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { useJournalEntry } from '../../api/hooks'
import { formatCurrency, formatDate } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import StatusBadge from '../../components/ui/StatusBadge'
import LoadingSpinner from '../../components/ui/LoadingSpinner'

export default function ScritturaDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: entry, isLoading, error } = useJournalEntry(id ?? '')

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  if (error || !entry) {
    return (
      <div className="mt-20 text-center">
        <p className="text-gray-600">Scrittura non trovata</p>
        <button onClick={() => navigate('/contabilita')} className="mt-4 text-blue-600 hover:underline">
          Torna alle scritture
        </button>
      </div>
    )
  }

  const lines = entry.lines ?? []

  return (
    <div>
      <PageHeader
        title="Dettaglio Scrittura"
        subtitle={entry.description}
        actions={
          <button
            onClick={() => navigate('/contabilita')}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <ArrowLeft className="h-4 w-4" />
            Indietro
          </button>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <h3 className="mb-3 text-sm font-medium text-gray-500">Data</h3>
          <p className="text-lg font-semibold text-gray-900">{formatDate(entry.entry_date)}</p>
        </Card>
        <Card>
          <h3 className="mb-3 text-sm font-medium text-gray-500">Stato</h3>
          <StatusBadge status={entry.status} />
        </Card>
        <Card>
          <h3 className="mb-3 text-sm font-medium text-gray-500">Totale</h3>
          <p className="text-lg font-semibold text-gray-900">
            Dare: {formatCurrency(entry.total_debit)} / Avere: {formatCurrency(entry.total_credit)}
          </p>
        </Card>
      </div>

      {/* Journal lines */}
      <Card className="mt-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Righe contabili</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Conto</th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Descrizione</th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase text-gray-500">Dare</th>
                <th className="px-4 py-3 text-right text-xs font-medium uppercase text-gray-500">Avere</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {lines.map((line: Record<string, unknown>, idx: number) => (
                <tr key={idx}>
                  <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
                    {line.account_code as string}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    {line.account_name as string}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-700">
                    {(line.debit as number) > 0 ? formatCurrency(line.debit as number) : '-'}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm text-gray-700">
                    {(line.credit as number) > 0 ? formatCurrency(line.credit as number) : '-'}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-gray-50">
              <tr>
                <td colSpan={2} className="px-4 py-3 text-sm font-semibold text-gray-900">
                  Totale
                </td>
                <td className="px-4 py-3 text-right text-sm font-semibold text-gray-900">
                  {formatCurrency(entry.total_debit)}
                </td>
                <td className="px-4 py-3 text-right text-sm font-semibold text-gray-900">
                  {formatCurrency(entry.total_credit)}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>

        {entry.error_message && (
          <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
            Errore: {entry.error_message}
          </div>
        )}
      </Card>
    </div>
  )
}
