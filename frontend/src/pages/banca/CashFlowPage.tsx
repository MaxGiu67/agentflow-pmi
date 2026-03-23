import { useState } from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { useCashflow, useCashflowAlerts } from '../../api/hooks'
import { formatCurrency } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import LoadingSpinner from '../../components/ui/LoadingSpinner'

export default function CashFlowPage() {
  const [days, setDays] = useState(90)
  const { data, isLoading } = useCashflow(days)
  const { data: alerts } = useCashflowAlerts()

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const chartData = data?.daily_predictions ?? []
  const alertsList = alerts?.alerts ?? []

  return (
    <div>
      <PageHeader
        title="Previsione Cash Flow"
        subtitle={`Proiezione a ${days} giorni`}
        actions={
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
          >
            <option value={30}>30 giorni</option>
            <option value={60}>60 giorni</option>
            <option value={90}>90 giorni</option>
            <option value={180}>180 giorni</option>
            <option value={365}>1 anno</option>
          </select>
        }
      />

      {/* Alerts */}
      {alertsList.length > 0 && (
        <div className="mb-6 space-y-2">
          {alertsList.map((alert: Record<string, unknown>, idx: number) => (
            <div
              key={idx}
              className={`rounded-lg p-3 text-sm ${
                alert.severity === 'critical'
                  ? 'bg-red-50 text-red-700'
                  : 'bg-amber-50 text-amber-700'
              }`}
            >
              {alert.message as string}
            </div>
          ))}
        </div>
      )}

      {/* Stale data warning */}
      {data?.stale_data && (
        <div className="mb-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-700">
          I dati bancari non sono aggiornati. Sincronizza il conto per una previsione piu accurata.
        </div>
      )}

      {/* Chart */}
      <Card className="mb-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Andamento previsto</h2>
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={400}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="colorBalance" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#2563eb" stopOpacity={0.1} />
                  <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorIncome" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22c55e" stopOpacity={0.1} />
                  <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorExpense" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.1} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 12 }}
                tickFormatter={(v) => {
                  const d = new Date(v)
                  return `${d.getDate()}/${d.getMonth() + 1}`
                }}
              />
              <YAxis
                tick={{ fontSize: 12 }}
                tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
              />
              <Tooltip
                formatter={(value) => formatCurrency(Number(value))}
                labelFormatter={(label) => {
                  const d = new Date(label)
                  return d.toLocaleDateString('it-IT')
                }}
              />
              <Legend />
              <Area
                type="monotone"
                dataKey="projected_balance"
                name="Saldo previsto"
                stroke="#2563eb"
                fill="url(#colorBalance)"
                strokeWidth={2}
              />
              <Area
                type="monotone"
                dataKey="expected_income"
                name="Entrate"
                stroke="#22c55e"
                fill="url(#colorIncome)"
                strokeWidth={1}
              />
              <Area
                type="monotone"
                dataKey="expected_expenses"
                name="Uscite"
                stroke="#ef4444"
                fill="url(#colorExpense)"
                strokeWidth={1}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <p className="py-16 text-center text-sm text-gray-500">
            Dati insufficienti per la previsione
          </p>
        )}
      </Card>

      {/* Summary stats */}
      {data && (
        <div className="grid gap-4 sm:grid-cols-3">
          <Card>
            <p className="text-sm text-gray-500">Saldo attuale</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">
              {formatCurrency(data.current_balance ?? 0)}
            </p>
          </Card>
          <Card>
            <p className="text-sm text-gray-500">Entrate previste</p>
            <p className="mt-1 text-2xl font-bold text-green-600">
              {formatCurrency(data.total_expected_income ?? 0)}
            </p>
          </Card>
          <Card>
            <p className="text-sm text-gray-500">Uscite previste</p>
            <p className="mt-1 text-2xl font-bold text-red-600">
              {formatCurrency(data.total_expected_expenses ?? 0)}
            </p>
          </Card>
        </div>
      )}
    </div>
  )
}
