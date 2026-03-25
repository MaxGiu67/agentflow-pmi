import { useState, useRef, useEffect, useCallback } from 'react'
import { MessageSquare, X, Send } from 'lucide-react'
import { useSendMessage } from '../../api/hooks'
import { cn } from '../../lib/utils'

interface FloatingMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export default function ChatbotFloating() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<FloatingMessage[]>([])
  const [text, setText] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [unreadCount, setUnreadCount] = useState(0)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const sendMessage = useSendMessage()

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setUnreadCount(0)
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [isOpen])

  const handleSend = useCallback(async () => {
    const trimmed = text.trim()
    if (!trimmed || isTyping) return

    const userMsg: FloatingMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: trimmed,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMsg])
    setText('')
    setIsTyping(true)

    try {
      const result = await sendMessage.mutateAsync({
        message: trimmed,
        conversationId: conversationId ?? undefined,
      })

      if (!conversationId && result.conversation_id) {
        setConversationId(result.conversation_id)
      }

      const assistantMsg: FloatingMessage = {
        id: result.message_id ?? `asst-${Date.now()}`,
        role: 'assistant',
        content: result.content ?? 'Risposta non disponibile.',
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, assistantMsg])

      if (!isOpen) {
        setUnreadCount((c) => c + 1)
      }
    } catch {
      const errorMsg: FloatingMessage = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: 'Si e verificato un errore. Riprova tra poco.',
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, errorMsg])
    } finally {
      setIsTyping(false)
    }
  }, [text, isTyping, conversationId, sendMessage, isOpen])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void handleSend()
    }
  }

  return (
    <>
      {/* Floating chat panel */}
      {isOpen && (
        <div className="fixed bottom-20 right-4 z-50 flex h-[500px] w-[350px] flex-col overflow-hidden rounded-xl border border-gray-200 bg-white shadow-2xl">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-gray-200 bg-blue-600 px-4 py-3">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-white" />
              <span className="text-sm font-semibold text-white">AgentFlow</span>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="rounded p-1 text-white/80 hover:bg-blue-700 hover:text-white"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Messages area */}
          <div className="flex-1 overflow-y-auto px-3 py-3">
            {messages.length === 0 && (
              <div className="flex h-full items-center justify-center">
                <p className="text-center text-sm text-gray-400">
                  Scrivi un messaggio per iniziare...
                </p>
              </div>
            )}
            <div className="space-y-3">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={cn('flex', msg.role === 'user' ? 'justify-end' : 'justify-start')}
                >
                  <div
                    className={cn(
                      'max-w-[85%] rounded-xl px-3 py-2 text-sm',
                      msg.role === 'user'
                        ? 'rounded-br-sm bg-blue-600 text-white'
                        : 'rounded-bl-sm border border-gray-100 bg-gray-50 text-gray-900',
                    )}
                  >
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  </div>
                </div>
              ))}
              {isTyping && (
                <div className="flex justify-start">
                  <div className="rounded-xl rounded-bl-sm border border-gray-100 bg-gray-50 px-3 py-2">
                    <div className="flex items-center gap-1">
                      <span className="text-xs text-gray-500">Sto scrivendo</span>
                      <span className="flex gap-0.5">
                        <span className="h-1 w-1 animate-bounce rounded-full bg-gray-400 [animation-delay:0ms]" />
                        <span className="h-1 w-1 animate-bounce rounded-full bg-gray-400 [animation-delay:150ms]" />
                        <span className="h-1 w-1 animate-bounce rounded-full bg-gray-400 [animation-delay:300ms]" />
                      </span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Input area */}
          <div className="border-t border-gray-200 px-3 py-2">
            <div className="flex items-center gap-2">
              <input
                ref={inputRef}
                type="text"
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isTyping}
                placeholder="Scrivi un messaggio..."
                className="flex-1 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400 disabled:opacity-50"
              />
              <button
                onClick={() => void handleSend()}
                disabled={isTyping || !text.trim()}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white transition-colors hover:bg-blue-700 disabled:bg-gray-300 disabled:text-gray-500"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Floating button */}
      <button
        onClick={() => setIsOpen((o) => !o)}
        className={cn(
          'fixed bottom-4 right-4 z-50 flex h-14 w-14 items-center justify-center rounded-full shadow-lg transition-all hover:scale-105',
          isOpen ? 'bg-gray-600 hover:bg-gray-700' : 'bg-blue-600 hover:bg-blue-700',
        )}
      >
        {isOpen ? (
          <X className="h-6 w-6 text-white" />
        ) : (
          <>
            <MessageSquare className="h-6 w-6 text-white" />
            {unreadCount > 0 && (
              <span className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-xs font-bold text-white">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </>
        )}
      </button>
    </>
  )
}
