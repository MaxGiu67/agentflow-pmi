import { formatCurrency, formatNumber } from '../../lib/utils'

interface ColumnDef {
  key: string
  label: string
  format?: string
}

interface TableWidgetConfig {
  columns?: ColumnDef[]
}

interface TableWidgetProps {
  title: string
  data: Record<string, unknown>[]
  config: TableWidgetConfig
}

function formatCell(value: unknown, format?: string): string {
  if (value == null) return '-'
  if (format === 'currency') return formatCurrency(Number(value))
  if (format === 'number') return formatNumber(Number(value))
  return String(value)
}

export default function TableWidget({ title, data, config }: TableWidgetProps) {
  const columns = config.columns ?? []

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
      <h3 className="mb-3 text-sm font-semibold text-gray-900">{title}</h3>
      <div className="flex-1 overflow-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead>
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={`px-3 py-2 text-xs font-medium uppercase text-gray-500 ${
                    col.format === 'currency' || col.format === 'number' ? 'text-right' : 'text-left'
                  }`}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.map((row, i) => (
              <tr key={i}>
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={`px-3 py-1.5 text-sm text-gray-700 ${
                      col.format === 'currency' || col.format === 'number' ? 'text-right font-medium' : 'text-left'
                    }`}
                  >
                    {formatCell(row[col.key], col.format)}
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
