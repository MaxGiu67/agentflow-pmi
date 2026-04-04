import type { ReactNode } from 'react'

interface Column<T> {
  key: string
  label: string
  render: (item: T) => ReactNode
  priority?: 'high' | 'medium' | 'low'
  align?: 'left' | 'right' | 'center'
}

interface ResponsiveTableProps<T> {
  columns: Column<T>[]
  data: T[]
  keyExtractor: (item: T) => string
  onRowClick?: (item: T) => void
  emptyMessage?: string
}

export default function ResponsiveTable<T>({
  columns,
  data,
  keyExtractor,
  onRowClick,
  emptyMessage = 'Nessun dato',
}: ResponsiveTableProps<T>) {
  if (data.length === 0) {
    return (
      <div className="py-12 text-center text-sm text-gray-400">{emptyMessage}</div>
    )
  }

  const highCols = columns.filter((c) => c.priority !== 'low')
  const _lowCols = columns.filter((c) => c.priority === 'low')

  return (
    <>
      {/* Mobile: Card layout */}
      <div className="space-y-2 md:hidden">
        {data.map((item) => (
          <div
            key={keyExtractor(item)}
            onClick={() => onRowClick?.(item)}
            className={`rounded-xl border border-gray-200 bg-white p-4 ${
              onRowClick ? 'cursor-pointer active:bg-gray-50' : ''
            }`}
          >
            {/* Primary info (high priority columns) */}
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1 space-y-1">
                {highCols.slice(0, 2).map((col) => (
                  <div key={col.key} className={col.key === highCols[0]?.key ? 'font-medium text-gray-900 text-sm' : 'text-xs text-gray-500'}>
                    {col.render(item)}
                  </div>
                ))}
              </div>
              {highCols.length > 2 && (
                <div className="shrink-0 text-right">
                  {highCols.slice(2, 4).map((col) => (
                    <div key={col.key} className="text-sm font-medium text-gray-900">
                      {col.render(item)}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Secondary info (remaining high + medium) */}
            {highCols.length > 4 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {highCols.slice(4).map((col) => (
                  <span key={col.key} className="text-xs text-gray-400">
                    {col.label}: {col.render(item)}
                  </span>
                ))}
              </div>
            )}

            {/* Low priority: hidden on mobile by default */}
          </div>
        ))}
      </div>

      {/* Desktop: Standard table */}
      <div className="hidden overflow-hidden rounded-xl border border-gray-200 bg-white md:block">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={`px-4 py-3 text-xs font-semibold uppercase text-gray-500 ${
                    col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'
                  } ${col.priority === 'low' ? 'hidden lg:table-cell' : ''}`}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {data.map((item) => (
              <tr
                key={keyExtractor(item)}
                onClick={() => onRowClick?.(item)}
                className={`transition-colors ${onRowClick ? 'cursor-pointer hover:bg-gray-50' : ''}`}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={`px-4 py-3 text-sm ${
                      col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'
                    } ${col.priority === 'low' ? 'hidden lg:table-cell' : ''}`}
                  >
                    {col.render(item)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
