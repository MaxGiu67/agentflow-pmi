import { useState } from 'react'
import { Link, useSearchParams, useNavigate } from 'react-router-dom'
import api from '../../api/client'

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token') || ''

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (password.length < 8) {
      setError('La password deve avere almeno 8 caratteri')
      return
    }
    if (password !== confirmPassword) {
      setError('Le password non coincidono')
      return
    }
    if (!token) {
      setError('Link non valido. Richiedi un nuovo reset.')
      return
    }

    setLoading(true)
    try {
      await api.post('/auth/password-reset/confirm', { token, new_password: password })
      setSuccess(true)
      setTimeout(() => navigate('/login'), 3000)
    } catch {
      setError('Il link e scaduto o non valido. Richiedi un nuovo reset.')
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
    return (
      <div className="flex min-h-[100dvh] items-center justify-center bg-gray-50 px-4">
        <div className="w-full max-w-md text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-purple-600 text-lg font-bold text-white">AF</div>
          <h1 className="text-xl font-bold text-gray-900">Link non valido</h1>
          <p className="mt-2 text-sm text-gray-500">Il link di reset password non e valido o e mancante.</p>
          <Link to="/forgot-password" className="mt-4 inline-block text-sm font-medium text-purple-600 hover:underline">
            Richiedi un nuovo link
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-[100dvh] items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <Link to="/">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-purple-600 text-lg font-bold text-white">AF</div>
          </Link>
          <h1 className="text-2xl font-bold text-gray-900" style={{ fontFamily: 'var(--font-display)' }}>Nuova password</h1>
          <p className="mt-1 text-sm text-gray-500">Scegli una nuova password per il tuo account</p>
        </div>

        <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
          {success ? (
            <div className="text-center space-y-4">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-green-100">
                <svg className="h-7 w-7 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div>
                <p className="font-medium text-gray-900">Password aggiornata!</p>
                <p className="mt-1 text-sm text-gray-500">Verrai reindirizzato al login...</p>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>
              )}

              <div>
                <label htmlFor="password" className="mb-1 block text-sm font-medium text-gray-700">Nuova password</label>
                <input
                  id="password" type="password" required value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-purple-500 focus:ring-1 focus:ring-purple-500 focus:outline-none"
                  placeholder="Minimo 8 caratteri"
                />
              </div>

              <div>
                <label htmlFor="confirmPassword" className="mb-1 block text-sm font-medium text-gray-700">Conferma password</label>
                <input
                  id="confirmPassword" type="password" required value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-purple-500 focus:ring-1 focus:ring-purple-500 focus:outline-none"
                  placeholder="Ripeti la password"
                />
              </div>

              <button type="submit" disabled={loading}
                className="w-full rounded-lg bg-purple-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50">
                {loading ? 'Salvataggio...' : 'Salva nuova password'}
              </button>

              <p className="text-center text-sm text-gray-500">
                <Link to="/login" className="text-purple-600 hover:underline">Torna al login</Link>
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  )
}
