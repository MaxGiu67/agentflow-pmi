import { useState, useRef } from 'react'
import { Plus, Trash2, Upload, Pencil, X, FileSignature } from 'lucide-react'
import {
  useRecurringContracts,
  useCreateRecurring,
  useUpdateRecurring,
  useDeleteRecurring,
  useImportRecurringPdf,
} from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'
import { formatCurrency } from '../../lib/utils'

interface RecurringContract {
  id: string
  descrizione: string
  controparte: string
  importo: number
  frequenza: string
  attivo: boolean
}

const emptyForm = {
  descrizione: '',
  controparte: '',
  importo: '',
  frequenza: 'mensile',
  attivo: true,
}

export default function RecurringPage() {
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [formData, setFormData] = useState(emptyForm)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { data, isLoading } = useRecurringContracts()
  const createMut = useCreateRecurring()
  const updateMut = useUpdateRecurring()
  const deleteMut = useDeleteRecurring()
  const importPdf = useImportRecurringPdf()

  const contracts = (data as RecurringContract[]) ?? (data as { items?: RecurringContract[] })?.items ?? []

  const openCreate = () => {
    setEditingId(null)
    setFormData(emptyForm)
    setShowForm(true)
  }

  const openEdit = (c: RecurringContract) => {
    setEditingId(c.id)
    setFormData({
      descrizione: c.descrizione,
      controparte: c.controparte,
      importo: String(c.importo),
      frequenza: c.frequenza,
      attivo: c.attivo,
    })
    setShowForm(true)
  }

  const handleSave = async () => {
    const payload = {
      descrizione: formData.descrizione,
      controparte: formData.controparte,
      importo: parseFloat(formData.importo) || 0,
      frequenza: formData.frequenza,
      attivo: formData.attivo,
    }
    if (editingId) {
      await updateMut.mutateAsync({ id: editingId, data: payload })
    } else {
      await createMut.mutateAsync(payload)
    }
    setShowForm(false)
    setEditingId(null)
    setFormData(emptyForm)
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Eliminare questo contratto?')) return
    await deleteMut.mutateAsync(id)
  }

  const handleImportPdf = () => {
    fileInputRef.current?.click()
  }

  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    await importPdf.mutateAsync(file)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const frequenzaLabel: Record<string, string> = {
    mensile: 'Mensile',
    trimestrale: 'Trimestrale',
    semestrale: 'Semestrale',
    annuale: 'Annuale',
  }

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="Contratti ricorrenti"
        subtitle="Gestisci abbonamenti, affitti e altri costi fissi"
        actions={
          <div className="flex items-center gap-3">
            <button
              onClick={handleImportPdf}
              disabled={importPdf.isPending}
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              <Upload className="h-4 w-4" />
              {importPdf.isPending ? 'Analisi PDF...' : 'Importa da PDF'}
            </button>
            <button
              onClick={openCreate}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" />
              Nuovo contratto
            </button>
          </div>
        }
      />

      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf"
        className="hidden"
        onChange={handleFileSelected}
      />

      {/* Form */}
      {showForm && (
        <Card className="mb-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-medium text-gray-900">
              {editingId ? 'Modifica contratto' : 'Nuovo contratto'}
            </h3>
            <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600">
              <X className="h-5 w-5" />
            </button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Descrizione</label>
              <input
                type="text"
                value={formData.descrizione}
                onChange={(e) => setFormData({ ...formData, descrizione: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                placeholder="Es. Affitto ufficio"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Controparte</label>
              <input
                type="text"
                value={formData.controparte}
                onChange={(e) => setFormData({ ...formData, controparte: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                placeholder="Es. Immobiliare Rossi"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Importo</label>
              <input
                type="number"
                step="0.01"
                value={formData.importo}
                onChange={(e) => setFormData({ ...formData, importo: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                placeholder="0.00"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Frequenza</label>
              <select
                value={formData.frequenza}
                onChange={(e) => setFormData({ ...formData, frequenza: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              >
                <option value="mensile">Mensile</option>
                <option value="trimestrale">Trimestrale</option>
                <option value="semestrale">Semestrale</option>
                <option value="annuale">Annuale</option>
              </select>
            </div>
          </div>
          <div className="mt-3 flex items-center gap-2">
            <input
              type="checkbox"
              id="attivo"
              checked={formData.attivo}
              onChange={(e) => setFormData({ ...formData, attivo: e.target.checked })}
              className="h-4 w-4 rounded border-gray-300 text-blue-600"
            />
            <label htmlFor="attivo" className="text-sm text-gray-700">Contratto attivo</label>
          </div>
          <div className="mt-4 flex gap-3">
            <button
              onClick={handleSave}
              disabled={createMut.isPending || updateMut.isPending}
              className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
            >
              {createMut.isPending || updateMut.isPending ? 'Salvataggio...' : 'Salva'}
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Annulla
            </button>
          </div>
        </Card>
      )}

      {/* Table */}
      {isLoading ? (
        <LoadingSpinner className="py-12" />
      ) : contracts.length > 0 ? (
        <Card className="!p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-200 bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Descrizione</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Controparte</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Importo</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Frequenza</th>
                  <th className="px-4 py-3 text-center font-medium text-gray-600">Attivo</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Azioni</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {contracts.map((c) => (
                  <tr key={c.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{c.descrizione}</td>
                    <td className="px-4 py-3 text-gray-700">{c.controparte}</td>
                    <td className="px-4 py-3 text-right text-gray-700">{formatCurrency(c.importo)}</td>
                    <td className="px-4 py-3 text-gray-700">{frequenzaLabel[c.frequenza] ?? c.frequenza}</td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`inline-block h-2.5 w-2.5 rounded-full ${
                          c.attivo ? 'bg-green-500' : 'bg-gray-300'
                        }`}
                      />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => openEdit(c)}
                          className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
                          title="Modifica"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(c.id)}
                          disabled={deleteMut.isPending}
                          className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600"
                          title="Elimina"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        <EmptyState
          icon={<FileSignature className="h-12 w-12" />}
          title="Nessun contratto ricorrente"
          description="Aggiungi i tuoi contratti fissi per tenere sotto controllo le spese ricorrenti."
          action={
            <button
              onClick={openCreate}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" /> Aggiungi contratto
            </button>
          }
        />
      )}
    </div>
  )
}
