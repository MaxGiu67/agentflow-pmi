import { useState, useMemo } from 'react'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin from '@fullcalendar/interaction'
import { useCrmActivities, useMicrosoftCalendarStatus, useMicrosoftConnect, useMicrosoftDisconnect, useCalendlyUrl, useUpdateCalendlyUrl } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import { Download, Link2, Unlink, Settings, ExternalLink } from 'lucide-react'

const TYPE_COLORS: Record<string, string> = {
  call: '#3b82f6',
  meeting: '#10b981',
  email: '#8b5cf6',
  task: '#6b7280',
  note: '#f59e0b',
}

function generateIcs(activity: any) {
  const start = new Date(activity.scheduled_at)
  const durationMin = activity.type === 'meeting' ? 60 : 30
  const end = new Date(start.getTime() + durationMin * 60000)

  const lines = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//AgentFlow PMI//Calendar//IT',
    'BEGIN:VEVENT',
    `DTSTART:${formatIcsDate(start)}`,
    `DTEND:${formatIcsDate(end)}`,
    `SUMMARY:${activity.subject}`,
    `DESCRIPTION:${(activity.description || '').replace(/\n/g, '\\n')}`,
    'END:VEVENT',
    'END:VCALENDAR',
  ]

  const blob = new Blob([lines.join('\r\n')], { type: 'text/calendar;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${activity.type}-${start.toISOString().slice(0, 10)}.ics`
  a.click()
  URL.revokeObjectURL(url)
}

function formatIcsDate(d: Date): string {
  return d.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '')
}

