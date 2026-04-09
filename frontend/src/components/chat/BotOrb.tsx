import SiriOrb from './SiriOrb'
import JarvisOrb from './JarvisOrb'
import { useSettingsStore, type OrbTheme } from '../../store/settings'

export type { OrbState } from './JarvisOrb'
export { SiriBorder } from './SiriOrb'

import type { OrbState } from './JarvisOrb'

/* ── Props ──────────────────────────────────────────────────────────── */

interface BotOrbProps {
  state: OrbState
  size?: number
  /** Force a specific theme (bypasses settings store) */
  theme?: OrbTheme
  /** Show outer glow halo (for FAB sleep state) — only applies to SiriOrb */
  showGlow?: boolean
  className?: string
  onClick?: () => void
}

/* ── Component ──────────────────────────────────────────────────────── */

/**
 * BotOrb — Unified wrapper that renders either JarvisOrb (SVG + Framer Motion)
 * or SiriOrb (CSS conic-gradient) based on user preference.
 *
 * Default theme: 'jarvis' (the original SVG orb).
 *
 * Usage:
 *   <BotOrb state="idle" size={40} />           // uses settings store
 *   <BotOrb state="thinking" size={58} theme="siri" />  // forced theme
 */
export default function BotOrb({
  state,
  size = 40,
  theme,
  showGlow = false,
  className,
  onClick,
}: BotOrbProps) {
  const storeTheme = useSettingsStore((s) => s.orbTheme)
  const activeTheme = theme ?? storeTheme

  if (activeTheme === 'siri') {
    return (
      <SiriOrb
        state={state}
        size={size}
        showGlow={showGlow}
        className={className}
        onClick={onClick}
      />
    )
  }

  // Default: JarvisOrb — the original SVG + Framer Motion orb
  return (
    <JarvisOrb
      state={state}
      size={size}
      className={className}
    />
  )
}
