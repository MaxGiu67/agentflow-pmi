import { useState } from 'react'
import { useEmailTemplates, useCreateEmailTemplate, useUpdateEmailTemplate, usePreviewTemplate } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import PageMeta from '../../components/ui/PageMeta'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'
import Badge from '../../components/ui/Badge'
import { Mail, Plus, Eye, Edit, X } from 'lucide-react'

const CATEGORIES = ['welcome', 'followup', 'proposal', 'reminder', 'nurture']
const CAT_LABELS: Record<string, string> = {
  welcome: 'Benvenuto', followup: 'Follow-up', proposal: 'Proposta',
  reminder: 'Reminder', nurture: 'Nurture',
}

export default function EmailTemplatesPage() {
  const { data: templates, isLoading } = useEmailTemplates()
  const createTpl = useCreateEmailTemplate()
  const updateTpl = useUpdateEmailTemplate()
  const previewTpl = usePreviewTemplate()

  const [showForm, setShowForm] = useState(false)
  const [editId, setEditId] = useState<string | null>(null)
  const [form, setForm] = useState({ name: '', subject: '', html_body: '', category: 'followup', variables: '' })
  const [preview, setPreview] = useState<{ subject: string; html_body: string } | null>(null)
  const [catFilter, setCatFilter] = useState('')

  const filtered = catFilter ? templates?.filter((t: any) => t.category === catFilter) : templates

  const handleSave = async () => {
    const vars = form.variables.split(',').map((v: string) => v.trim()).filter(Boolean)
    if (editId) {
      await updateTpl.mutateAsync({ id: editId, name: form.name, subject: form.subject, html_body: form.html_body, category: form.category, variables: vars })
    } else {
      await createTpl.mutateAsync({ name: form.name, subject: form.subject, html_body: form.html_body, category: form.category, variables: vars })
    }
    setShowForm(false); setEditId(null); setForm({ name: '', subject: '', html_body: '', category: 'followup', variables: '' })
  }

  const handleEdit = (tpl: any) => {
    setForm({ name: tpl.name, subject: tpl.subject, html_body: tpl.html_body, category: tpl.category, variables: (tpl.variables || []).join(', ') })
    setEditId(tpl.id); setShowForm(true)
  }

  const handlePreview = async (tpl: any) => {
    const params: Record<string, string> = {}
    ;(tpl.variables || []).forEach((v: string) => { params[v] = `[${v}]` })
    const result = await previewTpl.mutateAsync({ id: tpl.id, params })
    setPreview(result)
  }

  return (
    <div className="space-y-4">
      <PageMeta title="Email Templates" />
      <PageHeader title="Email Templates" subtitle="Gestisci i template per le comunicazioni"
        actions={<button onClick={() => { setShowForm(true); setEditId(null); setForm({ name: '', subject: '', html_body: '', category: 'followup', variables: '' }) }}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          <Plus className="h-4 w-4" /> Nuovo template
        </button>}
      />

      {/* Category filter */}
      <div className="flex flex-wrap gap-2">
        <button onClick={() => setCatFilter('')} className={`rounded-lg px-3 py-1.5 text-xs font-medium ${!catFilter ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'}`}>Tutti</button>
        {CATEGORIES.map((c) => (
          <button key={c} onClick={() => setCatFilter(c)} className={`rounded-lg px-3 py-1.5 text-xs font-medium capitalize ${catFilter === c ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600'}`}>
            {CAT_LABELS[c] || c}
          </button>
        ))}
      </div>

      {/* Form */}
      {showForm && (
        <div className="rounded-xl border border-blue-200 bg-blue-50/30 p-4 space-y-3">
          <h3 className="font-medium text-gray-900">{editId ? 'Modifica template' : 'Nuovo template'}</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Nome template *" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              {CATEGORIES.map((c) => <option key={c} value={c}>{CAT_LABELS[c]}</option>)}
            </select>
          </div>
          <input value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} placeholder="Oggetto (con variabili {{nome}})" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          <textarea value={form.html_body} onChange={(e) => setForm({ ...form, html_body: e.target.value })} placeholder="Corpo HTML (con variabili {{nome}}, {{azienda}}...)" rows={6} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono text-xs" />
          <input value={form.variables} onChange={(e) => setForm({ ...form, variables: e.target.value })} placeholder="Variabili (separate da virgola): nome, azienda, deal_name" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          <div className="flex gap-2">
            <button onClick={handleSave} disabled={createTpl.isPending || updateTpl.isPending || !form.name}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
              {editId ? 'Salva modifiche' : 'Crea'}
            </button>
            <button onClick={() => { setShowForm(false); setEditId(null) }} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600">Annulla</button>
          </div>
        </div>
      )}

      {/* Preview modal */}
      {preview && (
        <div className="rounded-xl border border-purple-200 bg-purple-50/30 p-4 space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="font-medium text-gray-900">Preview</h3>
            <button onClick={() => setPreview(null)}><X className="h-4 w-4 text-gray-400" /></button>
          </div>
          <p className="text-sm font-medium text-gray-700">Oggetto: {preview.subject}</p>
          <div className="rounded-lg border border-gray-200 bg-white p-4 text-sm" dangerouslySetInnerHTML={{ __html: preview.html_body }} />
        </div>
      )}

      {/* Template list */}
      {isLoading ? <LoadingSpinner /> : !filtered?.length ? (
        <EmptyState icon={Mail} title="Nessun template" description="Crea il primo template email." />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((tpl: any) => (
            <div key={tpl.id} className="rounded-xl border border-gray-200 bg-white p-4 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between">
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-gray-900 truncate">{tpl.name}</p>
                  <p className="mt-0.5 text-xs text-gray-400 truncate">{tpl.subject}</p>
                </div>
                <Badge variant="info">{CAT_LABELS[tpl.category] || tpl.category}</Badge>
              </div>
              {tpl.variables?.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {tpl.variables.map((v: string) => (
                    <span key={v} className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-mono text-gray-500">{`{{${v}}}`}</span>
                  ))}
                </div>
              )}
              <div className="mt-3 flex gap-2">
                <button onClick={() => handlePreview(tpl)} className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"><Eye className="h-3 w-3" /> Preview</button>
                <button onClick={() => handleEdit(tpl)} className="inline-flex items-center gap-1 text-xs text-gray-500 hover:underline"><Edit className="h-3 w-3" /> Modifica</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