export default function CrmCalendarPage() {
  const { data: activities, isLoading } = useCrmActivities()
  const { data: msStatus } = useMicrosoftCalendarStatus()
  const msConnect = useMicrosoftConnect()
  const msDisconnect = useMicrosoftDisconnect()
  const { data: calendlyData } = useCalendlyUrl()
  const updateCalendly = useUpdateCalendlyUrl()

  const [showSettings, setShowSettings] = useState(false)
  const [calendlyInput, setCalendlyInput] = useState('')
  const [selectedEvent, setSelectedEvent] = useState<any>(null)

  const events = useMemo(() => {
    if (!activities) return []
    const list = Array.isArray(activities) ? activities : activities.activities || []
    return list
      .filter((a: any) => a.scheduled_at)
      .map((a: any) => ({
        id: a.id,
        title: a.subject,
        start: a.scheduled_at,
        end: new Date(new Date(a.scheduled_at).getTime() + (a.type === 'meeting' ? 60 : 30) * 60000).toISOString(),
        backgroundColor: TYPE_COLORS[a.type] || '#6b7280',
        borderColor: TYPE_COLORS[a.type] || '#6b7280',
        extendedProps: a,
        classNames: a.status === 'completed' ? ['opacity-40'] : [],
      }))
  }, [activities])

  const handleMsConnect = async () => {
    const result = await msConnect.mutateAsync()
    if (result.auth_url) {
      window.open(result.auth_url, '_blank', 'width=600,height=700')
    }
  }

  const handleSaveCalendly = () => {
    updateCalendly.mutate(calendlyInput)
  }

  if (isLoading) return <LoadingSpinner />

  return (
    <div className="space-y-4">
      <PageHeader
        title="Calendario Attivita"
        subtitle="Vista agenda delle attivita pianificate"
        actions={
          <div className="flex items-center gap-2">
            {/* Microsoft 365 status */}
            {msStatus?.connected ? (
              <span className="inline-flex items-center gap-1 rounded-lg bg-green-50 px-3 py-1.5 text-xs font-medium text-green-700">
                <Link2 className="h-3.5 w-3.5" /> Outlook collegato
              </span>
            ) : null}
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50"
            >
              <Settings className="h-4 w-4" /> Impostazioni
            </button>
          </div>
        }
      />

      {/* Settings panel */}
      {showSettings && (
        <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
          <h3 className="font-medium text-gray-900">Impostazioni Calendario</h3>

          {/* Microsoft 365 */}
          <div className="flex items-center justify-between rounded-lg border border-gray-200 p-3">
            <div>
              <p className="text-sm font-medium text-gray-900">Microsoft 365 Calendar</p>
              <p className="text-xs text-gray-500">
                {msStatus?.connected
                  ? 'Collegato — le attivita pianificate appaiono su Outlook'
                  : 'Collega per sincronizzare le attivita con Outlook'}
              </p>
            </div>
            {msStatus?.connected ? (
              <button
                onClick={() => msDisconnect.mutate()}
                className="inline-flex items-center gap-1 rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50"
              >
                <Unlink className="h-3.5 w-3.5" /> Disconnetti
              </button>
            ) : (
              <button
                onClick={handleMsConnect}
                disabled={msConnect.isPending}
                className="inline-flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
              >
                <Link2 className="h-3.5 w-3.5" /> Collega Microsoft 365
              </button>
            )}
          </div>

          {/* Calendly */}
          <div className="rounded-lg border border-gray-200 p-3 space-y-2">
            <p className="text-sm font-medium text-gray-900">Link Calendly</p>
            <p className="text-xs text-gray-500">Il tuo link di prenotazione appuntamenti per i clienti</p>
            <div className="flex gap-2">
              <input
                type="url"
                value={calendlyInput || calendlyData?.calendly_url || ''}
                onChange={(e) => setCalendlyInput(e.target.value)}
                placeholder="https://calendly.com/tuonome"
                className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
              <button
                onClick={handleSaveCalendly}
                disabled={updateCalendly.isPending}
                className="rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Salva
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="flex flex-wrap gap-3">
        {Object.entries(TYPE_COLORS).map(([type, color]) => (
          <span key={type} className="inline-flex items-center gap-1.5 text-xs text-gray-600">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
            {type.charAt(0).toUpperCase() + type.slice(1)}
          </span>
        ))}
      </div>

      {/* Calendar */}
      <div className="rounded-xl border border-gray-200 bg-white p-4">
        <FullCalendar
          plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
          initialView="timeGridWeek"
          headerToolbar={{
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay',
          }}
          locale="it"
          firstDay={1}
          slotMinTime="07:00:00"
          slotMaxTime="20:00:00"
          events={events}
          eventClick={(info) => setSelectedEvent(info.event.extendedProps)}
          height="auto"
          buttonText={{
            today: 'Oggi',
            month: 'Mese',
            week: 'Settimana',
            day: 'Giorno',
          }}
        />
      </div>

      {/* Event popover */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => setSelectedEvent(null)}>
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{selectedEvent.subject}</h3>
                <p className="text-sm text-gray-500 mt-0.5">
                  <span
                    className="inline-block h-2 w-2 rounded-full mr-1.5"
                    style={{ backgroundColor: TYPE_COLORS[selectedEvent.type] || '#6b7280' }}
                  />
                  {selectedEvent.type} — {selectedEvent.status === 'completed' ? 'Completata' : 'Pianificata'}
                </p>
              </div>
              <button onClick={() => setSelectedEvent(null)} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
            </div>

            {selectedEvent.description && (
              <p className="text-sm text-gray-600 mb-3">{selectedEvent.description}</p>
            )}

            {selectedEvent.scheduled_at && (
              <p className="text-sm text-gray-500 mb-4">
                {new Date(selectedEvent.scheduled_at).toLocaleString('it-IT', {
                  weekday: 'long', day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit',
                })}
              </p>
            )}

            <div className="flex gap-2">
              <button
                onClick={() => { generateIcs(selectedEvent); setSelectedEvent(null) }}
                className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50"
              >
                <Download className="h-4 w-4" /> Aggiungi al calendario
              </button>
              {selectedEvent.deal_id && (
                <a
                  href={`/crm/deals/${selectedEvent.deal_id}`}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
                >
                  <ExternalLink className="h-4 w-4" /> Vai al deal
                </a>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
