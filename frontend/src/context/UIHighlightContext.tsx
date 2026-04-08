/**
 * UIHighlightContext — React Context for AI-driven UI highlights.
 *
 * Sprint 46-47: The Sales Agent can "point at" UI elements by returning
 * ui_actions in chat responses. This context manages the highlight state
 * and auto-clears highlights after 30 seconds.
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
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from 'react'

export interface UIHighlight {
  type: 'highlight' | 'navigate' | 'scroll'
  target: 'deal' | 'stage' | 'contact' | 'activity' | 'section' | 'button' | 'kpi'
  id: string
  style: 'pulse-border' | 'glow' | 'badge'
  color: string
  tooltip: string
}

interface UIHighlightContextType {
  highlights: UIHighlight[]
  setHighlights: (highlights: UIHighlight[]) => void
  clearHighlights: () => void
  getHighlight: (target: string, id: string) => UIHighlight | undefined
  hasHighlight: (target: string, id: string) => boolean
}

const UIHighlightContext = createContext<UIHighlightContextType>({
  highlights: [],
  setHighlights: () => {},
  clearHighlights: () => {},
  getHighlight: () => undefined,
  hasHighlight: () => false,
})

const AUTO_CLEAR_MS = 30_000 // 30 seconds

export function UIHighlightProvider({ children }: { children: ReactNode }) {
  const [highlights, setHighlightsState] = useState<UIHighlight[]>([])
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const clearHighlights = useCallback(() => {
    setHighlightsState([])
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const setHighlights = useCallback(
    (newHighlights: UIHighlight[]) => {
      setHighlightsState(newHighlights)
      // Auto-clear after 30 seconds
      if (timerRef.current) {
        clearTimeout(timerRef.current)
      }
      if (newHighlights.length > 0) {
        timerRef.current = setTimeout(clearHighlights, AUTO_CLEAR_MS)
      }
    },
    [clearHighlights],
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

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [])

  return (
    <UIHighlightContext.Provider
      value={{ highlights, setHighlights, clearHighlights, getHighlight, hasHighlight }}
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
