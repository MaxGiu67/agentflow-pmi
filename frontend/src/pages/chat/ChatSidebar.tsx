import { Plus, MessageSquare, Trash2 } from 'lucide-react'
import { cn } from '../../lib/utils'

interface ConversationItem {
  id: string
  title: string | null
  status: string
  message_count: number
  last_message_preview: string | null
  created_at: string
  updated_at: string
}

interface ChatSidebarProps {
  conversations: ConversationItem[]
  activeConversationId: string | null
  onSelectConversation: (id: string) => void
  onNewConversation: () => void
  onDeleteConversation: (id: string) => void
  isLoading?: boolean
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

    return d.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit' })
  } catch {
    return ''
  }
}

export default function ChatSidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  isLoading,
}: ChatSidebarProps) {
  return (
    <div className="flex h-full w-72 flex-col border-r border-gray-200 bg-gray-50">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-200 p-4">
        <h2 className="text-sm font-semibold text-gray-900">Conversazioni</h2>
        <button
          onClick={onNewConversation}
          className="flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-700"
        >
          <Plus className="h-3.5 w-3.5" />
          Nuova chat
        </button>
      </div>

      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto p-2">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
          </div>
        ) : conversations.length === 0 ? (
          <div className="py-8 text-center">
            <MessageSquare className="mx-auto mb-2 h-8 w-8 text-gray-300" />
            <p className="text-xs text-gray-400">Nessuna conversazione</p>
            <p className="mt-1 text-xs text-gray-400">Inizia una nuova chat!</p>
          </div>
        ) : (
          <ul className="space-y-1">
            {conversations.map((conv) => (
              <li key={conv.id}>
                <button
                  onClick={() => onSelectConversation(conv.id)}
                  className={cn(
                    'group flex w-full items-start gap-2 rounded-lg px-3 py-2.5 text-left transition-colors',
                    activeConversationId === conv.id
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-700 hover:bg-gray-100',
                  )}
                >
                  <MessageSquare className="mt-0.5 h-4 w-4 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">
                      {conv.title ?? 'Nuova conversazione'}
                    </p>
                    {conv.last_message_preview && (
                      <p className="mt-0.5 truncate text-xs text-gray-400">
                        {conv.last_message_preview}
                      </p>
                    )}
                    <p className="mt-0.5 text-xs text-gray-400">
                      {formatRelativeDate(conv.updated_at)}
                    </p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onDeleteConversation(conv.id)
                    }}
                    className="mt-0.5 hidden shrink-0 rounded p-0.5 text-gray-400 hover:bg-red-50 hover:text-red-500 group-hover:block"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
