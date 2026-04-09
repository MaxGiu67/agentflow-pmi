import SiriOrb, { type OrbState } from './SiriOrb'
import JarvisCanvasOrb from './JarvisCanvasOrb'
import { useSettingsStore, type OrbTheme } from '../../store/settings'

export type { OrbState } from './SiriOrb'
export { SiriBorder } from './SiriOrb'

/* ── Props ──────────────────────────────────────────────────────────── */

interface BotOrbProps {
  state: OrbState
  size?: number
  /** Force a specific theme (bypasses settings store) */
  theme?: OrbTheme
  /** Show outer glow halo (for FAB sleep state) */
  showGlow?: boolean
  className?: string
  onClick?: () => void
}

/* ── Component ──────────────────────────────────────────────────────── */

/**
 * BotOrb — Unified wrapper that renders either SiriOrb or JarvisCanvasOrb
 * based on user preference from the settings store.
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
  const jarvisVariant = useSettingsStore((s) => s.jarvisVariant)
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

  return (
    <JarvisCanvasOrb
      state={state}
      size={size}
      variant={jarvisVariant}
      className={className}
      onClick={onClick}
    />
  )
}
