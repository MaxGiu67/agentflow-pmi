import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, FileText } from 'lucide-react'
import { useInvoice } from '../../api/hooks'
import { formatCurrency, formatDate } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import StatusBadge from '../../components/ui/StatusBadge'
import LoadingSpinner from '../../components/ui/LoadingSpinner'

export default function FatturaDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: invoice, isLoading, error } = useInvoice(id ?? '')

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  if (error || !invoice) {
    return (
      <div className="mt-20 text-center">
        <p className="text-gray-600">Fattura non trovata</p>
        <button onClick={() => navigate('/fatture')} className="mt-4 text-blue-600 hover:underline">
          Torna alle fatture
        </button>
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        title={`Fattura ${invoice.number ?? ''}`}
        subtitle={invoice.emittente}
        actions={
          <button
            onClick={() => navigate('/fatture')}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <ArrowLeft className="h-4 w-4" />
            Indietro
          </button>
        }
      />

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Info card */}
        <Card>
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Dettagli</h2>
          <dl className="space-y-3">
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Data</dt>
              <dd className="text-sm font-medium text-gray-900">{formatDate(invoice.date)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Numero</dt>
              <dd className="text-sm font-medium text-gray-900">{invoice.number ?? '-'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Emittente</dt>
              <dd className="text-sm font-medium text-gray-900">{invoice.emittente}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Tipo</dt>
              <dd className="text-sm font-medium text-gray-900">
                {invoice.type === 'passive' ? 'Passiva' : 'Attiva'}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Importo totale</dt>
              <dd className="text-sm font-bold text-gray-900">{formatCurrency(invoice.total_amount)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Imponibile</dt>
              <dd className="text-sm font-medium text-gray-900">{formatCurrency(invoice.taxable_amount ?? 0)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">IVA</dt>
              <dd className="text-sm font-medium text-gray-900">{formatCurrency(invoice.vat_amount ?? 0)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Stato</dt>
              <dd><StatusBadge status={invoice.status} /></dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Fonte</dt>
              <dd className="text-sm font-medium text-gray-900">
                {invoice.source === 'cassetto' ? 'Cassetto Fiscale' : invoice.source === 'email' ? 'Email' : 'Manuale'}
              </dd>
            </div>
          </dl>
        </Card>

        {/* Category and additional info */}
        <Card>
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Categorizzazione</h2>
          <dl className="space-y-3">
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Categoria</dt>
              <dd className="text-sm font-medium text-gray-900">{invoice.category ?? 'Non categorizzata'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Confidenza</dt>
              <dd className="text-sm font-medium text-gray-900">
                {invoice.category_confidence != null ? `${Math.round(invoice.category_confidence * 100)}%` : '-'}
              </dd>
            </div>
            {invoice.xml_data && (
              <div className="mt-4">
                <h3 className="mb-2 text-sm font-medium text-gray-700">Dati XML</h3>
                <div className="max-h-64 overflow-auto rounded-lg bg-gray-50 p-3">
                  <pre className="text-xs text-gray-600">
                    {typeof invoice.xml_data === 'string'
                      ? invoice.xml_data
                      : JSON.stringify(invoice.xml_data, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </dl>

          {invoice.status === 'pending_review' && (
            <div className="mt-4 flex items-center gap-2 rounded-lg bg-amber-50 p-3">
              <FileText className="h-5 w-5 text-amber-500" />
              <span className="text-sm text-amber-700">
                Questa fattura richiede la verifica della categoria.
              </span>
              <button
                onClick={() => navigate('/fatture/verifica')}
                className="ml-auto text-sm font-medium text-blue-600 hover:underline"
              >
                Verifica
              </button>
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}
