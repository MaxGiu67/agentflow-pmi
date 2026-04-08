import { useState, useMemo } from 'react'
import FullCalendar from '@fullcalendar/react'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin from '@fullcalendar/interaction'
import { useCrmActivities, useCreateCrmActivity, useUpdateCrmActivity, useCrmDeals, useCrmContacts, useMicrosoftCalendarStatus } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import { Link2, Phone, Video, Users, Mail, MessageSquare, ClipboardList, X, ExternalLink, Check } from 'lucide-react'

const ACTIVITY_TYPES = [
  { value: 'call', label: 'Chiamata', icon: Phone, color: '#3b82f6', duration: 30 },
  { value: 'video_call', label: 'Videochiamata', icon: Video, color: '#8b5cf6', duration: 45 },
  { value: 'meeting', label: 'Riunione', icon: Users, color: '#10b981', duration: 60 },
  { value: 'email', label: 'Email', icon: Mail, color: '#f59e0b', duration: 15 },
  { value: 'task', label: 'Task', icon: ClipboardList, color: '#6b7280', duration: 30 },
  { value: 'note', label: 'Nota', icon: MessageSquare, color: '#ef4444', duration: 15 },
]

const TYPE_COLORS: Record<string, string> = Object.fromEntries(ACTIVITY_TYPES.map(t => [t.value, t.color]))
const TYPE_DURATION: Record<string, number> = Object.fromEntries(ACTIVITY_TYPES.map(t => [t.value, t.duration]))

