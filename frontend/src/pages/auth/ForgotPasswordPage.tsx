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
      setError('Errore durante la richiesta. Riprova.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-600 text-lg font-bold text-white">
            CB
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Recupera password</h1>
          <p className="mt-2 text-sm text-gray-500">
            Inserisci la tua email per ricevere il link di reset
          </p>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          {sent ? (
            <div className="text-center">
              <div className="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-700">
                Se l'email e registrata, riceverai un link per reimpostare la password.
              </div>
              <Link to="/login" className="text-sm text-blue-600 hover:underline">
                Torna al login
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              {error && (
                <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>
              )}

              <div className="mb-6">
                <label htmlFor="email" className="mb-1 block text-sm font-medium text-gray-700">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                  placeholder="nome@azienda.it"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? 'Invio in corso...' : 'Invia link di reset'}
              </button>

              <p className="mt-4 text-center text-sm text-gray-500">
                <Link to="/login" className="text-blue-600 hover:underline">
                  Torna al login
                </Link>
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
