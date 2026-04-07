import { useState } from 'react'
import {
  usePipelineTemplates, useCreatePipelineTemplate, useUpdatePipelineTemplate,
  useDeletePipelineTemplate, useAddTemplateStage, useUpdateTemplateStage, useDeleteTemplateStage,
} from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import { GitBranch, CheckCircle, XCircle, Clock, SkipForward, Plus, Pencil, Trash2, X, Check } from 'lucide-react'

const TYPE_COLORS: Record<string, string> = {
  services: 'bg-blue-100 text-blue-700',
  product: 'bg-purple-100 text-purple-700',
  custom: 'bg-gray-100 text-gray-700',
}

export default function PipelineTemplatesPage() {
  const { data: templates, isLoading } = usePipelineTemplates()
  const createTemplate = useCreatePipelineTemplate()
  const updateTemplate = useUpdatePipelineTemplate()
  const deleteTemplate = useDeletePipelineTemplate()
  const addStage = useAddTemplateStage()
  const updateStage = useUpdateTemplateStage()
  const deleteStage = useDeleteTemplateStage()

  const [showCreate, setShowCreate] = useState(false)
  const [createForm, setCreateForm] = useState({ name: '', code: '', pipeline_type: 'services', description: '' })
  const [editTemplateId, setEditTemplateId] = useState<string | null>(null)
  const [editTemplateForm, setEditTemplateForm] = useState({ name: '', description: '' })
  const [addStageTemplateId, setAddStageTemplateId] = useState<string | null>(null)
  const [stageForm, setStageForm] = useState({ name: '', code: '', sequence: '', sla_days: '7', is_won: false, is_lost: false, is_optional: false })
  const [editStageId, setEditStageId] = useState<string | null>(null)
  const [editStageForm, setEditStageForm] = useState({ name: '', sequence: '', sla_days: '', is_won: false, is_lost: false, is_optional: false })

  if (isLoading) return <LoadingSpinner />

  return (
    <div className="space-y-6">
      <PageHeader
        title="Pipeline Templates"
        subtitle="Template di processo vendita — il prodotto scelto attiva la pipeline corretta"
        actions={
          <button onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700">
            <Plus className="h-4 w-4" /> Nuovo Template
          </button>
        }
      />

      {/* Create template form */}
      {showCreate && (
        <div className="rounded-xl border border-indigo-200 bg-indigo-50/30 p-6 space-y-3">
          <h3 className="font-medium text-gray-900">Nuovo Pipeline Template</h3>
          <div className="grid gap-3 sm:grid-cols-4">
            <input type="text" value={createForm.name} onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
              placeholder="Nome template *" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <input type="text" value={createForm.code} onChange={(e) => setCreateForm({ ...createForm, code: e.target.value })}
              placeholder="Codice (es. vendita_diretta) *" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <select value={createForm.pipeline_type} onChange={(e) => setCreateForm({ ...createForm, pipeline_type: e.target.value })}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              <option value="services">Services</option>
              <option value="product">Product</option>
              <option value="custom">Custom</option>
            </select>
            <input type="text" value={createForm.description} onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
              placeholder="Descrizione" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </div>
          <div className="flex gap-2">
            <button onClick={async () => {
              if (!createForm.name.trim() || !createForm.code.trim()) return
              await createTemplate.mutateAsync(createForm)
              setCreateForm({ name: '', code: '', pipeline_type: 'services', description: '' })
              setShowCreate(false)
            }} disabled={createTemplate.isPending || !createForm.name.trim() || !createForm.code.trim()}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">Crea</button>
            <button onClick={() => setShowCreate(false)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600">Annulla</button>
          </div>
        </div>
      )}

      {/* Templates list */}
      <div className="space-y-6">
        {templates?.map((tmpl: any) => (
          <div key={tmpl.id} className="rounded-xl border border-gray-200 bg-white p-6">
            {/* Template header */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-100">
                  <GitBranch className="h-5 w-5 text-indigo-600" />
                </div>
                {editTemplateId === tmpl.id ? (
                  <div className="flex items-center gap-2">
                    <input type="text" value={editTemplateForm.name} onChange={(e) => setEditTemplateForm({ ...editTemplateForm, name: e.target.value })}
                      className="rounded-lg border border-gray-300 px-2 py-1 text-sm font-semibold" />
                    <input type="text" value={editTemplateForm.description} onChange={(e) => setEditTemplateForm({ ...editTemplateForm, description: e.target.value })}
                      placeholder="Descrizione" className="rounded-lg border border-gray-300 px-2 py-1 text-xs" />
                    <button onClick={async () => {
                      await updateTemplate.mutateAsync({ id: tmpl.id, ...editTemplateForm })
                      setEditTemplateId(null)
                    }} className="text-green-600"><Check className="h-4 w-4" /></button>
                    <button onClick={() => setEditTemplateId(null)} className="text-gray-400"><X className="h-4 w-4" /></button>
                  </div>
                ) : (
                  <div>
                    <h3 className="font-semibold text-gray-900">{tmpl.name}</h3>
                    <p className="text-xs text-gray-500">{tmpl.description}</p>
                  </div>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span className={`rounded-full px-3 py-1 text-xs font-medium ${TYPE_COLORS[tmpl.pipeline_type] || TYPE_COLORS.custom}`}>
                  {tmpl.pipeline_type}
                </span>
                <span className="text-xs text-gray-400">{tmpl.stage_count} stadi</span>
                <button onClick={() => { setEditTemplateId(tmpl.id); setEditTemplateForm({ name: tmpl.name, description: tmpl.description || '' }) }}
                  className="text-gray-400 hover:text-blue-600"><Pencil className="h-3.5 w-3.5" /></button>
                <button onClick={async () => { if (confirm(`Eliminare "${tmpl.name}" e tutti i suoi stadi?`)) await deleteTemplate.mutateAsync(tmpl.id) }}
                  className="text-gray-400 hover:text-red-600"><Trash2 className="h-3.5 w-3.5" /></button>
              </div>
            </div>

            {/* Pipeline stages visual */}
            <div className="flex items-center gap-1 overflow-x-auto pb-2">
              {tmpl.stages?.map((stage: any, i: number) => (
                <div key={stage.id} className="flex items-center">
                  {editStageId === stage.id ? (
                    <div className="flex-shrink-0 rounded-lg border-2 border-blue-300 bg-blue-50 px-2 py-1 min-w-[120px] space-y-1">
                      <input type="text" value={editStageForm.name} onChange={(e) => setEditStageForm({ ...editStageForm, name: e.target.value })}
                        className="w-full rounded border border-gray-300 px-1 py-0.5 text-xs" />
                      <div className="flex gap-1">
                        <input type="number" value={editStageForm.sequence} onChange={(e) => setEditStageForm({ ...editStageForm, sequence: e.target.value })}
                          placeholder="Seq" className="w-12 rounded border border-gray-300 px-1 py-0.5 text-[10px]" />
                        <input type="number" value={editStageForm.sla_days} onChange={(e) => setEditStageForm({ ...editStageForm, sla_days: e.target.value })}
                          placeholder="SLA" className="w-12 rounded border border-gray-300 px-1 py-0.5 text-[10px]" />
                      </div>
                      <div className="flex gap-1 text-[10px]">
                        <label className="flex items-center gap-0.5"><input type="checkbox" checked={editStageForm.is_won} onChange={(e) => setEditStageForm({ ...editStageForm, is_won: e.target.checked })} /> Won</label>
                        <label className="flex items-center gap-0.5"><input type="checkbox" checked={editStageForm.is_lost} onChange={(e) => setEditStageForm({ ...editStageForm, is_lost: e.target.checked })} /> Lost</label>
                        <label className="flex items-center gap-0.5"><input type="checkbox" checked={editStageForm.is_optional} onChange={(e) => setEditStageForm({ ...editStageForm, is_optional: e.target.checked })} /> Opz</label>
                      </div>
                      <div className="flex gap-1">
                        <button onClick={async () => {
                          await updateStage.mutateAsync({ id: stage.id, name: editStageForm.name, sequence: parseInt(editStageForm.sequence) || 0, sla_days: parseInt(editStageForm.sla_days) || 0, is_won: editStageForm.is_won, is_lost: editStageForm.is_lost, is_optional: editStageForm.is_optional })
                          setEditStageId(null)
                        }} className="text-green-600"><Check className="h-3 w-3" /></button>
                        <button onClick={() => setEditStageId(null)} className="text-gray-400"><X className="h-3 w-3" /></button>
                        <button onClick={async () => { if (confirm(`Eliminare "${stage.name}"?`)) { await deleteStage.mutateAsync(stage.id); setEditStageId(null) } }}
                          className="text-red-500"><Trash2 className="h-3 w-3" /></button>
                      </div>
                    </div>
                  ) : (
                    <div onClick={() => { setEditStageId(stage.id); setEditStageForm({ name: stage.name, sequence: String(stage.sequence), sla_days: String(stage.sla_days), is_won: stage.is_won, is_lost: stage.is_lost, is_optional: stage.is_optional }) }}
                      className={`flex-shrink-0 rounded-lg border px-3 py-2 text-center min-w-[100px] cursor-pointer hover:ring-2 hover:ring-blue-200 ${
                        stage.is_won ? 'border-green-300 bg-green-50' :
                        stage.is_lost ? 'border-red-300 bg-red-50' :
                        stage.is_optional ? 'border-dashed border-gray-300 bg-gray-50' :
                        'border-gray-200 bg-white'
                      }`}>
                      <p className="text-xs font-medium text-gray-900">{stage.name}</p>
                      <div className="flex items-center justify-center gap-1 mt-1">
                        {stage.is_won && <CheckCircle className="h-3 w-3 text-green-500" />}
                        {stage.is_lost && <XCircle className="h-3 w-3 text-red-500" />}
                        {stage.is_optional && <SkipForward className="h-3 w-3 text-gray-400" />}
                        {!stage.is_won && !stage.is_lost && stage.sla_days > 0 && (
                          <span className="text-[10px] text-gray-400 flex items-center gap-0.5">
                            <Clock className="h-2.5 w-2.5" />{stage.sla_days}gg
                          </span>
                        )}
                      </div>
                      {stage.required_fields?.length > 0 && (
                        <p className="text-[10px] text-gray-400 mt-0.5 truncate max-w-[90px]">
                          {stage.required_fields.join(', ')}
                        </p>
                      )}
                    </div>
                  )}
                  {i < tmpl.stages.length - 1 && !tmpl.stages[i + 1]?.is_lost && editStageId !== stage.id && (
                    <span className="mx-1 text-gray-300">→</span>
                  )}
                </div>
              ))}

              {/* Add stage button */}
              {addStageTemplateId === tmpl.id ? (
                <div className="flex-shrink-0 rounded-lg border-2 border-dashed border-indigo-300 bg-indigo-50 px-2 py-1 min-w-[140px] space-y-1">
                  <input type="text" value={stageForm.name} onChange={(e) => setStageForm({ ...stageForm, name: e.target.value })}
                    placeholder="Nome stadio *" className="w-full rounded border border-gray-300 px-1 py-0.5 text-xs" />
                  <div className="flex gap-1">
                    <input type="text" value={stageForm.code} onChange={(e) => setStageForm({ ...stageForm, code: e.target.value })}
                      placeholder="Codice" className="w-16 rounded border border-gray-300 px-1 py-0.5 text-[10px]" />
                    <input type="number" value={stageForm.sequence} onChange={(e) => setStageForm({ ...stageForm, sequence: e.target.value })}
                      placeholder="Seq" className="w-12 rounded border border-gray-300 px-1 py-0.5 text-[10px]" />
                    <input type="number" value={stageForm.sla_days} onChange={(e) => setStageForm({ ...stageForm, sla_days: e.target.value })}
                      placeholder="SLA gg" className="w-12 rounded border border-gray-300 px-1 py-0.5 text-[10px]" />
                  </div>
                  <div className="flex gap-1 text-[10px]">
                    <label className="flex items-center gap-0.5"><input type="checkbox" checked={stageForm.is_won} onChange={(e) => setStageForm({ ...stageForm, is_won: e.target.checked })} /> Won</label>
                    <label className="flex items-center gap-0.5"><input type="checkbox" checked={stageForm.is_lost} onChange={(e) => setStageForm({ ...stageForm, is_lost: e.target.checked })} /> Lost</label>
                    <label className="flex items-center gap-0.5"><input type="checkbox" checked={stageForm.is_optional} onChange={(e) => setStageForm({ ...stageForm, is_optional: e.target.checked })} /> Opz</label>
                  </div>
                  <div className="flex gap-1">
                    <button onClick={async () => {
                      if (!stageForm.name.trim()) return
                      await addStage.mutateAsync({ templateId: tmpl.id, ...stageForm, sequence: parseInt(stageForm.sequence) || (tmpl.stages.length + 1) * 10, sla_days: parseInt(stageForm.sla_days) || 7 })
                      setStageForm({ name: '', code: '', sequence: '', sla_days: '7', is_won: false, is_lost: false, is_optional: false })
                      setAddStageTemplateId(null)
                    }} disabled={!stageForm.name.trim()} className="text-green-600 disabled:opacity-50"><Check className="h-3 w-3" /></button>
                    <button onClick={() => setAddStageTemplateId(null)} className="text-gray-400"><X className="h-3 w-3" /></button>
                  </div>
                </div>
              ) : (
                <button onClick={() => setAddStageTemplateId(tmpl.id)}
                  className="flex-shrink-0 rounded-lg border-2 border-dashed border-gray-300 px-3 py-2 text-center min-w-[80px] text-gray-400 hover:border-indigo-300 hover:text-indigo-600">
                  <Plus className="h-4 w-4 mx-auto" />
                  <p className="text-[10px] mt-0.5">Stadio</p>
                </button>
              )}
            </div>
            <p className="text-[10px] text-gray-400 mt-2">Clicca su uno stadio per modificarlo</p>
          </div>
        ))}
      </div>
    </div>
  )
}
