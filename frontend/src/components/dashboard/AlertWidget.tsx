import { AlertTriangle, Info } from 'lucide-react'

interface AlertWidgetConfig {
  severity?: 'warning' | 'info' | 'error'
  message_path?: string
}

interface AlertWidgetProps {
  title: string
  value: unknown
  config: AlertWidgetConfig
}

const SEVERITY_STYLES = {
  warning: {
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    text: 'text-amber-800',
    icon: AlertTriangle,
    iconColor: 'text-amber-500',
  },
  info: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    text: 'text-blue-800',
    icon: Info,
    iconColor: 'text-blue-500',
  },
  error: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    text: 'text-red-800',
    icon: AlertTriangle,
    iconColor: 'text-red-500',
  },
}

export default function AlertWidget({ title, value, config }: AlertWidgetProps) {
  const severity = config.severity ?? 'info'
  const styles = SEVERITY_STYLES[severity] ?? SEVERITY_STYLES.info
  const Icon = styles.icon
  const message = value != null ? String(value) : ''

  return (
    <div className={`flex h-full items-center gap-3 rounded-lg border p-4 ${styles.bg} ${styles.border}`}>
      <Icon className={`h-6 w-6 shrink-0 ${styles.iconColor}`} />
      <div>
        <p className={`text-sm font-semibold ${styles.text}`}>{title}</p>
        {message && <p className={`mt-0.5 text-sm ${styles.text} opacity-80`}>{message}</p>}
      </div>
    </div>
  )
}
