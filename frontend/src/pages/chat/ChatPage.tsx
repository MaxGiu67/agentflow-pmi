import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { MessageSquare, Trash2, ChevronLeft, Clock, Bot } from 'lucide-react'
import ChatMessage from '../../components/chat/ChatMessage'
import {
  useConversations,
  useConversation,
  useDeleteConversation,
} from '../../api/hooks'
import { useAuthStore } from '../../store/auth'
import PageHeader from '../../components/ui/PageHeader'

interface MessageItem {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string | null
  agent_name?: string | null
  agent_type?: string | null
  created_at: string
}

interface ConversationItem {
  id: string
  title: string | null
  status: string
  message_count: number
  last_message_preview: string | null
  created_at: string
  updated_at: string
}

function formatRelativeDate(dateStr: string): string {
  try {
    const d = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - d.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))

    if (days === 0) return 'Oggi'
    if (days === 1) return 'Ieri'
    if (days < 7) return `${days}g fa`

    return d.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' })
  } catch {
    return ''
  }
}

function formatDateTime(dateStr: string): string {
  try {
    const d = new Date(dateStr)
    return d.toLocaleString('it-IT', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ''
  }
}

export default function ChatPage() {
  const { conversationId: paramConvId } = useParams<{ conversationId?: string }>()
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)

  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(
    paramConvId ?? null,
  )

  // Queries
  const { data: conversationsData, isLoading: convListLoading } = useConversations()
  const { data: conversationDetail, isLoading: detailLoading } = useConversation(
    selectedConversationId ?? '',
  )

  // Mutations
  const deleteConversation = useDeleteConversation()

  // Sync URL param with state
  useEffect(() => {
    if (paramConvId && paramConvId !== selectedConversationId) {
      setSelectedConversationId(paramConvId)
    }
  }, [paramConvId, selectedConversationId])

  const messages: MessageItem[] = (conversationDetail?.messages ?? []).map((m: MessageItem) => ({
    id: m.id,
    role: m.role as 'user' | 'assistant' | 'system',
    content: m.content,
    agent_name: m.agent_name,
    agent_type: m.agent_type,
    created_at: m.created_at,
  }))

  const handleSelectConversation = useCallback(
    (id: string) => {
      setSelectedConversationId(id)
      navigate(`/chat/${id}`, { replace: true })
    },
    [navigate],
  )

  const handleDeleteConversation = useCallback(
    async (id: string, e: React.MouseEvent) => {
      e.stopPropagation()
      await deleteConversation.mutateAsync(id)
      if (selectedConversationId === id) {
        setSelectedConversationId(null)
        navigate('/chat', { replace: true })
      }
    },
    [selectedConversationId, deleteConversation, navigate],
  )

  const handleBack = useCallback(() => {
    setSelectedConversationId(null)
    navigate('/chat', { replace: true })
  }, [navigate])

  const conversations: ConversationItem[] = conversationsData?.items ?? []

  return (
    <div className="mx-auto w-full max-w-5xl px-4 pb-8">
      <PageHeader
        title="Storico Conversazioni"
        subtitle={`${conversations.length} conversazion${conversations.length === 1 ? 'e' : 'i'} con AgentFlow`}
      />

      {/* Mobile: show detail or list */}
      {selectedConversationId ? (
        /* Conversation detail — read-only */
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm">
          {/* Detail header */}
          <div className="flex items-center gap-3 border-b border-gray-200 px-4 py-3">
            <button
              onClick={handleBack}
              className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
            <div className="min-w-0 flex-1">
              <h3 className="truncate text-sm font-semibold text-gray-900">
                {conversationDetail?.title ?? 'Conversazione'}
              </h3>
              {conversationDetail?.created_at && (
                <p className="text-xs text-gray-400">
                  {formatDateTime(conversationDetail.created_at)}
                </p>
              )}
            </div>
            <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs text-gray-500">
              {messages.length} messagg{messages.length === 1 ? 'io' : 'i'}
            </span>
          </div>

          {/* Messages — read-only */}
          <div className="max-h-[calc(100vh-16rem)] overflow-y-auto px-4 py-6">
            {detailLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
              </div>
            ) : messages.length === 0 ? (
              <p className="py-12 text-center text-sm text-gray-400">
                Nessun messaggio in questa conversazione.
              </p>
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
              </div>
            )}
          </div>

          {/* Footer hint */}
          <div className="border-t border-gray-100 px-4 py-3 text-center">
            <p className="text-xs text-gray-400">
              Questa e una vista di sola lettura. Usa il chatbot in basso a destra per continuare la
              conversazione.
            </p>
          </div>
        </div>
      ) : (
        /* Conversation list */
        <>
          {convListLoading ? (
            <div className="flex items-center justify-center py-20">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
            </div>
          ) : conversations.length === 0 ? (
            /* Empty state */
            <div className="flex flex-col items-center justify-center rounded-xl border border-gray-200 bg-white py-20 shadow-sm">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-blue-50">
                <Bot className="h-8 w-8 text-blue-600" />
              </div>
              <h2 className="mb-1 text-lg font-semibold text-gray-900">Nessuna conversazione</h2>
              <p className="mb-4 max-w-sm text-center text-sm text-gray-500">
                Inizia a parlare con AgentFlow usando il chatbot in basso a destra. Le tue
                conversazioni appariranno qui.
              </p>
            </div>
          ) : (
            /* Conversation cards */
            <div className="space-y-2">
              {conversations.map((conv) => (
                <button
                  key={conv.id}
                  onClick={() => handleSelectConversation(conv.id)}
                  className="group flex w-full items-center gap-4 rounded-xl border border-gray-200 bg-white px-5 py-4 text-left shadow-sm transition-all hover:border-blue-200 hover:shadow-md"
                >
                  {/* Icon */}
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-50 text-blue-600 transition-colors group-hover:bg-blue-100">
                    <MessageSquare className="h-5 w-5" />
                  </div>

                  {/* Content */}
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="truncate text-sm font-semibold text-gray-900">
                        {conv.title ?? 'Nuova conversazione'}
                      </h3>
                      <span className="shrink-0 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500">
                        {conv.message_count} msg
                      </span>
                    </div>
                    {conv.last_message_preview && (
                      <p className="mt-0.5 truncate text-sm text-gray-500">
                        {conv.last_message_preview}
                      </p>
                    )}
                  </div>

                  {/* Date + delete */}
                  <div className="flex shrink-0 items-center gap-3">
                    <div className="flex items-center gap-1 text-xs text-gray-400">
                      <Clock className="h-3.5 w-3.5" />
                      {formatRelativeDate(conv.updated_at)}
                    </div>
                    <button
                      onClick={(e) => handleDeleteConversation(conv.id, e)}
                      className="hidden rounded-lg p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-500 group-hover:block"
                      title="Elimina conversazione"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
