import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { formatCurrency } from '../../lib/utils'

const DEFAULT_COLORS = ['#22c55e', '#f97316', '#3b82f6', '#a855f7', '#ef4444', '#eab308', '#06b6d4', '#ec4899']

interface PieChartWidgetConfig {
  value_key?: string
  name_key?: string
  colors?: string[]
  format?: string
}

interface PieChartWidgetProps {
  title: string
  data: Record<string, unknown>[]
  config: PieChartWidgetConfig
}

function formatValue(value: unknown, format?: string): string {
  const num = Number(value ?? 0)
  if (format === 'currency') return formatCurrency(num)
  return String(num)
}

export default function PieChartWidget({ title, data, config }: PieChartWidgetProps) {
  const valueKey = config.value_key ?? 'value'
  const nameKey = config.name_key ?? 'name'
  const colors = config.colors ?? DEFAULT_COLORS

  if (!data || data.length === 0) {
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
          <PieChart>
            <Pie
              data={data}
              dataKey={valueKey}
              nameKey={nameKey}
              cx="50%"
              cy="50%"
              outerRadius="70%"
              label={({ name }: { name?: string }) => name ?? ''}
            >
              {data.map((_, index) => (
                <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: unknown) => formatValue(value, config.format)}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
