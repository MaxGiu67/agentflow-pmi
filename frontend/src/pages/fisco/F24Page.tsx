import { useState } from 'react'
import { Download, Plus, FileText } from 'lucide-react'
import { useF24s, useF24, useGenerateF24 } from '../../api/hooks'
import { formatCurrency, formatDate } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import StatusBadge from '../../components/ui/StatusBadge'
import DataTable, { type Column } from '../../components/ui/DataTable'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import api from '../../api/client'

type F24Row = Record<string, unknown>

export default function F24Page() {
  const currentYear = new Date().getFullYear()
  const [year, setYear] = useState(currentYear)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [showGenerate, setShowGenerate] = useState(false)
  const [genYear, setGenYear] = useState(currentYear)
  const [genMonth, setGenMonth] = useState(new Date().getMonth() + 1)

  const { data, isLoading } = useF24s(year)
  const { data: detail } = useF24(selectedId ?? '')
  const generateF24 = useGenerateF24()

  const handleGenerate = () => {
    generateF24.mutate({ year: genYear, month: genMonth })
    setShowGenerate(false)
  }

  const handleExport = async (f24Id: string, format: string) => {
    const { data: exportData } = await api.get(`/f24/${f24Id}/export`, { params: { format } })
    if (exportData.download_url) {
      window.open(exportData.download_url, '_blank')
    }
  }

  const columns: Column<F24Row>[] = [
    {
      key: 'period',
      header: 'Periodo',
      render: (row) => `${row.month ?? row.quarter ?? '-'}/${row.year}`,
    },
    {
      key: 'total_amount',
      header: 'Importo',
      render: (row) => formatCurrency(row.total_amount as number),
      className: 'text-right',
    },
    {
      key: 'deadline',
      header: 'Scadenza',
      render: (row) => row.deadline ? formatDate(row.deadline as string) : '-',
    },
    {
      key: 'status',
      header: 'Stato',
      render: (row) => <StatusBadge status={row.status as string} />,
    },
    {
      key: 'actions',
      header: '',
      render: (row) => (
        <div className="flex gap-2">
          <button
            onClick={(e) => { e.stopPropagation(); handleExport(row.id as string, 'pdf') }}
            className="text-blue-600 hover:underline text-xs"
          >
            PDF
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); handleExport(row.id as string, 'telematico') }}
            className="text-blue-600 hover:underline text-xs"
          >
            Telematico
          </button>
        </div>
      ),
    },
  ]

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const items = data?.items ?? []

  return (
    <div>
      <PageHeader
        title="Modelli F24"
        subtitle="Compilazione e gestione F24"
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
            <button
              onClick={() => setShowGenerate(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" />
              Genera F24
            </button>
          </div>
        }
      />

      {showGenerate && (
        <Card className="mb-6">
          <h3 className="mb-4 text-lg font-semibold">Genera nuovo F24</h3>
          <div className="flex flex-wrap gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500">Anno</label>
              <input
                type="number"
                value={genYear}
                onChange={(e) => setGenYear(Number(e.target.value))}
                className="mt-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500">Mese</label>
              <select
                value={genMonth}
                onChange={(e) => setGenMonth(Number(e.target.value))}
                className="mt-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
              >
                {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
            </div>
            <div className="flex items-end gap-2">
              <button onClick={handleGenerate} disabled={generateF24.isPending} className="rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                {generateF24.isPending ? 'Generazione...' : 'Genera'}
              </button>
              <button onClick={() => setShowGenerate(false)} className="rounded-lg border border-gray-300 px-4 py-1.5 text-sm text-gray-700 hover:bg-gray-50">
                Annulla
              </button>
            </div>
          </div>
        </Card>
      )}

      <div className={selectedId ? 'grid gap-6 lg:grid-cols-2' : ''}>
        <DataTable<F24Row>
          columns={columns}
          data={items}
          onRowClick={(row) => setSelectedId(row.id as string)}
          rowKey={(row) => row.id as string}
          emptyMessage="Nessun F24 trovato"
        />

        {selectedId && detail && (
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Dettaglio F24</h2>
              <div className="flex gap-2">
                <button
                  onClick={() => handleExport(selectedId, 'pdf')}
                  className="inline-flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
                >
                  <Download className="h-3 w-3" /> PDF
                </button>
                <button
                  onClick={() => handleExport(selectedId, 'telematico')}
                  className="inline-flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
                >
                  <FileText className="h-3 w-3" /> Telematico
                </button>
              </div>
            </div>

            <h3 className="mb-2 text-sm font-medium text-gray-700">Sezioni</h3>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Codice</th>
                    <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Descrizione</th>
                    <th className="px-3 py-2 text-right text-xs font-medium uppercase text-gray-500">Importo</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {(detail.sections ?? []).map((sec: Record<string, unknown>, idx: number) => (
                    <tr key={idx}>
                      <td className="px-3 py-2 text-sm font-mono text-gray-700">{sec.codice_tributo as string}</td>
                      <td className="px-3 py-2 text-sm text-gray-700">{sec.description as string}</td>
                      <td className="px-3 py-2 text-right text-sm font-medium text-gray-900">
                        {formatCurrency(sec.amount as number)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </div>
    </div>
  )
}
