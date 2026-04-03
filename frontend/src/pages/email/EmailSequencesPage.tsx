import { useState } from 'react'
import { useEmailSequences, useCreateSequence, useEmailTemplates } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import PageMeta from '../../components/ui/PageMeta'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'
import Badge from '../../components/ui/Badge'
import { Zap, Plus } from 'lucide-react'

const TRIGGERS: Record<string, string> = {
  manual: 'Manuale',
  deal_stage_changed: 'Deal cambia stage',
  contact_created: 'Nuovo contatto',
}

export default function EmailSequencesPage() {
  const { data: sequences, isLoading } = useEmailSequences()
  const createSeq = useCreateSequence()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', trigger_event: 'manual' })

  const handleCreate = async () => {
    await createSeq.mutateAsync(form)
    setShowForm(false)
    setForm({ name: '', trigger_event: 'manual' })
  }

  return (
    <div className="space-y-4">
      <PageMeta title="Sequenze Email" />
      <PageHeader title="Sequenze Email" subtitle="Automazione follow-up con condizioni"
        actions={<button onClick={() => setShowForm(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          <Plus className="h-4 w-4" /> Nuova sequenza
        </button>}
      />

      {showForm && (
        <div className="rounded-xl border border-blue-200 bg-blue-50/30 p-4 space-y-3">
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Nome sequenza *" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          <select value={form.trigger_event} onChange={(e) => setForm({ ...form, trigger_event: e.target.value })} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
            {Object.entries(TRIGGERS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <div className="flex gap-2">
            <button onClick={handleCreate} disabled={!form.name} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">Crea</button>
            <button onClick={() => setShowForm(false)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600">Annulla</button>
          </div>
        </div>
      )}

      {isLoading ? <LoadingSpinner /> : !sequences?.length ? (
        <EmptyState icon={Zap} title="Nessuna sequenza" description="Crea la prima sequenza email automatica." />
      ) : (
        <div className="space-y-2">
          {sequences.map((seq: any) => (
            <div key={seq.id} className="rounded-xl border border-gray-200 bg-white p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">{seq.name}</p>
                  <p className="text-xs text-gray-400">Trigger: {TRIGGERS[seq.trigger_event] || seq.trigger_event}</p>
                </div>
                <Badge variant={seq.status === 'active' ? 'success' : seq.status === 'draft' ? 'default' : 'warning'}>{seq.status}</Badge>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
