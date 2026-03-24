import type { ReactNode } from 'react'
import { User } from 'lucide-react'
import AgentBadge from './AgentBadge'
import { cn } from '../../lib/utils'

interface ChatMessageProps {
  role: 'user' | 'assistant' | 'system'
  content: string | null
  agentName?: string | null
  agentType?: string | null
  createdAt?: string
  userName?: string
}

/**
 * Simple markdown-like rendering:
 * - **bold** -> <strong>
 * - *italic* -> <em>
 * - `code` -> <code>
 * - Newlines -> <br>
 * - Lines starting with "- " -> bullet list items
 * - Numbers in format 1.234,56 or currency are kept as-is
 */
function renderContent(text: string): ReactNode {
  const lines = text.split('\n')
  const elements: ReactNode[] = []
  let listItems: string[] = []

  const flushList = () => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`list-${elements.length}`} className="my-1 ml-4 list-disc space-y-0.5">
          {listItems.map((item, i) => (
            <li key={i} className="text-sm">
              <InlineFormatted text={item} />
            </li>
          ))}
        </ul>,
      )
      listItems = []
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]

    if (line.startsWith('- ') || line.startsWith('* ')) {
      listItems.push(line.slice(2))
      continue
    }

    flushList()

    if (line.trim() === '') {
      elements.push(<br key={`br-${i}`} />)
    } else {
      elements.push(
        <p key={`p-${i}`} className="text-sm">
          <InlineFormatted text={line} />
        </p>,
      )
    }
  }

  flushList()

  return <>{elements}</>
}

function InlineFormatted({ text }: { text: string }) {
  // Process inline formatting: **bold**, *italic*, `code`
  const parts: ReactNode[] = []
  let remaining = text
  let idx = 0

  while (remaining.length > 0) {
    // Bold
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/)
    // Code
    const codeMatch = remaining.match(/`(.+?)`/)
    // Italic (single *)
    const italicMatch = remaining.match(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/)

    // Find earliest match
    type MatchInfo = { match: RegExpMatchArray; type: 'bold' | 'code' | 'italic' }
    const matches: MatchInfo[] = []
    if (boldMatch?.index !== undefined) matches.push({ match: boldMatch, type: 'bold' })
    if (codeMatch?.index !== undefined) matches.push({ match: codeMatch, type: 'code' })
    if (italicMatch?.index !== undefined) matches.push({ match: italicMatch, type: 'italic' })

    if (matches.length === 0) {
      parts.push(<span key={idx++}>{remaining}</span>)
      break
    }

    matches.sort((a, b) => (a.match.index ?? 0) - (b.match.index ?? 0))
    const first = matches[0]
    const matchIdx = first.match.index ?? 0

    if (matchIdx > 0) {
      parts.push(<span key={idx++}>{remaining.slice(0, matchIdx)}</span>)
    }

    if (first.type === 'bold') {
      parts.push(<strong key={idx++}>{first.match[1]}</strong>)
    } else if (first.type === 'code') {
      parts.push(
        <code key={idx++} className="rounded bg-gray-100 px-1 py-0.5 text-xs font-mono">
          {first.match[1]}
        </code>,
      )
    } else {
      parts.push(<em key={idx++}>{first.match[1]}</em>)
    }

    remaining = remaining.slice(matchIdx + first.match[0].length)
  }

  return <>{parts}</>
}

function formatTime(dateStr: string | undefined): string {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    return d.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

export default function ChatMessage({
  role,
  content,
  agentName,
  agentType,
  createdAt,
  userName,
}: ChatMessageProps) {
  const isUser = role === 'user'
  const displayContent = content ?? ''

  return (
    <div className={cn('flex gap-3', isUser ? 'flex-row-reverse' : 'flex-row')}>
      {/* Avatar */}
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm',
          isUser ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600',
        )}
      >
        {isUser ? (
          <User className="h-4 w-4" />
        ) : (
          <span>{agentType === 'orchestrator' || !agentType ? '\u{1f916}' : '\u{1f4ac}'}</span>
        )}
      </div>

      {/* Message bubble */}
      <div className={cn('max-w-[75%] space-y-1', isUser ? 'items-end' : 'items-start')}>
        {/* Header */}
        <div className={cn('flex items-center gap-2', isUser ? 'justify-end' : 'justify-start')}>
          {isUser ? (
            <span className="text-xs font-medium text-gray-500">{userName ?? 'Tu'}</span>
          ) : (
            <AgentBadge agentType={agentType} agentName={agentName} />
          )}
          {createdAt && <span className="text-xs text-gray-400">{formatTime(createdAt)}</span>}
        </div>

        {/* Content */}
        <div
          className={cn(
            'rounded-2xl px-4 py-2.5',
            isUser
              ? 'rounded-tr-sm bg-blue-600 text-white'
              : 'rounded-tl-sm border border-gray-100 bg-white text-gray-900 shadow-sm',
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap text-sm">{displayContent}</p>
          ) : (
            <div className="space-y-1">{renderContent(displayContent)}</div>
          )}
        </div>
      </div>
    </div>
  )
}
