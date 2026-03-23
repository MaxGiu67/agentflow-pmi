import { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import api from '../../api/client'

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!token) {
      setStatus('error')
      setMessage('Token di verifica mancante')
      return
    }

    api.post('/auth/verify-email', { token })
      .then(() => {
        setStatus('success')
        setMessage('Email verificata con successo!')
      })
      .catch((err) => {
        setStatus('error')
        setMessage(err.response?.data?.detail || 'Token non valido o scaduto')
      })
  }, [token])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white rounded-xl shadow-sm border p-8 text-center">
        {status === 'loading' && (
          <>
            <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-gray-900">Verifica in corso...</h2>
          </>
        )}

        {status === 'success' && (
          <>
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">{message}</h2>
            <p className="text-gray-500 mb-6">Ora puoi accedere al tuo account AgentFlow.</p>
            <Link
              to="/login"
              className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700"
            >
              Vai al login
            </Link>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Verifica fallita</h2>
            <p className="text-gray-500 mb-6">{message}</p>
            <Link
              to="/login"
              className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700"
            >
              Torna al login
            </Link>
          </>
        )}
      </div>
    </div>
  )
}
