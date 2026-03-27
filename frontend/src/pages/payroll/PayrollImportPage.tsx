import { useState, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, Save, CheckCircle, AlertTriangle, ArrowLeft } from 'lucide-react'
import { usePreviewPayrollPdf, useImportPayrollPdf } from '../../api/hooks'
import { formatCurrency } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'

interface PreviewLine {
  descrizione: string
  importo: number
  dare_avere: string
  sezione: string
  conto_suggerito: string
}

const MONTHS = ['', 'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno', 'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']

export default function PayrollImportPage() {
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const previewMut = usePreviewPayrollPdf()
  const importMut = useImportPayrollPdf()

  const [preview, setPreview] = useState<{
    mese: number; anno: number; azienda: string; linee: PreviewLine[]; bilanciato: boolean
  } | null>(null)
  const [fileName, setFileName] = useState('')
  const [saved, setSaved] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  const [form, setForm] = useState({
    salari_stipendi: 0, netto_in_busta: 0, contributi_inps: 0,
    irpef: 0, tfr: 0, inail: 0, totale_dare: 0, totale_avere: 0,
  })

  const handleFileSelect = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setFileName(file.name)
    setSelectedFile(file)
    setSaved(false)
    try {
      const data = await previewMut.mutateAsync(file)
      setPreview({ mese: data.mese, anno: data.anno, azienda: data.azienda, linee: data.linee, bilanciato: data.bilanciato })
      setForm({
        salari_stipendi: data.salari_stipendi, netto_in_busta: data.netto_in_busta,
        contributi_inps: data.contributi_inps, irpef: data.irpef,
        tfr: data.tfr, inail: data.inail,
        totale_dare: data.totale_dare, totale_avere: data.totale_avere,
      })
    } catch { /* handled by mutation */ }
  }, [previewMut])

  const handleSave = useCallback(async (createJournal: boolean) => {
    if (!selectedFile) return
    try {
      await importMut.mutateAsync({ file: selectedFile, createJournal })
      setSaved(true)
    } catch { /* error */ }
  }, [selectedFile, importMut])

  const updateField = (field: string, value: string) => {
    setForm((prev) => ({ ...prev, [field]: parseFloat(value.replace(',', '.')) || 0 }))
  }

  const isBalanced = Math.abs(form.totale_dare - form.totale_avere) < 1

  const fields = [
    { key: 'salari_stipendi', label: 'Salari & Stipendi' },
    { key: 'netto_in_busta', label: 'Netto in Busta' },
    { key: 'contributi_inps', label: 'Contributi INPS (DM10)' },
    { key: 'irpef', label: 'IRPEF' },
    { key: 'tfr', label: 'TFR' },
    { key: 'inail', label: 'INAIL' },
    { key: 'totale_dare', label: 'Totale DARE' },
    { key: 'totale_avere', label: 'Totale AVERE' },
  ]

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
          <p className="mb-6 text-sm text-gray-500">Formato: "Riepilogo Paghe e Contributi" mensile</p>
          <input ref={fileInputRef} type="file" accept=".pdf" onChange={handleFileSelect} className="hidden" />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={previewMut.isPending}
            className="rounded-lg bg-blue-600 px-6 py-3 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {previewMut.isPending ? 'Analisi in corso...' : 'Scegli PDF'}
          </button>
          {previewMut.isError && <p className="mt-4 text-sm text-red-600">Errore nell'analisi del PDF. Verifica il formato.</p>}
        </div>
      )}

      {/* Risultati import */}
      {preview && !saved && (
        <div className="space-y-6">
          {/* Status */}
          <div className={`flex items-center justify-between rounded-lg p-4 ${isBalanced ? 'border border-green-200 bg-green-50' : 'border border-amber-200 bg-amber-50'}`}>
            <div className="flex items-center gap-2">
              {isBalanced ? <CheckCircle className="h-5 w-5 text-green-600" /> : <AlertTriangle className="h-5 w-5 text-amber-600" />}
              <span className={`text-sm font-medium ${isBalanced ? 'text-green-700' : 'text-amber-700'}`}>
                {isBalanced ? 'Bilanciato — Dare = Avere' : `Non bilanciato — Diff: ${formatCurrency(Math.abs(form.totale_dare - form.totale_avere))}`}
              </span>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <span>{fileName}</span>
              <button onClick={() => { setPreview(null); setSaved(false) }} className="text-blue-600 hover:underline">Cambia</button>
            </div>
          </div>

          {/* Form editabile */}
          <div className="rounded-xl border border-gray-200 bg-white p-6">
            <h3 className="mb-4 text-sm font-semibold text-gray-800">Dati Estratti — Modifica se necessario</h3>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              {fields.map(({ key, label }) => (
                <div key={key}>
                  <label className="block text-xs font-medium text-gray-500">{label}</label>
                  <input
                    type="number"
                    step="0.01"
                    value={form[key as keyof typeof form]}
                    onChange={(e) => updateField(key, e.target.value)}
                    className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-right font-mono text-sm focus:border-blue-500 focus:outline-none"
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Linee scrittura contabile — editabili */}
          {preview.linee.length > 0 && (
            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-gray-800">Scrittura Contabile ({preview.linee.length} voci)</h3>
                <button
                  type="button"
                  onClick={() => setPreview({ ...preview, linee: [...preview.linee, { descrizione: '', importo: 0, dare_avere: 'D', sezione: 'manuale', conto_suggerito: '' }] })}
                  className="rounded-lg border border-gray-300 px-3 py-1 text-xs text-gray-600 hover:bg-gray-50"
                >
                  + Aggiungi riga
                </button>
              </div>
              <div className="max-h-96 overflow-y-auto">
                <table className="min-w-full text-xs">
                  <thead className="sticky top-0 bg-gray-50">
                    <tr>
                      <th className="px-2 py-2 text-left text-gray-500">Descrizione</th>
                      <th className="w-28 px-2 py-2 text-right text-gray-500">Importo</th>
                      <th className="w-20 px-2 py-2 text-center text-gray-500">D/A</th>
                      <th className="px-2 py-2 text-left text-gray-500">Conto</th>
                      <th className="w-8 px-2 py-2"></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {preview.linee.map((l, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-2 py-1">
                          <input
                            type="text"
                            value={l.descrizione}
                            onChange={(e) => {
                              const updated = [...preview.linee]
                              updated[i] = { ...updated[i], descrizione: e.target.value }
                              setPreview({ ...preview, linee: updated })
                            }}
                            className="w-full rounded border border-gray-200 px-2 py-1 text-xs focus:border-blue-400 focus:outline-none"
                          />
                        </td>
                        <td className="px-2 py-1">
                          <input
                            type="number"
                            step="0.01"
                            value={l.importo}
                            onChange={(e) => {
                              const updated = [...preview.linee]
                              updated[i] = { ...updated[i], importo: parseFloat(e.target.value) || 0 }
                              setPreview({ ...preview, linee: updated })
                            }}
                            className="w-full rounded border border-gray-200 px-2 py-1 text-right font-mono text-xs focus:border-blue-400 focus:outline-none"
                          />
                        </td>
                        <td className="px-2 py-1 text-center">
                          <select
                            value={l.dare_avere}
                            onChange={(e) => {
                              const updated = [...preview.linee]
                              updated[i] = { ...updated[i], dare_avere: e.target.value }
                              setPreview({ ...preview, linee: updated })
                            }}
                            className={`rounded px-2 py-1 text-[10px] font-bold ${l.dare_avere === 'D' ? 'bg-blue-100 text-blue-700' : 'bg-orange-100 text-orange-700'}`}
                          >
                            <option value="D">DARE</option>
                            <option value="A">AVERE</option>
                          </select>
                        </td>
                        <td className="px-2 py-1">
                          <input
                            type="text"
                            value={l.conto_suggerito}
                            onChange={(e) => {
                              const updated = [...preview.linee]
                              updated[i] = { ...updated[i], conto_suggerito: e.target.value }
                              setPreview({ ...preview, linee: updated })
                            }}
                            className="w-full rounded border border-gray-200 px-2 py-1 text-xs text-gray-500 focus:border-blue-400 focus:outline-none"
                          />
                        </td>
                        <td className="px-2 py-1">
                          <button
                            onClick={() => {
                              const updated = preview.linee.filter((_, idx) => idx !== i)
                              setPreview({ ...preview, linee: updated })
                            }}
                            className="rounded p-0.5 text-gray-300 hover:text-red-500"
                            title="Elimina riga"
                          >
                            &times;
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {/* Totali calcolati dalle righe */}
              <div className="mt-3 flex justify-end gap-6 border-t border-gray-100 pt-3 text-xs">
                <span className="text-gray-500">Totale Dare: <strong className="font-mono text-blue-700">{formatCurrency(preview.linee.filter(l => l.dare_avere === 'D').reduce((s, l) => s + l.importo, 0))}</strong></span>
                <span className="text-gray-500">Totale Avere: <strong className="font-mono text-orange-700">{formatCurrency(preview.linee.filter(l => l.dare_avere === 'A').reduce((s, l) => s + l.importo, 0))}</strong></span>
              </div>
            </div>
          )}

          {/* Azioni */}
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
        </div>
      )}

      {/* Successo */}
      {saved && preview && (
        <div className="flex items-center gap-4 rounded-xl border border-green-200 bg-green-50 p-6">
          <CheckCircle className="h-8 w-8 text-green-600" />
          <div>
            <p className="text-lg font-semibold text-green-800">Importazione completata!</p>
            <p className="text-sm text-green-600">Paghe {MONTHS[preview.mese]} {preview.anno} salvate con scritture contabili in partita doppia.</p>
          </div>
          <div className="ml-auto flex gap-2">
            <button onClick={() => { setPreview(null); setSaved(false) }} className="rounded-lg border border-green-300 px-4 py-2 text-sm text-green-700 hover:bg-green-100">
              Importa altro mese
            </button>
            <button onClick={() => navigate('/personale')} className="rounded-lg bg-green-600 px-4 py-2 text-sm text-white hover:bg-green-700">
              Torna alla lista
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
