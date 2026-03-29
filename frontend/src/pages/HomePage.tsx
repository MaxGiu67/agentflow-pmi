import { useNavigate } from 'react-router-dom'
import {
  TrendingUp,
  Wallet,
  CalendarClock,
  ArrowRight,
  AlertTriangle,
} from 'lucide-react'
import { useHomeSummary } from '../api/hooks'
import Card from '../components/ui/Card'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import { formatCurrency } from '../lib/utils'

interface UpcomingPayment {
  id: string
  description: string
  amount: number
  due_date: string
  type: string
}

interface PendingAction {
  id: string
  label: string
  route: string
  icon: string
  priority: string
}

interface HomeSummaryData {
  greeting: string
  ricavi_mese: number
  target_mese: number
  saldo_banca: number
  cash_flow_critical: boolean
  cash_flow_message?: string
  upcoming_payments: UpcomingPayment[]
  pending_actions: PendingAction[]
}

const actionIconMap: Record<string, React.ReactNode> = {
  invoice: <CalendarClock className="h-5 w-5" />,
  bank: <Wallet className="h-5 w-5" />,
  alert: <AlertTriangle className="h-5 w-5" />,
  trending: <TrendingUp className="h-5 w-5" />,
}

export default function HomePage() {
  const navigate = useNavigate()
  const { data, isLoading, error } = useHomeSummary()

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  if (error) {
    return (
      <div className="mt-20 text-center">
        <AlertTriangle className="mx-auto mb-4 h-12 w-12 text-amber-500" />
        <p className="text-gray-600">Non sono riuscito a caricare i dati. Riprova tra poco.</p>
      </div>
    )
  }

  const summary = data as HomeSummaryData | undefined
  const ricavi = summary?.ricavi_mese ?? 0
  const target = summary?.target_mese ?? 1
  const progressPct = Math.min(100, Math.round((ricavi / target) * 100))
  const payments = (summary?.upcoming_payments ?? []).slice(0, 3)
  const actions = (summary?.pending_actions ?? []).slice(0, 3)

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      {/* Greeting */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          {summary?.greeting ?? 'Bentornato!'}
        </h1>
        <p className="mt-1 text-gray-500">
          Ecco come sta andando la tua azienda oggi.
        </p>
      </div>

      {/* Critical cash flow alert */}
      {summary?.cash_flow_critical && (
        <div className="flex items-start gap-3 rounded-xl border-2 border-red-300 bg-red-50 p-4">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-red-600" />
          <div>
            <p className="font-medium text-red-800">Attenzione al cash flow</p>
            <p className="mt-0.5 text-sm text-red-700">
              {summary.cash_flow_message ?? 'Il saldo potrebbe non coprire le prossime scadenze.'}
            </p>
            <button
              onClick={() => navigate('/banca/cashflow')}
              className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-red-700 hover:text-red-900"
            >
              Vedi previsione <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* KPI row */}
      <div className="grid gap-4 sm:grid-cols-2">
        {/* Ricavi vs Target */}
        <Card>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100">
              <TrendingUp className="h-5 w-5 text-green-600" />
            </div>
            <div className="flex-1">
              <p className="text-sm text-gray-500">Ricavi del mese</p>
              <p className="text-xl font-bold text-gray-900">{formatCurrency(ricavi)}</p>
            </div>
          </div>
          <div className="mt-4">
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>Target: {formatCurrency(target)}</span>
              <span>{progressPct}%</span>
            </div>
            <div className="mt-1 h-2 overflow-hidden rounded-full bg-gray-100">
              <div
                className={`h-full rounded-full transition-all ${
                  progressPct >= 100
                    ? 'bg-green-500'
                    : progressPct >= 70
                      ? 'bg-amber-500'
                      : 'bg-red-500'
                }`}
                style={{ width: `${progressPct}%` }}
              />
            </div>
            {progressPct >= 100 && (
              <p className="mt-2 text-sm font-medium text-green-600">
                Hai raggiunto il target del mese!
              </p>
            )}
          </div>
        </Card>

        {/* Bank balance */}
        <Card>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100">
              <Wallet className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Saldo in banca</p>
              <p className="text-xl font-bold text-gray-900">
                {formatCurrency(summary?.saldo_banca ?? 0)}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Upcoming payments */}
      {payments.length > 0 && (
        <div>
          <h2 className="mb-3 text-lg font-semibold text-gray-900">Prossime scadenze</h2>
          <div className="space-y-2">
            {payments.map((p) => (
              <Card key={p.id} className="flex items-center justify-between !p-4">
                <div>
                  <p className="font-medium text-gray-900">{p.description}</p>
                  <p className="text-sm text-gray-500">
                    Scade il{' '}
                    {new Date(p.due_date).toLocaleDateString('it-IT', {
                      day: 'numeric',
                      month: 'long',
                    })}
                  </p>
                </div>
                <p className="font-semibold text-gray-900">{formatCurrency(p.amount)}</p>
              </Card>
            ))}
          </div>
          <button
            onClick={() => navigate('/scadenze')}
            className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-800"
          >
            Vedi tutte le scadenze <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* Pending actions */}
      {actions.length > 0 && (
        <div>
          <h2 className="mb-3 text-lg font-semibold text-gray-900">Cose da fare</h2>
          <div className="grid gap-3 sm:grid-cols-3">
            {actions.map((a) => (
              <button
                key={a.id}
                onClick={() => navigate(a.route)}
                className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-4 text-left shadow-sm transition hover:border-blue-300 hover:shadow-md"
              >
                <div
                  className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${
                    a.priority === 'high'
                      ? 'bg-red-100 text-red-600'
                      : a.priority === 'medium'
                        ? 'bg-amber-100 text-amber-600'
                        : 'bg-blue-100 text-blue-600'
                  }`}
                >
                  {actionIconMap[a.icon] ?? <ArrowRight className="h-5 w-5" />}
                </div>
                <span className="text-sm font-medium text-gray-900">{a.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
