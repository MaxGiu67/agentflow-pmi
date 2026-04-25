import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { formatCurrency } from '../../lib/utils'

const MONTH_LABELS = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu', 'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic']

interface YKeyDef {
  key: string
  color: string
  name: string
}

interface BarChartWidgetConfig {
  x_key?: string
  y_keys?: YKeyDef[]
}

interface BarChartWidgetProps {
  title: string
  data: Record<string, unknown>[]
  config: BarChartWidgetConfig
}

function formatTooltipValue(value: unknown): string {
  return formatCurrency(Number(value ?? 0))
}

function formatTooltipLabel(label: unknown): string {
  return `Mese: ${String(label ?? '')}`
}

export default function BarChartWidget({ title, data, config }: BarChartWidgetProps) {
  const xKey = config.x_key ?? 'mese'
  const yKeys = config.y_keys ?? []

  const chartData = (data ?? []).map((row) => ({
    ...row,
    label: xKey === 'mese'
      ? MONTH_LABELS[(Number(row[xKey]) || 1) - 1] ?? ''
      : String(row[xKey] ?? ''),
  }))

  if (chartData.length === 0) {
    return (
      <div className="flex h-full flex-col rounded-lg bg-white p-4 shadow-sm">
        <h3 className="mb-2 text-sm font-semibold text-gray-900">{title}</h3>
        <div className="flex flex-1 items-center justify-center text-sm text-gray-500">
          Nessun dato disponibile
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col rounded-lg bg-white p-4 shadow-sm">
      <h3 className="mb-2 text-sm font-semibold text-gray-900">{title}</h3>
      <div className="min-h-[220px] flex-1">
        <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={220}>
          <BarChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} />
            <YAxis
              tickFormatter={(v: number) =>
                v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)
              }
              tick={{ fontSize: 11 }}
            />
            <Tooltip formatter={formatTooltipValue} labelFormatter={formatTooltipLabel} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            {yKeys.map((yk) => (
              <Bar
                key={yk.key}
                dataKey={yk.key}
                name={yk.name}
                fill={yk.color}
                radius={[4, 4, 0, 0]}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
