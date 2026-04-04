import { useState } from 'react'
import { useGenerateEmail, useRefineEmail, useCreateEmailTemplate } from '../../api/hooks'
import { Sparkles, RefreshCw, Save, Code, Eye, Send } from 'lucide-react'

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
  onClose?: () => void
}

export default function AIEmailEditor({ contactName, dealName, onSend, onClose }: AIEmailEditorProps) {
  const [prompt, setPrompt] = useState('')
  const [tone, setTone] = useState('professionale')
  const [subject, setSubject] = useState('')
  const [htmlBody, setHtmlBody] = useState('')
  const [variables, setVariables] = useState<string[]>([])
  const [showHtml, setShowHtml] = useState(false)
  const [showSave, setShowSave] = useState(false)
  const [saveName, setSaveName] = useState('')
  const [saveCategory, setSaveCategory] = useState('followup')
  const [refinePrompt, setRefinePrompt] = useState('')

  const generate = useGenerateEmail()
  const refine = useRefineEmail()
  const saveTemplate = useCreateEmailTemplate()

  const handleGenerate = async () => {
    const result = await generate.mutateAsync({
      prompt,
      tone,
      contact_name: contactName || '',
      deal_name: dealName || '',
    })
    setSubject(result.subject)
    setHtmlBody(result.html_body)
    setVariables(result.variables_detected || [])
  }

  const handleRefine = async () => {
    if (!refinePrompt) return
    const result = await refine.mutateAsync({
      html_body: htmlBody,
      instruction: refinePrompt,
    })
    setSubject(result.subject)
    setHtmlBody(result.html_body)
    setVariables(result.variables_detected || [])
    setRefinePrompt('')
  }

  const handleSave = async () => {
    await saveTemplate.mutateAsync({
      name: saveName,
      subject,
      html_body: htmlBody,
      category: saveCategory,
      variables,
    })
    setShowSave(false)
    setSaveName('')
  }

  const insertVariable = (varName: string) => {
    navigator.clipboard.writeText(`{{${varName}}}`)
  }

  const hasResult = !!htmlBody

  return (
    <div className="space-y-4">
      {/* Prompt input */}
      {!hasResult && (
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Descrivi l'email che vuoi</label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="es. Crea una email per presentare i nostri servizi di consulenza SAP a un nuovo prospect..."
              rows={3}
              className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-purple-500 focus:ring-1 focus:ring-purple-500 focus:outline-none"
            />
          </div>
          <div className="flex items-center gap-3">
            <select value={tone} onChange={(e) => setTone(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              {TONES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
            <button
              onClick={handleGenerate}
              disabled={generate.isPending || prompt.length < 10}
              className="inline-flex items-center gap-2 rounded-lg bg-purple-600 px-5 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50 transition-colors"
            >
              {generate.isPending ? (
                <><RefreshCw className="h-4 w-4 animate-spin" /> Generazione...</>
              ) : (
                <><Sparkles className="h-4 w-4" /> Genera con AI</>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Result */}
      {hasResult && (
        <div className="space-y-3">
          {/* Subject */}
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500">Oggetto</label>
            <input
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium"
            />
          </div>

          {/* Preview / HTML toggle */}
          <div className="flex items-center justify-between">
            <div className="flex gap-1">
              <button onClick={() => setShowHtml(false)}
                className={`inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium ${!showHtml ? 'bg-purple-100 text-purple-700' : 'text-gray-500 hover:bg-gray-100'}`}>
                <Eye className="h-3 w-3" /> Preview
              </button>
              <button onClick={() => setShowHtml(true)}
                className={`inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium ${showHtml ? 'bg-purple-100 text-purple-700' : 'text-gray-500 hover:bg-gray-100'}`}>
                <Code className="h-3 w-3" /> HTML
              </button>
            </div>
            {generate.data?.tokens_used && (
              <span className="text-[10px] text-gray-400">{generate.data.tokens_used} token usati</span>
            )}
          </div>

          {/* Content */}
          {showHtml ? (
            <textarea
              value={htmlBody}
              onChange={(e) => setHtmlBody(e.target.value)}
              rows={12}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-xs font-mono"
            />
          ) : (
            <div className="rounded-lg border border-gray-200 bg-white p-1 overflow-auto max-h-[400px]">
              <div dangerouslySetInnerHTML={{ __html: htmlBody }} />
            </div>
          )}

          {/* Variables toolbar */}
          <div>
            <p className="mb-1 text-xs font-medium text-gray-500">Variabili (click per copiare)</p>
            <div className="flex flex-wrap gap-1.5">
              {VARIABLES.map((v) => (
                <button
                  key={v}
                  onClick={() => insertVariable(v)}
                  className={`rounded-md px-2.5 py-1 text-xs font-mono transition-colors ${
                    variables.includes(v) ? 'bg-purple-100 text-purple-700 border border-purple-200' : 'bg-gray-100 text-gray-500 border border-gray-200'
                  } hover:bg-purple-50`}
                >
                  {`{{${v}}}`}
                </button>
              ))}
            </div>
          </div>

          {/* Refine */}
          <div className="flex gap-2">
            <input
              value={refinePrompt}
              onChange={(e) => setRefinePrompt(e.target.value)}
              placeholder="Modifica: es. Aggiungi un paragrafo sui tempi di consegna..."
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm"
            />
            <button onClick={handleRefine} disabled={refine.isPending || !refinePrompt}
              className="inline-flex items-center gap-1 rounded-lg bg-gray-100 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 disabled:opacity-50">
              {refine.isPending ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
              Modifica
            </button>
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-2 border-t border-gray-100 pt-3">
            <button onClick={() => { setHtmlBody(''); setSubject(''); setVariables([]) }}
              className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50">
              <RefreshCw className="h-3.5 w-3.5" /> Ricomincia
            </button>
            <button onClick={() => setShowSave(true)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-purple-300 bg-purple-50 px-3 py-2 text-sm font-medium text-purple-700 hover:bg-purple-100">
              <Save className="h-3.5 w-3.5" /> Salva template
            </button>
            {onSend && (
              <button onClick={() => onSend(subject, htmlBody)}
                className="inline-flex items-center gap-1.5 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700">
                <Send className="h-3.5 w-3.5" /> Invia subito
              </button>
            )}
          </div>

          {/* Save form */}
          {showSave && (
            <div className="rounded-lg border border-purple-200 bg-purple-50/50 p-3 space-y-2">
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
                  className="rounded-lg bg-purple-600 px-4 py-1.5 text-sm font-medium text-white disabled:opacity-50">Salva</button>
                <button onClick={() => setShowSave(false)}
                  className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-500">Annulla</button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
