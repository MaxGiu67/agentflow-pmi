import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { AlertTriangle, CheckCircle, ArrowLeft, Save, Trash2, Plus } from 'lucide-react'
import { useCreatePayrollJournal } from '../../api/hooks'
import { formatCurrency } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'

interface LineaContabile {
  account: string
  description: string
  debit: number
  credit: number
}

interface ImportData {
  payroll_cost_id: string
  mese: string
  azienda: string
  salari_stipendi: number
  netto_in_busta: number
  contributi_inps: number
  irpef: number
  totale_dare: number
  totale_avere: number
  bilanciato: boolean
  linee_estratte: number
  linee_contabili: LineaContabile[]
  message: string
}

export default function GestioneImportPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const importData = (location.state as { importData: ImportData } | null)?.importData

  const createJournal = useCreatePayrollJournal()
  const [linee, setLinee] = useState<LineaContabile[]>(importData?.linee_contabili ?? [])
  const [saved, setSaved] = useState(false)

  if (!importData) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <AlertTriangle className="mb-4 h-12 w-12 text-amber-500" />
        <h2 className="text-lg font-semibold text-gray-900">Nessun dato di importazione</h2>
        <p className="mt-1 text-sm text-gray-500">Torna alla pagina Personale per importare un PDF.</p>
        <button
          onClick={() => navigate('/personale')}
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          <ArrowLeft className="h-4 w-4" />
          Torna a Personale
        </button>
      </div>
    )
  }

  const totaleDare = linee.reduce((sum, l) => sum + l.debit, 0)
  const totaleAvere = linee.reduce((sum, l) => sum + l.credit, 0)
  const differenza = Math.abs(totaleDare - totaleAvere)
  const isBalanced = differenza < 0.10

  const updateLinea = (index: number, field: keyof LineaContabile, value: string | number) => {
    setLinee(prev => prev.map((l, i) => i === index ? { ...l, [field]: value } : l))
  }

  const removeLinea = (index: number) => {
    setLinee(prev => prev.filter((_, i) => i !== index))
  }

  const addLinea = () => {
    setLinee(prev => [...prev, { account: '', description: '', debit: 0, credit: 0 }])
  }

  const handleConfirm = async () => {
    try {
      await createJournal.mutateAsync({
        costId: importData.payroll_cost_id,
        linee_contabili: linee,
        totale_dare: totaleDare,
        totale_avere: totaleAvere,
      })
      setSaved(true)
      setTimeout(() => navigate('/personale'), 2000)
    } catch {
      // error handled by mutation
    }
  }

  if (saved) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <CheckCircle className="mb-4 h-16 w-16 text-green-500" />
        <h2 className="text-lg font-semibold text-gray-900">Scrittura contabile creata!</h2>
        <p className="mt-1 text-sm text-gray-500">Reindirizzamento alla pagina Personale...</p>
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        title="Gestione Importazione Paghe"
        subtitle={`${importData.azienda} — ${importData.mese}`}
        actions={
          <button
            onClick={() => navigate('/personale')}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <ArrowLeft className="h-4 w-4" />
            Torna a Personale
          </button>
        }
      />

      {/* Alert sbilanciamento */}
      <div className={`mb-6 rounded-lg border p-4 ${isBalanced ? 'border-green-200 bg-green-50' : 'border-amber-200 bg-amber-50'}`}>
        <div className="flex items-start gap-3">
          {isBalanced ? (
            <CheckCircle className="mt-0.5 h-5 w-5 text-green-600" />
          ) : (
            <AlertTriangle className="mt-0.5 h-5 w-5 text-amber-600" />
          )}
          <div>
            <h3 className={`text-sm font-semibold ${isBalanced ? 'text-green-800' : 'text-amber-800'}`}>
              {isBalanced ? 'Importazione bilanciata' : 'Importazione NON bilanciata'}
            </h3>
            <p className={`mt-1 text-sm ${isBalanced ? 'text-green-700' : 'text-amber-700'}`}>
              Dare: {formatCurrency(totaleDare)} | Avere: {formatCurrency(totaleAvere)}
              {!isBalanced && ` | Differenza: ${formatCurrency(differenza)}`}
            </p>
            {!isBalanced && (
              <p className="mt-1 text-xs text-amber-600">
                Modifica le righe sottostanti per bilanciare dare e avere, oppure conferma comunque.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Riepilogo importazione */}
      <div className="mb-6 grid grid-cols-4 gap-4">
        <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
          <p className="text-xs font-medium text-blue-600">Salari & Stipendi</p>
          <p className="mt-1 text-xl font-bold text-blue-900">{formatCurrency(importData.salari_stipendi)}</p>
        </div>
        <div className="rounded-lg border border-green-200 bg-green-50 p-4">
          <p className="text-xs font-medium text-green-600">Netto in Busta</p>
          <p className="mt-1 text-xl font-bold text-green-900">{formatCurrency(importData.netto_in_busta)}</p>
        </div>
        <div className="rounded-lg border border-purple-200 bg-purple-50 p-4">
          <p className="text-xs font-medium text-purple-600">Contributi INPS</p>
          <p className="mt-1 text-xl font-bold text-purple-900">{formatCurrency(importData.contributi_inps)}</p>
        </div>
        <div className="rounded-lg border border-red-200 bg-red-50 p-4">
          <p className="text-xs font-medium text-red-600">IRPEF</p>
          <p className="mt-1 text-xl font-bold text-red-900">{formatCurrency(importData.irpef)}</p>
        </div>
      </div>

      {/* Tabella linee contabili editabile */}
      <div className="mb-4 overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Conto</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500">Descrizione</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">Dare</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500">Avere</th>
              <th className="px-4 py-3 w-10"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {linee.map((linea, idx) => (
              <tr key={idx} className="hover:bg-gray-50">
                <td className="px-4 py-2">
                  <input
                    type="text"
                    value={linea.account}
                    onChange={(e) => updateLinea(idx, 'account', e.target.value)}
                    className="w-full rounded border border-gray-200 px-2 py-1 text-sm focus:border-blue-400 focus:outline-none"
                  />
                </td>
                <td className="px-4 py-2">
                  <input
                    type="text"
                    value={linea.description}
                    onChange={(e) => updateLinea(idx, 'description', e.target.value)}
                    className="w-full rounded border border-gray-200 px-2 py-1 text-sm focus:border-blue-400 focus:outline-none"
                  />
                </td>
                <td className="px-4 py-2">
                  <input
                    type="number"
                    step="0.01"
                    value={linea.debit || ''}
                    onChange={(e) => updateLinea(idx, 'debit', parseFloat(e.target.value) || 0)}
                    className="w-28 rounded border border-gray-200 px-2 py-1 text-right text-sm focus:border-blue-400 focus:outline-none"
                  />
                </td>
                <td className="px-4 py-2">
                  <input
                    type="number"
                    step="0.01"
                    value={linea.credit || ''}
                    onChange={(e) => updateLinea(idx, 'credit', parseFloat(e.target.value) || 0)}
                    className="w-28 rounded border border-gray-200 px-2 py-1 text-right text-sm focus:border-blue-400 focus:outline-none"
                  />
                </td>
                <td className="px-4 py-2">
                  <button
                    onClick={() => removeLinea(idx)}
                    className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-500"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot className="bg-gray-50 font-medium">
            <tr>
              <td colSpan={2} className="px-4 py-3 text-right text-xs text-gray-600">TOTALI</td>
              <td className="px-4 py-3 text-right text-sm text-gray-900">{formatCurrency(totaleDare)}</td>
              <td className="px-4 py-3 text-right text-sm text-gray-900">{formatCurrency(totaleAvere)}</td>
              <td></td>
            </tr>
            {!isBalanced && (
              <tr>
                <td colSpan={2} className="px-4 py-2 text-right text-xs text-amber-600 font-semibold">DIFFERENZA</td>
                <td colSpan={2} className="px-4 py-2 text-center text-sm font-bold text-amber-700">{formatCurrency(differenza)}</td>
                <td></td>
              </tr>
            )}
          </tfoot>
        </table>
      </div>

      {/* Azioni */}
      <div className="flex items-center justify-between">
        <button
          onClick={addLinea}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <Plus className="h-4 w-4" />
          Aggiungi riga
        </button>

        <div className="flex gap-3">
          <button
            onClick={() => navigate('/personale')}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Annulla
          </button>
          <button
            onClick={handleConfirm}
            disabled={createJournal.isPending || linee.length === 0}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            <Save className="h-4 w-4" />
            {createJournal.isPending ? 'Creazione...' : 'Conferma e Crea Scritture'}
          </button>
        </div>
      </div>

      {createJournal.isError && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3">
          <p className="text-sm text-red-700">Errore nella creazione delle scritture contabili. Riprovare.</p>
        </div>
      )}
    </div>
  )
}
