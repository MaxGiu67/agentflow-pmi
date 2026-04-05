import { useState } from 'react'
import { useActivityTypes, useCreateActivityType, useUpdateActivityType } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import { Plus, ToggleLeft, ToggleRight, Phone } from 'lucide-react'

const CATEGORIES = [
  { value: 'sales', label: 'Sales', color: 'bg-blue-100 text-blue-700' },
  { value: 'marketing', label: 'Marketing', color: 'bg-purple-100 text-purple-700' },
  { value: 'support', label: 'Support', color: 'bg-green-100 text-green-700' },
]

export default function ActivityTypesPage() {
  const { data: types, isLoading } = useActivityTypes()
  const createType = useCreateActivityType()
  const updateType = useUpdateActivityType()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ code: '', label: '', category: 'sales', counts_as_last_contact: false })

  const handleCreate = async () => {
    if (!form.code.trim() || !form.label.trim()) return
    await createType.mutateAsync(form)
    setForm({ code: '', label: '', category: 'sales', counts_as_last_contact: false })
    setShowForm(false)
  }

  const catBadge = (cat: string) => {
    const c = CATEGORIES.find((c) => c.value === cat)
    return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${c?.color || 'bg-gray-100 text-gray-600'}`}>{c?.label || cat}</span>
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Tipi Attivita" subtitle="Definisci i tipi di interazione tracciabili dal team commerciale"
        actions={<button onClick={() => setShowForm(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          <Plus className="h-4 w-4" /> Nuovo Tipo</button>} />

      {showForm && (
        <div className="rounded-xl border border-blue-200 bg-blue-50/30 p-6 space-y-3">
          <div className="grid gap-3 sm:grid-cols-2">
            <input type="text" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })}
              placeholder="Codice (es. inmail_linkedin)" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <input type="text" value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })}
              placeholder="Etichetta (es. InMail LinkedIn)" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <input type="checkbox" checked={form.counts_as_last_contact}
                onChange={(e) => setForm({ ...form, counts_as_last_contact: e.target.checked })}
                className="rounded border-gray-300" />
              Conta come ultimo contatto
            </label>
          </div>
          <div className="flex gap-2">
            <button onClick={handleCreate} disabled={createType.isPending || !form.code.trim()}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">Crea</button>
            <button onClick={() => setShowForm(false)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600">Annulla</button>
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
                <th className="px-4 py-3">Categoria</th>
                <th className="px-4 py-3">Ultimo Contatto</th>
                <th className="px-4 py-3">Stato</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {types?.map((t: any) => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-mono text-xs">{t.code}</td>
                  <td className="px-4 py-3 font-medium">{t.label}</td>
                  <td className="px-4 py-3">{catBadge(t.category)}</td>
                  <td className="px-4 py-3">{t.counts_as_last_contact ? <Phone className="h-4 w-4 text-green-500" /> : <span className="text-gray-300">-</span>}</td>
                  <td className="px-4 py-3">
                    <button onClick={() => updateType.mutate({ id: t.id, is_active: !t.is_active })}
                      className={`inline-flex items-center gap-1 text-xs font-medium ${t.is_active ? 'text-green-600' : 'text-gray-400'}`}>
                      {t.is_active ? <ToggleRight className="h-4 w-4" /> : <ToggleLeft className="h-4 w-4" />}
                      {t.is_active ? 'Attivo' : 'Disattivato'}
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
