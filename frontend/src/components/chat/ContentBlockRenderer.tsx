import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { formatCurrency } from '../../lib/utils'

interface StatItem {
  label: string
  value: number
  format?: string
  sub?: string
}

interface ContentBlock {
  type: 'stat_row' | 'bar_chart' | 'table' | 'pie_chart'
  title?: string
  items?: StatItem[]
  data?: Record<string, unknown>[]
  keys?: string[]
  colors?: string[]
  columns?: string[]
  rows?: (string | number)[][]
}

const COLORS = ['#22c55e', '#f97316', '#3b82f6', '#eab308', '#ec4899']

function formatValue(value: number, format?: string): string {
  if (format === 'currency') return formatCurrency(value)
  if (format === 'percent') return `${value.toFixed(1)}%`
  return value.toLocaleString('it-IT')
}

function StatRow({ items }: { items: StatItem[] }) {
  return (
    <div className="grid grid-cols-3 gap-3">
      {items.map((item, i) => (
        <div key={i} className="rounded-lg border border-gray-100 bg-gray-50/50 p-3 text-center">
          <p className="text-xs text-gray-500">{item.label}</p>
          <p className={`text-lg font-bold ${item.value < 0 ? 'text-red-600' : 'text-gray-900'}`}>
            {formatValue(item.value, item.format)}
          </p>
          {item.sub && <p className="text-xs text-gray-400">{item.sub}</p>}
        </div>
      ))}
    </div>
  )
}

function BarChartBlock({ block }: { block: ContentBlock }) {
  const data = block.data ?? []
  const keys = block.keys ?? ['Emesse', 'Ricevute']
  const colors = block.colors ?? COLORS

  return (
    <div>
      {block.title && <p className="mb-2 text-xs font-medium text-gray-600">{block.title}</p>}
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data} margin={{ top: 5, right: 5, left: -10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="label" tick={{ fontSize: 10 }} />
          <YAxis tick={{ fontSize: 10 }} tickFormatter={(v: number) => `€${(v / 1000).toFixed(0)}k`} />
          <Tooltip
            formatter={(value) => formatCurrency(Number(value ?? 0))}
            labelStyle={{ fontSize: 12 }}
          />
          <Legend wrapperStyle={{ fontSize: 10 }} />
          {keys.map((key, i) => (
            <Bar key={key} dataKey={key} fill={colors[i % colors.length]} radius={[2, 2, 0, 0]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function TableBlock({ block }: { block: ContentBlock }) {
  const columns = block.columns ?? []
  const rows = block.rows ?? []

  return (
    <div>
      {block.title && <p className="mb-2 text-xs font-medium text-gray-600">{block.title}</p>}
      <div className="overflow-x-auto rounded-lg border border-gray-100">
        <table className="min-w-full text-xs">
          <thead className="bg-gray-50">
            <tr>
              {columns.map((col, i) => (
                <th key={i} className="px-3 py-1.5 text-left font-medium text-gray-600">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {rows.map((row, i) => (
              <tr key={i} className="hover:bg-gray-50/50">
                {row.map((cell, j) => (
                  <td key={j} className="whitespace-nowrap px-3 py-1.5 text-gray-700">
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function ContentBlockRenderer({ blocks }: { blocks: ContentBlock[] }) {
  if (!blocks || blocks.length === 0) return null

  return (
    <div className="mt-3 space-y-4">
      {blocks.map((block, i) => {
        switch (block.type) {
          case 'stat_row':
            return <StatRow key={i} items={block.items ?? []} />
          case 'bar_chart':
            return <BarChartBlock key={i} block={block} />
          case 'table':
            return <TableBlock key={i} block={block} />
          default:
            return null
        }
      })}
    </div>
  )
}
