import { useWithholdingTaxes } from '../../api/hooks'
import { formatCurrency, formatDate } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import DataTable, { type Column } from '../../components/ui/DataTable'
import StatusBadge from '../../components/ui/StatusBadge'
import LoadingSpinner from '../../components/ui/LoadingSpinner'

type WithholdingRow = Record<string, unknown>

export default function RitenutePage() {
  const { data, isLoading } = useWithholdingTaxes()

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const items = data?.items ?? []

  const columns: Column<WithholdingRow>[] = [
    {
      key: 'supplier_name',
      header: 'Fornitore',
    },
    {
      key: 'invoice_date',
      header: 'Data fattura',
      render: (row) => row.invoice_date ? formatDate(row.invoice_date as string) : '-',
    },
    {
      key: 'gross_amount',
      header: 'Lordo',
      render: (row) => formatCurrency(row.gross_amount as number),
      className: 'text-right',
    },
    {
      key: 'withholding_amount',
      header: 'Ritenuta',
      render: (row) => formatCurrency(row.withholding_amount as number),
      className: 'text-right',
    },
    {
      key: 'net_amount',
      header: 'Netto',
      render: (row) => formatCurrency(row.net_amount as number),
      className: 'text-right',
    },
    {
      key: 'rate',
      header: 'Aliquota',
      render: (row) => `${row.rate as number}%`,
    },
    {
      key: 'f24_deadline',
      header: 'Scadenza F24',
      render: (row) => row.f24_deadline ? formatDate(row.f24_deadline as string) : '-',
    },
    {
      key: 'status',
      header: 'Stato',
      render: (row) => <StatusBadge status={row.status as string} />,
    },
  ]

  return (
    <div>
      <PageHeader
        title="Ritenute d'acconto"
        subtitle="Gestione ritenute operate sui pagamenti ai professionisti"
      />

      <DataTable<WithholdingRow>
        columns={columns}
        data={items}
        rowKey={(row) => row.id as string}
        emptyMessage="Nessuna ritenuta trovata"
      />
    </div>
  )
}
