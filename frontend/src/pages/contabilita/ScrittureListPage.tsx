import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useJournalEntries } from '../../api/hooks'
import { formatCurrency, formatDate } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import DataTable, { type Column } from '../../components/ui/DataTable'
import StatusBadge from '../../components/ui/StatusBadge'
import DateRangeFilter from '../../components/ui/DateRangeFilter'
import LoadingSpinner from '../../components/ui/LoadingSpinner'

type JournalRow = Record<string, unknown>

export default function ScrittureListPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const { data, isLoading } = useJournalEntries({
    page,
    page_size: 20,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  })

  const columns: Column<JournalRow>[] = [
    {
      key: 'entry_date',
      header: 'Data',
      sortable: true,
      render: (row) => formatDate(row.entry_date as string),
    },
    {
      key: 'description',
      header: 'Descrizione',
    },
    {
      key: 'total_debit',
      header: 'Dare',
      render: (row) => formatCurrency(row.total_debit as number),
      className: 'text-right',
    },
    {
      key: 'total_credit',
      header: 'Avere',
      render: (row) => formatCurrency(row.total_credit as number),
      className: 'text-right',
    },
    {
      key: 'status',
      header: 'Stato',
      render: (row) => <StatusBadge status={row.status as string} />,
    },
  ]

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const entries = data?.items ?? []
  const totalPages = data?.total_pages ?? 1

  return (
    <div>
      <PageHeader
        title="Scritture contabili"
        subtitle="Registrazioni in partita doppia"
        actions={
          <div className="flex gap-2">
            <button
              onClick={() => navigate('/contabilita/piano-conti')}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Piano dei Conti
            </button>
            <button
              onClick={() => navigate('/contabilita/bilancio')}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Bilancio CEE
            </button>
          </div>
        }
      />

      <div className="mb-4">
        <DateRangeFilter
          dateFrom={dateFrom}
          dateTo={dateTo}
          onDateFromChange={(v) => { setDateFrom(v); setPage(1) }}
          onDateToChange={(v) => { setDateTo(v); setPage(1) }}
        />
      </div>

      <DataTable<JournalRow>
        columns={columns}
        data={entries}
        page={page}
        totalPages={totalPages}
        onPageChange={setPage}
        onRowClick={(row) => navigate(`/contabilita/${row.id}`)}
        rowKey={(row) => row.id as string}
        emptyMessage="Nessuna scrittura contabile"
      />
    </div>
  )
}
