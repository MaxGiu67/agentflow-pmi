import { Package } from 'lucide-react'
import { useAssets } from '../../api/hooks'
import { formatCurrency, formatDate } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import DataTable, { type Column } from '../../components/ui/DataTable'
import StatusBadge from '../../components/ui/StatusBadge'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'

type AssetRow = Record<string, unknown>

export default function CespitiPage() {
  const { data, isLoading } = useAssets()

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const assets = data?.items ?? []

  if (assets.length === 0) {
    return (
      <div>
        <PageHeader title="Cespiti" subtitle="Registro cespiti ammortizzabili" />
        <EmptyState
          title="Nessun cespite registrato"
          description="I cespiti vengono creati automaticamente dalle fatture con importo sopra soglia."
          icon={<Package className="h-12 w-12" />}
        />
      </div>
    )
  }

  const columns: Column<AssetRow>[] = [
    { key: 'description', header: 'Descrizione', sortable: true },
    { key: 'category', header: 'Categoria' },
    {
      key: 'purchase_date',
      header: 'Data acquisto',
      render: (row) => formatDate(row.purchase_date as string),
    },
    {
      key: 'purchase_amount',
      header: 'Costo',
      render: (row) => formatCurrency(row.purchase_amount as number),
      className: 'text-right',
    },
    {
      key: 'depreciation_rate',
      header: 'Aliquota',
      render: (row) => `${row.depreciation_rate as number}%`,
    },
    {
      key: 'accumulated_depreciation',
      header: 'Fondo ammort.',
      render: (row) => formatCurrency(row.accumulated_depreciation as number),
      className: 'text-right',
    },
    {
      key: 'residual_value',
      header: 'Valore residuo',
      render: (row) => formatCurrency(row.residual_value as number),
      className: 'text-right',
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
        title="Cespiti"
        subtitle="Registro cespiti ammortizzabili"
      />

      <DataTable<AssetRow>
        columns={columns}
        data={assets}
        rowKey={(row) => row.id as string}
        emptyMessage="Nessun cespite"
      />
    </div>
  )
}
