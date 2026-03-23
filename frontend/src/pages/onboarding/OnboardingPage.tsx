import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Building2, CreditCard, Shield, RefreshCw, Check } from 'lucide-react'
import { useOnboardingStatus, useCompleteOnboardingStep } from '../../api/hooks'
import LoadingSpinner from '../../components/ui/LoadingSpinner'

const steps = [
  { num: 1, label: 'Tipo azienda', icon: Building2 },
  { num: 2, label: 'P.IVA e Regime', icon: CreditCard },
  { num: 3, label: 'Collegamento SPID', icon: Shield },
  { num: 4, label: 'Sincronizzazione', icon: RefreshCw },
]

const tipiAzienda = ['srl', 'srls', 'snc', 'sas', 'ditta_individuale', 'professionista']
const regimiFiscali = ['ordinario', 'semplificato', 'forfettario']

export default function OnboardingPage() {
  const navigate = useNavigate()
  const { data: status, isLoading } = useOnboardingStatus()
  const completeStep = useCompleteOnboardingStep()
  const [currentStep, setCurrentStep] = useState(1)
  const [tipoAzienda, setTipoAzienda] = useState('')
  const [piva, setPiva] = useState('')
  const [regime, setRegime] = useState('')
  const [error, setError] = useState('')

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const completedSteps = status?.completed_steps ?? []

  const handleNext = async () => {
    setError('')
    try {
      const stepData: Record<string, unknown> = {}
      if (currentStep === 1) stepData.tipo_azienda = tipoAzienda
      if (currentStep === 2) {
        stepData.piva = piva
        stepData.regime_fiscale = regime
      }
      await completeStep.mutateAsync({ step: currentStep, data: stepData })
      if (currentStep < 4) {
        setCurrentStep(currentStep + 1)
      } else {
        navigate('/')
      }
    } catch (err: unknown) {
      setError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          'Errore nel completamento dello step'
      )
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-2xl">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-gray-900">Configurazione AgentFlow</h1>
          <p className="mt-2 text-sm text-gray-500">Completa la configurazione per iniziare</p>
        </div>

        {/* Step indicators */}
        <div className="mb-8 flex items-center justify-center gap-2">
          {steps.map((step) => {
            const isCompleted = completedSteps.includes(step.num)
            const isCurrent = step.num === currentStep
            return (
              <div key={step.num} className="flex items-center gap-2">
                <div
                  className={`flex h-10 w-10 items-center justify-center rounded-full text-sm font-medium ${
                    isCompleted
                      ? 'bg-green-500 text-white'
                      : isCurrent
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-200 text-gray-500'
                  }`}
                >
                  {isCompleted ? <Check className="h-5 w-5" /> : step.num}
                </div>
                <span className="hidden text-sm text-gray-600 sm:inline">{step.label}</span>
                {step.num < 4 && <div className="mx-2 h-px w-8 bg-gray-300" />}
              </div>
            )
          })}
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          {error && (
            <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>
          )}

          {currentStep === 1 && (
            <div>
              <h2 className="mb-4 text-lg font-semibold text-gray-900">Tipo di azienda</h2>
              <div className="grid grid-cols-2 gap-3">
                {tipiAzienda.map((tipo) => (
                  <button
                    key={tipo}
                    onClick={() => setTipoAzienda(tipo)}
                    className={`rounded-lg border p-3 text-left text-sm font-medium transition-colors ${
                      tipoAzienda === tipo
                        ? 'border-blue-500 bg-blue-50 text-blue-700'
                        : 'border-gray-200 text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    {tipo.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                  </button>
                ))}
              </div>
            </div>
          )}

          {currentStep === 2 && (
            <div>
              <h2 className="mb-4 text-lg font-semibold text-gray-900">Partita IVA e Regime Fiscale</h2>
              <div className="mb-4">
                <label className="mb-1 block text-sm font-medium text-gray-700">Partita IVA</label>
                <input
                  type="text"
                  value={piva}
                  onChange={(e) => setPiva(e.target.value)}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
                  placeholder="12345678901"
                  maxLength={11}
                />
              </div>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">Regime Fiscale</label>
                <div className="grid grid-cols-3 gap-3">
                  {regimiFiscali.map((r) => (
                    <button
                      key={r}
                      onClick={() => setRegime(r)}
                      className={`rounded-lg border p-3 text-center text-sm font-medium transition-colors ${
                        regime === r
                          ? 'border-blue-500 bg-blue-50 text-blue-700'
                          : 'border-gray-200 text-gray-700 hover:bg-gray-50'
                      }`}
                    >
                      {r.charAt(0).toUpperCase() + r.slice(1)}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {currentStep === 3 && (
            <div className="text-center">
              <Shield className="mx-auto mb-4 h-16 w-16 text-blue-600" />
              <h2 className="mb-2 text-lg font-semibold text-gray-900">Collegamento SPID</h2>
              <p className="mb-4 text-sm text-gray-500">
                Collega il tuo SPID per accedere automaticamente al cassetto fiscale
                e sincronizzare le fatture.
              </p>
              <p className="text-xs text-gray-400">
                Puoi saltare questo passaggio e collegarlo piu tardi dalle Impostazioni.
              </p>
            </div>
          )}

          {currentStep === 4 && (
            <div className="text-center">
              <RefreshCw className="mx-auto mb-4 h-16 w-16 text-green-500" />
              <h2 className="mb-2 text-lg font-semibold text-gray-900">Sincronizzazione</h2>
              <p className="text-sm text-gray-500">
                AgentFlow sincronizzera automaticamente le tue fatture dal cassetto fiscale,
                le categorizzera con l'intelligenza artificiale e le registrera in contabilita.
              </p>
            </div>
          )}

          <div className="mt-6 flex justify-between">
            {currentStep > 1 && (
              <button
                onClick={() => setCurrentStep(currentStep - 1)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Indietro
              </button>
            )}
            <button
              onClick={handleNext}
              disabled={
                completeStep.isPending ||
                (currentStep === 1 && !tipoAzienda) ||
                (currentStep === 2 && (!piva || !regime))
              }
              className="ml-auto rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {completeStep.isPending
                ? 'Salvataggio...'
                : currentStep === 4
                  ? 'Inizia'
                  : currentStep === 3
                    ? 'Salta / Continua'
                    : 'Avanti'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
