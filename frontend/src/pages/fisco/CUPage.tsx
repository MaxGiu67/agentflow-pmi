import { useState } from 'react'
import { FileText, Download } from 'lucide-react'
import { useCUs, useGenerateCU } from '../../api/hooks'
import { formatCurrency } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import DataTable, { type Column } from '../../components/ui/DataTable'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import api from '../../api/client'

type CURow = Record<string, unknown>

export default function CUPage() {
  const currentYear = new Date().getFullYear()
  const [year, setYear] = useState(currentYear - 1)
  const { data, isLoading } = useCUs(year)
  const generateCU = useGenerateCU()

  const handleExport = async (cuId: string, format: string) => {
    const { data: exportData } = await api.get(`/cu/${cuId}/export`, { params: { format } })
    if (exportData.download_url) {
      window.open(exportData.download_url, '_blank')
    }
  }

  const columns: Column<CURow>[] = [
    { key: 'supplier_name', header: 'Percipiente' },
    { key: 'codice_fiscale', header: 'Codice Fiscale' },
    {
      key: 'gross_amount',
      header: 'Compenso lordo',
      render: (row) => formatCurrency(row.gross_amount as number),
      className: 'text-right',
    },
    {
      key: 'withholding_total',
      header: 'Ritenute',
      render: (row) => formatCurrency(row.withholding_total as number),
      className: 'text-right',
    },
    {
      key: 'net_amount',
      header: 'Netto',
      render: (row) => formatCurrency(row.net_amount as number),
      className: 'text-right',
    },
    {
      key: 'actions',
      header: '',
      render: (row) => (
        <div className="flex gap-2">
          <button
            onClick={(e) => { e.stopPropagation(); handleExport(row.id as string, 'csv') }}
            className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
          >
            <Download className="h-3 w-3" /> CSV
          </button>
          <button
            onClick={(e) => { e.stopPropagation(); handleExport(row.id as string, 'telematico') }}
            className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
          >
            <FileText className="h-3 w-3" /> Telematico
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
        title="Certificazione Unica"
        subtitle="Generazione CU per professionisti"
        actions={
          <div className="flex gap-2">
            <select
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              {Array.from({ length: 3 }, (_, i) => currentYear - 1 - i).map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
            <button
              onClick={() => generateCU.mutate(year)}
              disabled={generateCU.isPending}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {generateCU.isPending ? 'Generazione...' : 'Genera CU'}
            </button>
          </div>
        }
      />

      <DataTable<CURow>
        columns={columns}
        data={items}
        rowKey={(row) => row.id as string}
        emptyMessage="Nessuna CU trovata per l'anno selezionato"
      />
    </div>
  )
}
