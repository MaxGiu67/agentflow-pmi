import { useState } from 'react'
import { useResources, useCreateResource, useUpdateResource, useAddResourceSkill, useResourceBench } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'
import { Users, Plus, Search, Star, Calendar, AlertTriangle } from 'lucide-react'

const SENIORITY_COLORS: Record<string, string> = {
  junior: 'bg-green-100 text-green-700',
  mid: 'bg-blue-100 text-blue-700',
  senior: 'bg-purple-100 text-purple-700',
  lead: 'bg-amber-100 text-amber-700',
}

export default function ResourcesPage() {
  const [skillFilter, setSkillFilter] = useState('')
  const [seniorityFilter, setSeniorityFilter] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [showBench, setShowBench] = useState(false)
  const [form, setForm] = useState({ name: '', seniority: 'mid', daily_cost: '', suggested_daily_rate: '' })
  const [skillForm, setSkillForm] = useState({ resourceId: '', skill_name: '', skill_level: 3 })

  const { data: resources, isLoading } = useResources(skillFilter, seniorityFilter)
  const { data: bench } = useResourceBench()
  const createResource = useCreateResource()
  const addSkill = useAddResourceSkill()

  const handleCreate = async () => {
    if (!form.name.trim()) return
    await createResource.mutateAsync({
      name: form.name,
      seniority: form.seniority,
      daily_cost: parseFloat(form.daily_cost) || 0,
      suggested_daily_rate: parseFloat(form.suggested_daily_rate) || 0,
    })
    setForm({ name: '', seniority: 'mid', daily_cost: '', suggested_daily_rate: '' })
    setShowForm(false)
  }

  const handleAddSkill = async () => {
    if (!skillForm.resourceId || !skillForm.skill_name.trim()) return
    await addSkill.mutateAsync({
      resourceId: skillForm.resourceId,
      skill_name: skillForm.skill_name,
      skill_level: skillForm.skill_level,
    })
    setSkillForm({ ...skillForm, skill_name: '', skill_level: 3 })
  }

  if (isLoading) return <LoadingSpinner />

  return (
    <div className="space-y-6">
      <PageHeader
        title="Risorse Interne"
        subtitle="Consulenti, sviluppatori e profili disponibili per matching T&M"
        actions={
          <div className="flex gap-2">
            <button onClick={() => setShowBench(!showBench)}
              className="inline-flex items-center gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-700 hover:bg-amber-100">
              <AlertTriangle className="h-4 w-4" /> Bench ({bench?.length || 0})
            </button>
            <button onClick={() => setShowForm(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
              <Plus className="h-4 w-4" /> Nuova Risorsa
            </button>
          </div>
        }
      />

      {/* Filters */}
      <div className="flex gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input type="text" value={skillFilter} onChange={(e) => setSkillFilter(e.target.value)}
            placeholder="Filtra per skill (es. Java)"
            className="w-full rounded-lg border border-gray-300 pl-10 pr-4 py-2 text-sm" />
        </div>
        <select value={seniorityFilter} onChange={(e) => setSeniorityFilter(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
          <option value="">Tutte le seniority</option>
          <option value="junior">Junior</option>
          <option value="mid">Mid</option>
          <option value="senior">Senior</option>
          <option value="lead">Lead</option>
        </select>
      </div>

      {/* Bench alert */}
      {showBench && bench?.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-4 space-y-2">
          <h3 className="font-medium text-amber-800">Risorse in scadenza (prossimi 30gg)</h3>
          {bench.map((r: any) => (
            <div key={r.id} className="flex items-center justify-between rounded-lg bg-white border border-amber-100 p-3">
              <div>
                <span className="font-medium text-gray-900">{r.name}</span>
                <span className={`ml-2 rounded px-2 py-0.5 text-xs font-medium ${SENIORITY_COLORS[r.seniority]}`}>{r.seniority}</span>
              </div>
              <div className="text-xs text-amber-600">
                <Calendar className="inline h-3 w-3 mr-1" />
                Disponibile dal {r.available_from}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* New resource form */}
      {showForm && (
        <div className="rounded-xl border border-blue-200 bg-blue-50/30 p-5 space-y-3">
          <h3 className="font-medium text-gray-900">Nuova Risorsa</h3>
          <div className="grid gap-3 sm:grid-cols-4">
            <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Nome e cognome *" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <select value={form.seniority} onChange={(e) => setForm({ ...form, seniority: e.target.value })}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              <option value="junior">Junior</option>
              <option value="mid">Mid</option>
              <option value="senior">Senior</option>
              <option value="lead">Lead</option>
            </select>
            <input type="number" value={form.daily_cost} onChange={(e) => setForm({ ...form, daily_cost: e.target.value })}
              placeholder="Costo/gg EUR" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <input type="number" value={form.suggested_daily_rate} onChange={(e) => setForm({ ...form, suggested_daily_rate: e.target.value })}
              placeholder="Tariffa suggerita/gg" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </div>
          <div className="flex gap-2">
            <button onClick={handleCreate} disabled={!form.name.trim() || createResource.isPending}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
              {createResource.isPending ? 'Creazione...' : 'Crea risorsa'}
            </button>
            <button onClick={() => setShowForm(false)}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600">Annulla</button>
          </div>
        </div>
      )}

      {/* Resources grid */}
      {!resources?.length ? (
        <EmptyState icon={<Users className="h-12 w-12" />} title="Nessuna risorsa"
          description="Aggiungi le risorse interne per il matching con le richieste dei clienti." />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {resources.map((r: any) => (
            <div key={r.id} className="rounded-xl border border-gray-200 bg-white p-5 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <p className="font-semibold text-gray-900">{r.name}</p>
                  <span className={`inline-block mt-1 rounded px-2 py-0.5 text-xs font-medium ${SENIORITY_COLORS[r.seniority]}`}>
                    {r.seniority}
                  </span>
                </div>
                {r.available_from && (
                  <span className="text-xs text-gray-400">
                    <Calendar className="inline h-3 w-3 mr-1" />
                    {r.available_from}
                  </span>
                )}
              </div>

              {/* Skills */}
              <div className="flex flex-wrap gap-1 mb-3">
                {r.skills?.map((s: any) => (
                  <span key={s.id} className="inline-flex items-center gap-1 rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-700">
                    {s.skill_name}
                    <span className="text-gray-400">{'*'.repeat(s.skill_level)}</span>
                  </span>
                ))}
              </div>

              {/* Costs */}
              <div className="flex gap-4 text-xs text-gray-500">
                {r.daily_cost > 0 && <span>Costo: {r.daily_cost} EUR/gg</span>}
                {r.suggested_daily_rate > 0 && <span>Tariffa: {r.suggested_daily_rate} EUR/gg</span>}
              </div>

              {/* Add skill inline */}
              <div className="mt-3 flex gap-1">
                <input type="text" value={skillForm.resourceId === r.id ? skillForm.skill_name : ''}
                  onFocus={() => setSkillForm({ ...skillForm, resourceId: r.id })}
                  onChange={(e) => setSkillForm({ ...skillForm, resourceId: r.id, skill_name: e.target.value })}
                  placeholder="+ Aggiungi skill"
                  className="flex-1 rounded border border-gray-200 px-2 py-1 text-xs" />
                {skillForm.resourceId === r.id && skillForm.skill_name && (
                  <button onClick={handleAddSkill}
                    className="rounded bg-blue-600 px-2 py-1 text-xs text-white">+</button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
