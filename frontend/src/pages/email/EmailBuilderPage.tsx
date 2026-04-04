import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useGenerateEmail, useRefineEmail, useCreateEmailTemplate } from '../../api/hooks'
import PageMeta from '../../components/ui/PageMeta'
import {
  Sparkles, Send, Save, Undo2, Type, Palette,
  MessageCircle, X, ChevronRight, Wand2, Eye, Code,
  Bold, Italic, AlignLeft, AlignCenter, Link2,
} from 'lucide-react'

const SUGGESTIONS = [
  'Crea una email per presentare i nostri servizi',
  'Scrivi un follow-up per una proposta inviata',
  'Genera un reminder gentile per un preventivo',
  'Crea una email di benvenuto per un nuovo cliente',
  'Scrivi una email per proporre una demo',
]

const VARIABLES = [
  { key: 'nome', label: 'Nome', example: 'Mario Rossi' },
  { key: 'azienda', label: 'Azienda', example: 'Acme SPA' },
  { key: 'deal_name', label: 'Progetto', example: 'SAP Migration' },
  { key: 'deal_value', label: 'Valore', example: '45.000 EUR' },
  { key: 'commerciale', label: 'Commerciale', example: 'Luigi Bianchi' },
]

interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
}

export default function EmailBuilderPage() {
  const navigate = useNavigate()
  const generate = useGenerateEmail()
  const refine = useRefineEmail()
  const saveTemplate = useCreateEmailTemplate()
  const chatEndRef = useRef<HTMLDivElement>(null)

  // State
  const [subject, setSubject] = useState('')
  const [htmlBody, setHtmlBody] = useState('')
  const [variables, setVariables] = useState<string[]>([])
  const [chatInput, setChatInput] = useState('')
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    { role: 'system', content: 'Ciao! Sono il tuo assistente email. Dimmi che tipo di email vuoi creare e la genero per te. Poi puoi chiedermi modifiche.', timestamp: new Date() },
  ])
  const [view, setView] = useState<'preview' | 'code'>('preview')
  const [showSave, setShowSave] = useState(false)
  const [saveName, setSaveName] = useState('')
  const [saveCategory, setSaveCategory] = useState('followup')
  const [isGenerating, setIsGenerating] = useState(false)
  const [editingSubject, setEditingSubject] = useState(false)

  // Auto-scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  const addMessage = (role: 'user' | 'assistant' | 'system', content: string) => {
    setChatMessages(prev => [...prev, { role, content, timestamp: new Date() }])
  }

  const handleSend = async () => {
    if (!chatInput.trim() || isGenerating) return
    const userMsg = chatInput.trim()
    setChatInput('')
    addMessage('user', userMsg)
    setIsGenerating(true)

    try {
      if (!htmlBody) {
        // First generation
        const result = await generate.mutateAsync({
          prompt: userMsg,
          tone: 'professionale',
        })
        setSubject(result.subject)
        setHtmlBody(result.html_body)
        setVariables(result.variables_detected || [])
        addMessage('assistant', `Email creata! Oggetto: "${result.subject}". Puoi chiedermi modifiche o personalizzarla direttamente.`)
      } else {
        // Refinement
        const result = await refine.mutateAsync({
          html_body: htmlBody,
          instruction: userMsg,
        })
        setSubject(result.subject)
        setHtmlBody(result.html_body)
        setVariables(result.variables_detected || [])
        addMessage('assistant', 'Fatto! Ho aggiornato l\'email. Vuoi altre modifiche?')
      }
    } catch {
      addMessage('assistant', 'Mi dispiace, c\'e stato un errore. Riprova.')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleSuggestion = (s: string) => {
    setChatInput(s)
  }

  const handleSaveTemplate = async () => {
    if (!saveName) return
    await saveTemplate.mutateAsync({
      name: saveName,
      subject,
      html_body: htmlBody,
      category: saveCategory,
      variables,
    })
    setShowSave(false)
    addMessage('system', `Template "${saveName}" salvato!`)
  }

  const handleReset = () => {
    setSubject('')
    setHtmlBody('')
    setVariables([])
    setChatMessages([
      { role: 'system', content: 'Ricominciamo! Dimmi che email vuoi creare.', timestamp: new Date() },
    ])
  }

  const insertVariable = (varKey: string) => {
    const tag = `{{${varKey}}}`
    if (view === 'code') {
      setHtmlBody(prev => prev + tag)
    } else {
      navigator.clipboard.writeText(tag)
      addMessage('system', `Variabile ${tag} copiata! Incollala dove vuoi nel testo.`)
    }
  }

  return (
    <div className="h-[calc(100dvh-8rem)] flex flex-col lg:flex-row gap-0 -m-3 sm:-m-4 lg:-m-6">
      <PageMeta title="Crea Email" />

      {/* ─── LEFT: Chat Panel ─── */}
      <div className="flex flex-col w-full lg:w-[380px] lg:min-w-[380px] border-r border-gray-200 bg-white">
        {/* Chat header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-purple-600">
              <Sparkles className="h-4 w-4 text-white" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900">Email AI</p>
              <p className="text-[10px] text-gray-400">Descrivi, genera, personalizza</p>
            </div>
          </div>
          <div className="flex gap-1">
            {htmlBody && (
              <button onClick={handleReset} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100" title="Ricomincia">
                <Undo2 className="h-4 w-4" />
              </button>
            )}
            <button onClick={() => navigate('/email/templates')} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100" title="Chiudi">
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Chat messages */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
          {chatMessages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] rounded-2xl px-3.5 py-2 text-sm ${
                msg.role === 'user'
                  ? 'bg-purple-600 text-white rounded-br-md'
                  : msg.role === 'system'
                  ? 'bg-amber-50 text-amber-800 border border-amber-200 rounded-bl-md'
                  : 'bg-gray-100 text-gray-800 rounded-bl-md'
              }`}>
                {msg.content}
              </div>
            </div>
          ))}
          {isGenerating && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-2xl rounded-bl-md px-4 py-3">
                <div className="flex gap-1">
                  <span className="h-2 w-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="h-2 w-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="h-2 w-2 rounded-full bg-purple-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Suggestions (before first generation) */}
        {!htmlBody && chatMessages.length <= 1 && (
          <div className="px-4 pb-2 space-y-1">
            <p className="text-[10px] font-medium text-gray-400 uppercase">Suggerimenti</p>
            {SUGGESTIONS.map((s, i) => (
              <button key={i} onClick={() => handleSuggestion(s)}
                className="flex w-full items-center justify-between rounded-lg border border-gray-200 px-3 py-2 text-left text-xs text-gray-600 hover:bg-purple-50 hover:border-purple-200 hover:text-purple-700 transition-colors">
                {s}
                <ChevronRight className="h-3 w-3 shrink-0 opacity-40" />
              </button>
            ))}
          </div>
        )}

        {/* Chat input */}
        <div className="border-t border-gray-200 p-3">
          <div className="flex gap-2">
            <input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              placeholder={htmlBody ? 'Chiedi una modifica...' : 'Descrivi l\'email che vuoi...'}
              disabled={isGenerating}
              className="flex-1 rounded-xl border border-gray-300 px-3.5 py-2.5 text-sm focus:border-purple-500 focus:ring-1 focus:ring-purple-500 focus:outline-none disabled:opacity-50"
            />
            <button onClick={handleSend} disabled={isGenerating || !chatInput.trim()}
              className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50 transition-colors shrink-0">
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* ─── RIGHT: Preview Panel ─── */}
      <div className="flex-1 flex flex-col bg-gray-50 min-h-0">
        {!htmlBody ? (
          /* Empty state */
          <div className="flex-1 flex items-center justify-center p-8">
            <div className="text-center max-w-sm">
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-purple-100">
                <Wand2 className="h-8 w-8 text-purple-500" />
              </div>
              <h2 className="text-lg font-semibold text-gray-900" style={{ fontFamily: 'var(--font-display)' }}>
                Crea la tua email con l'AI
              </h2>
              <p className="mt-2 text-sm text-gray-500">
                Usa la chat a sinistra per descrivere l'email. L'AI la genera in pochi secondi. Poi puoi personalizzarla qui.
              </p>
            </div>
          </div>
        ) : (
          <>
            {/* Toolbar */}
            <div className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-2">
              <div className="flex items-center gap-2">
                {/* View toggle */}
                <div className="flex rounded-lg border border-gray-200 bg-gray-50">
                  <button onClick={() => setView('preview')}
                    className={`inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-l-lg ${view === 'preview' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'}`}>
                    <Eye className="h-3 w-3" /> Preview
                  </button>
                  <button onClick={() => setView('code')}
                    className={`inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-r-lg ${view === 'code' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'}`}>
                    <Code className="h-3 w-3" /> HTML
                  </button>
                </div>

                <div className="h-4 w-px bg-gray-200" />

                {/* Variable buttons */}
                <div className="flex gap-1 overflow-x-auto">
                  {VARIABLES.map((v) => (
                    <button key={v.key} onClick={() => insertVariable(v.key)}
                      className={`shrink-0 rounded-md px-2 py-0.5 text-[10px] font-mono border transition-colors ${
                        variables.includes(v.key)
                          ? 'bg-purple-50 text-purple-700 border-purple-200'
                          : 'bg-gray-50 text-gray-400 border-gray-200 hover:border-purple-200'
                      }`}>
                      {`{{${v.key}}}`}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-1.5">
                <button onClick={() => setShowSave(true)}
                  className="inline-flex items-center gap-1 rounded-lg border border-gray-300 px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50">
                  <Save className="h-3 w-3" /> Salva
                </button>
              </div>
            </div>

            {/* Subject bar */}
            <div className="border-b border-gray-200 bg-white px-4 py-2">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-gray-400 shrink-0">Oggetto:</span>
                {editingSubject ? (
                  <input value={subject} onChange={(e) => setSubject(e.target.value)}
                    onBlur={() => setEditingSubject(false)} onKeyDown={(e) => e.key === 'Enter' && setEditingSubject(false)}
                    autoFocus className="flex-1 rounded border border-purple-300 px-2 py-0.5 text-sm font-medium focus:outline-none" />
                ) : (
                  <button onClick={() => setEditingSubject(true)} className="flex-1 text-left text-sm font-medium text-gray-900 hover:text-purple-700 truncate">
                    {subject || 'Clicca per modificare...'}
                  </button>
                )}
              </div>
            </div>

            {/* Content area */}
            <div className="flex-1 overflow-auto p-4">
              {view === 'code' ? (
                <textarea
                  value={htmlBody}
                  onChange={(e) => setHtmlBody(e.target.value)}
                  className="h-full w-full rounded-lg border border-gray-300 bg-white p-4 text-xs font-mono leading-relaxed focus:border-purple-500 focus:ring-1 focus:ring-purple-500 focus:outline-none"
                  spellCheck={false}
                />
              ) : (
                <div className="mx-auto max-w-[640px]">
                  <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
                    <div dangerouslySetInnerHTML={{ __html: htmlBody }} />
                  </div>
                </div>
              )}
            </div>

            {/* Save modal */}
            {showSave && (
              <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/20" onClick={() => setShowSave(false)}>
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
          </>
        )}
      </div>
    </div>
  )
}
