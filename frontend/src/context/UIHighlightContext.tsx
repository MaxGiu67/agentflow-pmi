/**
 * UIHighlightContext — React Context for AI-driven UI highlights.
 *
 * Sprint 46-47: The Sales Agent can "point at" UI elements by returning
 * ui_actions in chat responses. This context manages the highlight state.
 * Highlights are permanent until individually dismissed or the chatbot closes.
 *
 * Target types:
 * - deal: highlight a deal card on the Kanban or deal detail
 * - stage: highlight a pipeline stage column
 * - contact: highlight a contact row
 * - activity: highlight an activity entry
 * - section: highlight a section of the deal detail (offer, resources, documents, activities, order)
 * - button: highlight a specific button (create-offer, approve-offer, assign-resource, create-activity)
 * - kpi: highlight a dashboard KPI card
 */

import {
  createContext,
  useCallback,
  useContext,
  useState,
  type ReactNode,
} from 'react'

export interface CoachingData {
  message: string
  priority: 'high' | 'medium' | 'low'
  actions?: Array<{ label: string; icon?: string; href?: string }>
}

export interface UIHighlight {
  type: 'highlight' | 'navigate' | 'scroll'
  target: 'deal' | 'stage' | 'contact' | 'activity' | 'section' | 'button' | 'kpi'
  id: string
  style: 'pulse-border' | 'glow' | 'badge'
  color: string
  tooltip: string
  coaching?: CoachingData
}

interface UIHighlightContextType {
  highlights: UIHighlight[]
  setHighlights: (highlights: UIHighlight[]) => void
  clearHighlights: () => void
  dismissHighlight: (id: string) => void
  getHighlight: (target: string, id: string) => UIHighlight | undefined
  hasHighlight: (target: string, id: string) => boolean
}

const UIHighlightContext = createContext<UIHighlightContextType>({
  highlights: [],
  setHighlights: () => {},
  clearHighlights: () => {},
  dismissHighlight: () => {},
  getHighlight: () => undefined,
  hasHighlight: () => false,
})

export function UIHighlightProvider({ children }: { children: ReactNode }) {
  const [highlights, setHighlightsState] = useState<UIHighlight[]>([])

  const clearHighlights = useCallback(() => {
    setHighlightsState([])
  }, [])

  const dismissHighlight = useCallback((id: string) => {
    setHighlightsState((prev) => prev.filter((h) => h.id !== id))
  }, [])

  const setHighlights = useCallback(
    (newHighlights: UIHighlight[]) => {
      setHighlightsState(newHighlights)
    },
    [],
  )

  const getHighlight = useCallback(
    (target: string, id: string) => {
      return highlights.find((h) => h.target === target && h.id === id)
    },
    [highlights],
  )

  const hasHighlight = useCallback(
    (target: string, id: string) => {
      return highlights.some((h) => h.target === target && h.id === id)
    },
    [highlights],
  )

  return (
    <UIHighlightContext.Provider
      value={{ highlights, setHighlights, clearHighlights, dismissHighlight, getHighlight, hasHighlight }}
    >
      {children}
    </UIHighlightContext.Provider>
  )
}

/**
 * Hook to access UI highlights.
 *
 * Usage in page components:
 * ```tsx
 * const { hasHighlight, getHighlight, clearHighlights } = useUIHighlights()
 *
 * // Check if a deal card should be highlighted
 * const highlight = getHighlight('deal', deal.id)
 * if (highlight) {
 *   className += ' ai-highlight-pulse'
 *   style.borderColor = highlight.color
 * }
 * ```
 */
export function useUIHighlights() {
  return useContext(UIHighlightContext)
}

/**
 * Helper component: renders a tooltip bubble for an AI highlight.
 */
export function AIHighlightTooltip({
  highlight,
  onDismiss,
}: {
  highlight: UIHighlight
  onDismiss?: () => void
}) {
  if (!highlight.tooltip) return null

  return (
    <div
      className="ai-highlight-tooltip"
      style={{ '--ai-color': highlight.color } as React.CSSProperties}
      onClick={onDismiss}
      role="tooltip"
    >
      <span className="ai-highlight-tooltip-icon">AI</span>
      <span className="ai-highlight-tooltip-text">{highlight.tooltip}</span>
    </div>
  )
}
