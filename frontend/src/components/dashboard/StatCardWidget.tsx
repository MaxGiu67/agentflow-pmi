import { formatCurrency, formatNumber } from '../../lib/utils'

interface WidgetConfig {
  format?: string
  color?: string
  subtitle_path?: string
  subtitle_suffix?: string
}

interface StatCardWidgetProps {
  title: string
  value: unknown
  config: WidgetConfig
  subtitle?: unknown
}

const COLOR_MAP: Record<string, { border: string; text: string; bg: string }> = {
  green: { border: 'border-l-green-500', text: 'text-green-600', bg: 'bg-green-50' },
  orange: { border: 'border-l-orange-500', text: 'text-orange-600', bg: 'bg-orange-50' },
  blue: { border: 'border-l-blue-500', text: 'text-blue-600', bg: 'bg-blue-50' },
  gray: { border: 'border-l-gray-400', text: 'text-gray-600', bg: 'bg-gray-100' },
  red: { border: 'border-l-red-500', text: 'text-red-600', bg: 'bg-red-50' },
  purple: { border: 'border-l-purple-500', text: 'text-purple-600', bg: 'bg-purple-50' },
}

function formatValue(value: unknown, format?: string): string {
  if (value == null) return '-'
  const num = Number(value)
  if (isNaN(num)) return String(value)
  if (format === 'currency') return formatCurrency(num)
  if (format === 'percent') return `${num.toFixed(1)}%`
  return formatNumber(num)
}

export default function StatCardWidget({ title, value, config, subtitle }: StatCardWidgetProps) {
  const colors = COLOR_MAP[config.color ?? 'blue'] ?? COLOR_MAP.blue

  return (
    <div className={`flex h-full flex-col justify-center rounded-lg border-l-4 bg-white p-4 shadow-sm ${colors.border}`}>
      <p className="text-sm font-medium text-gray-500">{title}</p>
      <p className="mt-1 text-2xl font-semibold text-gray-900">
        {formatValue(value, config.format)}
      </p>
      {subtitle != null && (
        <p className={`mt-0.5 text-sm ${colors.text}`}>
          {String(subtitle)}{config.subtitle_suffix ?? ''}
        </p>
      )}
    </div>
  )
}
