import { Component, type ReactNode } from 'react'
import { AlertTriangle, RotateCcw } from 'lucide-react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error) {
    // Auto-reload on dynamic import failure (stale chunks after deploy)
    const msg = error.message || ''
    if (
      msg.includes('Failed to fetch dynamically imported module') ||
      msg.includes('Loading chunk') ||
      msg.includes('Loading CSS chunk')
    ) {
      // Prevent infinite reload loop
      const key = 'chunk_reload_ts'
      const last = Number(sessionStorage.getItem(key) || 0)
      if (Date.now() - last > 10000) {
        sessionStorage.setItem(key, String(Date.now()))
        window.location.reload()
      }
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback

      return (
        <div className="flex min-h-[300px] flex-col items-center justify-center gap-4 p-8 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-red-100">
            <AlertTriangle className="h-7 w-7 text-red-500" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Qualcosa e andato storto</h2>
            <p className="mt-1 max-w-md text-sm text-gray-500">
              {this.state.error?.message || 'Errore imprevisto. Riprova.'}
            </p>
          </div>
          <button
            onClick={this.handleRetry}
            className="inline-flex items-center gap-2 rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 transition-colors"
          >
            <RotateCcw className="h-4 w-4" />
            Riprova
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
