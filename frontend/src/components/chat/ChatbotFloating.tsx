import { useState, useRef, useCallback, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, X, ArrowRight } from 'lucide-react'
import { useSendMessage } from '../../api/hooks'
import { useActionExecutor, type ActionCommand } from '../../hooks/useActionExecutor'
import Toast from '../ui/Toast'
import ContentBlockRenderer from './ContentBlockRenderer'
import { useAIBlocksStore } from '../../store/aiBlocks'
import JarvisOrb, { type OrbState } from './JarvisOrb'

/* ── Placeholder per pagina ──────────────────────────────────────── */

const getPlaceholder = (page: string): string => {
  switch (page) {
    case 'dashboard': return 'Chiedi sui KPI, fatturato, clienti...'
    case 'fatture': return 'Cerca fattura, cliente, fornitore...'
    case 'contabilita': return 'Chiedi sulle scritture contabili...'
    case 'scadenze': return 'Chiedi sulle scadenze fiscali...'
    case 'fisco': return 'Chiedi su IVA, F24, ritenute...'
    case 'ceo': return 'Chiedi su KPI, budget, margini...'
    case 'banca': return 'Chiedi su movimenti, saldi, riconciliazione...'
    case 'spese': return 'Chiedi sulle note spese...'
    case 'cespiti': return 'Chiedi sui cespiti e ammortamenti...'
    default: return 'Chiedi qualcosa ad AgentFlow...'
  }
}

/* ── Suggestion chips per pagina ─────────────────────────────────── */

const suggestions: Record<string, string[]> = {
  dashboard: ['Qual è il fatturato del mese?', 'Top 5 clienti', 'Come stanno le finanze?'],
  fatture: ['Fatture NTT Data', 'Quante fatture ricevute?', 'Fatture in attesa'],
  contabilita: ['Ultime registrazioni', 'Stato patrimoniale', 'Prima nota'],
  scadenze: ['Prossime scadenze', 'Scadenze in ritardo', 'F24 da pagare'],
  ceo: ['KPI annuali', 'EBITDA', 'Cash flow previsto'],
  default: ['Come stanno le finanze?', 'Prossime scadenze', 'Fatture da verificare'],
}

/* ── Typing messages contestuali ─────────────────────────────────── */

function getTypingMessage(page: string): string {
  if (page === 'dashboard') return 'Analizzo i KPI...'
  if (page.startsWith('crm') && page.includes('pipeline')) return 'Controllo la pipeline...'
  if (page.startsWith('crm') && page.includes('deal')) return 'Verifico il deal...'
  if (page.startsWith('crm')) return 'Controllo la pipeline...'
  if (page === 'fatture') return 'Analizzo le fatture...'
  if (page === 'contabilita') return 'Verifico le scritture...'
  if (page === 'scadenze' || page === 'fisco') return 'Controllo le scadenze...'
  if (page === 'banca') return 'Verifico i movimenti...'
  if (page === 'ceo') return 'Analizzo i KPI...'
  return 'Elaboro la richiesta...'
}

/* ── Agent badge per contesto ────────────────────────────────────── */

interface AgentInfo {
  name: string
  colorClass: string
}

function getAgentForPage(pathname: string): AgentInfo {
  const path = pathname.toLowerCase()
  if (path.includes('crm') || path.includes('pipeline') || path.includes('deal') || path.includes('contact'))
    return { name: 'SalesBot', colorClass: 'bg-purple-100 text-purple-700' }
  if (path.includes('fattur') || path.includes('contabil'))
    return { name: 'ContaBot', colorClass: 'bg-blue-100 text-blue-700' }
  if (path.includes('fisco') || path.includes('scadenz'))
    return { name: 'FiscoBot', colorClass: 'bg-orange-100 text-orange-700' }
  if (path.includes('dashboard') || path.includes('ceo'))
    return { name: 'ControllerBot', colorClass: 'bg-green-100 text-green-700' }
  return { name: 'AgentFlow AI', colorClass: 'bg-gray-100 text-gray-700' }
}

/* ── Glow shadow per stato ───────────────────────────────────────── */

function getGlowShadow(orbState: OrbState): string {
  switch (orbState) {
    case 'thinking':
      return '0 0 20px rgba(167,139,250,0.3), 0 0 40px rgba(147,51,234,0.1)'
    case 'responding':
      return '0 0 16px rgba(52,211,153,0.3), 0 0 32px rgba(34,197,94,0.1)'
    case 'error':
      return '0 0 20px rgba(248,113,113,0.3), 0 0 40px rgba(251,146,60,0.1)'
    default:
      return 'none'
  }
}

/* ── Bold markdown renderer ──────────────────────────────────────── */

function renderBold(text: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>
    }
    return part
  })
}

/* ── Main component ──────────────────────────────────────────────── */

