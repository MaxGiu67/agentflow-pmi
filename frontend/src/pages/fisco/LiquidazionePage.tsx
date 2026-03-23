import { useState } from 'react'
import { Calculator } from 'lucide-react'
import { useVatSettlement, useComputeVatSettlement } from '../../api/hooks'
import { formatCurrency } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'

export default function LiquidazionePage() {
  const currentYear = new Date().getFullYear()
  const currentQuarter = Math.ceil((new Date().getMonth() + 1) / 3)
  const [year, setYear] = useState(currentYear)
  const [quarter, setQuarter] = useState(currentQuarter)

  const { data, isLoading, error } = useVatSettlement(year, quarter)
  const computeMutation = useComputeVatSettlement()

  const handleCompute = () => {
    computeMutation.mutate({ year, quarter })
  }

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  return (
    <div>
      <PageHeader
        title="Liquidazione IVA"
        subtitle="Calcolo IVA trimestrale"
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
            <button
              onClick={handleCompute}
              disabled={computeMutation.isPending}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              <Calculator className="h-4 w-4" />
              {computeMutation.isPending ? 'Calcolo...' : 'Calcola'}
            </button>
          </div>
        }
      />

      {error && !data ? (
        <EmptyState
          title={`Liquidazione IVA Q${quarter} ${year} non ancora calcolata`}
          description="Clicca su 'Calcola' per generare la liquidazione IVA."
          icon={<Calculator className="h-12 w-12" />}
        />
      ) : data ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <h2 className="mb-4 text-lg font-semibold text-gray-900">Riepilogo Q{quarter} {year}</h2>
            <dl className="space-y-3">
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">IVA a debito (vendite)</dt>
                <dd className="text-sm font-medium text-gray-900">{formatCurrency(data.iva_debito ?? 0)}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">IVA a credito (acquisti)</dt>
                <dd className="text-sm font-medium text-gray-900">{formatCurrency(data.iva_credito ?? 0)}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Credito periodo precedente</dt>
                <dd className="text-sm font-medium text-gray-900">{formatCurrency(data.credito_precedente ?? 0)}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Interessi (1% trim.)</dt>
                <dd className="text-sm font-medium text-gray-900">{formatCurrency(data.interessi ?? 0)}</dd>
              </div>
              <div className="flex justify-between border-t border-gray-200 pt-3">
                <dt className="text-sm font-bold text-gray-900">
                  {(data.saldo ?? 0) >= 0 ? 'IVA da versare' : 'Credito IVA'}
                </dt>
                <dd className={`text-lg font-bold ${(data.saldo ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                  {formatCurrency(Math.abs(data.saldo ?? 0))}
                </dd>
              </div>
            </dl>
          </Card>

          <Card>
            <h2 className="mb-4 text-lg font-semibold text-gray-900">Dettaglio operazioni</h2>
            <dl className="space-y-3">
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Fatture attive</dt>
                <dd className="text-sm font-medium text-gray-900">{data.num_fatture_attive ?? 0}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Fatture passive</dt>
                <dd className="text-sm font-medium text-gray-900">{data.num_fatture_passive ?? 0}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Imponibile vendite</dt>
                <dd className="text-sm font-medium text-gray-900">{formatCurrency(data.imponibile_vendite ?? 0)}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Imponibile acquisti</dt>
                <dd className="text-sm font-medium text-gray-900">{formatCurrency(data.imponibile_acquisti ?? 0)}</dd>
              </div>
            </dl>
          </Card>
        </div>
      ) : null}
    </div>
  )
}
