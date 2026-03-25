import StatCardWidget from './StatCardWidget'
import BarChartWidget from './BarChartWidget'
import PieChartWidget from './PieChartWidget'
import TableWidget from './TableWidget'
import AlertWidget from './AlertWidget'

export interface WidgetDef {
  id: string
  type: string
  title: string
  data_source: string
  data_path: string
  config: Record<string, unknown>
  layout: { x: number; y: number; w: number; h: number }
}

interface WidgetRendererProps {
  widget: WidgetDef
  data: Record<string, unknown> | null
}

/**
 * Navigate a nested object by dot-separated path.
 * E.g., "fatture_attive.totale" on {fatture_attive: {totale: 1000}} -> 1000
 */
function getByPath(obj: Record<string, unknown> | null, path: string): unknown {
  if (!obj || !path) return null
  const parts = path.split('.')
  let current: unknown = obj
  for (const part of parts) {
    if (current == null || typeof current !== 'object') return null
    current = (current as Record<string, unknown>)[part]
  }
  return current
}

export default function WidgetRenderer({ widget, data }: WidgetRendererProps) {
  if (!data) {
    return (
      <div className="flex h-full items-center justify-center rounded-lg bg-white p-4 shadow-sm">
        <p className="text-sm text-gray-400">Caricamento...</p>
      </div>
    )
  }

  const resolvedData = getByPath(data, widget.data_path)
  const config = widget.config ?? {}

  switch (widget.type) {
    case 'stat_card': {
      const subtitlePath = config.subtitle_path as string | undefined
      const subtitle = subtitlePath ? getByPath(data, subtitlePath) : undefined
      return (
        <StatCardWidget
          title={widget.title}
          value={resolvedData}
          config={config as { format?: string; color?: string; subtitle_path?: string; subtitle_suffix?: string }}
          subtitle={subtitle}
        />
      )
    }

    case 'bar_chart':
      return (
        <BarChartWidget
          title={widget.title}
          data={Array.isArray(resolvedData) ? (resolvedData as Record<string, unknown>[]) : []}
          config={config as { x_key?: string; y_keys?: { key: string; color: string; name: string }[] }}
        />
      )

    case 'pie_chart':
      return (
        <PieChartWidget
          title={widget.title}
          data={Array.isArray(resolvedData) ? (resolvedData as Record<string, unknown>[]) : []}
          config={config as { value_key?: string; name_key?: string; colors?: string[]; format?: string }}
        />
      )

    case 'table':
      return (
        <TableWidget
          title={widget.title}
          data={Array.isArray(resolvedData) ? (resolvedData as Record<string, unknown>[]) : []}
          config={config as { columns?: { key: string; label: string; format?: string }[] }}
        />
      )

    case 'alert':
      return (
        <AlertWidget
          title={widget.title}
          value={resolvedData}
          config={config as { severity?: 'warning' | 'info' | 'error'; message_path?: string }}
        />
      )

    default:
      return (
        <div className="flex h-full items-center justify-center rounded-lg bg-white p-4 shadow-sm">
          <p className="text-sm text-gray-400">Widget tipo &quot;{widget.type}&quot; non supportato</p>
        </div>
      )
  }
}
