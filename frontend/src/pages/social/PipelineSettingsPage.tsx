import { useState } from 'react'
import { useSocialPipelineStages } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import { Plus, GripVertical, Pencil, Check, X } from 'lucide-react'
import api from '../../api/client'
import { useQueryClient } from '@tanstack/react-query'

export default function PipelineSettingsPage() {
  const { data: stages, isLoading } = useSocialPipelineStages()
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [editId, setEditId] = useState<string | null>(null)
  const [form, setForm] = useState({ name: '', sequence: '', probability: '', color: '#6B7280', stage_type: 'pipeline' })
  const [editForm, setEditForm] = useState({ name: '', probability: '', color: '' })

  const handleCreate = async () => {
    if (!form.name.trim()) return
    await api.post('/social/pipeline/stages', {
      name: form.name,
      sequence: Number(form.sequence) || 0,
      probability: Number(form.probability) || 0,
      color: form.color,
      stage_type: form.stage_type,
    })
    qc.invalidateQueries({ queryKey: ['social-pipeline-stages'] })
    setForm({ name: '', sequence: '', probability: '', color: '#6B7280', stage_type: 'pipeline' })
    setShowForm(false)
  }

  const handleUpdate = async (id: string) => {
    await api.patch(`/social/pipeline/stages/${id}`, {
      name: editForm.name || undefined,
      probability: editForm.probability ? Number(editForm.probability) : undefined,
      color: editForm.color || undefined,
    })
    qc.invalidateQueries({ queryKey: ['social-pipeline-stages'] })
    setEditId(null)
  }

  const handleToggle = async (id: string, isActive: boolean) => {
    await api.patch(`/social/pipeline/stages/${id}`, { is_active: !isActive })
    qc.invalidateQueries({ queryKey: ['social-pipeline-stages'] })
  }

  const startEdit = (s: any) => {
    setEditId(s.id)
    setEditForm({ name: s.name, probability: String(s.probability || 0), color: s.color || '#6B7280' })
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Stadi Pipeline" subtitle="Configura gli stadi della pipeline CRM, inclusi pre-funnel"
        actions={
          <button onClick={() => setShowForm(!showForm)}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
            <Plus className="h-4 w-4" /> Nuovo Stadio
          </button>
        } />

      {showForm && (
        <div className="rounded-xl border border-blue-200 bg-blue-50/30 p-6 space-y-3">
          <h3 className="font-medium text-gray-900">Nuovo stadio pipeline</h3>
          <div className="grid gap-3 sm:grid-cols-3">
            <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Nome stadio *" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <input type="number" value={form.sequence} onChange={(e) => setForm({ ...form, sequence: e.target.value })}
              placeholder="Sequenza (ordine)" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <input type="number" value={form.probability} onChange={(e) => setForm({ ...form, probability: e.target.value })}
              placeholder="Probabilita % (0-100)" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <select value={form.stage_type} onChange={(e) => setForm({ ...form, stage_type: e.target.value })}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              <option value="pipeline">Pipeline (standard)</option>
              <option value="pre_funnel">Pre-funnel (prima di Nuovo Lead)</option>
            </select>
            <input type="color" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })}
              className="h-10 w-16 rounded-lg border border-gray-300 p-1" />
          </div>
          <div className="flex gap-2">
            <button onClick={handleCreate} disabled={!form.name.trim()}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">Crea</button>
            <button onClick={() => setShowForm(false)}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600">Annulla</button>
          </div>
        </div>
      )}

      {isLoading ? <LoadingSpinner /> : (
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs font-semibold uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3 w-8"></th>
                <th className="px-4 py-3">Seq.</th>
                <th className="px-4 py-3">Nome</th>
                <th className="px-4 py-3">Tipo</th>
                <th className="px-4 py-3">Probabilita</th>
                <th className="px-4 py-3">Colore</th>
                <th className="px-4 py-3">Stato</th>
                <th className="px-4 py-3">Azioni</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {stages?.map((s: any) => (
                <tr key={s.id} className={`hover:bg-gray-50 ${!s.is_active ? 'opacity-40' : ''}`}>
                  <td className="px-4 py-3 text-gray-300"><GripVertical className="h-4 w-4" /></td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{s.sequence}</td>
                  <td className="px-4 py-3">
                    {editId === s.id ? (
                      <input type="text" value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                        className="rounded border border-blue-300 px-2 py-1 text-sm w-full" />
                    ) : (
                      <span className="font-medium text-gray-900">{s.name}</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                      s.stage_type === 'pre_funnel' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'
                    }`}>
                      {s.stage_type === 'pre_funnel' ? 'Pre-funnel' : 'Pipeline'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {editId === s.id ? (
                      <input type="number" value={editForm.probability} onChange={(e) => setEditForm({ ...editForm, probability: e.target.value })}
                        className="rounded border border-blue-300 px-2 py-1 text-sm w-20" />
                    ) : (
                      <span className="text-gray-600">{s.probability}%</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {editId === s.id ? (
                      <input type="color" value={editForm.color} onChange={(e) => setEditForm({ ...editForm, color: e.target.value })}
                        className="h-7 w-10 rounded border p-0.5" />
                    ) : (
                      <div className="h-5 w-5 rounded-full border border-gray-200" style={{ backgroundColor: s.color }} />
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <button onClick={() => handleToggle(s.id, s.is_active)}
                      className={`text-xs font-medium ${s.is_active ? 'text-green-600' : 'text-gray-400'}`}>
                      {s.is_active ? 'Attivo' : 'Disattivato'}
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    {editId === s.id ? (
                      <div className="flex gap-1">
                        <button onClick={() => handleUpdate(s.id)} className="rounded p-1 text-green-600 hover:bg-green-50"><Check className="h-4 w-4" /></button>
                        <button onClick={() => setEditId(null)} className="rounded p-1 text-gray-400 hover:bg-gray-100"><X className="h-4 w-4" /></button>
                      </div>
                    ) : (
                      <button onClick={() => startEdit(s)} className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-blue-600">
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="rounded-lg bg-amber-50 border border-amber-200 p-4 text-sm text-amber-800">
        <strong>Pre-funnel:</strong> Gli stadi pre-funnel (es. Prospect, Contatto Qualificato) appaiono prima di "Nuovo Lead" nella pipeline Kanban.
        Usa una sequenza inferiore al primo stadio pipeline per posizionarli correttamente.
      </div>
    </div>
  )
}
