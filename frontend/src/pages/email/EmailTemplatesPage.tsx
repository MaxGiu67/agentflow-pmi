import { useState } from 'react'
import { useEmailTemplates, useCreateEmailTemplate, useUpdateEmailTemplate, usePreviewTemplate } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import PageMeta from '../../components/ui/PageMeta'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'
import Badge from '../../components/ui/Badge'
import AIEmailEditor from '../../components/email/AIEmailEditor'
import { Mail, Plus, Eye, Edit, X, Sparkles } from 'lucide-react'

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

  const [mode, setMode] = useState<'list' | 'manual' | 'ai'>('list')
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
    setMode('list'); setEditId(null); setForm({ name: '', subject: '', html_body: '', category: 'followup', variables: '' })
  }

  const handleEdit = (tpl: any) => {
    setForm({ name: tpl.name, subject: tpl.subject, html_body: tpl.html_body, category: tpl.category, variables: (tpl.variables || []).join(', ') })
    setEditId(tpl.id); setMode('ai')
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
      <PageHeader title="Email Templates" subtitle="Crea e gestisci i template per le comunicazioni"
        actions={
          mode === 'list' ? (
            <div className="flex gap-2">
              <button onClick={() => { setMode('ai'); setEditId(null) }}
                className="inline-flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700">
                <Sparkles className="h-4 w-4" /> Crea con AI
              </button>
              <button onClick={() => { setMode('manual'); setEditId(null); setForm({ name: '', subject: '', html_body: '', category: 'followup', variables: '' }) }}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50">
                <Plus className="h-4 w-4" /> Manuale
              </button>
            </div>
          ) : (
            <button onClick={() => { setMode('list'); setEditId(null); setPreview(null) }}
              className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700">
              <X className="h-4 w-4" /> Torna alla lista
            </button>
          )
        }
      />

      {/* ─── AI Builder Mode ─── */}
      {mode === 'ai' && (
        <div className="rounded-2xl border border-purple-200 bg-purple-50/20 p-5">
          <div className="flex items-center gap-2 mb-4">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-600">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900">Crea template con AI</p>
              <p className="text-xs text-gray-500">Descrivi l'email e l'AI la genera. Poi personalizzala e salva.</p>
            </div>
          </div>
          <AIEmailEditor
            editTemplateId={editId || undefined}
            editSubject={editId ? form.subject : undefined}
            editHtmlBody={editId ? form.html_body : undefined}
            editCategory={editId ? form.category : undefined}
            editName={editId ? form.name : undefined}
          />
        </div>
      )}

      {/* ─── Manual Form Mode ─── */}
      {mode === 'manual' && (
        <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-medium text-gray-900">{editId ? 'Modifica template' : 'Nuovo template manuale'}</h3>
            <button onClick={() => setMode('ai')}
              className="inline-flex items-center gap-1.5 rounded-lg bg-purple-100 px-3 py-1.5 text-xs font-medium text-purple-700 hover:bg-purple-200">
              <Sparkles className="h-3.5 w-3.5" /> Passa a Editor AI
            </button>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Nome template *" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              {CATEGORIES.map((c) => <option key={c} value={c}>{CAT_LABELS[c]}</option>)}
            </select>
          </div>
          <input value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} placeholder="Oggetto (con variabili {{nome}})" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />

          {/* Variable insertion toolbar */}
          <div className="flex flex-wrap items-center gap-1.5 rounded-lg bg-gray-50 px-3 py-2 border border-gray-200">
            <span className="text-[10px] font-semibold uppercase text-gray-400 mr-1">Inserisci variabile:</span>
            {['nome', 'azienda', 'deal_name', 'deal_value', 'email'].map((v) => (
              <button key={v} onClick={() => setForm({ ...form, html_body: form.html_body + `{{${v}}}` })}
                className="rounded bg-white px-2 py-0.5 text-xs font-mono text-purple-600 border border-purple-200 hover:bg-purple-50">
                {`{{${v}}}`}
              </button>
            ))}
          </div>

          <textarea value={form.html_body} onChange={(e) => setForm({ ...form, html_body: e.target.value })}
            placeholder="Corpo HTML (con variabili {{nome}}, {{azienda}}...)"
            rows={12} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono text-xs" />

          {/* Live preview */}
          {form.html_body && (
            <div className="rounded-lg border border-gray-200 bg-white p-4">
              <p className="text-[10px] font-semibold uppercase text-gray-400 mb-2">Anteprima</p>
              <div className="prose prose-sm max-w-none" dangerouslySetInnerHTML={{ __html: form.html_body }} />
            </div>
          )}

          <input value={form.variables} onChange={(e) => setForm({ ...form, variables: e.target.value })} placeholder="Variabili (separate da virgola): nome, azienda, deal_name" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          <div className="flex gap-2">
            <button onClick={handleSave} disabled={createTpl.isPending || updateTpl.isPending || !form.name}
              className="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50">
              {editId ? 'Salva modifiche' : 'Crea'}
            </button>
            <button onClick={() => { setMode('list'); setEditId(null) }} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600">Annulla</button>
          </div>
        </div>
      )}

      {/* ─── List Mode ─── */}
      {mode === 'list' && (
        <>
          {/* Category filter */}
          <div className="flex flex-wrap gap-2">
            <button onClick={() => setCatFilter('')} className={`rounded-lg px-3 py-1.5 text-xs font-medium ${!catFilter ? 'bg-purple-600 text-white' : 'bg-gray-100 text-gray-600'}`}>Tutti</button>
            {CATEGORIES.map((c) => (
              <button key={c} onClick={() => setCatFilter(c)} className={`rounded-lg px-3 py-1.5 text-xs font-medium capitalize ${catFilter === c ? 'bg-purple-600 text-white' : 'bg-gray-100 text-gray-600'}`}>
                {CAT_LABELS[c] || c}
              </button>
            ))}
          </div>

          {/* Preview */}
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
            <EmptyState icon={<Mail className="h-12 w-12" />} title="Nessun template"
              description="Crea il primo template con l'AI o manualmente." />
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
                    <button onClick={() => handlePreview(tpl)} className="inline-flex items-center gap-1 text-xs text-purple-600 hover:underline"><Eye className="h-3 w-3" /> Preview</button>
                    <button onClick={() => handleEdit(tpl)} className="inline-flex items-center gap-1 text-xs text-gray-500 hover:underline"><Edit className="h-3 w-3" /> Modifica</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
