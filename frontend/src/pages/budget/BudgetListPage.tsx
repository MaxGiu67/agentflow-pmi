import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Plus, Pencil, BarChart3, Target, Calendar } from 'lucide-react'
import api from '../../api/client'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'

interface BudgetSummary {
  year: number
  sector_id: string | null
  sector_label: string | null
  fatturato: number
  total_costi: number
  ebitda: number
  n_categories: number
  created_at: string | null
}

function fmtCur(n: number): string {
  return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(n)
}

export default function BudgetListPage() {
  const navigate = useNavigate()

  const { data: budgets, isLoading } = useQuery<BudgetSummary[]>({
    queryKey: ['budgets-list'],
    queryFn: async () => (await api.get('/controller/budgets')).data,
  })

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const items = budgets ?? []
  const currentYear = new Date().getFullYear()

  return (
    <div className="mx-auto max-w-4xl px-4 pb-12">
      <PageHeader
        title="I miei Budget"
        subtitle="Piano economico per anno — crea, modifica e confronta con il consuntivo"
        actions={
          <button
            onClick={() => navigate('/budget/wizard')}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            Nuovo budget
          </button>
        }
      />

      {items.length === 0 ? (
        /* Empty state */
        <div className="flex flex-col items-center rounded-xl border border-slate-200 bg-white py-20 shadow-sm">
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-blue-50">
            <Target className="h-8 w-8 text-blue-600" />
          </div>
          <h2 className="mb-1 text-lg font-semibold text-slate-800">Nessun budget creato</h2>
          <p className="mb-6 max-w-sm text-center text-sm text-slate-500">
            Crea il tuo primo budget per pianificare ricavi e costi e confrontarli con i dati reali.
          </p>
          <button
            onClick={() => navigate(`/budget/wizard?year=${currentYear + 1}`)}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-700"
          >
            <Plus className="h-5 w-5" />
            Crea budget {currentYear + 1}
          </button>
        </div>
      ) : (
        /* Budget cards */
        <div className="space-y-4">
          {items.map((b) => (
            <div
              key={b.year}
              className="flex items-center gap-6 rounded-xl border border-slate-200 bg-white px-6 py-5 shadow-sm transition-all hover:shadow-md"
            >
              {/* Year badge */}
              <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-xl font-bold text-blue-700">
                {String(b.year).slice(2)}
              </div>

              {/* Info */}
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-bold text-slate-800">Budget {b.year}</h3>
                  {b.sector_label && (
                    <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600">
                      {b.sector_label}
                    </span>
                  )}
                </div>
                <div className="mt-1 flex items-center gap-4 text-sm text-slate-500">
                  <span>Ricavi: <strong className="text-slate-700">{fmtCur(b.fatturato)}</strong></span>
                  <span>Costi: <strong className="text-slate-700">{fmtCur(b.total_costi)}</strong></span>
                  <span className={b.ebitda >= 0 ? 'text-green-600' : 'text-red-600'}>
                    EBITDA: <strong>{fmtCur(b.ebitda)}</strong>
                  </span>
                  <span className="text-xs text-slate-400">{b.n_categories} voci</span>
                </div>
                {b.created_at && (
                  <p className="mt-0.5 flex items-center gap-1 text-xs text-slate-400">
                    <Calendar className="h-3 w-3" />
                    Creato il {new Date(b.created_at).toLocaleDateString('it-IT')}
                  </p>
                )}
              </div>

              {/* Actions */}
              <div className="flex shrink-0 gap-2">
                <button
                  onClick={() => navigate(`/budget/wizard?edit=true&year=${b.year}`)}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-blue-300 px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50"
                >
                  <Pencil className="h-3.5 w-3.5" /> Modifica
                </button>
                <button
                  onClick={() => navigate(`/ceo/budget?year=${b.year}`)}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  <BarChart3 className="h-3.5 w-3.5" /> Consuntivo
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
