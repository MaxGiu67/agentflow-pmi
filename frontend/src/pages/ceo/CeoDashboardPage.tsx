import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  LineChart,
  Line,
} from 'recharts'
import { useCeoDashboard, useCeoAlerts, useCeoYoY } from '../../api/hooks'
import { formatCurrency, formatNumber } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import StatCard from '../../components/ui/StatCard'
import LoadingSpinner from '../../components/ui/LoadingSpinner'

export default function CeoDashboardPage() {
  const navigate = useNavigate()
  const currentYear = new Date().getFullYear()
  const [year, setYear] = useState(currentYear)

  const { data: dashboard, isLoading } = useCeoDashboard(year)
  const { data: alerts } = useCeoAlerts(year)
  const { data: yoy } = useCeoYoY(year)

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const kpis = dashboard?.kpis ?? {}
  const topClients = dashboard?.top_clients ?? []
  const topSuppliers = dashboard?.top_suppliers ?? []
  const dsoTrend = dashboard?.dso_trend ?? []
  const alertsList = alerts?.alerts ?? []

  return (
    <div>
      <PageHeader
        title="Cruscotto CEO"
        subtitle="KPI e analisi strategiche"
        actions={
          <div className="flex gap-2">
            <select
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
            >
              {Array.from({ length: 3 }, (_, i) => currentYear - i).map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
            <button
              onClick={() => navigate('/ceo/budget')}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Budget
            </button>
          </div>
        }
      />

      {/* KPI Cards */}
      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Fatturato"
          value={formatCurrency(kpis.revenue ?? 0)}
          trend={yoy?.revenue_change}
        />
        <StatCard
          title="Margine lordo"
          value={`${formatNumber(kpis.gross_margin ?? 0)}%`}
          trend={yoy?.margin_change}
        />
        <StatCard
          title="DSO (giorni)"
          value={formatNumber(kpis.dso ?? 0)}
          subtitle="Days Sales Outstanding"
        />
        <StatCard
          title="DPO (giorni)"
          value={formatNumber(kpis.dpo ?? 0)}
          subtitle="Days Payable Outstanding"
        />
      </div>

      {/* Alerts */}
      {alertsList.length > 0 && (
        <Card className="mb-6">
          <h2 className="mb-3 text-lg font-semibold text-gray-900">Avvisi</h2>
          <div className="space-y-2">
            {alertsList.map((alert: Record<string, unknown>, idx: number) => (
              <div
                key={idx}
                className={`rounded-lg p-3 text-sm ${
                  alert.severity === 'critical' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'
                }`}
              >
                <span className="font-medium">{alert.title as string}:</span> {alert.message as string}
              </div>
            ))}
          </div>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Top Clients */}
        <Card>
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Top Clienti</h2>
          {topClients.length > 0 ? (
            <div className="space-y-3">
              {topClients.map((client: Record<string, unknown>, idx: number) => (
                <div key={idx} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-xs font-bold text-blue-700">
                      {idx + 1}
                    </span>
                    <span className="text-sm text-gray-700">{client.name as string}</span>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-gray-900">{formatCurrency(client.revenue as number)}</p>
                    <p className="text-xs text-gray-500">{formatNumber(client.percentage as number)}%</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="py-4 text-center text-sm text-gray-500">Dati non disponibili</p>
          )}
        </Card>

        {/* Top Suppliers */}
        <Card>
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Top Fornitori</h2>
          {topSuppliers.length > 0 ? (
            <div className="space-y-3">
              {topSuppliers.map((supplier: Record<string, unknown>, idx: number) => (
                <div key={idx} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-orange-100 text-xs font-bold text-orange-700">
                      {idx + 1}
                    </span>
                    <span className="text-sm text-gray-700">{supplier.name as string}</span>
                  </div>
                  <p className="text-sm font-semibold text-gray-900">{formatCurrency(supplier.cost as number)}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="py-4 text-center text-sm text-gray-500">Dati non disponibili</p>
          )}
        </Card>

        {/* DSO/DPO Trend */}
        <Card className="lg:col-span-2">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Trend DSO/DPO</h2>
          {dsoTrend.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={dsoTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="dso" name="DSO" stroke="#2563eb" strokeWidth={2} />
                <Line type="monotone" dataKey="dpo" name="DPO" stroke="#f59e0b" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="py-16 text-center text-sm text-gray-500">Dati insufficienti</p>
          )}
        </Card>
      </div>

      {/* Data sufficiency note */}
      {dashboard?.data_note && (
        <p className="mt-4 text-xs text-gray-400">{dashboard.data_note}</p>
      )}
    </div>
  )
}
