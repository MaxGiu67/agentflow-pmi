import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuthStore } from '../../store/auth'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const requestPasswordReset = useAuthStore((s) => s.requestPasswordReset)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await requestPasswordReset(email)
      setSent(true)
    } catch {
      // Always show success — anti-enumeration
      setSent(true)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-[100dvh] items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <Link to="/">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-purple-600 text-lg font-bold text-white">AF</div>
          </Link>
          <h1 className="text-2xl font-bold text-gray-900" style={{ fontFamily: 'var(--font-display)' }}>Recupera password</h1>
          <p className="mt-1 text-sm text-gray-500">Inserisci la tua email per ricevere il link di reset</p>
        </div>

        <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          {sent ? (
            <div className="text-center space-y-4">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-green-100">
                <svg className="h-7 w-7 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div>
                <p className="font-medium text-gray-900">Controlla la tua casella email</p>
                <p className="mt-1 text-sm text-gray-500">
                  Se l'indirizzo e associato a un account, riceverai un link per reimpostare la password.
                </p>
              </div>
              <Link to="/login" className="inline-block text-sm font-medium text-purple-600 hover:underline">
                Torna al login
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              {error && (
                <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>
              )}

              <div className="mb-6">
                <label htmlFor="email" className="mb-1 block text-sm font-medium text-gray-700">Email</label>
                <input
                  id="email" type="email" required value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-purple-500 focus:ring-1 focus:ring-purple-500 focus:outline-none"
                  placeholder="nome@azienda.it"
                />
              </div>

              <button type="submit" disabled={loading}
                className="w-full rounded-lg bg-purple-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50">
                {loading ? 'Invio in corso...' : 'Invia link di reset'}
              </button>

              <p className="mt-4 text-center text-sm text-gray-500">
                <Link to="/login" className="text-purple-600 hover:underline">Torna al login</Link>
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
