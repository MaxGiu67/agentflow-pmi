import { useState, useRef, useCallback, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, Send, X, ArrowRight } from 'lucide-react'
import { useSendMessage } from '../../api/hooks'
import { useActionExecutor, type ActionCommand } from '../../hooks/useActionExecutor'
import Toast from '../ui/Toast'
import ContentBlockRenderer from './ContentBlockRenderer'
import { useAIBlocksStore } from '../../store/aiBlocks'

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

const suggestions: Record<string, string[]> = {
  dashboard: ['Qual è il fatturato del mese?', 'Top 5 clienti', 'Come stanno le finanze?'],
  fatture: ['Fatture NTT Data', 'Quante fatture ricevute?', 'Fatture in attesa'],
  contabilita: ['Ultime registrazioni', 'Stato patrimoniale', 'Prima nota'],
  scadenze: ['Prossime scadenze', 'Scadenze in ritardo', 'F24 da pagare'],
  ceo: ['KPI annuali', 'EBITDA', 'Cash flow previsto'],
  default: ['Come stanno le finanze?', 'Prossime scadenze', 'Fatture da verificare'],
}

/**
 * Render **bold** markdown as <strong> elements.
 */
function renderBold(text: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>
    }
    return part
  })
}

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

  // Close response when navigating to a different page
  useEffect(() => {
    if (showResponse) {
      setShowResponse(false)
      setResponse('')
      setError(null)
      setSuggestedActions([])
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname])

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
              className="mb-2 overflow-hidden rounded-2xl border border-gray-200/50 bg-white/95 shadow-2xl backdrop-blur-xl"
            >
              {/* Response Header */}
              <div className="flex items-center justify-between border-b border-gray-100 px-4 py-2">
                <div className="flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-blue-500" />
                  <span className="text-sm font-medium text-gray-700">AgentFlow AI</span>
                  {isLoading && (
                    <motion.span
                      animate={{ opacity: [1, 0.4, 1] }}
                      transition={{ duration: 1.5, repeat: Infinity }}
                      className="text-xs text-blue-500"
                    >
                      sta scrivendo...
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
                    <span className="text-sm text-gray-500">Sto elaborando</span>
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
            <Sparkles
              className="h-5 w-5 flex-shrink-0 text-blue-500"
              aria-hidden="true"
            />

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
