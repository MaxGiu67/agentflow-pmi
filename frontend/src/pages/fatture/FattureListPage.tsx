import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Search, Filter } from 'lucide-react'
import { useInvoices } from '../../api/hooks'
import { formatCurrency, formatDate } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import DataTable, { type Column } from '../../components/ui/DataTable'
import StatusBadge from '../../components/ui/StatusBadge'
import DateRangeFilter from '../../components/ui/DateRangeFilter'
import LoadingSpinner from '../../components/ui/LoadingSpinner'

type InvoiceRow = Record<string, unknown>

export default function FattureListPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [sourceFilter, setSourceFilter] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [showFilters, setShowFilters] = useState(false)

  const { data, isLoading } = useInvoices({
    page,
    page_size: 20,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    type: typeFilter || undefined,
    status: statusFilter || undefined,
    source: sourceFilter || undefined,
    emittente: searchTerm || undefined,
  })

  const columns: Column<InvoiceRow>[] = [
    {
      key: 'date',
      header: 'Data',
      sortable: true,
      render: (row) => formatDate(row.date as string),
    },
    {
      key: 'number',
      header: 'Numero',
      render: (row) => (row.number as string) ?? '-',
    },
    {
      key: 'emittente',
      header: 'Emittente',
      sortable: true,
    },
    {
      key: 'type',
      header: 'Tipo',
      render: (row) => (row.type === 'passive' ? 'Passiva' : 'Attiva'),
    },
    {
      key: 'total_amount',
      header: 'Importo',
      sortable: true,
      render: (row) => formatCurrency(row.total_amount as number),
      className: 'text-right',
    },
    {
      key: 'source',
      header: 'Fonte',
      render: (row) => {
        const src = row.source as string
        return src === 'cassetto' ? 'Cassetto Fiscale' : src === 'email' ? 'Email' : src === 'manual' ? 'Manuale' : src
      },
    },
    {
      key: 'status',
      header: 'Stato',
      render: (row) => <StatusBadge status={row.status as string} />,
    },
  ]

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const invoices = data?.items ?? []
  const totalPages = data?.total_pages ?? 1

  return (
    <div>
      <PageHeader
        title="Fatture"
        subtitle="Gestione fatture attive e passive"
        actions={
          <div className="flex gap-2">
            <button
              onClick={() => navigate('/fatture/verifica')}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Da verificare
            </button>
            <button
              onClick={() => navigate('/fatture/upload')}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" />
              Carica
            </button>
          </div>
        }
      />

      {/* Search and filters */}
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Cerca per emittente..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value)
              setPage(1)
            }}
            className="w-full rounded-lg border border-gray-300 py-2 pl-9 pr-3 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
          />
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <Filter className="h-4 w-4" />
          Filtri
        </button>
      </div>

      {showFilters && (
        <div className="mb-4 flex flex-wrap gap-4 rounded-lg border border-gray-200 bg-white p-4">
          <DateRangeFilter
            dateFrom={dateFrom}
            dateTo={dateTo}
            onDateFromChange={(v) => { setDateFrom(v); setPage(1) }}
            onDateToChange={(v) => { setDateTo(v); setPage(1) }}
          />
          <div>
            <label className="block text-xs font-medium text-gray-500">Tipo</label>
            <select
              value={typeFilter}
              onChange={(e) => { setTypeFilter(e.target.value); setPage(1) }}
              className="mt-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="">Tutti</option>
              <option value="passive">Passiva</option>
              <option value="active">Attiva</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500">Stato</label>
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
              className="mt-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="">Tutti</option>
              <option value="verified">Verificata</option>
              <option value="pending_review">Da verificare</option>
              <option value="synced">Sincronizzata</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500">Fonte</label>
            <select
              value={sourceFilter}
              onChange={(e) => { setSourceFilter(e.target.value); setPage(1) }}
              className="mt-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="">Tutte</option>
              <option value="cassetto">Cassetto Fiscale</option>
              <option value="email">Email</option>
              <option value="manual">Manuale</option>
            </select>
          </div>
        </div>
      )}

      <DataTable<InvoiceRow>
        columns={columns}
        data={invoices}
        page={page}
        totalPages={totalPages}
        onPageChange={setPage}
        onRowClick={(row) => navigate(`/fatture/${row.id}`)}
        rowKey={(row) => row.id as string}
        emptyMessage="Nessuna fattura trovata"
      />
    </div>
  )
}
