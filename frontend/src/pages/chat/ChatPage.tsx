import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Bot } from 'lucide-react'
import ChatSidebar from './ChatSidebar'
import ChatMessage from '../../components/chat/ChatMessage'
import ChatInput from '../../components/chat/ChatInput'
import SuggestionChips from '../../components/chat/SuggestionChips'
import {
  useConversations,
  useConversation,
  useSendMessage,
  useCreateConversation,
  useDeleteConversation,
} from '../../api/hooks'
import { useAuthStore } from '../../store/auth'

const DEFAULT_SUGGESTIONS = [
  'Come stanno le mie finanze?',
  'Fatture da verificare',
  'Prossime scadenze',
  'Mostra la dashboard',
]

interface MessageItem {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string | null
  agent_name?: string | null
  agent_type?: string | null
  created_at: string
}

export default function ChatPage() {
  const { conversationId: paramConvId } = useParams<{ conversationId?: string }>()
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)

  const [activeConversationId, setActiveConversationId] = useState<string | null>(
    paramConvId ?? null,
  )
  const [messages, setMessages] = useState<MessageItem[]>([])
  const [isTyping, setIsTyping] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>(DEFAULT_SUGGESTIONS)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Queries
  const { data: conversationsData, isLoading: convListLoading } = useConversations()
  const { data: conversationDetail } = useConversation(activeConversationId ?? '')

  // Mutations
  const sendMessage = useSendMessage()
  const createConversation = useCreateConversation()
  const deleteConversation = useDeleteConversation()

  // Sync URL param with state
  useEffect(() => {
    if (paramConvId && paramConvId !== activeConversationId) {
      setActiveConversationId(paramConvId)
    }
  }, [paramConvId, activeConversationId])

  // Load messages when conversation changes
  useEffect(() => {
    if (conversationDetail?.messages) {
      setMessages(
        conversationDetail.messages.map((m: MessageItem) => ({
          id: m.id,
          role: m.role as 'user' | 'assistant' | 'system',
          content: m.content,
          agent_name: m.agent_name,
          agent_type: m.agent_type,
          created_at: m.created_at,
        })),
      )
      setSuggestions([])
    }
  }, [conversationDetail])

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  const handleSend = useCallback(
    async (text: string) => {
      // Optimistic: add user message
      const tempUserMsg: MessageItem = {
        id: `temp-${Date.now()}`,
        role: 'user',
        content: text,
        created_at: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, tempUserMsg])
      setIsTyping(true)
      setSuggestions([])

      try {
        const result = await sendMessage.mutateAsync({
          message: text,
          conversationId: activeConversationId ?? undefined,
        })

        // If new conversation was created, update the active one
        if (!activeConversationId && result.conversation_id) {
          setActiveConversationId(result.conversation_id)
          navigate(`/chat/${result.conversation_id}`, { replace: true })
        }

        // Add assistant response
        const assistantMsg: MessageItem = {
          id: result.message_id,
          role: 'assistant',
          content: result.content,
          agent_name: result.agent_name,
          agent_type: result.agent_type,
          created_at: new Date().toISOString(),
        }
        setMessages((prev) => [...prev, assistantMsg])

        // Update suggestions
        if (result.suggestions && result.suggestions.length > 0) {
          setSuggestions(result.suggestions)
        } else {
          setSuggestions([])
        }
      } catch {
        // Add error message
        const errorMsg: MessageItem = {
          id: `error-${Date.now()}`,
          role: 'assistant',
          content: 'Mi dispiace, si e verificato un errore. Riprova tra poco.',
          agent_name: 'AgentFlow',
          agent_type: 'orchestrator',
          created_at: new Date().toISOString(),
        }
        setMessages((prev) => [...prev, errorMsg])
      } finally {
        setIsTyping(false)
      }
    },
    [activeConversationId, sendMessage, navigate],
  )

  const handleNewConversation = useCallback(async () => {
    try {
      const result = await createConversation.mutateAsync()
      setActiveConversationId(result.id)
      setMessages([])
      setSuggestions(DEFAULT_SUGGESTIONS)
      navigate(`/chat/${result.id}`, { replace: true })
    } catch {
      // Fallback: just clear the chat
      setActiveConversationId(null)
      setMessages([])
      setSuggestions(DEFAULT_SUGGESTIONS)
      navigate('/chat', { replace: true })
    }
  }, [createConversation, navigate])

  const handleSelectConversation = useCallback(
    (id: string) => {
      setActiveConversationId(id)
      navigate(`/chat/${id}`, { replace: true })
    },
    [navigate],
  )

  const handleDeleteConversation = useCallback(
    async (id: string) => {
      await deleteConversation.mutateAsync(id)
      if (activeConversationId === id) {
        setActiveConversationId(null)
        setMessages([])
        setSuggestions(DEFAULT_SUGGESTIONS)
        navigate('/chat', { replace: true })
      }
    },
    [activeConversationId, deleteConversation, navigate],
  )

  const conversations = conversationsData?.items ?? []

  return (
    <div className="flex h-[calc(100vh-4rem)] overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      {/* Sidebar */}
      <ChatSidebar
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
        isLoading={convListLoading}
      />

      {/* Main chat area */}
      <div className="flex flex-1 flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-6">
          {messages.length === 0 && !isTyping ? (
            /* Empty state */
            <div className="flex h-full flex-col items-center justify-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-blue-50">
                <Bot className="h-8 w-8 text-blue-600" />
              </div>
              <h2 className="mb-1 text-lg font-semibold text-gray-900">Ciao! Sono AgentFlow</h2>
              <p className="mb-6 max-w-md text-center text-sm text-gray-500">
                Il tuo assistente contabile AI. Chiedimi qualsiasi cosa sulla tua azienda: fatture,
                scadenze, cash flow, normative e molto altro.
              </p>
              <SuggestionChips
                suggestions={DEFAULT_SUGGESTIONS}
                onSelect={handleSend}
                disabled={isTyping}
              />
            </div>
          ) : (
            <div className="mx-auto max-w-3xl space-y-4">
              {messages.map((msg) => (
                <ChatMessage
                  key={msg.id}
                  role={msg.role}
                  content={msg.content}
                  agentName={msg.agent_name}
                  agentType={msg.agent_type}
                  createdAt={msg.created_at}
                  userName={user?.name ?? undefined}
                />
              ))}

              {/* Typing indicator */}
              {isTyping && (
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100 text-sm">
                    {'\u{1f916}'}
                  </div>
                  <div className="rounded-2xl rounded-tl-sm border border-gray-100 bg-white px-4 py-2.5 shadow-sm">
                    <div className="flex items-center gap-1.5">
                      <span className="text-sm text-gray-500">AgentFlow sta scrivendo</span>
                      <span className="flex gap-0.5">
                        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400 [animation-delay:0ms]" />
                        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400 [animation-delay:150ms]" />
                        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-gray-400 [animation-delay:300ms]" />
                      </span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Suggestions (when conversation has messages) */}
        {messages.length > 0 && suggestions.length > 0 && (
          <div className="border-t border-gray-100 px-4 py-2">
            <SuggestionChips suggestions={suggestions} onSelect={handleSend} disabled={isTyping} />
          </div>
        )}

        {/* Input */}
        <div className="border-t border-gray-200 bg-gray-50 p-4">
          <div className="mx-auto max-w-3xl">
            <ChatInput onSend={handleSend} disabled={isTyping} />
            <p className="mt-1.5 text-center text-xs text-gray-400">
              AgentFlow puo commettere errori. Verifica le informazioni importanti.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
