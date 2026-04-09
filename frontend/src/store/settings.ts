import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/* ── Types ──────────────────────────────────────────────────────────── */

export type OrbTheme = 'siri' | 'jarvis'
export type JarvisVariant = 'hud-rings' | 'arc-reactor' | 'particle-sphere'

interface SettingsState {
  /** Tema orb del chatbot: 'siri' (CSS conic-gradient) o 'jarvis' (Canvas 2D) */
  orbTheme: OrbTheme
  /** Variante Jarvis: 'hud-rings' | 'arc-reactor' | 'particle-sphere' */
  jarvisVariant: JarvisVariant
  setOrbTheme: (theme: OrbTheme) => void
  setJarvisVariant: (variant: JarvisVariant) => void
}

/* ── Store ──────────────────────────────────────────────────────────── */

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      orbTheme: 'siri',
      jarvisVariant: 'hud-rings',
      setOrbTheme: (orbTheme) => set({ orbTheme }),
      setJarvisVariant: (jarvisVariant) => set({ jarvisVariant }),
    }),
    { name: 'agentflow-settings' },
  ),
)
