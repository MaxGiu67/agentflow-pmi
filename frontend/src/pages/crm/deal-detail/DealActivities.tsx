import { useState } from 'react'
import {
  useActivityTypes, useCrmActivities, useCreateCrmActivity, useUpdateCrmActivity,
  useEmailSends,
} from '../../../api/hooks'
import {
  Plus, Phone, Video, Calendar, Mail, MessageSquare, Activity, Pencil,
  ChevronUp, Save, CheckCircle, AlertCircle, Eye, MousePointer,
} from 'lucide-react'

const ACTIVITY_ICONS: Record<string, typeof Phone> = {
  call: Phone, video_call: Video, meeting: Calendar, email: Mail, note: MessageSquare, task: Activity,
}

const STATUS_ICONS: Record<string, { icon: typeof Mail; color: string; label: string }> = {
  sent: { icon: Mail, color: 'text-gray-400', label: 'Inviata' },
  delivered: { icon: CheckCircle, color: 'text-blue-400', label: 'Consegnata' },
  opened: { icon: Eye, color: 'text-green-500', label: 'Letta' },
  clicked: { icon: MousePointer, color: 'text-purple-500', label: 'Cliccata' },
  bounced: { icon: AlertCircle, color: 'text-red-500', label: 'Rimbalzata' },
}

interface DealActivitiesProps {
  deal: any
}

