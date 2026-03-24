import { useState } from 'react'
import { CalendarClock, AlertTriangle, Bell } from 'lucide-react'
import { useDeadlines, useFiscalAlerts } from '../api/hooks'
import { formatDate, formatCurrency, cn } from '../lib/utils'
import PageHeader from '../components/ui/PageHeader'
import Card from '../components/ui/Card'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import EmptyState from '../components/ui/EmptyState'

export default function ScadenzarioPage() {
  const currentYear = new Date().getFullYear()
  const [year, setYear] = useState(currentYear)
  const { data: deadlines, isLoading } = useDeadlines(year)
  const { data: alerts } = useFiscalAlerts(year)

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const items = deadlines?.deadlines ?? deadlines?.items ?? []
  const alertsList = alerts?.alerts ?? []

  const getCountdownColor = (daysLeft: number) => {
    if (daysLeft < 0) return 'text-red-600 bg-red-50'
    if (daysLeft <= 7) return 'text-red-600 bg-red-50'
    if (daysLeft <= 30) return 'text-amber-600 bg-amber-50'
    return 'text-green-600 bg-green-50'
  }

  // Filter: show only future deadlines or recently past (< 30 days)
  const visibleItems = items.filter((item: Record<string, unknown>) => {
    const days = item.days_remaining as number
    return days >= -30
  })

  return (
    <div>
      <PageHeader
        title="Scadenzario"
        subtitle="Scadenze fiscali e adempimenti"
        actions={
          <select
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          >
            {[currentYear - 1, currentYear, currentYear + 1].map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        }
      />

      {/* Alerts */}
      {alertsList.length > 0 && (
        <div className="mb-6 space-y-3">
          {alertsList.map((alert: Record<string, unknown>, idx: number) => (
            <div
              key={idx}
              className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4"
            >
              <Bell className="mt-0.5 h-5 w-5 text-amber-500" />
              <div>
                <p className="text-sm font-medium text-amber-800">{alert.title as string ?? alert.name as string}</p>
                <p className="mt-1 text-sm text-amber-700">{alert.message as string ?? alert.description as string}</p>
                {alert.estimated_amount != null && (
                  <p className="mt-1 text-sm font-semibold text-amber-900">
                    Importo stimato: {formatCurrency(alert.estimated_amount as number)}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Deadlines list */}
      {visibleItems.length === 0 ? (
        <EmptyState
          title="Nessuna scadenza"
          description="Non ci sono scadenze imminenti per l'anno selezionato."
          icon={<CalendarClock className="h-12 w-12" />}
        />
      ) : (
        <div className="space-y-3">
          {visibleItems.map((item: Record<string, unknown>, idx: number) => {
            const daysLeft = item.days_remaining as number
            return (
              <Card key={idx} className="flex items-center gap-4">
                <div
                  className={cn(
                    'flex h-14 w-14 shrink-0 flex-col items-center justify-center rounded-lg text-center',
                    getCountdownColor(daysLeft)
                  )}
                >
                  <span className="text-lg font-bold">{Math.abs(daysLeft)}</span>
                  <span className="text-[10px] font-medium">
                    {daysLeft < 0 ? 'scaduta' : 'giorni'}
                  </span>
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-gray-900">{item.name as string}</p>
                  <p className="mt-0.5 text-xs text-gray-500">
                    {item.description as string}
                  </p>
                  <p className="mt-0.5 text-xs text-gray-400">
                    Scadenza: {formatDate(item.effective_date as string)}
                    {item.category ? ` — ${String(item.category).toUpperCase()}` : ''}
                  </p>
                </div>
                {daysLeft < 0 && (
                  <AlertTriangle className="h-5 w-5 shrink-0 text-red-500" />
                )}
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
