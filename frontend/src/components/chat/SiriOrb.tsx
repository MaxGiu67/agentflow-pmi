import { useEffect, useRef, type CSSProperties } from 'react'
import styles from './SiriOrb.module.css'

/* ── Types ──────────────────────────────────────────────────────────── */

export type OrbState = 'sleep' | 'idle' | 'thinking' | 'responding' | 'error'

interface SiriOrbProps {
  state: OrbState
  size?: number
  showGlow?: boolean
  className?: string
  onClick?: () => void
}

/* ── Color configs per state (oklch, low saturation for AgentFlow) ── */

const ORB_COLORS: Record<OrbState, Record<string, string>> = {
  sleep: {
    '--siri-bg': 'oklch(14% 0.005 220)',
    '--siri-c1': 'oklch(40% 0.04 220)',
    '--siri-c2': 'oklch(35% 0.04 210)',
    '--siri-c3': 'oklch(38% 0.03 230)',
    '--siri-blur': '1.5px',
    '--siri-contrast': '1.2',
    '--siri-shadow': '0.5px',
    '--siri-speed': '35s',
    '--siri-glow-color': 'rgba(125, 211, 252, 0.4)',
  },
  idle: {
    '--siri-bg': 'oklch(22% 0.01 220)',
    '--siri-c1': 'oklch(65% 0.08 220)',
    '--siri-c2': 'oklch(60% 0.10 210)',
    '--siri-c3': 'oklch(58% 0.07 230)',
    '--siri-blur': '2px',
    '--siri-contrast': '1.4',
    '--siri-shadow': '1px',
    '--siri-speed': '20s',
    '--siri-glow-color': 'rgba(125, 211, 252, 0.5)',
  },
  thinking: {
    '--siri-bg': 'oklch(18% 0.02 240)',
    '--siri-c1': 'oklch(60% 0.12 250)',
    '--siri-c2': 'oklch(55% 0.14 270)',
    '--siri-c3': 'oklch(62% 0.10 230)',
    '--siri-blur': '2px',
    '--siri-contrast': '1.5',
    '--siri-shadow': '1px',
    '--siri-speed': '4s',
    '--siri-glow-color': 'rgba(165, 180, 252, 0.6)',
  },
  responding: {
    '--siri-bg': 'oklch(20% 0.01 180)',
    '--siri-c1': 'oklch(65% 0.09 180)',
    '--siri-c2': 'oklch(60% 0.08 195)',
    '--siri-c3': 'oklch(68% 0.07 165)',
    '--siri-blur': '2px',
    '--siri-contrast': '1.4',
    '--siri-shadow': '1px',
    '--siri-speed': '10s',
    '--siri-glow-color': 'rgba(110, 231, 183, 0.5)',
  },
  error: {
    '--siri-bg': 'oklch(18% 0.02 25)',
    '--siri-c1': 'oklch(60% 0.15 25)',
    '--siri-c2': 'oklch(55% 0.12 35)',
    '--siri-c3': 'oklch(58% 0.10 15)',
    '--siri-blur': '2px',
    '--siri-contrast': '1.5',
    '--siri-shadow': '1px',
    '--siri-speed': '2s',
    '--siri-glow-color': 'rgba(248, 113, 113, 0.5)',
  },
}

/* ── Component ──────────────────────────────────────────────────────── */

/**
 * SiriOrb — Pure CSS animated orb using conic-gradient technique.
 *
 * Uses @property for GPU-accelerated rotation, 6 overlapping conic-gradients
 * for the fluid color effect, and blur/contrast for depth.
 *
 * Zero JS rendering — all animation runs on the compositor thread.
 */
export default function SiriOrb({
  state,
  size = 40,
  showGlow = false,
  className = '',
  onClick,
}: SiriOrbProps) {
  const orbRef = useRef<HTMLDivElement>(null)

  // Apply CSS custom properties when state changes
  useEffect(() => {
    const el = orbRef.current
    if (!el) return

    const colors = ORB_COLORS[state]
    for (const [key, value] of Object.entries(colors)) {
      el.style.setProperty(key, value)
    }
  }, [state])

  const wrapperStyle: CSSProperties = {
    width: size,
    height: size,
    position: 'relative',
    flexShrink: 0,
  }

  return (
    <div
      ref={orbRef}
      className={className}
      style={wrapperStyle}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      aria-label={onClick ? 'Apri chat AgentFlow' : 'AgentFlow AI'}
      onKeyDown={onClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') onClick() } : undefined}
    >
      {showGlow && <div className={styles.glow} />}
      <div
        className={styles.orb}
        style={{ width: size, height: size }}
      />
    </div>
  )
}

/* ── SiriBorder — Animated border wrapper for chatbar ──────────────── */

export interface SiriBorderProps {
  state: OrbState
  enabled?: boolean
  children: React.ReactNode
  className?: string
}

const BORDER_COLORS: Record<string, Record<string, string>> = {
  idle: {
    '--siri-bc1': 'rgba(125,211,252,0.35)',
    '--siri-bc2': 'rgba(165,180,252,0.25)',
    '--siri-bc3': 'rgba(110,231,183,0.2)',
    '--siri-border-speed': '8s',
    '--siri-border-opacity': '0.5',
    '--siri-glow-opacity': '0.06',
  },
  thinking: {
    '--siri-bc1': 'rgba(165,180,252,0.75)',
    '--siri-bc2': 'rgba(192,132,252,0.65)',
    '--siri-bc3': 'rgba(125,211,252,0.55)',
    '--siri-border-speed': '2s',
    '--siri-border-opacity': '0.9',
    '--siri-glow-opacity': '0.15',
  },
  responding: {
    '--siri-bc1': 'rgba(110,231,183,0.55)',
    '--siri-bc2': 'rgba(125,211,252,0.45)',
    '--siri-bc3': 'rgba(165,180,252,0.35)',
    '--siri-border-speed': '5s',
    '--siri-border-opacity': '0.7',
    '--siri-glow-opacity': '0.1',
  },
  error: {
    '--siri-bc1': 'rgba(248,113,113,0.7)',
    '--siri-bc2': 'rgba(251,146,60,0.6)',
    '--siri-bc3': 'rgba(248,113,113,0.5)',
    '--siri-border-speed': '1.5s',
    '--siri-border-opacity': '0.85',
    '--siri-glow-opacity': '0.12',
  },
}

/**
 * SiriBorder — Animated conic-gradient border using mask-composite: exclude.
 * Wraps any content (chatbar, response panel) with a Siri-style rotating border.
 */
export function SiriBorder({ state, enabled = true, children, className = '' }: SiriBorderProps) {
  const borderRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = borderRef.current
    if (!el || !enabled) return

    // Map orb state to border state (sleep maps to idle)
    const borderState = state === 'sleep' ? 'idle' : state
    const colors = BORDER_COLORS[borderState] ?? BORDER_COLORS.idle

    for (const [key, value] of Object.entries(colors)) {
      el.style.setProperty(key, value)
    }
  }, [state, enabled])

  if (!enabled) {
    return <div className={className}>{children}</div>
  }

  return (
    <div ref={borderRef} className={`${styles.border} ${className}`}>
      {children}
    </div>
  )
}
