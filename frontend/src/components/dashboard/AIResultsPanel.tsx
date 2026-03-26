import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, X } from 'lucide-react'
import { useAIBlocksStore } from '../../store/aiBlocks'
import ContentBlockRenderer from '../chat/ContentBlockRenderer'

export default function AIResultsPanel() {
  const { blocks, visible, clear } = useAIBlocksStore()

  return (
    <AnimatePresence>
      {visible && blocks.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -20, height: 0 }}
          animate={{ opacity: 1, y: 0, height: 'auto' }}
          exit={{ opacity: 0, y: -20, height: 0 }}
          transition={{ duration: 0.4 }}
          className="mb-6 overflow-hidden rounded-2xl border border-blue-200 bg-gradient-to-r from-blue-50/80 to-white shadow-lg"
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-blue-100 px-5 py-3">
            <div className="flex min-w-0 items-center gap-2">
              <Sparkles className="h-4 w-4 flex-shrink-0 text-blue-500" />
              <span className="flex-shrink-0 text-sm font-semibold text-gray-800">AgentFlow AI</span>
            </div>
            <button
              onClick={clear}
              className="flex-shrink-0 rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-600"
              title="Chiudi risultati AI"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Content blocks */}
          <div className="px-5 py-4">
            <ContentBlockRenderer blocks={blocks as never[]} />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
