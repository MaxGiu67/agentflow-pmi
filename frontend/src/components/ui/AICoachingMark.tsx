/**
 * AICoachingMark — persistent coaching balloon that attaches below Kanban deal cards.
 *
 * Displays AI-generated suggestions with priority-coloured border,
 * action buttons, and a dismiss control. Appears with a subtle
 * fade-in + slide-up entrance animation.
 */

import { X, Phone, Mail, Eye, Pencil } from 'lucide-react'

export interface CoachingAction {
  label: string
  icon?: string
  onClick: () => void
}

export interface AICoachingMarkProps {
  message: string
  priority: 'high' | 'medium' | 'low'
  actions?: CoachingAction[]
  onDismiss: () => void
  agentName?: string
}

const PRIORITY_STYLES = {
  high: {
    border: 'border-red-400',
    bg: 'bg-red-50/90',
    accent: 'bg-red-400',
    arrow: '#f87171',   // red-400
  },
  medium: {
    border: 'border-amber-400',
    bg: 'bg-amber-50/90',
    accent: 'bg-amber-400',
    arrow: '#fbbf24',   // amber-400
  },
  low: {
    border: 'border-emerald-400',
    bg: 'bg-emerald-50/90',
    accent: 'bg-emerald-400',
    arrow: '#34d399',   // emerald-400
  },
} as const

const ICON_MAP: Record<string, typeof Phone> = {
  phone: Phone,
  email: Mail,
  eye: Eye,
  edit: Pencil,
}

export default function AICoachingMark({
  message,
  priority,
  actions,
  onDismiss,
  agentName = 'SalesBot',
}: AICoachingMarkProps) {
  const style = PRIORITY_STYLES[priority]

  return (
    <div
      className="ai-coaching-mark-enter relative mt-1 max-w-[240px]"
    >
      {/* Arrow pointing UP */}
      <div
        className="absolute -top-[6px] left-5 h-3 w-3 rotate-45 border-l border-t"
        style={{
          backgroundColor: style.arrow,
          borderColor: style.arrow,
        }}
      />

      {/* Card body */}
      <div
        className={`relative overflow-hidden rounded-lg border ${style.border} ${style.bg} backdrop-blur-sm shadow-sm`}
      >
        {/* Left accent bar */}
        <div className={`absolute inset-y-0 left-0 w-1 ${style.accent}`} />

        <div className="py-2 pl-3 pr-2">
          {/* Header: agent badge + dismiss */}
          <div className="flex items-center justify-between">
            <span className="inline-flex items-center gap-1 rounded-full bg-white/60 px-1.5 py-0.5 text-[9px] font-semibold text-gray-600">
              <span className="text-[10px]" role="img" aria-label="robot">🤖</span>
              {agentName}
            </span>
            <button
              onClick={onDismiss}
              className="rounded p-0.5 text-gray-400 hover:bg-white/50 hover:text-gray-600 transition-colors"
              aria-label="Chiudi suggerimento"
            >
              <X className="h-3 w-3" />
            </button>
          </div>

          {/* Message */}
          <p className="mt-1 text-[11px] leading-snug text-gray-700 line-clamp-3">
            {message}
          </p>

          {/* Action buttons */}
          {actions && actions.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-1">
              {actions.map((action, idx) => {
                const IconComp = action.icon ? ICON_MAP[action.icon] : undefined
                return (
                  <button
                    key={idx}
                    onClick={action.onClick}
                    className="inline-flex items-center gap-1 rounded-full bg-white/70 px-2 py-0.5 text-[9px] font-medium text-gray-700 shadow-sm hover:bg-white hover:shadow transition-all"
                  >
                    {IconComp && <IconComp className="h-2.5 w-2.5" />}
                    {action.label}
                  </button>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