export default function CrmCalendarPage() {
  const { data: activities, isLoading } = useCrmActivities()
  const { data: msStatus } = useMicrosoftCalendarStatus()
  const createActivity = useCreateCrmActivity()
  const updateActivity = useUpdateCrmActivity()
  const { data: dealsData } = useCrmDeals('', '')
  const { data: contactsData } = useCrmContacts('')

  const [selectedEvent, setSelectedEvent] = useState<any>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [createForm, setCreateForm] = useState({
    type: 'call',
    subject: '',
    description: '',
    scheduled_at: '',
    deal_id: '',
    contact_id: '',
  })

  // Map activities to FullCalendar events
  const events = useMemo(() => {
    if (!activities) return []
    const list = Array.isArray(activities) ? activities : activities.activities || []
    return list
      .filter((a: any) => a.scheduled_at)
      .map((a: any) => {
        const duration = TYPE_DURATION[a.type] || 30
        return {
          id: a.id,
          title: a.subject,
          start: a.scheduled_at,
          end: new Date(new Date(a.scheduled_at).getTime() + duration * 60000).toISOString(),
          backgroundColor: TYPE_COLORS[a.type] || '#6b7280',
          borderColor: TYPE_COLORS[a.type] || '#6b7280',
          extendedProps: a,
          classNames: a.status === 'completed' ? ['opacity-40', 'line-through'] : [],
        }
      })
  }, [activities])

  // Click on empty time slot → open create form with pre-filled time
  const handleDateClick = (info: any) => {
    const dt = info.dateStr.includes('T') ? info.dateStr : `${info.dateStr}T09:00`
    setCreateForm({
      type: 'call',
      subject: '',
      description: '',
      scheduled_at: dt.slice(0, 16), // format for datetime-local input
      deal_id: '',
      contact_id: '',
    })
    setShowCreateForm(true)
  }

  // Drag to move — update scheduled_at directly
  const handleEventDrop = (info: any) => {
    const activityId = info.event.extendedProps?.id
    if (!activityId) { info.revert(); return }
    const newDate = info.event.start?.toISOString()
    if (!newDate) { info.revert(); return }
    updateActivity.mutate(
      { activityId, scheduled_at: newDate },
      { onError: () => info.revert() }
    )
  }

  // Drag to resize — update scheduled_at to new start
  const handleEventResize = (info: any) => {
    const activityId = info.event.extendedProps?.id
    if (!activityId) { info.revert(); return }
    const newDate = info.event.start?.toISOString()
    if (!newDate) { info.revert(); return }
    updateActivity.mutate(
      { activityId, scheduled_at: newDate },
      { onError: () => info.revert() }
    )
  }

  const handleCreate = async () => {
    if (!createForm.subject.trim() || !createForm.scheduled_at) return
    await createActivity.mutateAsync({
      type: createForm.type,
      subject: createForm.subject,
      description: createForm.description || undefined,
      scheduled_at: createForm.scheduled_at,
      deal_id: createForm.deal_id || undefined,
      contact_id: createForm.contact_id || undefined,
      status: 'planned',
    })
    setShowCreateForm(false)
  }

  if (isLoading) return <LoadingSpinner />

  return (
    <div className="space-y-4">
      <PageHeader
        title="Calendario"
        subtitle="Pianifica e gestisci chiamate, videochiamate, riunioni"
        actions={
          <div className="flex items-center gap-2">
            {msStatus?.connected && (
              <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-3 py-1.5 text-xs font-medium text-green-700 border border-green-200">
                <Link2 className="h-3 w-3" /> Outlook sincronizzato
              </span>
            )}
            <button
              onClick={() => {
                const now = new Date()
                const dt = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}T${String(now.getHours() + 1).padStart(2, '0')}:00`
                setCreateForm({ type: 'call', subject: '', description: '', scheduled_at: dt, deal_id: '', contact_id: '' })
                setShowCreateForm(true)
              }}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              + Nuova Attivita
            </button>
          </div>
        }
      />

      {/* Legend */}
      <div className="flex flex-wrap gap-3">
        {ACTIVITY_TYPES.map(({ value, label, color, icon: Icon }) => (
          <span key={value} className="inline-flex items-center gap-1.5 text-xs text-gray-600">
            <Icon className="h-3 w-3" style={{ color }} />
            {label}
          </span>
        ))}
        <span className="inline-flex items-center gap-1.5 text-xs text-gray-400 ml-2">
          <span className="h-2.5 w-2.5 rounded-full bg-gray-300 opacity-40" /> = completata
        </span>
      </div>

      {/* Calendar */}
      <div className="rounded-xl border border-gray-200 bg-white p-3">
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
          slotMaxTime="21:00:00"
          slotDuration="00:30:00"
          nowIndicator={true}
          selectable={true}
          editable={true}
          events={events}
          dateClick={handleDateClick}
          eventDrop={handleEventDrop}
          eventResize={handleEventResize}
          eventClick={(info) => setSelectedEvent(info.event.extendedProps)}
          height="auto"
          allDaySlot={false}
          buttonText={{
            today: 'Oggi',
            month: 'Mese',
            week: 'Settimana',
            day: 'Giorno',
          }}
          eventContent={(eventInfo) => {
            const type = eventInfo.event.extendedProps?.type || 'call'
            const TypeIcon = ACTIVITY_TYPES.find(t => t.value === type)?.icon || Phone
            return (
              <div className="flex items-center gap-1 px-1 py-0.5 overflow-hidden">
                <TypeIcon className="h-3 w-3 shrink-0" />
                <span className="text-xs truncate">{eventInfo.event.title}</span>
              </div>
            )
          }}
        />
      </div>

      {/* ── Create Activity Modal ── */}
      {showCreateForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setShowCreateForm(false)}>
          <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl space-y-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Nuova Attivita</h3>
              <button onClick={() => setShowCreateForm(false)} className="text-gray-400 hover:text-gray-600">
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Activity type selector — big buttons */}
            <div className="grid grid-cols-3 gap-2">
              {ACTIVITY_TYPES.map(({ value, label, icon: Icon, color }) => (
                <button
                  key={value}
                  onClick={() => setCreateForm({ ...createForm, type: value })}
                  className={`flex flex-col items-center gap-1 rounded-xl border-2 p-3 text-xs font-medium transition-all ${
                    createForm.type === value
                      ? 'border-blue-500 bg-blue-50 text-blue-700'
                      : 'border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  <Icon className="h-5 w-5" style={{ color: createForm.type === value ? color : undefined }} />
                  {label}
                </button>
              ))}
            </div>

            {/* Form */}
            <div className="space-y-3">
              <input
                type="text"
                value={createForm.subject}
                onChange={(e) => setCreateForm({ ...createForm, subject: e.target.value })}
                placeholder="Oggetto (es. Chiamata qualifica con Mario Rossi)"
                className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                autoFocus
              />

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-gray-500 mb-1 block">Data e ora</label>
                  <input
                    type="datetime-local"
                    value={createForm.scheduled_at}
                    onChange={(e) => setCreateForm({ ...createForm, scheduled_at: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-500 mb-1 block">Deal collegato</label>
                  <select
                    value={createForm.deal_id}
                    onChange={(e) => setCreateForm({ ...createForm, deal_id: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                  >
                    <option value="">-- Nessun deal --</option>
                    {dealsData?.deals?.map((d: any) => (
                      <option key={d.id} value={d.id}>{d.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-gray-500 mb-1 block">Contatto</label>
                <select
                  value={createForm.contact_id}
                  onChange={(e) => setCreateForm({ ...createForm, contact_id: e.target.value })}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
                >
                  <option value="">-- Nessun contatto --</option>
                  {contactsData?.contacts?.map((c: any) => (
                    <option key={c.id} value={c.id}>{c.contact_name || c.name}{c.email ? ` (${c.email})` : ''}</option>
                  ))}
                </select>
              </div>

              <textarea
                value={createForm.description}
                onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                placeholder="Note (opzionale)"
                rows={2}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>

            {/* Outlook sync note */}
            {msStatus?.connected && (
              <p className="text-xs text-green-600 flex items-center gap-1">
                <Check className="h-3 w-3" /> Verra sincronizzata automaticamente con Outlook
              </p>
            )}

            <div className="flex gap-2 pt-1">
              <button
                onClick={handleCreate}
                disabled={!createForm.subject.trim() || !createForm.scheduled_at || createActivity.isPending}
                className="flex-1 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {createActivity.isPending ? 'Salvataggio...' : 'Pianifica'}
              </button>
              <button
                onClick={() => setShowCreateForm(false)}
                className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm text-gray-600 hover:bg-gray-50"
              >
                Annulla
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Event Detail Popover ── */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => setSelectedEvent(null)}>
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">{selectedEvent.subject}</h3>
                <div className="flex items-center gap-2 mt-1">
                  {(() => {
                    const typeInfo = ACTIVITY_TYPES.find(t => t.value === selectedEvent.type)
                    const Icon = typeInfo?.icon || Phone
                    return (
                      <span className="inline-flex items-center gap-1 text-xs font-medium" style={{ color: typeInfo?.color }}>
                        <Icon className="h-3.5 w-3.5" /> {typeInfo?.label || selectedEvent.type}
                      </span>
                    )
                  })()}
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    selectedEvent.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {selectedEvent.status === 'completed' ? 'Completata' : 'Pianificata'}
                  </span>
                  {selectedEvent.outlook_event_id && (
                    <span className="inline-flex items-center gap-0.5 text-xs text-blue-500">
                      <Link2 className="h-3 w-3" /> Outlook
                    </span>
                  )}
                </div>
              </div>
              <button onClick={() => setSelectedEvent(null)} className="text-gray-400 hover:text-gray-600">
                <X className="h-5 w-5" />
              </button>
            </div>

            {selectedEvent.description && (
              <p className="text-sm text-gray-600 mb-3">{selectedEvent.description}</p>
            )}

            {selectedEvent.scheduled_at && (
              <p className="text-sm text-gray-700 font-medium mb-4">
                {new Date(selectedEvent.scheduled_at).toLocaleString('it-IT', {
                  weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
                  hour: '2-digit', minute: '2-digit',
                })}
              </p>
            )}

            <div className="flex gap-2">
              {selectedEvent.deal_id && (
                <a
                  href={`/crm/deals/${selectedEvent.deal_id}`}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
                >
                  <ExternalLink className="h-4 w-4" /> Vai al deal
                </a>
              )}
              <button
                onClick={() => setSelectedEvent(null)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50"
              >
                Chiudi
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
