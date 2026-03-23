import { useState, useEffect } from 'react'
import { Save, Bell, Shield, CreditCard } from 'lucide-react'
import { useProfile, useUpdateProfile, useNotificationConfigs, useCreateNotificationConfig } from '../api/hooks'
import PageHeader from '../components/ui/PageHeader'
import Card from '../components/ui/Card'
import StatusBadge from '../components/ui/StatusBadge'
import LoadingSpinner from '../components/ui/LoadingSpinner'

export default function ImpostazioniPage() {
  const { data: profile, isLoading } = useProfile()
  const updateProfile = useUpdateProfile()
  const { data: notifConfigs } = useNotificationConfigs()
  const createNotifConfig = useCreateNotificationConfig()

  const [name, setName] = useState('')
  const [aziendaNome, setAziendaNome] = useState('')
  const [piva, setPiva] = useState('')
  const [codiceAteco, setCodiceAteco] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (profile) {
      setName(profile.name ?? '')
      setAziendaNome(profile.azienda_nome ?? '')
      setPiva(profile.piva ?? '')
      setCodiceAteco(profile.codice_ateco ?? '')
    }
  }, [profile])

  const handleSave = async () => {
    await updateProfile.mutateAsync({
      name: name || undefined,
      azienda_nome: aziendaNome || undefined,
      piva: piva || undefined,
      codice_ateco: codiceAteco || undefined,
    })
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  const handleToggleNotification = (channel: string, enabled: boolean) => {
    createNotifConfig.mutate({ channel, enabled })
  }

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const configs = notifConfigs?.configs ?? []

  return (
    <div>
      <PageHeader title="Impostazioni" subtitle="Configurazione profilo e connessioni" />

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Profile form */}
        <Card>
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Profilo</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-500">Nome</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500">Nome azienda</label>
              <input
                type="text"
                value={aziendaNome}
                onChange={(e) => setAziendaNome(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500">Partita IVA</label>
              <input
                type="text"
                value={piva}
                onChange={(e) => setPiva(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                maxLength={11}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500">Codice ATECO</label>
              <input
                type="text"
                value={codiceAteco}
                onChange={(e) => setCodiceAteco(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>

            {profile?.tipo_azienda && (
              <div className="flex justify-between">
                <span className="text-sm text-gray-500">Tipo azienda</span>
                <span className="text-sm font-medium text-gray-900">{profile.tipo_azienda}</span>
              </div>
            )}
            {profile?.regime_fiscale && (
              <div className="flex justify-between">
                <span className="text-sm text-gray-500">Regime fiscale</span>
                <span className="text-sm font-medium text-gray-900">{profile.regime_fiscale}</span>
              </div>
            )}
          </div>

          <div className="mt-6">
            <button
              onClick={handleSave}
              disabled={updateProfile.isPending}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              <Save className="h-4 w-4" />
              {updateProfile.isPending ? 'Salvataggio...' : 'Salva'}
            </button>
            {saved && (
              <span className="ml-3 text-sm text-green-600">Salvato con successo!</span>
            )}
          </div>
        </Card>

        {/* Connections status */}
        <div className="space-y-6">
          <Card>
            <h2 className="mb-4 text-lg font-semibold text-gray-900">Connessioni</h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-lg border border-gray-200 p-3">
                <div className="flex items-center gap-3">
                  <Shield className="h-5 w-5 text-blue-600" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">SPID / CIE</p>
                    <p className="text-xs text-gray-500">Accesso al cassetto fiscale</p>
                  </div>
                </div>
                <StatusBadge status={profile?.spid_connected ? 'active' : 'idle'} />
              </div>
              <div className="flex items-center justify-between rounded-lg border border-gray-200 p-3">
                <div className="flex items-center gap-3">
                  <CreditCard className="h-5 w-5 text-blue-600" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">Conto bancario</p>
                    <p className="text-xs text-gray-500">Open Banking PSD2</p>
                  </div>
                </div>
                <StatusBadge status={profile?.bank_connected ? 'active' : 'idle'} />
              </div>
            </div>
          </Card>

          {/* Notifications */}
          <Card>
            <h2 className="mb-4 flex items-center gap-2 text-lg font-semibold text-gray-900">
              <Bell className="h-5 w-5" />
              Notifiche
            </h2>
            <div className="space-y-3">
              {['email', 'telegram', 'whatsapp'].map((channel) => {
                const config = configs.find((c: Record<string, unknown>) => c.channel === channel)
                const enabled = config?.enabled ?? false
                return (
                  <div key={channel} className="flex items-center justify-between">
                    <span className="text-sm font-medium capitalize text-gray-700">{channel}</span>
                    <button
                      onClick={() => handleToggleNotification(channel, !enabled)}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        enabled ? 'bg-blue-600' : 'bg-gray-300'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          enabled ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </div>
                )
              })}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
