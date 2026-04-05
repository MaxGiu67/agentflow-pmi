import { useState } from 'react'
import { useOrigins, useCreateOrigin, useUpdateOrigin, useDeleteOrigin } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import { Plus, ToggleLeft, ToggleRight, Trash2 } from 'lucide-react'

export default function OriginsPage() {
  const { data: origins, isLoading } = useOrigins()
  const createOrigin = useCreateOrigin()
  const updateOrigin = useUpdateOrigin()
  const deleteOrigin = useDeleteOrigin()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ code: '', label: '', parent_channel: '' })

  const handleCreate = async () => {
    if (!form.code.trim() || !form.label.trim()) return
    await createOrigin.mutateAsync(form)
    setForm({ code: '', label: '', parent_channel: '' })
    setShowForm(false)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Origini Contatto"
        subtitle="Configura i canali di acquisizione per tracciare da dove arrivano i contatti"
        actions={
          <button onClick={() => setShowForm(true)}
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
              placeholder="Codice (es. linkedin_inmail)" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <input type="text" value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })}
              placeholder="Etichetta (es. InMail LinkedIn)" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <input type="text" value={form.parent_channel} onChange={(e) => setForm({ ...form, parent_channel: e.target.value })}
              placeholder="Canale (digital, social, direct)" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </div>
          <div className="flex gap-2">
            <button onClick={handleCreate} disabled={createOrigin.isPending || !form.code.trim()}
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
                  <td className="px-4 py-3 font-medium">{o.label}</td>
                  <td className="px-4 py-3 text-gray-500">{o.parent_channel || '-'}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => updateOrigin.mutate({ id: o.id, is_active: !o.is_active })}
                      className={`inline-flex items-center gap-1 text-xs font-medium ${o.is_active ? 'text-green-600' : 'text-gray-400'}`}>
                      {o.is_active ? <ToggleRight className="h-4 w-4" /> : <ToggleLeft className="h-4 w-4" />}
                      {o.is_active ? 'Attiva' : 'Disattivata'}
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <button onClick={() => deleteOrigin.mutate(o.id)}
                      className="text-red-400 hover:text-red-600"><Trash2 className="h-4 w-4" /></button>
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
