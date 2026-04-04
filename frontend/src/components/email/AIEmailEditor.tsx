import { useState } from 'react'
import { useGenerateEmail, useRefineEmail, useCreateEmailTemplate } from '../../api/hooks'
import GrapesEditor from './GrapesEditor'
import { Sparkles, RefreshCw, Save, Send } from 'lucide-react'

const TONES = [
  { value: 'professionale', label: 'Professionale' },
  { value: 'amichevole', label: 'Amichevole' },
  { value: 'formale', label: 'Formale' },
]

const VARIABLES = ['nome', 'azienda', 'deal_name', 'deal_value', 'commerciale']

interface AIEmailEditorProps {
  contactName?: string
  dealName?: string
  onSend?: (subject: string, htmlBody: string) => void
  // Edit existing template
  editTemplateId?: string
  editSubject?: string
  editHtmlBody?: string
  editCategory?: string
  editName?: string
}

export default function AIEmailEditor({ contactName, dealName, onSend, editTemplateId, editSubject, editHtmlBody, editCategory, editName }: AIEmailEditorProps) {
  const generate = useGenerateEmail()
  const refine = useRefineEmail()
  const saveTemplate = useCreateEmailTemplate()

  const [prompt, setPrompt] = useState('')
  const [tone, setTone] = useState('professionale')
  const [subject, setSubject] = useState(editSubject || '')
  const [htmlBody, setHtmlBody] = useState(editHtmlBody || '')
  const [editorHtml, setEditorHtml] = useState(editHtmlBody || '')
  const [variables, setVariables] = useState<string[]>([])
  const [showSave, setShowSave] = useState(false)
  const [saveName, setSaveName] = useState(editName || '')
  const [saveCategory, setSaveCategory] = useState(editCategory || 'followup')
  const [refinePrompt, setRefinePrompt] = useState('')

  const handleGenerate = async () => {
    const result = await generate.mutateAsync({
      prompt,
      tone,
      contact_name: contactName || '',
      deal_name: dealName || '',
    })
    setSubject(result.subject)
    setHtmlBody(result.html_body)
    setEditorHtml(result.html_body)
    setVariables(result.variables_detected || [])
  }

  const handleRefine = async () => {
    if (!refinePrompt) return
    const currentHtml = editorHtml || htmlBody
    const result = await refine.mutateAsync({
      html_body: currentHtml,
      instruction: refinePrompt,
    })
    setSubject(result.subject)
    setHtmlBody(result.html_body)
    setEditorHtml(result.html_body)
    setVariables(result.variables_detected || [])
    setRefinePrompt('')
  }

  const handleSave = async () => {
    if (!saveName) return
    const finalHtml = editorHtml || htmlBody
    await saveTemplate.mutateAsync({
      name: saveName,
      subject,
      html_body: finalHtml,
      category: saveCategory,
      variables: VARIABLES.filter(v => finalHtml.includes(`{{${v}}}`)),
    })
    setShowSave(false)
    setSaveName('')
  }

  const insertVariable = (varKey: string) => {
    navigator.clipboard.writeText(`{{${varKey}}}`)
  }

  const hasResult = !!htmlBody

  return (
    <div className="space-y-4">
      {/* ── AI Generation Bar ── */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex-1 min-w-64">
          <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)}
            placeholder="Descrivi l'email: es. Crea email per presentare i servizi di consulenza SAP..."
            rows={2} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-purple-500 focus:ring-1 focus:ring-purple-500 focus:outline-none resize-none" />
        </div>
        <div className="flex items-end gap-2">
          <select value={tone} onChange={(e) => setTone(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm h-10">
            {TONES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
          <button onClick={handleGenerate} disabled={generate.isPending || prompt.length < 10}
            className="inline-flex items-center gap-2 rounded-lg bg-purple-600 px-5 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50 h-10 shrink-0">
            {generate.isPending ? <><RefreshCw className="h-4 w-4 animate-spin" /> Genero...</> : <><Sparkles className="h-4 w-4" /> {hasResult ? 'Rigenera' : 'Genera con AI'}</>}
          </button>
        </div>
      </div>

      {hasResult && (
        <>
          {/* ── Subject + Variables + Actions ── */}
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 flex-1 min-w-48">
              <span className="text-xs font-medium text-gray-400 shrink-0">Oggetto:</span>
              <input value={subject} onChange={(e) => setSubject(e.target.value)}
                className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium focus:border-purple-500 focus:outline-none" />
            </div>
            <div className="flex gap-1">
              {VARIABLES.map((v) => (
                <button key={v} onClick={() => insertVariable(v)} title={`Copia {{${v}}} — incolla nell'editor`}
                  className={`rounded-md border px-2 py-0.5 text-[10px] font-mono transition-colors ${
                    variables.includes(v) ? 'bg-purple-50 text-purple-700 border-purple-200' : 'bg-gray-50 text-gray-400 border-gray-200 hover:border-purple-200'
                  }`}>
                  {`{{${v}}}`}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <button onClick={() => setShowSave(true)}
                className="inline-flex items-center gap-1 rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50">
                <Save className="h-3 w-3" /> Salva
              </button>
              {onSend && (
                <button onClick={() => onSend(subject, editorHtml || htmlBody)}
                  className="inline-flex items-center gap-1 rounded-lg bg-purple-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-purple-700">
                  <Send className="h-3 w-3" /> Invia
                </button>
              )}
            </div>
          </div>

          {/* ── Visual Editor (GrapesJS) ── */}
          <GrapesEditor
            initialHtml={htmlBody}
            onHtmlChange={setEditorHtml}
            height={550}
          />

          {/* ── Refine via AI Chat ── */}
          <div className="flex gap-2">
            <input value={refinePrompt} onChange={(e) => setRefinePrompt(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleRefine()}
              placeholder="Chiedi una modifica all'AI: es. Aggiungi una sezione con i tempi di consegna..."
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-purple-500 focus:outline-none" />
            <button onClick={handleRefine} disabled={refine.isPending || !refinePrompt}
              className="inline-flex items-center gap-1.5 rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 disabled:opacity-50">
              {refine.isPending ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
              Modifica con AI
            </button>
          </div>

          {/* ── Reset ── */}
          <button onClick={() => { setHtmlBody(''); setEditorHtml(''); setSubject(''); setVariables([]) }}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50">
            <RefreshCw className="h-3.5 w-3.5" /> Ricomincia
          </button>
        </>
      )}

      {/* ── Save Modal ── */}
      {showSave && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/20" onClick={() => setShowSave(false)}>
          <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-semibold text-gray-900">Salva come template</h3>
            <div className="mt-3 space-y-3">
              <input value={saveName} onChange={(e) => setSaveName(e.target.value)}
                placeholder="Nome template *" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              <select value={saveCategory} onChange={(e) => setSaveCategory(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
                <option value="welcome">Benvenuto</option>
                <option value="followup">Follow-up</option>
                <option value="proposal">Proposta</option>
                <option value="reminder">Reminder</option>
                <option value="nurture">Nurture</option>
              </select>
              <div className="flex gap-2">
                <button onClick={handleSave} disabled={!saveName || saveTemplate.isPending}
                  className="flex-1 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">Salva</button>
                <button onClick={() => setShowSave(false)}
                  className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600">Annulla</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
