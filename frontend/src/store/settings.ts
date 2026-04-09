import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/* ── Types ──────────────────────────────────────────────────────────── */

export type OrbTheme = 'jarvis' | 'siri'

interface SettingsState {
  /** Tema orb del chatbot: 'jarvis' (SVG + Framer Motion) o 'siri' (CSS conic-gradient) */
  orbTheme: OrbTheme
  setOrbTheme: (theme: OrbTheme) => void
}

/* ── Store ──────────────────────────────────────────────────────────── */

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      orbTheme: 'jarvis',
      setOrbTheme: (orbTheme) => set({ orbTheme }),
    }),
    { name: 'agentflow-settings' },
  ),
)