export default function ChatbotFloating() {
  const [query, setQuery] = useState('')
  const [isFocused, setIsFocused] = useState(false)
  const [response, setResponse] = useState('')
  const [showResponse, setShowResponse] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [suggestedActions, setSuggestedActions] = useState<ActionCommand[]>([])
  const [contentBlocks, setContentBlocks] = useState<Record<string, unknown>[]>([])
  const [toastMessage, setToastMessage] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const location = useLocation()
  const page = location.pathname.split('/')[1] || 'dashboard'
  const fullPath = location.pathname

  const { executeActions, executeSingle } = useActionExecutor()

  const getSelectedYear = (): number => {
    const params = new URLSearchParams(location.search)
    const yearParam = params.get('year')
    if (yearParam) {
      const parsed = parseInt(yearParam, 10)
      if (!isNaN(parsed)) return parsed
    }
    return new Date().getFullYear()
  }

  const sendMessage = useSendMessage()

  const pageSuggestions = suggestions[page] ?? suggestions['default']

  /* ── Derive orb state ─────────────────────────────────────────── */

  const orbState: OrbState = error
    ? 'error'
    : isLoading && !response
      ? 'thinking'
      : isLoading && !!response
        ? 'responding'
        : 'idle'

  const agent = getAgentForPage(fullPath)
  const typingMessage = getTypingMessage(fullPath)

  /* ── Close response on navigation ─────────────────────────────── */

  useEffect(() => {
    if (showResponse) {
      setShowResponse(false)
      setResponse('')
      setError(null)
      setSuggestedActions([])
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname])

  /* ── Global keyboard shortcuts ────────────────────────────────── */

  useEffect(() => {
    function handleGlobalKeyDown(e: KeyboardEvent) {
      // Ctrl+Space or Cmd+Space -> focus chatbot input
      if (e.code === 'Space' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault()
        inputRef.current?.focus()
      }

      // Escape -> close response panel if open
      if (e.key === 'Escape' && showResponse) {
        closeResponse()
      }
    }

    window.addEventListener('keydown', handleGlobalKeyDown)
    return () => window.removeEventListener('keydown', handleGlobalKeyDown)
  }, [showResponse])

  /* ── Submit handler ────────────────────────────────────────────── */

  const handleSubmit = useCallback(async () => {
    const trimmed = query.trim()
    if (!trimmed || isLoading) return

    const sentAt = Date.now()
    setResponse('')
    setError(null)
    setShowResponse(true)
    setIsLoading(true)
    setQuery('')
    setSuggestedActions([])
    setContentBlocks([])

    try {
      const result = await sendMessage.mutateAsync({
        message: trimmed,
        conversationId: conversationId ?? undefined,
        context: { page, year: getSelectedYear() },
      })

      if (!conversationId && result.conversation_id) {
        setConversationId(result.conversation_id)
      }

      setResponse(result.content ?? 'Risposta non disponibile.')

      // Execute auto actions from response_meta
      const meta = result.response_meta
      if (meta) {
        const autoActions = (meta.actions ?? []) as ActionCommand[]
        if (autoActions.length > 0) {
          const toasts = executeActions(autoActions, sentAt)
          if (toasts.length > 0) {
            setToastMessage(toasts.join(' • '))
          }
        }

        const suggested = (meta.suggested_actions ?? []) as ActionCommand[]
        if (suggested.length > 0) {
          setSuggestedActions(suggested)
        }

        const blocks = meta.content_blocks
        if (Array.isArray(blocks) && blocks.length > 0) {
          setContentBlocks(blocks)
          // Send blocks to dashboard for full-size rendering
          console.log('[AgentFlow] Sending content_blocks to dashboard:', blocks.length)
          useAIBlocksStore.getState().setBlocks(blocks, result.content?.slice(0, 100) ?? '')
        }
      }
    } catch {
      setError('Si è verificato un errore. Riprova tra poco.')
    } finally {
      setIsLoading(false)
    }
  }, [query, isLoading, conversationId, sendMessage, page, location.search, executeActions])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void handleSubmit()
    }
  }

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion)
    inputRef.current?.focus()
  }

  const handleActionClick = (action: ActionCommand) => {
    const msg = executeSingle(action)
    if (msg) setToastMessage(msg)
    closeResponse()
  }

  const clearQuery = () => {
    setQuery('')
    inputRef.current?.focus()
  }

  const closeResponse = () => {
    setShowResponse(false)
    setResponse('')
    setError(null)
    setSuggestedActions([])
    setContentBlocks([])
  }

  /* ── Glow shadow for response panel ────────────────────────────── */

  const panelGlow = showResponse ? getGlowShadow(orbState) : 'none'

  return (
    <>
      <div
        className="fixed z-50
          bottom-20 left-3 right-3
          lg:bottom-6 lg:left-1/2 lg:right-auto lg:-translate-x-1/2 lg:w-[min(600px,90vw)]"
        role="search"
        aria-label="Chat con AgentFlow AI"
      >
        {/* Response Panel */}
        <AnimatePresence>
          {showResponse && (response || isLoading || error) && (
            <motion.div
              initial={{ opacity: 0, y: 10, height: 0 }}
              animate={{ opacity: 1, y: 0, height: 'auto' }}
              exit={{ opacity: 0, y: 10, height: 0 }}
              transition={{ duration: 0.3 }}
              className="mb-2 overflow-hidden rounded-2xl border border-gray-200/50 bg-white/95 backdrop-blur-xl"
              style={{
                boxShadow: panelGlow !== 'none'
                  ? `${panelGlow}, 0 25px 50px -12px rgba(0,0,0,0.25)`
                  : '0 25px 50px -12px rgba(0,0,0,0.25)',
                transition: 'box-shadow 0.5s ease',
              }}
            >
              {/* Response Header */}
              <div className="flex items-center justify-between border-b border-gray-100 px-4 py-2">
                <div className="flex items-center gap-2">
                  <JarvisOrb state={orbState} size={20} />
                  {/* Agent badge */}
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${agent.colorClass}`}
                  >
                    {agent.name}
                  </span>
                  {isLoading && (
                    <motion.span
                      animate={{ opacity: [1, 0.4, 1] }}
                      transition={{ duration: 1.5, repeat: Infinity }}
                      className="text-xs text-blue-500"
                    >
                      {typingMessage}
                    </motion.span>
                  )}
                </div>
                <button
                  type="button"
                  onClick={closeResponse}
                  className="p-1 text-gray-400 transition-colors hover:text-gray-600"
                  aria-label="Chiudi risposta"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Response Body */}
              <div className={`overflow-y-auto px-4 py-3 ${contentBlocks.length > 0 ? 'max-h-[60vh]' : 'max-h-[40vh] md:max-h-[300px]'}`}>
                {error ? (
                  <p className="text-sm text-red-600">{error}</p>
                ) : isLoading && !response ? (
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-500">{typingMessage}</span>
                    <span className="flex gap-0.5">
                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-blue-400 [animation-delay:0ms]" />
                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-blue-400 [animation-delay:150ms]" />
                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-blue-400 [animation-delay:300ms]" />
                    </span>
                  </div>
                ) : (
                  <>
                    <div className="whitespace-pre-wrap text-sm leading-relaxed text-gray-700">
                      {renderBold(response)}
                    </div>
                    <ContentBlockRenderer blocks={contentBlocks as never[]} />
                  </>
                )}
              </div>

              {/* Suggested Actions (buttons) */}
              {!isLoading && suggestedActions.length > 0 && (
                <div className="flex flex-wrap gap-2 border-t border-gray-100 px-4 py-2.5">
                  {suggestedActions.map((action, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => handleActionClick(action)}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700 transition-colors hover:bg-blue-100"
                    >
                      {action.label ?? 'Vai'}
                      <ArrowRight className="h-3.5 w-3.5" />
                    </button>
                  ))}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Input Bar */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="rounded-2xl border border-blue-100 bg-white/95 p-4 shadow-[0_8px_32px_rgba(59,130,246,0.12)] backdrop-blur-xl"
        >
          {/* Input Row */}
          <div className="flex items-center gap-3">
            <JarvisOrb state={orbState} size={40} />

            <div className="relative flex-1">
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                onFocus={() => setIsFocused(true)}
                onBlur={() => setTimeout(() => setIsFocused(false), 200)}
                placeholder={getPlaceholder(page)}
                aria-label="Scrivi la tua domanda"
                className="w-full rounded-lg bg-gray-50 px-4 py-3 pr-10 text-gray-900 placeholder-gray-400 transition-shadow focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                disabled={isLoading}
              />

              {/* Clear button */}
              <AnimatePresence>
                {query && !isLoading && (
                  <motion.button
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                    type="button"
                    onClick={clearQuery}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    aria-label="Cancella"
                  >
                    <X className="h-4 w-4" />
                  </motion.button>
                )}
              </AnimatePresence>
            </div>

            {/* Submit button */}
            <button
              type="button"
              onClick={() => void handleSubmit()}
              disabled={isLoading || !query.trim()}
              className="rounded-lg bg-blue-500 p-3 text-white transition-colors hover:bg-blue-600 disabled:cursor-not-allowed disabled:opacity-50"
              aria-label="Invia domanda"
            >
              <Send className="h-5 w-5" />
            </button>
          </div>

          {/* Suggestions */}
          <AnimatePresence>
            {isFocused && !query && !showResponse && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mt-3 border-t border-gray-100 pt-3"
              >
                <p className="mb-2 text-xs text-gray-400">Prova a chiedere:</p>
                <div className="flex flex-wrap gap-2">
                  {pageSuggestions.map((suggestion) => (
                    <button
                      key={suggestion}
                      type="button"
                      onClick={() => handleSuggestionClick(suggestion)}
                      className="rounded-full bg-gray-100 px-3 py-1.5 text-sm text-gray-600 transition-colors hover:bg-blue-100 hover:text-blue-700"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>

      {/* Toast feedback for auto-actions */}
      <Toast message={toastMessage} onClose={() => setToastMessage(null)} />
    </>
  )
}
