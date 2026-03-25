import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Search, Filter } from 'lucide-react'
import { useInvoices } from '../../api/hooks'
import { formatCurrency, formatDate } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import StatusBadge from '../../components/ui/StatusBadge'
import DateRangeFilter from '../../components/ui/DateRangeFilter'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'

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

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const invoices = data?.items ?? []
  const totalPages = data?.pages ?? data?.total_pages ?? 1
  const total = data?.total ?? 0

  return (
    <div>
      <PageHeader
        title="Fatture"
        subtitle={`Gestione fatture attive e passive — ${total} totali`}
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
            onChange={(e) => { setSearchTerm(e.target.value); setPage(1) }}
            className="w-full rounded-lg border border-gray-300 py-2 pl-9 pr-3 text-sm focus:border-blue-500 focus:outline-none"
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
              <option value="passiva">Passiva</option>
              <option value="attiva">Attiva</option>
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
              <option value="pending">In attesa</option>
              <option value="parsed">Elaborata</option>
              <option value="categorized">Categorizzata</option>
              <option value="registered">Registrata</option>
              <option value="error">Errore</option>
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
              <option value="cassetto_fiscale">Cassetto Fiscale</option>
              <option value="upload">Upload</option>
              <option value="sdi_realtime">SDI</option>
              <option value="email">Email</option>
            </select>
          </div>
        </div>
      )}

      {invoices.length === 0 ? (
        <EmptyState
          title="Nessuna fattura trovata"
          description="Carica le tue fatture o collega il cassetto fiscale per importarle automaticamente."
        />
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Data</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Numero</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Controparte</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Tipo</th>
                  <th className="px-4 py-3 text-right text-xs font-medium uppercase text-gray-500">Importo</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Fonte</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Stato</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {invoices.map((inv: Record<string, unknown>) => {
                  // Get the counterpart name (for emesse: destinatario from structured_data, for ricevute: emittente)
                  const structuredData = inv.structured_data as Record<string, unknown> | null
                  // Per fatture EMESSE (attiva): mostra il CLIENTE (destinatario)
                  // Per fatture RICEVUTE (passiva): mostra il FORNITORE (emittente)
                  const destinatario = (structuredData?.destinatario_nome ?? structuredData?.cessionario_nome) as string | undefined
                  const displayName = inv.type === 'attiva'
                    ? (destinatario || '-')
                    : (inv.emittente_nome as string || '-')

                  return (
                    <tr
                      key={inv.id as string}
                      className="cursor-pointer hover:bg-gray-50"
                      onClick={() => navigate(`/fatture/${inv.id}`)}
                    >
                      <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                        {inv.data_fattura ? formatDate(inv.data_fattura as string) : '-'}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
                        {inv.numero_fattura as string || '-'}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        <div>
                          <p className="font-medium">{displayName}</p>
                          <p className="text-xs text-gray-400">
                            {inv.type === 'attiva' ? 'Cliente' : 'Fornitore'}
                          </p>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                          inv.type === 'attiva' ? 'bg-green-100 text-green-800' : 'bg-orange-100 text-orange-800'
                        }`}>
                          {inv.type === 'attiva' ? '↑ Emessa' : '↓ Ricevuta'}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-right text-sm font-medium text-gray-900">
                        {inv.importo_totale != null ? formatCurrency(inv.importo_totale as number) : '-'}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-500">
                        {inv.source as string || '-'}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={inv.processing_status as string} />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-between">
              <p className="text-sm text-gray-500">
                Pagina {page} di {totalPages} — {total} fatture
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page <= 1}
                  className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm disabled:opacity-50"
                >
                  Precedente
                </button>
                <button
                  onClick={() => setPage(Math.min(totalPages, page + 1))}
                  disabled={page >= totalPages}
                  className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm disabled:opacity-50"
                >
                  Successiva
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
