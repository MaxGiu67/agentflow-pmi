import { useState, useRef } from 'react'
import { Upload, Plus, Trash2 } from 'lucide-react'
import { usePayrollCosts, usePayrollSummary, useCreatePayrollCost, useImportPayrollPdf, useDeletePayrollCost } from '../../api/hooks'
import { formatCurrency } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'

const MONTHS = ['', 'Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu', 'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic']

export default function PayrollPage() {
  const currentYear = new Date().getFullYear()
  const [year, setYear] = useState(2024)
  const [showAddForm, setShowAddForm] = useState(false)
  const [importResult, setImportResult] = useState<Record<string, unknown> | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { data: costsData, isLoading: loadingCosts } = usePayrollCosts(year)
  const { data: summary, isLoading: loadingSummary } = usePayrollSummary(year)
  const createCost = useCreatePayrollCost()
  const importPdf = useImportPayrollPdf()
  const deleteCost = useDeletePayrollCost()

  const costs = costsData?.items ?? []

  const handleImportPdf = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const result = await importPdf.mutateAsync({ file, createJournal: true })
      setImportResult(result)
    } catch (err) {
      setImportResult({ error: 'Errore durante l\'importazione' })
    }
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleAddManual = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    await createCost.mutateAsync({
      mese: form.get('mese') as string,
      dipendente_nome: form.get('dipendente_nome') as string,
      importo_lordo: Number(form.get('importo_lordo')),
      importo_netto: Number(form.get('importo_netto')) || undefined,
      contributi_inps: Number(form.get('contributi_inps')) || undefined,
      irpef: Number(form.get('irpef')) || undefined,
      costo_totale_azienda: Number(form.get('costo_totale_azienda')),
    })
    setShowAddForm(false)
  }

  if (loadingCosts || loadingSummary) return <LoadingSpinner className="mt-20" size="lg" />

  return (
    <div>
      <PageHeader
        title="Costi del Personale"
        subtitle={`Anno ${year} — Gestione stipendi, contributi e costi aziendali`}
        actions={
          <div className="flex gap-2">
            <select
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              {[currentYear, currentYear - 1, currentYear - 2].map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              onChange={handleImportPdf}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={importPdf.isPending}
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              <Upload className="h-4 w-4" />
              {importPdf.isPending ? 'Importando...' : 'Importa PDF Paghe'}
            </button>
            <button
              onClick={() => setShowAddForm(!showAddForm)}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" />
              Aggiungi Manuale
            </button>
          </div>
        }
      />

      {/* Import result */}
      {importResult && (
        <div className={`mb-4 rounded-lg border p-4 ${(importResult as Record<string, unknown>).error ? 'border-red-200 bg-red-50' : 'border-green-200 bg-green-50'}`}>
          {(importResult as Record<string, unknown>).error ? (
            <p className="text-sm text-red-700">{String((importResult as Record<string, unknown>).error)}</p>
          ) : (
            <div className="text-sm text-green-700">
              <p className="font-medium">{String((importResult as Record<string, unknown>).message)}</p>
              <p>Salari: {formatCurrency(Number((importResult as Record<string, unknown>).salari_stipendi) || 0)} | Netto: {formatCurrency(Number((importResult as Record<string, unknown>).netto_in_busta) || 0)} | IRPEF: {formatCurrency(Number((importResult as Record<string, unknown>).irpef) || 0)}</p>
              {(importResult as Record<string, unknown>).journal_entry ? <p>Scrittura contabile creata (partita doppia)</p> : null}
            </div>
          )}
          <button onClick={() => setImportResult(null)} className="mt-2 text-xs text-gray-500 hover:text-gray-700">Chiudi</button>
        </div>
      )}

      {/* Summary KPI cards */}
      {summary && (
        <div className="mb-6 grid grid-cols-4 gap-4">
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
            <p className="text-xs font-medium text-blue-600">Costo Totale Azienda</p>
            <p className="mt-1 text-2xl font-bold text-blue-900">{formatCurrency(summary.total_costo_azienda)}</p>
          </div>
          <div className="rounded-lg border border-green-200 bg-green-50 p-4">
            <p className="text-xs font-medium text-green-600">Totale Lordo</p>
            <p className="mt-1 text-2xl font-bold text-green-900">{formatCurrency(summary.total_lordo)}</p>
          </div>
          <div className="rounded-lg border border-purple-200 bg-purple-50 p-4">
            <p className="text-xs font-medium text-purple-600">Dipendenti</p>
            <p className="mt-1 text-2xl font-bold text-purple-900">{summary.num_dipendenti}</p>
          </div>
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
            <p className="text-xs font-medium text-amber-600">Costo Medio Mensile</p>
            <p className="mt-1 text-2xl font-bold text-amber-900">
              {summary.monthly?.length > 0 ? formatCurrency(summary.total_costo_azienda / summary.monthly.length) : '-'}
            </p>
          </div>
        </div>
      )}

      {/* Monthly summary */}
      {summary?.monthly && summary.monthly.length > 0 && (
        <div className="mb-6 overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Mese</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">Dipendenti</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">Lordo</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">Netto</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">Contributi</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">Costo Azienda</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {summary.monthly.map((m: Record<string, unknown>) => {
                const meseDate = String(m.mese)
                const monthNum = parseInt(meseDate.split('-')[1] || '0')
                return (
                  <tr key={meseDate} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-medium text-gray-900">{MONTHS[monthNum] || meseDate} {year}</td>
                    <td className="px-4 py-2 text-right text-gray-700">{String(m.num_dipendenti)}</td>
                    <td className="px-4 py-2 text-right text-gray-700">{formatCurrency(Number(m.totale_lordo))}</td>
                    <td className="px-4 py-2 text-right text-gray-700">{formatCurrency(Number(m.totale_netto))}</td>
                    <td className="px-4 py-2 text-right text-gray-700">{formatCurrency(Number(m.totale_contributi))}</td>
                    <td className="px-4 py-2 text-right font-medium text-gray-900">{formatCurrency(Number(m.totale_costo_azienda))}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Add manual form */}
      {showAddForm && (
        <div className="mb-6 rounded-lg border border-gray-200 bg-white p-6">
          <h3 className="mb-4 text-sm font-semibold text-gray-800">Aggiungi voce manuale</h3>
          <form onSubmit={handleAddManual} className="grid grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500">Mese (YYYY-MM-DD)</label>
              <input name="mese" type="date" required className="mt-1 w-full rounded-lg border px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500">Dipendente / Voce</label>
              <input name="dipendente_nome" required placeholder="Riepilogo mensile" className="mt-1 w-full rounded-lg border px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500">Importo Lordo</label>
              <input name="importo_lordo" type="number" step="0.01" required className="mt-1 w-full rounded-lg border px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500">Costo Totale Azienda</label>
              <input name="costo_totale_azienda" type="number" step="0.01" required className="mt-1 w-full rounded-lg border px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500">Importo Netto</label>
              <input name="importo_netto" type="number" step="0.01" className="mt-1 w-full rounded-lg border px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500">Contributi INPS</label>
              <input name="contributi_inps" type="number" step="0.01" className="mt-1 w-full rounded-lg border px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500">IRPEF</label>
              <input name="irpef" type="number" step="0.01" className="mt-1 w-full rounded-lg border px-3 py-2 text-sm" />
            </div>
            <div className="flex items-end gap-2">
              <button type="submit" disabled={createCost.isPending} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                Salva
              </button>
              <button type="button" onClick={() => setShowAddForm(false)} className="rounded-lg border px-4 py-2 text-sm text-gray-600 hover:bg-gray-50">
                Annulla
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Costs list */}
      {costs.length === 0 ? (
        <EmptyState
          title="Nessun costo del personale"
          description="Importa un PDF Riepilogo Paghe o aggiungi manualmente le voci di costo."
        />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Mese</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Dipendente / Voce</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">Lordo</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">Netto</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">INPS</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">IRPEF</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">Costo Azienda</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Note</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {costs.map((c: Record<string, unknown>) => (
                <tr key={String(c.id)} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-4 py-2 text-gray-700">{String(c.mese).slice(0, 7)}</td>
                  <td className="px-4 py-2 font-medium text-gray-900">{String(c.dipendente_nome)}</td>
                  <td className="px-4 py-2 text-right text-gray-700">{formatCurrency(Number(c.importo_lordo))}</td>
                  <td className="px-4 py-2 text-right text-gray-700">{c.importo_netto ? formatCurrency(Number(c.importo_netto)) : '-'}</td>
                  <td className="px-4 py-2 text-right text-gray-700">{c.contributi_inps ? formatCurrency(Number(c.contributi_inps)) : '-'}</td>
                  <td className="px-4 py-2 text-right text-gray-700">{c.irpef ? formatCurrency(Number(c.irpef)) : '-'}</td>
                  <td className="px-4 py-2 text-right font-medium text-gray-900">{formatCurrency(Number(c.costo_totale_azienda))}</td>
                  <td className="max-w-[150px] truncate px-4 py-2 text-xs text-gray-500">{String(c.note || '-')}</td>
                  <td className="px-4 py-2">
                    <button
                      onClick={() => deleteCost.mutate(String(c.id))}
                      className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
