import { create } from 'zustand'

export interface ContentBlock {
  type: 'stat_row' | 'bar_chart' | 'table'
  title?: string
  items?: { label: string; value: number; format?: string; sub?: string }[]
  data?: Record<string, unknown>[]
  keys?: string[]
  colors?: string[]
  columns?: string[]
  rows?: (string | number)[][]
}

interface AIBlocksState {
  blocks: ContentBlock[]
  textSummary: string
  visible: boolean
  setBlocks: (blocks: ContentBlock[], text: string) => void
  clear: () => void
}

export const useAIBlocksStore = create<AIBlocksState>((set) => ({
  blocks: [],
  textSummary: '',
  visible: false,
  setBlocks: (blocks, text) => set({ blocks, textSummary: text, visible: true }),
  clear: () => set({ blocks: [], textSummary: '', visible: false }),
}))
