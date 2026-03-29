import { useNavigate } from 'react-router-dom'
import { CheckCircle2, Lock, ArrowRight } from 'lucide-react'
import { useCompletenessScore } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import LoadingSpinner from '../../components/ui/LoadingSpinner'

interface SourceItem {
  id: string
  name: string
  connected: boolean
  setup_route: string
  unlocked_features: string[]
  benefit_text?: string
  is_next_suggested?: boolean
}

interface CompletenessData {
  score: number
  total_sources: number
  connected_sources: number
  sources: SourceItem[]
}

export default function CompletenessPage() {
  const navigate = useNavigate()
  const { data, isLoading } = useCompletenessScore()

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const completeness = data as CompletenessData | undefined
  const sources = completeness?.sources ?? []
  const score = completeness?.score ?? 0

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        title="Configura il tuo assistente"
        subtitle="Ogni fonte collegata sblocca nuove funzionalita per la tua azienda"
      />

      {/* Score bar */}
      <Card className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-500">Completezza configurazione</p>
            <p className="text-3xl font-bold text-gray-900">{score}%</p>
          </div>
          <div className="text-right text-sm text-gray-500">
            {completeness?.connected_sources ?? 0} di {completeness?.total_sources ?? 0} fonti collegate
          </div>
        </div>
        <div className="mt-3 h-3 overflow-hidden rounded-full bg-gray-100">
          <div
            className="h-full rounded-full bg-green-500 transition-all"
            style={{ width: `${score}%` }}
          />
        </div>
      </Card>

      {/* Source cards */}
      <div className="space-y-3">
        {sources.map((source) => (
          <Card
            key={source.id}
            className={
              source.is_next_suggested && !source.connected
                ? '!border-blue-300 !shadow-md'
                : ''
            }
          >
            <div className="flex items-start gap-4">
              {/* Status icon */}
              <div
                className={`mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${
                  source.connected
                    ? 'bg-green-100 text-green-600'
                    : 'bg-gray-100 text-gray-400'
                }`}
              >
                {source.connected ? (
                  <CheckCircle2 className="h-5 w-5" />
                ) : (
                  <Lock className="h-5 w-5" />
                )}
              </div>

              {/* Content */}
              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-gray-900">{source.name}</h3>
                  {source.connected ? (
                    <span className="rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700">
                      Collegato
                    </span>
                  ) : (
                    <button
                      onClick={() => navigate(source.setup_route)}
                      className="inline-flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
                    >
                      Collega <ArrowRight className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>

                {/* Connected: show unlocked features */}
                {source.connected && source.unlocked_features.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {source.unlocked_features.map((feat) => (
                      <span
                        key={feat}
                        className="rounded-full bg-green-50 px-2.5 py-0.5 text-xs font-medium text-green-700"
                      >
                        {feat}
                      </span>
                    ))}
                  </div>
                )}

                {/* Next suggested: show benefit */}
                {!source.connected && source.is_next_suggested && source.benefit_text && (
                  <p className="mt-1.5 text-sm text-blue-700">{source.benefit_text}</p>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}
