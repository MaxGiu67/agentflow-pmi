import { useState, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/esm/Page/AnnotationLayer.css'
import 'react-pdf/dist/esm/Page/TextLayer.css'
import { Upload, ChevronLeft, ChevronRight, Save, CheckCircle, AlertTriangle, ArrowLeft } from 'lucide-react'
import { usePreviewPayrollPdf, useImportPayrollPdf } from '../../api/hooks'
import { formatCurrency } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'

// PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`

interface PreviewData {
  pdf_base64: string
  mese: number
  anno: number
  azienda: string
  salari_stipendi: number
  netto_in_busta: number
  contributi_inps: number
  irpef: number
  tfr: number
  inail: number
  totale_dare: number
  totale_avere: number
  bilanciato: boolean
  linee: { descrizione: string; importo: number; dare_avere: string; sezione: string; conto_suggerito: string }[]
}

const MONTHS = ['', 'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno', 'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']

export default function PayrollImportPage() {
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const previewMut = usePreviewPayrollPdf()
  const importMut = useImportPayrollPdf()

  const [preview, setPreview] = useState<PreviewData | null>(null)
  const [pdfData, setPdfData] = useState<string | null>(null)
  const [numPages, setNumPages] = useState(0)
  const [pageNum, setPageNum] = useState(1)
  const [fileName, setFileName] = useState('')
  const [saved, setSaved] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  // Editable form fields
  const [form, setForm] = useState({
    salari_stipendi: 0,
    netto_in_busta: 0,
    contributi_inps: 0,
    irpef: 0,
    tfr: 0,
    inail: 0,
    totale_dare: 0,
    totale_avere: 0,
  })

  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setFileName(file.name)
    setSelectedFile(file)
    setSaved(false)

    try {
      const data = await previewMut.mutateAsync(file)
      setPreview(data)
      setPdfData(`data:application/pdf;base64,${data.pdf_base64}`)
      setForm({
        salari_stipendi: data.salari_stipendi,
        netto_in_busta: data.netto_in_busta,
        contributi_inps: data.contributi_inps,
        irpef: data.irpef,
        tfr: data.tfr,
        inail: data.inail,
        totale_dare: data.totale_dare,
        totale_avere: data.totale_avere,
      })
    } catch {
      // error handled by mutation
    }
  }, [previewMut])

  const handleSave = useCallback(async (createJournal: boolean) => {
    if (!selectedFile) return
    try {
      await importMut.mutateAsync({ file: selectedFile, createJournal })
      setSaved(true)
    } catch {
      // error
    }
  }, [selectedFile, importMut])

  const updateField = (field: string, value: string) => {
    const num = parseFloat(value.replace(',', '.')) || 0
    setForm((prev) => ({ ...prev, [field]: num }))
  }

  const isBalanced = Math.abs(form.totale_dare - form.totale_avere) < 1

  return (
    <div>
      <PageHeader
        title="Importa Riepilogo Paghe"
        subtitle={preview ? `${MONTHS[preview.mese]} ${preview.anno} — ${preview.azienda}` : 'Seleziona un PDF per iniziare'}
        actions={
          <button onClick={() => navigate('/personale')} className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
            <ArrowLeft className="h-4 w-4" /> Indietro
          </button>
        }
      />

      {/* File picker */}
      {!preview && (
        <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-gray-300 bg-gray-50 p-12">
          <Upload className="mb-4 h-12 w-12 text-gray-400" />
          <p className="mb-2 text-lg font-medium text-gray-700">Seleziona il PDF Riepilogo Paghe</p>
          <p className="mb-6 text-sm text-gray-500">Formato supportato: "Riepilogo Paghe e Contributi" mensile</p>
          <input ref={fileInputRef} type="file" accept=".pdf" onChange={handleFileSelect} className="hidden" />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={previewMut.isPending}
            className="rounded-lg bg-blue-600 px-6 py-3 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {previewMut.isPending ? 'Analisi in corso...' : 'Scegli PDF'}
          </button>
          {previewMut.isError && (
            <p className="mt-4 text-sm text-red-600">Errore nell'analisi del PDF. Verifica il formato.</p>
          )}
        </div>
      )}

      {/* Split View */}
      {preview && (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* LEFT — PDF Viewer */}
          <div className="rounded-xl border border-gray-200 bg-white p-4">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-800">{fileName}</h3>
              <div className="flex items-center gap-2">
                <button onClick={() => setPageNum((p) => Math.max(1, p - 1))} disabled={pageNum <= 1} className="rounded border px-2 py-1 text-xs disabled:opacity-30">
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="text-xs text-gray-500">{pageNum}/{numPages}</span>
                <button onClick={() => setPageNum((p) => Math.min(numPages, p + 1))} disabled={pageNum >= numPages} className="rounded border px-2 py-1 text-xs disabled:opacity-30">
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
              <button
                onClick={() => { setPreview(null); setPdfData(null); setSaved(false) }}
                className="text-xs text-blue-600 hover:underline"
              >
                Cambia PDF
              </button>
            </div>

            <div className="flex justify-center overflow-auto rounded-lg bg-gray-100" style={{ maxHeight: '70vh' }}>
              {pdfData && (
                <Document file={pdfData} onLoadSuccess={({ numPages: n }) => setNumPages(n)} loading={<p className="p-8 text-gray-400">Caricamento PDF...</p>}>
                  <Page pageNumber={pageNum} width={480} />
                </Document>
              )}
            </div>
          </div>

          {/* RIGHT — Form editabile */}
          <div className="space-y-4">
            {/* Status banner */}
            <div className={`flex items-center gap-2 rounded-lg p-3 ${isBalanced ? 'border border-green-200 bg-green-50' : 'border border-amber-200 bg-amber-50'}`}>
              {isBalanced ? <CheckCircle className="h-5 w-5 text-green-600" /> : <AlertTriangle className="h-5 w-5 text-amber-600" />}
              <span className={`text-sm font-medium ${isBalanced ? 'text-green-700' : 'text-amber-700'}`}>
                {isBalanced ? 'Bilanciato — Dare = Avere' : `Non bilanciato — Differenza: ${formatCurrency(Math.abs(form.totale_dare - form.totale_avere))}`}
              </span>
            </div>

            {/* Editable fields */}
            <div className="rounded-xl border border-gray-200 bg-white p-5">
              <h3 className="mb-4 text-sm font-semibold text-gray-800">Dati Estratti — Modifica se necessario</h3>
              <div className="grid grid-cols-2 gap-4">
                {[
                  { key: 'salari_stipendi', label: 'Salari & Stipendi' },
                  { key: 'netto_in_busta', label: 'Netto in Busta' },
                  { key: 'contributi_inps', label: 'Contributi INPS (DM10)' },
                  { key: 'irpef', label: 'IRPEF' },
                  { key: 'tfr', label: 'TFR' },
                  { key: 'inail', label: 'INAIL' },
                  { key: 'totale_dare', label: 'Totale DARE' },
                  { key: 'totale_avere', label: 'Totale AVERE' },
                ].map(({ key, label }) => (
                  <div key={key}>
                    <label className="block text-xs font-medium text-gray-500">{label}</label>
                    <input
                      type="number"
                      step="0.01"
                      value={form[key as keyof typeof form]}
                      onChange={(e) => updateField(key, e.target.value)}
                      className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm text-right font-mono focus:border-blue-500 focus:outline-none"
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* Linee estratte */}
            {preview.linee.length > 0 && (
              <div className="rounded-xl border border-gray-200 bg-white p-5">
                <h3 className="mb-3 text-sm font-semibold text-gray-800">Linee Estratte ({preview.linee.length})</h3>
                <div className="max-h-60 overflow-y-auto">
                  <table className="min-w-full text-xs">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-2 py-1 text-left text-gray-500">Descrizione</th>
                        <th className="px-2 py-1 text-right text-gray-500">Importo</th>
                        <th className="px-2 py-1 text-center text-gray-500">D/A</th>
                        <th className="px-2 py-1 text-left text-gray-500">Sezione</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {preview.linee.map((l, i) => (
                        <tr key={i} className="hover:bg-gray-50">
                          <td className="px-2 py-1 text-gray-700">{l.descrizione}</td>
                          <td className="px-2 py-1 text-right font-mono text-gray-900">{formatCurrency(l.importo)}</td>
                          <td className="px-2 py-1 text-center">
                            <span className={`rounded px-1 py-0.5 text-[10px] font-bold ${l.dare_avere === 'D' ? 'bg-blue-100 text-blue-700' : 'bg-orange-100 text-orange-700'}`}>
                              {l.dare_avere}
                            </span>
                          </td>
                          <td className="px-2 py-1 text-gray-500">{l.sezione}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Actions */}
            {!saved ? (
              <div className="flex gap-3">
                <button
                  onClick={() => void handleSave(false)}
                  disabled={importMut.isPending}
                  className="flex-1 rounded-lg border border-gray-300 px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                >
                  Salva Solo Costi
                </button>
                <button
                  onClick={() => void handleSave(true)}
                  disabled={importMut.isPending}
                  className="flex-1 rounded-lg bg-blue-600 px-4 py-3 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  <Save className="mr-2 inline h-4 w-4" />
                  {importMut.isPending ? 'Salvataggio...' : 'Salva + Scritture Contabili'}
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-3 rounded-lg border border-green-200 bg-green-50 p-4">
                <CheckCircle className="h-5 w-5 text-green-600" />
                <div>
                  <p className="text-sm font-medium text-green-700">Importazione completata!</p>
                  <p className="text-xs text-green-600">Paghe {MONTHS[preview.mese]} {preview.anno} salvate con scritture contabili.</p>
                </div>
                <button onClick={() => navigate('/personale')} className="ml-auto rounded-lg bg-green-600 px-4 py-2 text-sm text-white hover:bg-green-700">
                  Torna alla lista
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
