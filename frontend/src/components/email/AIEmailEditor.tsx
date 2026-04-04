import { useState, useRef, useCallback } from 'react'
import EmailEditor from 'react-email-editor'
import { useGenerateEmail, useCreateEmailTemplate } from '../../api/hooks'
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
}

export default function AIEmailEditor({ contactName, dealName, onSend }: AIEmailEditorProps) {
  const emailEditorRef = useRef<any>(null)
  const generate = useGenerateEmail()
  const saveTemplate = useCreateEmailTemplate()

  const [prompt, setPrompt] = useState('')
  const [tone, setTone] = useState('professionale')
  const [subject, setSubject] = useState('')
  const [editorReady, setEditorReady] = useState(false)
  const [hasContent, setHasContent] = useState(false)
  const [showSave, setShowSave] = useState(false)
  const [saveName, setSaveName] = useState('')
  const [saveCategory, setSaveCategory] = useState('followup')

  const onReady = useCallback(() => {
    setEditorReady(true)
  }, [])

  const handleGenerate = async () => {
    const result = await generate.mutateAsync({
      prompt,
      tone,
      contact_name: contactName || '',
      deal_name: dealName || '',
    })
    setSubject(result.subject)

    // Load HTML into Unlayer editor
    if (emailEditorRef.current?.editor) {
      emailEditorRef.current.editor.loadDesign({
        html: result.html_body,
        classic: true,
      })
      setHasContent(true)
    }
  }

  const exportHtml = (): Promise<string> => {
    return new Promise((resolve) => {
      if (emailEditorRef.current?.editor) {
        emailEditorRef.current.editor.exportHtml((data: any) => {
          resolve(data.html)
        })
      } else {
        resolve('')
      }
    })
  }

  const handleSaveTemplate = async () => {
    if (!saveName) return
    const html = await exportHtml()
    await saveTemplate.mutateAsync({
      name: saveName,
      subject,
      html_body: html,
      category: saveCategory,
      variables: VARIABLES.filter(v => html.includes(`{{${v}}}`)),
    })
    setShowSave(false)
    setSaveName('')
  }

  const handleSend = async () => {
    if (!onSend) return
    const html = await exportHtml()
    onSend(subject, html)
  }

  const insertVariable = (varKey: string) => {
    if (emailEditorRef.current?.editor) {
      // Copy to clipboard — user pastes into editor
      navigator.clipboard.writeText(`{{${varKey}}}`)
    }
  }

  return (
    <div className="space-y-4">
      {/* ── AI Generation Bar ── */}
      <div className="flex flex-wrap items-end gap-3 rounded-xl border border-purple-200 bg-purple-50/30 p-4">
        <div className="flex-1 min-w-64">
          <label className="mb-1 block text-xs font-medium text-gray-600">Descrivi l'email</label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="es. Crea email per presentare i servizi di consulenza SAP a un nuovo prospect..."
            rows={2}
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-purple-500 focus:ring-1 focus:ring-purple-500 focus:outline-none resize-none"
          />
        </div>
        <div className="flex items-end gap-2">
          <select value={tone} onChange={(e) => setTone(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm h-10">
            {TONES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
          <button
            onClick={handleGenerate}
            disabled={generate.isPending || prompt.length < 10 || !editorReady}
            className="inline-flex items-center gap-2 rounded-lg bg-purple-600 px-5 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50 h-10 shrink-0"
          >
            {generate.isPending ? (
              <><RefreshCw className="h-4 w-4 animate-spin" /> Genero...</>
            ) : (
              <><Sparkles className="h-4 w-4" /> {hasContent ? 'Rigenera' : 'Genera con AI'}</>
            )}
          </button>
        </div>
      </div>

      {/* ── Subject + Variables + Actions Bar ── */}
      {hasContent && (
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 flex-1 min-w-48">
            <span className="text-xs font-medium text-gray-400 shrink-0">Oggetto:</span>
            <input
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium focus:border-purple-500 focus:outline-none"
            />
          </div>

          {/* Variables */}
          <div className="flex gap-1">
            {VARIABLES.map((v) => (
              <button key={v} onClick={() => insertVariable(v)} title={`Copia {{${v}}} negli appunti`}
                className="rounded-md border border-gray-200 bg-gray-50 px-2 py-0.5 text-[10px] font-mono text-gray-500 hover:border-purple-300 hover:bg-purple-50 hover:text-purple-700">
                {`{{${v}}}`}
              </button>
            ))}
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            <button onClick={() => setShowSave(true)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50">
              <Save className="h-3 w-3" /> Salva template
            </button>
            {onSend && (
              <button onClick={handleSend}
                className="inline-flex items-center gap-1.5 rounded-lg bg-purple-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-purple-700">
                <Send className="h-3 w-3" /> Invia
              </button>
            )}
          </div>
        </div>
      )}

      {/* ── Unlayer Editor ── */}
      <div className="rounded-xl border border-gray-200 overflow-hidden" style={{ height: 600 }}>
        <EmailEditor
          ref={emailEditorRef}
          onReady={onReady}
          options={{
            locale: 'it-IT',
            appearance: {
              theme: 'light',
              panels: {
                tools: {
                  dock: 'left',
                },
              },
            },
            tools: {
              image: { enabled: true },
              button: { enabled: true },
              divider: { enabled: true },
              html: { enabled: true },
              social: { enabled: true },
              video: { enabled: false },
              timer: { enabled: false },
              menu: { enabled: false },
            },
            features: {
              stockImages: { enabled: false },
              smartMergeTags: { enabled: true },
            },
            mergeTags: VARIABLES.map(v => ({
              name: v.charAt(0).toUpperCase() + v.slice(1),
              value: `{{${v}}}`,
            })),
          }}
          style={{ minHeight: 600 }}
        />
      </div>

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
                <button onClick={handleSaveTemplate} disabled={!saveName || saveTemplate.isPending}
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
