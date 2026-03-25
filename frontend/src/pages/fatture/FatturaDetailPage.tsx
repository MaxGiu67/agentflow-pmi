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

  const structuredData = invoice.structured_data as Record<string, unknown> | null
  const destinatario = (structuredData?.destinatario_nome ?? structuredData?.cessionario_nome) as string | undefined
  const righe = (structuredData?.linee_dettaglio ?? structuredData?.righe ?? []) as Record<string, unknown>[]
  const riepilogo = (structuredData?.riepilogo ?? []) as Record<string, unknown>[]

  return (
    <div>
      <PageHeader
        title={`Fattura ${invoice.numero_fattura ?? ''}`}
        subtitle={invoice.emittente_nome}
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
              <dd className="text-sm font-medium text-gray-900">
                {invoice.data_fattura ? formatDate(invoice.data_fattura) : '-'}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Numero</dt>
              <dd className="text-sm font-medium text-gray-900">{invoice.numero_fattura ?? '-'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Emittente</dt>
              <dd className="text-sm font-medium text-gray-900">{invoice.emittente_nome ?? '-'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">P.IVA Emittente</dt>
              <dd className="text-sm font-medium text-gray-900">{invoice.emittente_piva ?? '-'}</dd>
            </div>
            {destinatario && (
              <>
                <div className="flex justify-between">
                  <dt className="text-sm text-gray-500">Destinatario</dt>
                  <dd className="text-sm font-medium text-gray-900">{destinatario}</dd>
                </div>
                {structuredData?.destinatario_piva && (
                  <div className="flex justify-between">
                    <dt className="text-sm text-gray-500">P.IVA Destinatario</dt>
                    <dd className="text-sm font-medium text-gray-900">{structuredData.destinatario_piva as string}</dd>
                  </div>
                )}
              </>
            )}
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Tipo documento</dt>
              <dd className="text-sm font-medium text-gray-900">
                <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                  invoice.type === 'attiva' ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'
                }`}>
                  {invoice.document_type ?? 'TD01'} — {invoice.type === 'attiva' ? 'Emessa' : 'Ricevuta'}
                </span>
              </dd>
            </div>
            <hr className="border-gray-100" />
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Imponibile</dt>
              <dd className="text-sm font-medium text-gray-900">
                {invoice.importo_netto != null ? formatCurrency(invoice.importo_netto) : '-'}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">IVA</dt>
              <dd className="text-sm font-medium text-gray-900">
                {invoice.importo_iva != null ? formatCurrency(invoice.importo_iva) : '-'}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-sm font-semibold text-gray-700">Importo totale</dt>
              <dd className="text-sm font-bold text-gray-900">
                {invoice.importo_totale != null ? formatCurrency(invoice.importo_totale) : '-'}
              </dd>
            </div>
            <hr className="border-gray-100" />
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Stato</dt>
              <dd><StatusBadge status={invoice.processing_status} /></dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-sm text-gray-500">Fonte</dt>
              <dd className="text-sm text-gray-900">{invoice.source ?? '-'}</dd>
            </div>
          </dl>
        </Card>

        {/* Category + Righe */}
        <div className="space-y-6">
          <Card>
            <h2 className="mb-4 text-lg font-semibold text-gray-900">Categorizzazione</h2>
            <dl className="space-y-3">
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Categoria</dt>
                <dd className="text-sm font-medium text-gray-900">{invoice.category ?? 'Non categorizzata'}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Confidenza</dt>
                <dd className="text-sm text-gray-900">
                  {invoice.category_confidence != null ? `${Math.round(invoice.category_confidence * 100)}%` : '-'}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Verificata</dt>
                <dd className="text-sm text-gray-900">{invoice.verified ? 'Si' : 'No'}</dd>
              </div>
            </dl>

            {invoice.processing_status === 'categorized' && !invoice.verified && (
              <div className="mt-4 flex items-center gap-2 rounded-lg bg-amber-50 p-3">
                <FileText className="h-5 w-5 text-amber-500" />
                <span className="text-sm text-amber-700">Da verificare</span>
                <button
                  onClick={() => navigate('/fatture/verifica')}
                  className="ml-auto text-sm font-medium text-blue-600 hover:underline"
                >
                  Verifica
                </button>
              </div>
            )}
          </Card>

          {/* Righe dettaglio */}
          {righe.length > 0 && (
            <Card>
              <h2 className="mb-4 text-lg font-semibold text-gray-900">Righe dettaglio</h2>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead>
                    <tr>
                      <th className="px-2 py-1 text-left text-xs text-gray-500">#</th>
                      <th className="px-2 py-1 text-left text-xs text-gray-500">Descrizione</th>
                      <th className="px-2 py-1 text-right text-xs text-gray-500">Importo</th>
                      <th className="px-2 py-1 text-right text-xs text-gray-500">IVA %</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {righe.map((riga, i) => (
                      <tr key={i}>
                        <td className="px-2 py-1 text-gray-500">{riga.numero_linea as string ?? i + 1}</td>
                        <td className="px-2 py-1">{riga.descrizione as string ?? '-'}</td>
                        <td className="px-2 py-1 text-right">
                          {riga.prezzo_totale != null ? formatCurrency(riga.prezzo_totale as number) : '-'}
                        </td>
                        <td className="px-2 py-1 text-right">{riga.aliquota_iva as string ?? '-'}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {/* Riepilogo IVA */}
          {riepilogo.length > 0 && (
            <Card>
              <h2 className="mb-4 text-lg font-semibold text-gray-900">Riepilogo IVA</h2>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 text-sm">
                  <thead>
                    <tr>
                      <th className="px-2 py-1 text-left text-xs text-gray-500">Aliquota</th>
                      <th className="px-2 py-1 text-right text-xs text-gray-500">Imponibile</th>
                      <th className="px-2 py-1 text-right text-xs text-gray-500">Imposta</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {riepilogo.map((r, i) => (
                      <tr key={i}>
                        <td className="px-2 py-1">{r.aliquota_iva as string ?? '-'}%</td>
                        <td className="px-2 py-1 text-right">
                          {r.imponibile != null ? formatCurrency(r.imponibile as number) : '-'}
                        </td>
                        <td className="px-2 py-1 text-right">
                          {r.imposta != null ? formatCurrency(r.imposta as number) : '-'}
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
    </div>
  )
}
