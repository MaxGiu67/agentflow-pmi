import { useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, FileText, Download, Upload, Send, CheckCircle2, AlertCircle, Zap } from 'lucide-react'
import { useInvoice, useSendInvoicePec, usePollPecReceipts, buildInvoiceXmlUrl } from '../../api/hooks'
import api from '../../api/client'
import { formatCurrency, formatDate } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import StatusBadge from '../../components/ui/StatusBadge'
import LoadingSpinner from '../../components/ui/LoadingSpinner'

export default function FatturaDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: invoice, isLoading, error } = useInvoice(id ?? '')
  const sendPec = useSendInvoicePec()
  const pollReceipts = usePollPecReceipts()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [pecFeedback, setPecFeedback] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const isAttiva = invoice?.type === 'attiva'

  const handleDownloadXml = async () => {
    if (!id) return
    const token = localStorage.getItem('access_token')
    const r = await fetch(buildInvoiceXmlUrl(id), {
      headers: { Authorization: `Bearer ${token ?? ''}` },
    })
    if (!r.ok) {
      setPecFeedback({ type: 'error', text: 'Impossibile scaricare XML' })
      return
    }
    const disposition = r.headers.get('Content-Disposition') || ''
    const match = /filename="([^"]+)"/.exec(disposition)
    const filename = match?.[1] || 'fattura.xml'
    const blob = await r.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleSendPec = async (testMode: boolean) => {
    if (!id || !selectedFile) return
    setPecFeedback(null)
    try {
      const r = await sendPec.mutateAsync({ invoiceId: id, file: selectedFile, testMode })
      setPecFeedback({
        type: 'success',
        text: testMode
          ? `Test inviato a te stesso (${r.recipient}) — Message-ID ${r.pec_message_id}`
          : `Inviato a SDI (${r.recipient}) — Message-ID ${r.pec_message_id}`,
      })
      setSelectedFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setPecFeedback({ type: 'error', text: detail ?? 'Invio fallito' })
    }
  }

  const [acubeBusy, setAcubeBusy] = useState(false)
  const handleSendAcube = async () => {
    if (!id) return
    if (!confirm('Invia la fattura al SDI via A-Cube (sandbox)? A-Cube firma server-side e inoltra al SDI.')) return
    setPecFeedback(null)
    setAcubeBusy(true)
    try {
      const r = await api.post(`/invoices/active/${id}/send`, {})
      const d = r.data as { sdi_id: string; sdi_status: string; message: string }
      setPecFeedback({
        type: 'success',
        text: `A-Cube: ${d.message} — UUID ${d.sdi_id}`,
      })
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setPecFeedback({ type: 'error', text: detail ?? 'Errore invio A-Cube' })
    } finally {
      setAcubeBusy(false)
    }
  }

  const handlePollReceipts = async () => {
    setPecFeedback(null)
    try {
      const r = await pollReceipts.mutateAsync()
      setPecFeedback({
        type: 'success',
        text: r.new_receipts > 0
          ? `${r.new_receipts} nuove ricevute SDI trovate`
          : 'Nessuna nuova ricevuta SDI',
      })
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setPecFeedback({ type: 'error', text: detail ?? 'Errore poll PEC' })
    }
  }

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

      {isAttiva && (
        <Card className="mb-6 border-indigo-200 bg-indigo-50/40">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h3 className="text-base font-semibold text-gray-900">Invio a SDI — via A-Cube (raccomandato)</h3>
              <p className="mt-1 text-sm text-gray-600">
                A-Cube firma la fattura server-side (CAdES) e la inoltra al SDI. Nessuna firma o PEC
                necessarie — ambiente attuale: <b>sandbox</b>.
              </p>
            </div>
            <button
              onClick={handleSendAcube}
              disabled={acubeBusy}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
            >
              <Zap className="h-4 w-4" />
              {acubeBusy ? 'Invio…' : 'Invia via A-Cube'}
            </button>
          </div>

          <div className="mt-4 rounded-lg bg-white p-3">
            <h4 className="text-sm font-semibold text-gray-900">Alternativa — Invio manuale via PEC</h4>
            <p className="mt-1 text-xs text-gray-600">
              Scarica l'XML → firmalo con firma digitale (CAdES .p7m) → caricalo e invia al SDI tramite la
              tua PEC configurata. Usa questo flusso se A-Cube non è attivo.
              <a href="/impostazioni/pec" className="ml-1 text-blue-600 hover:underline">
                Configura PEC →
              </a>
            </p>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              onClick={handleDownloadXml}
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              <Download className="h-4 w-4" />
              Scarica XML
            </button>

            <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
              <Upload className="h-4 w-4" />
              {selectedFile ? selectedFile.name : 'Seleziona .p7m firmato'}
              <input
                ref={fileInputRef}
                type="file"
                accept=".p7m,.xml"
                className="hidden"
                onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
              />
            </label>

            <button
              onClick={() => handleSendPec(true)}
              disabled={!selectedFile || sendPec.isPending}
              className="inline-flex items-center gap-2 rounded-lg border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-medium text-amber-900 hover:bg-amber-100 disabled:opacity-50"
              title="Invia la PEC al tuo stesso indirizzo — zero impatto SDI"
            >
              <Send className="h-4 w-4" />
              {sendPec.isPending ? 'Invio…' : 'Invio test (a me)'}
            </button>

            <button
              onClick={() => {
                if (confirm('Confermi l\'invio REALE al Sistema di Interscambio? La fattura avrà effetti fiscali.')) {
                  handleSendPec(false)
                }
              }}
              disabled={!selectedFile || sendPec.isPending}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
              {sendPec.isPending ? 'Invio…' : 'Invia a SDI via PEC'}
            </button>

            <button
              onClick={handlePollReceipts}
              disabled={pollReceipts.isPending}
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              {pollReceipts.isPending ? 'Lettura…' : 'Controlla ricevute'}
            </button>
          </div>

          {pecFeedback && (
            <div
              className={`mt-3 flex items-start gap-2 rounded-lg border px-3 py-2 text-sm ${
                pecFeedback.type === 'success'
                  ? 'border-green-200 bg-green-50 text-green-800'
                  : 'border-red-200 bg-red-50 text-red-800'
              }`}
            >
              {pecFeedback.type === 'success' ? (
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
              ) : (
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              )}
              <span>{pecFeedback.text}</span>
            </div>
          )}
        </Card>
      )}

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
