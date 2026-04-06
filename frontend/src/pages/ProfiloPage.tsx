import { useState, useEffect } from 'react'
import {
  Save, CalendarClock, Link2, Unlink, ExternalLink, User, Mail,
} from 'lucide-react'
import {
  useProfile, useUpdateProfile,
  useMicrosoftCalendarStatus, useMicrosoftConnect, useMicrosoftDisconnect,
  useCalendlyUrl, useUpdateCalendlyUrl,
} from '../api/hooks'
import PageHeader from '../components/ui/PageHeader'
import Card from '../components/ui/Card'
import LoadingSpinner from '../components/ui/LoadingSpinner'

export default function ProfiloPage() {
  const { data: profile, isLoading } = useProfile()
  const updateProfile = useUpdateProfile()
  const { data: msStatus } = useMicrosoftCalendarStatus()
  const msConnect = useMicrosoftConnect()
  const msDisconnect = useMicrosoftDisconnect()
  const { data: calendlyData } = useCalendlyUrl()
  const updateCalendly = useUpdateCalendlyUrl()

  const [name, setName] = useState('')
  const [senderEmail, setSenderEmail] = useState('')
  const [senderName, setSenderName] = useState('')
  const [calendlyInput, setCalendlyInput] = useState('')
  const [saved, setSaved] = useState(false)
  const [calendlySaved, setCalendlySaved] = useState(false)

  useEffect(() => {
    if (profile) {
      setName(profile.name ?? '')
      setSenderEmail(profile.sender_email ?? '')
      setSenderName(profile.sender_name ?? '')
    }
  }, [profile])

  useEffect(() => {
    if (calendlyData?.calendly_url) {
      setCalendlyInput(calendlyData.calendly_url)
    }
  }, [calendlyData])

  const handleSave = async () => {
    await updateProfile.mutateAsync({
      name: name || undefined,
      sender_email: senderEmail || undefined,
      sender_name: senderName || undefined,
    })
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  const handleMsConnect = async () => {
    const result = await msConnect.mutateAsync()
    if (result.auth_url) {
      window.open(result.auth_url, '_blank', 'width=600,height=700')
    }
  }

  const handleSaveCalendly = () => {
    updateCalendly.mutate(calendlyInput)
    setCalendlySaved(true)
    setTimeout(() => setCalendlySaved(false), 3000)
  }

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  return (
    <div>
      <PageHeader title="Il mio profilo" subtitle="Gestisci i tuoi dati personali e le integrazioni calendario" />

      <div className="grid gap-6 lg:grid-cols-2">
        {/* ── Dati personali ── */}
        <Card>
          <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900">
            <User className="h-5 w-5" />
            Dati personali
          </h2>
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-500">Nome e cognome</label>
              <input type="text" value={name} onChange={(e) => setName(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500">Email account</label>
              <input type="email" value={profile?.email ?? ''} disabled
                className="mt-1 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-500" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500">Ruolo</label>
              <input type="text" value={profile?.role ?? ''} disabled
                className="mt-1 w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-500 capitalize" />
            </div>
          </div>

          {/* Email sender */}
          <h3 className="mt-6 mb-3 flex items-center gap-2 text-sm font-semibold text-gray-900">
            <Mail className="h-4 w-4" />
            Email mittente (per invio commerciale)
          </h3>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-medium text-gray-500">Email mittente</label>
              <input type="email" value={senderEmail} onChange={(e) => setSenderEmail(e.target.value)}
                placeholder={profile?.email ?? 'la tua email'}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500">Nome mittente</label>
              <input type="text" value={senderName} onChange={(e) => setSenderName(e.target.value)}
                placeholder={name || 'Il tuo nome'}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
            </div>
          </div>

          <div className="mt-5">
            <button onClick={handleSave} disabled={updateProfile.isPending}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
              <Save className="h-4 w-4" />
              {updateProfile.isPending ? 'Salvataggio...' : 'Salva profilo'}
            </button>
            {saved && <span className="ml-3 text-sm text-green-600">Salvato!</span>}
          </div>
        </Card>

        {/* ── Calendario e Appuntamenti ── */}
        <div className="space-y-6">
          <Card>
            <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900">
              <CalendarClock className="h-5 w-5" />
              Calendario e Appuntamenti
            </h2>

            {/* Microsoft 365 */}
            <div className="flex items-center justify-between rounded-lg border border-gray-200 p-4 mb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100">
                  <CalendarClock className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900">Microsoft 365 Calendar</p>
                  <p className="text-xs text-gray-500">
                    {msStatus?.connected
                      ? 'Collegato — le tue attivita pianificate appaiono su Outlook'
                      : 'Sincronizza le attivita con il tuo Outlook Calendar'}
                  </p>
                </div>
              </div>
              {msStatus?.connected ? (
                <button onClick={() => msDisconnect.mutate()} disabled={msDisconnect.isPending}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 px-3 py-2 text-xs font-medium text-red-600 hover:bg-red-50">
                  <Unlink className="h-3.5 w-3.5" /> Disconnetti
                </button>
              ) : (
                <button onClick={handleMsConnect} disabled={msConnect.isPending}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                  <Link2 className="h-3.5 w-3.5" /> {msConnect.isPending ? 'Connessione...' : 'Collega Microsoft 365'}
                </button>
              )}
            </div>

            {/* Calendly */}
            <div className="rounded-lg border border-gray-200 p-4">
              <p className="text-sm font-medium text-gray-900 mb-1">Link Calendly</p>
              <p className="text-xs text-gray-500 mb-3">
                Il tuo link di prenotazione appuntamenti. Apparira nel dettaglio deal e nei template email come variabile {'{{calendly_link}}'}.
              </p>
              <div className="flex gap-2">
                <input type="url" value={calendlyInput}
                  onChange={(e) => { setCalendlyInput(e.target.value); setCalendlySaved(false) }}
                  placeholder="https://calendly.com/tuonome/30min"
                  className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                <button onClick={handleSaveCalendly} disabled={updateCalendly.isPending}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                  {updateCalendly.isPending ? '...' : 'Salva'}
                </button>
              </div>
              {calendlySaved && <p className="mt-1 text-xs text-green-600">Salvato!</p>}
              {calendlyInput && (
                <a href={calendlyInput} target="_blank" rel="noopener noreferrer"
                  className="mt-2 inline-flex items-center gap-1 text-xs text-blue-600 hover:underline">
                  <ExternalLink className="h-3 w-3" /> Apri il tuo Calendly
                </a>
              )}
            </div>
          </Card>

          {/* Info */}
          <Card>
            <h3 className="text-sm font-medium text-gray-700 mb-2">Come funziona</h3>
            <ul className="space-y-2 text-xs text-gray-500">
              <li className="flex items-start gap-2">
                <span className="mt-0.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-blue-500" />
                <span><strong>Microsoft 365:</strong> Collegando il tuo account, le attivita pianificate in AgentFlow appariranno automaticamente sul tuo Outlook Calendar.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="mt-0.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-green-500" />
                <span><strong>Calendly:</strong> Il link apparira come bottone "Prenota appuntamento" nel dettaglio di ogni deal. Puoi anche usarlo nei template email con la variabile {'{{calendly_link}}'}.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="mt-0.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-gray-400" />
                <span><strong>File .ics:</strong> Dal calendario puoi scaricare qualsiasi attivita come file .ics per aggiungerla manualmente a Google Calendar, Apple Calendar o qualsiasi altro client.</span>
              </li>
            </ul>
          </Card>
        </div>
      </div>
    </div>
  )
}
