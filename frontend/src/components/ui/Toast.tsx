import { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, X } from 'lucide-react'

interface ToastProps {
  message: string | null
  onClose: () => void
  duration?: number
}

export default function Toast({ message, onClose, duration = 3000 }: ToastProps) {
  useEffect(() => {
    if (!message) return
    const timer = setTimeout(onClose, duration)
    return () => clearTimeout(timer)
  }, [message, onClose, duration])

  return (
    <AnimatePresence>
      {message && (
        <motion.div
          initial={{ opacity: 0, y: 20, x: '-50%' }}
          animate={{ opacity: 1, y: 0, x: '-50%' }}
          exit={{ opacity: 0, y: 20, x: '-50%' }}
          transition={{ duration: 0.3 }}
          className="fixed bottom-20 left-1/2 z-[60] flex items-center gap-2 rounded-xl border border-blue-100 bg-white/95 px-4 py-2.5 shadow-lg backdrop-blur-xl md:bottom-24"
        >
          <Sparkles className="h-4 w-4 flex-shrink-0 text-blue-500" />
          <span className="text-sm text-gray-700">{message}</span>
          <button
            onClick={onClose}
            className="ml-1 p-0.5 text-gray-400 hover:text-gray-600"
          >
            <X className="h-3 w-3" />
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
