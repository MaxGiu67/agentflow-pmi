import { useState } from 'react'
import { useOrigins, useCreateOrigin, useUpdateOrigin, useDeleteOrigin } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import { Plus, ToggleLeft, ToggleRight, Trash2, Pencil, Check, X } from 'lucide-react'

export default function OriginsPage() {
  const { data: origins, isLoading } = useOrigins()
  const createOrigin = useCreateOrigin()
  const updateOrigin = useUpdateOrigin()
  const deleteOrigin = useDeleteOrigin()
  const [showForm, setShowForm] = useState(false)
  const [editId, setEditId] = useState<string | null>(null)
  const [form, setForm] = useState({ code: '', label: '', parent_channel: '' })
  const [editForm, setEditForm] = useState({ label: '', parent_channel: '' })

  const handleCreate = async () => {
    if (!form.code.trim() || !form.label.trim()) return
    await createOrigin.mutateAsync(form)
    setForm({ code: '', label: '', parent_channel: '' })
    setShowForm(false)
  }

  const startEdit = (o: any) => {
    setEditId(o.id)
    setEditForm({ label: o.label || '', parent_channel: o.parent_channel || '' })
  }

  const handleSaveEdit = async (id: string) => {
    await updateOrigin.mutateAsync({ id, label: editForm.label, })
    setEditId(null)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Origini Contatto"
        subtitle="Configura i canali di acquisizione per tracciare da dove arrivano i contatti"
        actions={
          <button onClick={() => setShowForm(!showForm)}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
            <Plus className="h-4 w-4" /> Nuova Origine
          </button>
        }
      />

      {showForm && (
        <div className="rounded-xl border border-blue-200 bg-blue-50/30 p-6 space-y-3">
          <h3 className="font-medium text-gray-900">Nuova origine</h3>
          <div className="grid gap-3 sm:grid-cols-3">
            <input type="text" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })}
              placeholder="Codice (es. linkedin_inmail) *" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <input type="text" value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })}
              placeholder="Etichetta (es. InMail LinkedIn) *" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <input type="text" value={form.parent_channel} onChange={(e) => setForm({ ...form, parent_channel: e.target.value })}
              placeholder="Canale (digital, social, direct, event)" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </div>
          <div className="flex gap-2">
            <button onClick={handleCreate} disabled={createOrigin.isPending || !form.code.trim() || !form.label.trim()}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
              {createOrigin.isPending ? 'Creazione...' : 'Crea'}
            </button>
            <button onClick={() => setShowForm(false)}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50">Annulla</button>
          </div>
        </div>
      )}

      {isLoading ? <LoadingSpinner /> : (
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs font-semibold uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3">Codice</th>
                <th className="px-4 py-3">Etichetta</th>
                <th className="px-4 py-3">Canale</th>
                <th className="px-4 py-3">Stato</th>
                <th className="px-4 py-3">Azioni</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {origins?.map((o: any) => (
                <tr key={o.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs">{o.code}</td>
                  <td className="px-4 py-3">
                    {editId === o.id ? (
                      <input type="text" value={editForm.label} onChange={(e) => setEditForm({ ...editForm, label: e.target.value })}
                        className="rounded border border-blue-300 px-2 py-1 text-sm" />
                    ) : (
                      <span className="font-medium">{o.label}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500">{o.parent_channel || '-'}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => updateOrigin.mutate({ id: o.id, is_active: !o.is_active })}
                      className={`inline-flex items-center gap-1 text-xs font-medium ${o.is_active ? 'text-green-600' : 'text-gray-400'}`}>
                      {o.is_active ? <ToggleRight className="h-4 w-4" /> : <ToggleLeft className="h-4 w-4" />}
                      {o.is_active ? 'Attiva' : 'Disattivata'}
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      {editId === o.id ? (
                        <>
                          <button onClick={() => handleSaveEdit(o.id)} className="rounded p-1 text-green-600 hover:bg-green-50">
                            <Check className="h-4 w-4" />
                          </button>
                          <button onClick={() => setEditId(null)} className="rounded p-1 text-gray-400 hover:bg-gray-100">
                            <X className="h-4 w-4" />
                          </button>
                        </>
                      ) : (
                        <>
                          <button onClick={() => startEdit(o)} title="Modifica" className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-blue-600">
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                          <button onClick={() => deleteOrigin.mutate(o.id)} title="Elimina" className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600">
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </>
                      )}
                    </div>
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
