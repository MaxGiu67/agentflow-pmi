import { useState } from 'react'
import { Plus, Trash2, Pencil, X, Banknote } from 'lucide-react'
import {
  useLoans,
  useCreateLoan,
  useUpdateLoan,
  useDeleteLoan,
} from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'
import { formatCurrency } from '../../lib/utils'

interface Loan {
  id: string
  descrizione: string
  banca: string
  importo_originale: number
  rata_mensile: number
  debito_residuo: number
}

const emptyForm = {
  descrizione: '',
  banca: '',
  importo_originale: '',
  rata_mensile: '',
  debito_residuo: '',
}

export default function LoansPage() {
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [formData, setFormData] = useState(emptyForm)

  const { data, isLoading } = useLoans()
  const createMut = useCreateLoan()
  const updateMut = useUpdateLoan()
  const deleteMut = useDeleteLoan()

  const loans = (data as Loan[]) ?? (data as { items?: Loan[] })?.items ?? []

  const openCreate = () => {
    setEditingId(null)
    setFormData(emptyForm)
    setShowForm(true)
  }

  const openEdit = (l: Loan) => {
    setEditingId(l.id)
    setFormData({
      descrizione: l.descrizione,
      banca: l.banca,
      importo_originale: String(l.importo_originale),
      rata_mensile: String(l.rata_mensile),
      debito_residuo: String(l.debito_residuo),
    })
    setShowForm(true)
  }

  const handleSave = async () => {
    const payload = {
      descrizione: formData.descrizione,
      banca: formData.banca,
      importo_originale: parseFloat(formData.importo_originale) || 0,
      rata_mensile: parseFloat(formData.rata_mensile) || 0,
      debito_residuo: parseFloat(formData.debito_residuo) || 0,
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
    if (!confirm('Eliminare questo finanziamento?')) return
    await deleteMut.mutateAsync(id)
  }

  const totalDebitoResiduo = loans.reduce((sum, l) => sum + (l.debito_residuo ?? 0), 0)
  const totalRataMensile = loans.reduce((sum, l) => sum + (l.rata_mensile ?? 0), 0)

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="Finanziamenti"
        subtitle="Mutui, prestiti e linee di credito"
        actions={
          <button
            onClick={openCreate}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            Nuovo finanziamento
          </button>
        }
      />

      {/* Summary cards */}
      {loans.length > 0 && (
        <div className="mb-6 grid gap-4 sm:grid-cols-2">
          <Card>
            <p className="text-sm text-gray-500">Debito residuo totale</p>
            <p className="text-2xl font-bold text-gray-900">{formatCurrency(totalDebitoResiduo)}</p>
          </Card>
          <Card>
            <p className="text-sm text-gray-500">Rate mensili totali</p>
            <p className="text-2xl font-bold text-gray-900">{formatCurrency(totalRataMensile)}</p>
          </Card>
        </div>
      )}

      {/* Form */}
      {showForm && (
        <Card className="mb-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-medium text-gray-900">
              {editingId ? 'Modifica finanziamento' : 'Nuovo finanziamento'}
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
                placeholder="Es. Mutuo sede operativa"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Banca</label>
              <input
                type="text"
                value={formData.banca}
                onChange={(e) => setFormData({ ...formData, banca: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                placeholder="Es. Intesa Sanpaolo"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Importo originale</label>
              <input
                type="number"
                step="0.01"
                value={formData.importo_originale}
                onChange={(e) => setFormData({ ...formData, importo_originale: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                placeholder="0.00"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Rata mensile</label>
              <input
                type="number"
                step="0.01"
                value={formData.rata_mensile}
                onChange={(e) => setFormData({ ...formData, rata_mensile: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                placeholder="0.00"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="mb-1 block text-xs font-medium text-gray-600">Debito residuo</label>
              <input
                type="number"
                step="0.01"
                value={formData.debito_residuo}
                onChange={(e) => setFormData({ ...formData, debito_residuo: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                placeholder="0.00"
              />
            </div>
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
      ) : loans.length > 0 ? (
        <Card className="!p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-200 bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Descrizione</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Banca</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Importo originale</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Rata mensile</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Debito residuo</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Azioni</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {loans.map((l) => (
                  <tr key={l.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{l.descrizione}</td>
                    <td className="px-4 py-3 text-gray-700">{l.banca}</td>
                    <td className="px-4 py-3 text-right text-gray-700">{formatCurrency(l.importo_originale)}</td>
                    <td className="px-4 py-3 text-right text-gray-700">{formatCurrency(l.rata_mensile)}</td>
                    <td className="px-4 py-3 text-right font-medium text-gray-900">{formatCurrency(l.debito_residuo)}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => openEdit(l)}
                          className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700"
                          title="Modifica"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(l.id)}
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
          icon={<Banknote className="h-12 w-12" />}
          title="Nessun finanziamento registrato"
          description="Aggiungi i tuoi mutui e prestiti per monitorare il debito complessivo."
          action={
            <button
              onClick={openCreate}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" /> Aggiungi finanziamento
            </button>
          }
        />
      )}
    </div>
  )
}
