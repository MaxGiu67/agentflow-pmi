import { useState, useEffect, useRef, useCallback } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || ''

interface WSMessage {
  type: 'typing' | 'message' | 'error'
  data?: {
    conversation_id: string
    message_id: string
    role: string
    content: string
    agent_name: string | null
    agent_type: string | null
    tool_calls: unknown[] | null
    suggestions: string[]
  }
  detail?: string
}

interface UseWebSocketOptions {
  onMessage?: (msg: WSMessage) => void
  onTyping?: () => void
  onError?: (detail: string) => void
  enabled?: boolean
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const { onMessage, onTyping, onError, enabled = true } = options

  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 5
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const connect = useCallback(() => {
    if (!enabled) return

    const token = localStorage.getItem('access_token')
    if (!token) return

    // Build WS URL
    let wsBase = API_BASE
    if (wsBase.startsWith('http://')) {
      wsBase = wsBase.replace('http://', 'ws://')
    } else if (wsBase.startsWith('https://')) {
      wsBase = wsBase.replace('https://', 'wss://')
    } else {
      // Default: same origin
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      wsBase = `${proto}//${window.location.host}`
    }

    const url = `${wsBase}/api/v1/chat/ws?token=${encodeURIComponent(token)}`

    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        reconnectAttempts.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as WSMessage
          if (msg.type === 'typing') {
            onTyping?.()
          } else if (msg.type === 'message') {
            onMessage?.(msg)
          } else if (msg.type === 'error') {
            onError?.(msg.detail ?? 'Errore sconosciuto')
          }
        } catch {
          // Invalid JSON
        }
      }

      ws.onclose = () => {
        setConnected(false)
        wsRef.current = null

        // Auto-reconnect with backoff
        if (reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 30000)
          reconnectAttempts.current++
          reconnectTimeoutRef.current = setTimeout(connect, delay)
        }
      }

      ws.onerror = () => {
        // Will trigger onclose
      }
    } catch {
      setConnected(false)
    }
  }, [enabled, onMessage, onTyping, onError])

  useEffect(() => {
    connect()

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [connect])

  const sendMessage = useCallback(
    (message: string, conversationId?: string) => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({
            message,
            conversation_id: conversationId ?? null,
          }),
        )
        return true
      }
      return false
    },
    [],
  )

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  return { connected, sendMessage, disconnect }
}
