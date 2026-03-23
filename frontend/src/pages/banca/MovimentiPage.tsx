import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { useBankTransactions } from '../../api/hooks'
import { formatCurrency, formatDate } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import DataTable, { type Column } from '../../components/ui/DataTable'
import LoadingSpinner from '../../components/ui/LoadingSpinner'

type TxRow = Record<string, unknown>

export default function MovimentiPage() {
  const { accountId } = useParams<{ accountId: string }>()
  const navigate = useNavigate()
  const { data, isLoading } = useBankTransactions(accountId ?? '')

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const transactions = data?.items ?? []

  const columns: Column<TxRow>[] = [
    {
      key: 'date',
      header: 'Data',
      sortable: true,
      render: (row) => formatDate(row.date as string),
    },
    {
      key: 'description',
      header: 'Descrizione',
    },
    {
      key: 'amount',
      header: 'Importo',
      render: (row) => {
        const amount = row.amount as number
        return (
          <span className={amount >= 0 ? 'text-green-600' : 'text-red-600'}>
            {formatCurrency(amount)}
          </span>
        )
      },
      className: 'text-right',
    },
    {
      key: 'balance_after',
      header: 'Saldo',
      render: (row) => row.balance_after != null ? formatCurrency(row.balance_after as number) : '-',
      className: 'text-right',
    },
    {
      key: 'reconciled',
      header: 'Riconciliato',
      render: (row) => (
        <span className={`text-xs font-medium ${row.reconciled ? 'text-green-600' : 'text-gray-400'}`}>
          {row.reconciled ? 'Si' : 'No'}
        </span>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Movimenti bancari"
        subtitle={`Conto ${accountId?.slice(0, 8)}...`}
        actions={
          <button
            onClick={() => navigate('/banca')}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <ArrowLeft className="h-4 w-4" />
            Indietro
          </button>
        }
      />

      <DataTable<TxRow>
        columns={columns}
        data={transactions}
        rowKey={(row) => row.id as string}
        emptyMessage="Nessun movimento trovato"
      />
    </div>
  )
}
