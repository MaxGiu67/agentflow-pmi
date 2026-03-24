import { cn } from '../../lib/utils'

const AGENT_COLORS: Record<string, string> = {
  fisco: 'bg-blue-100 text-blue-700',
  conta: 'bg-green-100 text-green-700',
  cashflow: 'bg-amber-100 text-amber-700',
  conto_economico: 'bg-purple-100 text-purple-700',
  normativo: 'bg-indigo-100 text-indigo-700',
  parser: 'bg-gray-100 text-gray-700',
  learning: 'bg-pink-100 text-pink-700',
  ocr: 'bg-teal-100 text-teal-700',
  orchestrator: 'bg-slate-100 text-slate-700',
}

const AGENT_ICONS: Record<string, string> = {
  fisco: '\u{1f4cb}',
  conta: '\u{1f4d2}',
  cashflow: '\u{1f4b0}',
  conto_economico: '\u{1f3d7}\ufe0f',
  normativo: '\u2696\ufe0f',
  parser: '\u{1f4c4}',
  learning: '\u{1f9e0}',
  ocr: '\u{1f4f7}',
  orchestrator: '\u{1f916}',
}

interface AgentBadgeProps {
  agentType: string | null | undefined
  agentName: string | null | undefined
  className?: string
}

export default function AgentBadge({ agentType, agentName, className }: AgentBadgeProps) {
  const type = agentType ?? 'orchestrator'
  const colorClass = AGENT_COLORS[type] ?? 'bg-gray-100 text-gray-700'
  const icon = AGENT_ICONS[type] ?? '\u{1f916}'
  const name = agentName ?? 'AgentFlow'

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
        colorClass,
        className,
      )}
    >
      <span>{icon}</span>
      <span>{name}</span>
    </span>
  )
}
