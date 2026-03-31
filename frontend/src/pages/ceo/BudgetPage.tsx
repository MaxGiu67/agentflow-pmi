import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  LineChart,
  Line,
} from 'recharts'
import { Pencil, Plus } from 'lucide-react'
import { useBudget, useBudgetProjection } from '../../api/hooks'
import { formatCurrency } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import DataTable, { type Column } from '../../components/ui/DataTable'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'

type BudgetRow = Record<string, unknown>

export default function BudgetPage() {
  const navigate = useNavigate()
  const currentYear = new Date().getFullYear()
  const [year, setYear] = useState(currentYear)
  const { data: budget, isLoading } = useBudget(year)
  const { data: projection } = useBudgetProjection(year)

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const entries = budget?.entries ?? []
  const monthlyComparison = budget?.monthly_comparison ?? []
  const projectionData = projection?.monthly_projection ?? []

  const columns: Column<BudgetRow>[] = [
    {
      key: 'category',
      header: 'Categoria',
      sortable: true,
      render: (row) => (row.label as string) || (row.category as string),
    },
    {
      key: 'budget_amount',
      header: 'Budget',
      render: (row) => formatCurrency(row.budget_amount as number),
      className: 'text-right',
    },
    {
      key: 'actual_amount',
      header: 'Consuntivo',
      render: (row) => formatCurrency(row.actual_amount as number),
      className: 'text-right',
    },
    {
      key: 'variance',
      header: 'Scostamento',
      render: (row) => {
        const variance = row.variance as number
        return (
          <span className={variance >= 0 ? 'text-green-600' : 'text-red-600'}>
            {variance >= 0 ? '+' : ''}{formatCurrency(variance)}
          </span>
        )
      },
      className: 'text-right',
    },
    {
      key: 'variance_pct',
      header: '%',
      render: (row) => {
        const pct = row.variance_pct as number
        return (
          <span className={pct >= 0 ? 'text-green-600' : 'text-red-600'}>
            {pct >= 0 ? '+' : ''}{pct?.toFixed(1)}%
          </span>
        )
      },
      className: 'text-right',
    },
  ]

  return (
    <div>
      <PageHeader
        title="Budget vs Consuntivo"
        subtitle="Confronto budget e dati reali"
        actions={
          <div className="flex items-center gap-3">
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
              onClick={() => navigate(`/budget/wizard?edit=true&year=${year}`)}
              className="inline-flex items-center gap-2 rounded-lg border border-blue-300 px-4 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50"
            >
              <Pencil className="h-4 w-4" />
              Modifica budget
            </button>
          </div>
        }
      />

      {entries.length === 0 ? (
        <div className="flex flex-col items-center py-20">
          <EmptyState
            title="Nessun budget definito"
            description={`Crea il budget ${year} per confrontare previsioni e dati reali.`}
          />
          <button
            onClick={() => navigate(`/budget/wizard?year=${year}`)}
            className="mt-4 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-700"
          >
            <Plus className="h-5 w-5" />
            Crea budget {year}
          </button>
        </div>
      ) : (
        <>
          {/* Monthly comparison chart */}
          {monthlyComparison.length > 0 && (
            <Card className="mb-6">
              <h2 className="mb-4 text-lg font-semibold text-gray-900">Confronto mensile</h2>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={monthlyComparison}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                  <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                  <Legend />
                  <Bar dataKey="budget" name="Budget" fill="#93c5fd" />
                  <Bar dataKey="actual" name="Consuntivo" fill="#2563eb" />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          )}

          {/* Budget table */}
          <div className="mb-6">
            <DataTable<BudgetRow>
              columns={columns}
              data={entries}
              rowKey={(row) => row.category as string}
              emptyMessage="Nessuna voce di budget"
            />
          </div>

          {/* Projection chart */}
          {projectionData.length > 0 && (
            <Card>
              <h2 className="mb-4 text-lg font-semibold text-gray-900">Proiezione fine anno</h2>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={projectionData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                  <Tooltip formatter={(value) => formatCurrency(Number(value))} />
                  <Legend />
                  <Line type="monotone" dataKey="actual" name="Reale" stroke="#2563eb" strokeWidth={2} />
                  <Line
                    type="monotone"
                    dataKey="projected"
                    name="Proiezione"
                    stroke="#2563eb"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                  />
                  <Line type="monotone" dataKey="budget" name="Budget" stroke="#f59e0b" strokeWidth={1} />
                </LineChart>
              </ResponsiveContainer>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