export default function DealActivities({ deal }: DealActivitiesProps) {
  const { data: activityTypes } = useActivityTypes(true)
  const { data: activities } = useCrmActivities(undefined, deal?.id)
  const createActivity = useCreateCrmActivity()
  const updateActivity = useUpdateCrmActivity()
  const { data: emailHistory } = useEmailSends(deal?.client_id || undefined)

  const [showActivityForm, setShowActivityForm] = useState(false)
  const [actForm, setActForm] = useState({ type: 'call', activity_type_id: '', subject: '', description: '', status: 'completed', scheduled_at: '' })
  const [editingActivityId, setEditingActivityId] = useState<string | null>(null)
  const [editActForm, setEditActForm] = useState({ subject: '', description: '', type: '', status: '' })

  const handleCreateActivity = async () => {
    if (!actForm.subject.trim()) return
    await createActivity.mutateAsync({
      deal_id: deal.id,
      contact_id: deal.client_id || undefined,
      type: actForm.type,
      activity_type_id: actForm.activity_type_id || undefined,
      subject: actForm.subject,
      description: actForm.description || undefined,
      status: actForm.status,
      scheduled_at: actForm.scheduled_at || undefined,
    })
    setActForm({ type: 'call', activity_type_id: '', subject: '', description: '', status: 'completed', scheduled_at: '' })
    setShowActivityForm(false)
  }

  return (
    <>
      <div className="rounded-2xl border border-gray-200 bg-white p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold uppercase text-gray-400">Attivita</h3>
          <button onClick={() => setShowActivityForm(!showActivityForm)}
            className="inline-flex items-center gap-1 rounded-lg bg-green-50 px-3 py-1.5 text-xs font-medium text-green-700 hover:bg-green-100">
            <Plus className="h-3 w-3" /> Nuova Attivita
          </button>
        </div>

        {showActivityForm && (
          <div className="mb-4 rounded-lg border border-green-200 bg-green-50/30 p-4 space-y-3">
            {/* Activity type -- big buttons */}
            <div className="grid grid-cols-3 sm:grid-cols-6 gap-1.5">
              {[
                { value: 'call', label: 'Chiamata', emoji: '\u{1F4DE}' },
                { value: 'video_call', label: 'Video', emoji: '\u{1F4F9}' },
                { value: 'meeting', label: 'Riunione', emoji: '\u{1F91D}' },
                { value: 'email', label: 'Email', emoji: '\u{1F4E7}' },
                { value: 'task', label: 'Task', emoji: '\u{2705}' },
                { value: 'note', label: 'Nota', emoji: '\u{1F4DD}' },
              ].map(({ value, label, emoji }) => (
                <button key={value}
                  onClick={() => setActForm({ ...actForm, type: value, status: value === 'note' ? 'completed' : 'planned' })}
                  className={`flex flex-col items-center gap-0.5 rounded-lg border-2 p-2 text-xs font-medium transition-all ${
                    actForm.type === value ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-600 hover:border-gray-300'
                  }`}>
                  <span className="text-base">{emoji}</span>
                  {label}
                </button>
              ))}
            </div>

            <input type="text" value={actForm.subject} onChange={(e) => setActForm({ ...actForm, subject: e.target.value })}
              placeholder="Oggetto (es. Chiamata qualifica con Mario Rossi) *" className="w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm" />

            <div className="grid gap-2 sm:grid-cols-3">
              <select value={actForm.status} onChange={(e) => setActForm({ ...actForm, status: e.target.value })}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                <option value="planned">Pianificata</option>
                <option value="completed">Completata</option>
              </select>
              <input type="datetime-local" value={actForm.scheduled_at}
                onChange={(e) => setActForm({ ...actForm, scheduled_at: e.target.value })}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm"
                placeholder="Data e ora" />
              <select value={actForm.activity_type_id} onChange={(e) => setActForm({ ...actForm, activity_type_id: e.target.value })}
                className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                <option value="">-- Tipo specifico (opz.) --</option>
                {activityTypes?.map((t: any) => (
                  <option key={t.id} value={t.id}>{t.label}</option>
                ))}
              </select>
            </div>

            <textarea value={actForm.description} onChange={(e) => setActForm({ ...actForm, description: e.target.value })}
              placeholder="Note / descrizione" rows={2} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />

            {actForm.status === 'planned' && actForm.scheduled_at && (
              <p className="text-xs text-green-600">Verra sincronizzata automaticamente con Outlook Calendar</p>
            )}

            <div className="flex gap-2">
              <button onClick={handleCreateActivity} disabled={!actForm.subject.trim() || createActivity.isPending}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 hover:bg-blue-700">
                {createActivity.isPending ? 'Salvataggio...' : actForm.status === 'planned' ? 'Pianifica' : 'Salva'}
              </button>
              <button onClick={() => setShowActivityForm(false)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600">Annulla</button>
            </div>
          </div>
        )}

        {activities && activities.length > 0 ? (
          <div className="space-y-2">
            {activities.map((a: any) => {
              const AIcon = ACTIVITY_ICONS[a.type] || Activity
              const isPlanned = a.status === 'planned'
              const isEditing = editingActivityId === a.id
              return (
                <div key={a.id} className={`rounded-lg border px-4 py-2.5 ${isPlanned ? 'border-amber-200 bg-amber-50/50' : 'border-gray-100'}`}>
                  <div className="flex items-start gap-3">
                    <AIcon className={`h-4 w-4 mt-0.5 shrink-0 ${isPlanned ? 'text-amber-500' : 'text-gray-400'}`} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-gray-900">{a.subject}</p>
                        {isPlanned && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-700">Pianificata</span>}
                        {a.status === 'cancelled' && <span className="rounded-full bg-red-100 px-2 py-0.5 text-[10px] font-medium text-red-700">Annullata</span>}
                      </div>
                      {a.description && <p className="text-xs text-gray-500 mt-0.5">{a.description}</p>}
                      <p className="text-[10px] text-gray-400 mt-1">
                        {a.type} - {a.status}
                        {a.scheduled_at && ` - ${a.scheduled_at.split('T')[0]} ${a.scheduled_at.split('T')[1]?.slice(0, 5) || ''}`}
                        {!a.scheduled_at && a.created_at && ` - ${a.created_at.split('T')[0]}`}
                      </p>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      {isPlanned && (
                        <button onClick={() => updateActivity.mutateAsync({ activityId: a.id, status: 'completed' })}
                          className="rounded bg-green-50 px-2 py-1 text-[10px] font-medium text-green-700 hover:bg-green-100">
                          Completa
                        </button>
                      )}
                      <button onClick={() => {
                        if (isEditing) {
                          setEditingActivityId(null)
                        } else {
                          setEditingActivityId(a.id)
                          setEditActForm({
                            subject: a.subject || '',
                            description: a.description || '',
                            type: a.type || 'call',
                            status: a.status || 'planned',
                          })
                        }
                      }}
                        className={`rounded px-2 py-1 text-[10px] font-medium ${isEditing ? 'bg-purple-100 text-purple-700' : 'bg-gray-50 text-gray-500 hover:bg-gray-100'}`}>
                        {isEditing ? <ChevronUp className="h-3 w-3" /> : <Pencil className="h-3 w-3" />}
                      </button>
                    </div>
                  </div>

                  {/* Inline edit form */}
                  {isEditing && (
                    <div className="mt-3 ml-7 space-y-2 border-t border-gray-100 pt-3">
                      <input type="text" value={editActForm.subject} onChange={(e) => setEditActForm({ ...editActForm, subject: e.target.value })}
                        placeholder="Oggetto *" className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
                      <textarea value={editActForm.description} onChange={(e) => setEditActForm({ ...editActForm, description: e.target.value })}
                        placeholder="Descrizione" rows={2} className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
                      <div className="grid gap-2 sm:grid-cols-2">
                        <select value={editActForm.type} onChange={(e) => setEditActForm({ ...editActForm, type: e.target.value })}
                          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm">
                          <option value="call">Chiamata</option>
                          <option value="video_call">Video Call</option>
                          <option value="meeting">Riunione</option>
                          <option value="email">Email</option>
                          <option value="task">Task</option>
                          <option value="note">Nota</option>
                        </select>
                        <select value={editActForm.status} onChange={(e) => setEditActForm({ ...editActForm, status: e.target.value })}
                          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm">
                          <option value="planned">Pianificata</option>
                          <option value="completed">Completata</option>
                          <option value="cancelled">Annullata</option>
                        </select>
                      </div>
                      <div className="flex gap-2">
                        <button onClick={async () => {
                          if (!editActForm.subject.trim()) return
                          await updateActivity.mutateAsync({
                            activityId: a.id,
                            subject: editActForm.subject,
                            description: editActForm.description || undefined,
                            type: editActForm.type,
                            status: editActForm.status,
                          })
                          setEditingActivityId(null)
                        }} disabled={!editActForm.subject.trim() || updateActivity.isPending}
                          className="inline-flex items-center gap-1 rounded-lg bg-purple-600 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50">
                          <Save className="h-3 w-3" /> {updateActivity.isPending ? 'Salvataggio...' : 'Salva'}
                        </button>
                        <button onClick={() => setEditingActivityId(null)}
                          className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-600">Annulla</button>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        ) : (
          <p className="text-sm text-gray-400 text-center py-4">Nessuna attivita registrata</p>
        )}
      </div>

      {/* ── Email History ── */}
      {emailHistory && emailHistory.length > 0 && (
        <div className="rounded-2xl border border-gray-200 bg-white p-6">
          <h3 className="text-sm font-semibold uppercase text-gray-400 mb-4">Email inviate</h3>
          <div className="space-y-2">
            {emailHistory.map((email: any) => {
              const st = STATUS_ICONS[email.status] || STATUS_ICONS.sent
              const Icon = st.icon
              return (
                <div key={email.id} className="flex items-center justify-between rounded-lg border border-gray-100 px-4 py-2.5">
                  <div className="flex items-center gap-3 min-w-0">
                    <Icon className={`h-4 w-4 shrink-0 ${st.color}`} />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{email.subject}</p>
                      <p className="text-xs text-gray-400">{email.to_email} &mdash; {email.sent_at?.split('T')[0]}</p>
                    </div>
                  </div>
                  <span className={`text-xs font-medium shrink-0 ${st.color}`}>{st.label}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </>
  )
}
