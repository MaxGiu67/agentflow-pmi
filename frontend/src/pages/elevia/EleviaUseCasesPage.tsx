import { useState } from 'react'
import { useEleviaUseCases, useEleviaScoreProspect } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import { Cpu, Target, Calculator } from 'lucide-react'

const ATECO_LABELS: Record<string, string> = {
  '24': 'Metallurgia', '25': 'Prodotti in metallo', '46': 'Commercio ingrosso', '20': 'Chimica',
}

const FIT_COLORS: Record<string, string> = {
  high: 'bg-green-100 text-green-700',
  medium: 'bg-amber-100 text-amber-700',
  low: 'bg-gray-100 text-gray-500',
}

function fitLabel(score: number) {
  if (score >= 80) return 'high'
  if (score >= 50) return 'medium'
  return 'low'
}

export default function EleviaUseCasesPage() {
  const { data: useCases, isLoading } = useEleviaUseCases()
  const scoreProspect = useEleviaScoreProspect()
  const [showScorer, setShowScorer] = useState(false)
  const [scoreForm, setScoreForm] = useState({ ateco_code: '', employee_count: 80, has_decision_maker: false })
  const [scoreResult, setScoreResult] = useState<any>(null)

  const handleScore = async () => {
    const result = await scoreProspect.mutateAsync(scoreForm)
    setScoreResult(result)
  }

  if (isLoading) return <LoadingSpinner />

  return (
    <div className="space-y-6">
      <PageHeader
        title="Use Case Elevia"
        subtitle="Catalogo soluzioni AI con mappatura settore ATECO"
        actions={
          <button onClick={() => setShowScorer(!showScorer)}
            className="inline-flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700">
            <Target className="h-4 w-4" /> Score Prospect
          </button>
        }
      />

      {/* Prospect scorer */}
      {showScorer && (
        <div className="rounded-xl border border-purple-200 bg-purple-50/30 p-5 space-y-4">
          <h3 className="font-medium text-gray-900">Calcola Fit Score Prospect</h3>
          <div className="grid gap-3 sm:grid-cols-3">
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Codice ATECO</label>
              <input type="text" value={scoreForm.ateco_code}
                onChange={(e) => setScoreForm({ ...scoreForm, ateco_code: e.target.value })}
                placeholder="es. 25.11" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Dipendenti</label>
              <input type="number" value={scoreForm.employee_count}
                onChange={(e) => setScoreForm({ ...scoreForm, employee_count: parseInt(e.target.value) || 0 })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <div className="flex items-end gap-2">
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={scoreForm.has_decision_maker}
                  onChange={(e) => setScoreForm({ ...scoreForm, has_decision_maker: e.target.checked })}
                  className="rounded" />
                Decision maker diretto
              </label>
            </div>
          </div>
          <button onClick={handleScore} disabled={!scoreForm.ateco_code || scoreProspect.isPending}
            className="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
            {scoreProspect.isPending ? 'Calcolo...' : 'Calcola Score'}
          </button>

          {scoreResult && (
            <div className={`rounded-lg p-4 ${scoreResult.is_hot ? 'bg-green-50 border border-green-200' : scoreResult.is_qualified ? 'bg-blue-50 border border-blue-200' : 'bg-gray-50 border border-gray-200'}`}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-2xl font-bold">{scoreResult.total_score}/100</span>
                <span className={`rounded-full px-3 py-1 text-xs font-medium ${scoreResult.is_hot ? 'bg-green-100 text-green-700' : scoreResult.is_qualified ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'}`}>
                  {scoreResult.is_hot ? 'HOT' : scoreResult.is_qualified ? 'QUALIFICATO' : 'NON IN TARGET'}
                </span>
              </div>
              <div className="grid grid-cols-5 gap-2 text-xs text-gray-600 mb-3">
                {Object.entries(scoreResult.breakdown).map(([key, val]: [string, any]) => (
                  <div key={key} className="text-center">
                    <div className="font-medium text-gray-900">{val}</div>
                    <div>{key.replace('_', ' ')}</div>
                  </div>
                ))}
              </div>
              {scoreResult.suggested_bundle && (
                <p className="text-sm text-gray-700">
                  Bundle suggerito: <strong>{scoreResult.suggested_bundle.name}</strong> ({scoreResult.suggested_bundle.use_cases.join(', ')})
                </p>
              )}
              {scoreResult.applicable_use_cases?.length > 0 && (
                <p className="text-xs text-gray-500 mt-1">
                  {scoreResult.applicable_use_cases.length} use case applicabili
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Use case grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {useCases?.map((uc: any) => (
          <div key={uc.id} className="rounded-xl border border-gray-200 bg-white p-5 hover:shadow-md transition-shadow">
            <div className="flex items-start gap-3 mb-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100">
                <Cpu className="h-5 w-5 text-purple-600" />
              </div>
              <div>
                <p className="font-semibold text-gray-900">{uc.code}</p>
                <p className="text-sm text-gray-700">{uc.name}</p>
              </div>
            </div>
            {uc.description && (
              <p className="text-xs text-gray-500 mb-3">{uc.description}</p>
            )}
            <div className="flex flex-wrap gap-1">
              {uc.ateco_matrix?.map((m: any) => (
                <span key={m.ateco_code}
                  className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${FIT_COLORS[fitLabel(m.fit_score)]}`}>
                  {ATECO_LABELS[m.ateco_code] || `ATECO ${m.ateco_code}`}: {m.fit_score}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
