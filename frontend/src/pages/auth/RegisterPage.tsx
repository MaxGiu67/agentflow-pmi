import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/auth'

const TIPI_AZIENDA = [
  { value: 'srl', label: 'SRL' },
  { value: 'srls', label: 'SRLS' },
  { value: 'piva', label: 'Partita IVA' },
  { value: 'ditta_individuale', label: 'Ditta Individuale' },
  { value: 'spa', label: 'SPA' },
]

const REGIMI_FISCALI = [
  { value: 'ordinario', label: 'Ordinario' },
  { value: 'semplificato', label: 'Semplificato' },
  { value: 'forfettario', label: 'Forfettario' },
]

export default function RegisterPage() {
  const [step, setStep] = useState(1)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [aziendaNome, setAziendaNome] = useState('')
  const [aziendaTipo, setAziendaTipo] = useState('srl')
  const [aziendaPiva, setAziendaPiva] = useState('')
  const [regimeFiscale, setRegimeFiscale] = useState('ordinario')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)
  const register = useAuthStore((s) => s.register)
  const navigate = useNavigate()

  const handleNext = () => {
    if (!email || !password) { setError('Email e password sono obbligatori'); return }
    if (password !== confirmPassword) { setError('Le password non coincidono'); return }
    if (password.length < 8) { setError('La password deve avere almeno 8 caratteri'); return }
    setError('')
    setStep(2)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    if (!aziendaNome) { setError('Il nome azienda e obbligatorio'); return }

    setLoading(true)
    try {
      const result = await register(email, password, name || undefined, {
        azienda_nome: aziendaNome,
        azienda_tipo: aziendaTipo,
        azienda_piva: aziendaPiva || undefined,
        regime_fiscale: regimeFiscale,
      })
      setSuccess(result.message || 'Registrazione completata! Controlla la tua email.')
      setTimeout(() => navigate('/login'), 3000)
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Errore durante la registrazione'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-[100dvh] items-center justify-center bg-gray-50 px-4 py-8">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-purple-600 text-lg font-bold text-white">
            AF
          </div>
          <h1 className="text-2xl font-bold text-gray-900" style={{ fontFamily: 'var(--font-display)' }}>
            {step === 1 ? 'Crea il tuo account' : 'La tua azienda'}
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            {step === 1 ? 'Controller aziendale AI per la tua PMI' : 'Configura il tuo spazio di lavoro'}
          </p>

          {/* Step indicator */}
          <div className="mt-4 flex justify-center gap-2">
            <div className={`h-1.5 w-12 rounded-full ${step >= 1 ? 'bg-purple-600' : 'bg-gray-200'}`} />
            <div className={`h-1.5 w-12 rounded-full ${step >= 2 ? 'bg-purple-600' : 'bg-gray-200'}`} />
          </div>
        </div>

        <form onSubmit={step === 1 ? (e) => { e.preventDefault(); handleNext() } : handleSubmit}
          className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">

          {error && <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>}
          {success && <div className="mb-4 rounded-lg bg-green-50 p-3 text-sm text-green-700">{success}</div>}

          {step === 1 ? (
            /* Step 1: Account */
            <div className="space-y-4">
              <div>
                <label htmlFor="name" className="mb-1 block text-sm font-medium text-gray-700">Il tuo nome</label>
                <input id="name" type="text" value={name} onChange={(e) => setName(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-purple-500 focus:ring-1 focus:ring-purple-500 focus:outline-none"
                  placeholder="Mario Rossi" />
              </div>
              <div>
                <label htmlFor="email" className="mb-1 block text-sm font-medium text-gray-700">Email *</label>
                <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-purple-500 focus:ring-1 focus:ring-purple-500 focus:outline-none"
                  placeholder="nome@azienda.it" />
              </div>
              <div>
                <label htmlFor="password" className="mb-1 block text-sm font-medium text-gray-700">Password *</label>
                <input id="password" type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-purple-500 focus:ring-1 focus:ring-purple-500 focus:outline-none"
                  placeholder="Minimo 8 caratteri, 1 maiuscola, 1 numero" />
              </div>
              <div>
                <label htmlFor="confirmPassword" className="mb-1 block text-sm font-medium text-gray-700">Conferma password *</label>
                <input id="confirmPassword" type="password" required value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-purple-500 focus:ring-1 focus:ring-purple-500 focus:outline-none"
                  placeholder="Ripeti la password" />
              </div>
              <button type="submit"
                className="w-full rounded-lg bg-purple-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-purple-700">
                Continua
              </button>
            </div>
          ) : (
            /* Step 2: Azienda */
            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Ragione sociale *</label>
                <input type="text" required value={aziendaNome} onChange={(e) => setAziendaNome(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-purple-500 focus:ring-1 focus:ring-purple-500 focus:outline-none"
                  placeholder="La Mia Azienda SRL" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Tipo azienda</label>
                  <select value={aziendaTipo} onChange={(e) => setAziendaTipo(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm">
                    {TIPI_AZIENDA.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Regime fiscale</label>
                  <select value={regimeFiscale} onChange={(e) => setRegimeFiscale(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm">
                    {REGIMI_FISCALI.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Partita IVA</label>
                <input type="text" value={aziendaPiva} onChange={(e) => setAziendaPiva(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-purple-500 focus:ring-1 focus:ring-purple-500 focus:outline-none"
                  placeholder="12345678901" maxLength={11} />
              </div>

              <div className="flex gap-2">
                <button type="button" onClick={() => setStep(1)}
                  className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-50">
                  Indietro
                </button>
                <button type="submit" disabled={loading}
                  className="flex-1 rounded-lg bg-purple-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50">
                  {loading ? 'Creazione...' : 'Crea account'}
                </button>
              </div>
            </div>
          )}

          <p className="mt-4 text-center text-sm text-gray-500">
            Hai gia un account?{' '}
            <Link to="/login" className="text-purple-600 hover:underline">Accedi</Link>
          </p>
        </form>

        <p className="mt-4 text-center text-xs text-gray-400">
          AgentFlow PMI — Controller aziendale AI
        </p>
      </div>
    </div>
  )
}
