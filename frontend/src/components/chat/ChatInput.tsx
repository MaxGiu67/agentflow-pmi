import { useState, useRef, useCallback } from 'react'
import type { KeyboardEvent } from 'react'
import { SendHorizonal } from 'lucide-react'

interface ChatInputProps {
  onSend: (message: string) => void
  disabled?: boolean
  placeholder?: string
}

export default function ChatInput({
  onSend,
  disabled = false,
  placeholder = 'Scrivi un messaggio...',
}: ChatInputProps) {
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSend = useCallback(() => {
    const trimmed = text.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setText('')
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }, [text, disabled, onSend])

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = () => {
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = `${Math.min(el.scrollHeight, 160)}px`
    }
  }

  return (
    <div className="flex items-end gap-2 rounded-xl border border-gray-200 bg-white px-3 py-2 shadow-sm focus-within:border-blue-400 focus-within:ring-1 focus-within:ring-blue-400">
      <textarea
        ref={textareaRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        disabled={disabled}
        placeholder={placeholder}
        rows={1}
        className="max-h-40 flex-1 resize-none bg-transparent text-sm text-gray-900 placeholder-gray-400 outline-none disabled:opacity-50"
      />
      <button
        onClick={handleSend}
        disabled={disabled || !text.trim()}
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white transition-colors hover:bg-blue-700 disabled:bg-gray-300 disabled:text-gray-500"
      >
        <SendHorizonal className="h-4 w-4" />
      </button>
    </div>
  )
}
