import { useCallback, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

export interface ActionCommand {
  type: 'navigate' | 'set_year' | 'set_filter'
  mode: 'auto' | 'suggest'
  label?: string
  path?: string
  value?: number | string
  filters?: Record<string, string>
}

/** Whitelisted navigation paths */
const ALLOWED_PATHS = new Set([
  '/dashboard',
  '/fatture',
  '/fatture/verifica',
  '/contabilita',
  '/contabilita/bilancio',
  '/scadenze',
  '/fisco',
  '/ceo',
  '/banca',
  '/banca/cashflow',
  '/spese',
  '/cespiti',
  '/impostazioni',
])

/**
 * Hook that executes Action Commands from the chatbot orchestrator.
 *
 * - Whitelist-validated: only known action types and paths are executed
 * - Batch execution: all actions applied in a single render cycle
 * - User priority: if user interacted manually after sending message, actions are skipped
 *
 * Returns:
 *   executeActions(actions) — runs auto actions, returns toast messages
 *   executeSingle(action) — runs a single suggested action (user clicked button)
 */
export function useActionExecutor() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const lastUserInteraction = useRef<number>(0)

  /** Record that the user interacted manually with the UI */
  const recordUserInteraction = useCallback(() => {
    lastUserInteraction.current = Date.now()
  }, [])

  /** Validate and execute a single action. Returns toast message or null. */
  const executeSingle = useCallback(
    (action: ActionCommand): string | null => {
      switch (action.type) {
        case 'navigate': {
          const path = action.path ?? ''
          // Extract base path (before query string) for whitelist check
          const basePath = path.split('?')[0]
          if (!ALLOWED_PATHS.has(basePath)) return null
          navigate(path)
          return action.label ?? `Navigato a ${basePath}`
        }

        case 'set_year': {
          const year = Number(action.value)
          if (isNaN(year) || year < 2020 || year > 2030) return null
          const newParams = new URLSearchParams(searchParams)
          newParams.set('year', String(year))
          setSearchParams(newParams, { replace: true })
          return action.label ?? `Anno impostato su ${year}`
        }

        case 'set_filter': {
          const filters = action.filters ?? {}
          const path = action.path
          const newParams = new URLSearchParams(searchParams)
          for (const [key, val] of Object.entries(filters)) {
            if (typeof val === 'string' && val.length < 100) {
              newParams.set(key, val)
            }
          }
          if (path) {
            const basePath = path.split('?')[0]
            if (ALLOWED_PATHS.has(basePath)) {
              navigate(`${basePath}?${newParams.toString()}`)
            }
          } else {
            setSearchParams(newParams, { replace: true })
          }
          return action.label ?? 'Filtri applicati'
        }

        default:
          return null
      }
    },
    [navigate, searchParams, setSearchParams],
  )

  /** Execute all auto actions in batch. Returns list of toast messages. */
  const executeActions = useCallback(
    (actions: ActionCommand[], sentAt: number): string[] => {
      // User priority: skip if user interacted after the message was sent
      if (lastUserInteraction.current > sentAt) return []

      const toasts: string[] = []
      for (const action of actions) {
        if (action.mode !== 'auto') continue
        const msg = executeSingle(action)
        if (msg) toasts.push(msg)
      }
      return toasts
    },
    [executeSingle],
  )

  return { executeActions, executeSingle, recordUserInteraction }
}
