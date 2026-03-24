import { useState, useEffect } from 'react'
import { Save, Bell, Shield, CreditCard, ExternalLink, RefreshCw } from 'lucide-react'
import { useProfile, useUpdateProfile, useNotificationConfigs, useCreateNotificationConfig, useCassettoStatus } from '../api/hooks'
import api from '../api/client'
import PageHeader from '../components/ui/PageHeader'
import Card from '../components/ui/Card'
import StatusBadge from '../components/ui/StatusBadge'
import LoadingSpinner from '../components/ui/LoadingSpinner'

export default function ImpostazioniPage() {
  const { data: profile, isLoading } = useProfile()
  const updateProfile = useUpdateProfile()
  const { data: notifConfigs } = useNotificationConfigs()
  const createNotifConfig = useCreateNotificationConfig()
  const { data: cassettoStatus } = useCassettoStatus()

  const [name, setName] = useState('')
  const [aziendaNome, setAziendaNome] = useState('')
  const [piva, setPiva] = useState('')
  const [codiceAteco, setCodiceAteco] = useState('')
  const [tipoAzienda, setTipoAzienda] = useState('')
  const [regimeFiscale, setRegimeFiscale] = useState('')
  const [saved, setSaved] = useState(false)
  const [spidLoading, setSpidLoading] = useState(false)
  const [spidQrCode, setSpidQrCode] = useState('')
  const [_spidSessionId, setSpidSessionId] = useState('')
  const [spidMessage, setSpidMessage] = useState('')
  const [spidPolling, setSpidPolling] = useState(false)
  const [spidProvider, setSpidProvider] = useState('poste')
  const [showSpidSelector, setShowSpidSelector] = useState(false)
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)
  const [bankIban, setBankIban] = useState('')
  const [bankName, setBankName] = useState('')
  const [bankLoading, setBankLoading] = useState(false)
  const [bankMessage, setBankMessage] = useState('')

  useEffect(() => {
    if (profile) {
      setName(profile.name ?? '')
      setAziendaNome(profile.azienda_nome ?? '')
      setPiva(profile.piva ?? '')
      setCodiceAteco(profile.codice_ateco ?? '')
      setTipoAzienda(profile.tipo_azienda ?? '')
      setRegimeFiscale(profile.regime_fiscale ?? '')
    }
  }, [profile])

  const handleSave = async () => {
    await updateProfile.mutateAsync({
      name: name || undefined,
      azienda_nome: aziendaNome || undefined,
      piva: piva || undefined,
      codice_ateco: codiceAteco || undefined,
      tipo_azienda: tipoAzienda || undefined,
      regime_fiscale: regimeFiscale || undefined,
    })
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 5000)
  }

  const handleConnectSpid = async () => {
    if (!showSpidSelector) {
      setShowSpidSelector(true)
      return
    }
    setShowSpidSelector(false)
    setSpidLoading(true)
    setSpidMessage('')
    setSpidQrCode('')
    try {
      const { data } = await api.post('/auth/spid/init', { tipo_login: spidProvider })

      if (data.session_id) {
        setSpidSessionId(data.session_id)
        if (data.qr_code) {
          setSpidQrCode(data.qr_code)
        }
        setSpidMessage('Preparazione autenticazione SPID...')
        startSpidPolling(data.session_id)
      } else if (data.redirect_url) {
        window.open(data.redirect_url, '_blank')
      } else {
        setSpidMessage(data.message || 'Sessione SPID creata')
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Errore nella connessione SPID'
      showToast(msg, 'error')
    } finally {
      setSpidLoading(false)
    }
  }

  const startSpidPolling = (sessionId: string) => {
    setSpidPolling(true)
    const interval = setInterval(async () => {
      try {
        const { data } = await api.get(`/auth/spid/session/${sessionId}`)
        const session = data.sessione ?? data
        const stato = session.stato ?? data.stato

        if (stato === 'sessione_attiva' || stato === 'autenticato') {
          clearInterval(interval)
          setSpidPolling(false)
          setSpidQrCode('')
          setSpidMessage('SPID collegato con successo!')
        } else if (stato === 'sessione_in_errore' || stato === 'sessione_scaduta' || stato === 'credenziali_errate') {
          clearInterval(interval)
          setSpidPolling(false)
          setSpidQrCode('')
          setSpidMessage(`Autenticazione fallita: ${stato.replace(/_/g, ' ')}`)
        } else if (session.qr_code && !spidQrCode) {
          setSpidQrCode(session.qr_code)
        }
        // else keep polling (richiesta_accesso, richiesta_app_otp, etc.)
      } catch {
        // ignore polling errors
      }
    }, 3000) // poll every 3 seconds

    // Stop after 5 minutes
    setTimeout(() => {
      clearInterval(interval)
      setSpidPolling(false)
      if (spidQrCode) {
        setSpidMessage('QR code scaduto. Riprova.')
        setSpidQrCode('')
      }
    }, 300000)
  }

  const handleConnectBank = async () => {
    setBankLoading(true)
    setBankMessage('')
    try {
      // Try Salt Edge connect session first (opens bank selection page)
      const { data } = await api.post('/bank-accounts/connect-session')
      if (data.connect_url) {
        window.open(data.connect_url, '_blank')
        setBankMessage('Completa l\'autenticazione nella finestra della banca.')
      } else {
        setBankMessage(data.error || 'Errore creazione sessione')
      }
    } catch {
      // Fallback: manual IBAN connection
      if (!bankIban) {
        setBankMessage('Inserisci l\'IBAN per collegare manualmente')
        setBankLoading(false)
        return
      }
      try {
        const { data } = await api.post('/bank-accounts/connect', {
          iban: bankIban,
          bank_name: bankName || undefined,
        })
        if (data.supported === false) {
          setBankMessage(data.message)
        } else {
          setBankMessage('Conto collegato con successo!')
          setBankIban('')
          setBankName('')
        }
      } catch (err: any) {
        setBankMessage(err.response?.data?.detail || 'Errore collegamento')
      }
    } finally {
      setBankLoading(false)
    }
  }

  const handleToggleNotification = (channel: string, enabled: boolean) => {
    createNotifConfig.mutate({ channel, enabled })
  }

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const configs = notifConfigs?.configs ?? []
  const spidConnected = cassettoStatus?.connected ?? false

  return (
    <div>
      {/* Toast notification */}
      {toast && (
        <div className={`fixed right-4 top-4 z-50 rounded-lg px-4 py-3 shadow-lg ${
          toast.type === 'error' ? 'bg-red-600 text-white' : 'bg-green-600 text-white'
        }`}>
          {toast.message}
        </div>
      )}

      <PageHeader title="Impostazioni" subtitle="Configurazione profilo e connessioni" />

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Profile form */}
        <Card>
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Profilo Azienda</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-500">Nome referente</label>
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
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-500">Tipo azienda</label>
                <select
                  value={tipoAzienda}
                  onChange={(e) => setTipoAzienda(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                >
                  <option value="">Seleziona...</option>
                  <option value="srl">SRL</option>
                  <option value="srls">SRLS</option>
                  <option value="piva">P.IVA</option>
                  <option value="ditta_individuale">Ditta individuale</option>
                  <option value="altro">Altro</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500">Regime fiscale</label>
                <select
                  value={regimeFiscale}
                  onChange={(e) => setRegimeFiscale(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                >
                  <option value="">Seleziona...</option>
                  <option value="ordinario">Ordinario</option>
                  <option value="semplificato">Semplificato</option>
                  <option value="forfettario">Forfettario</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500">Partita IVA</label>
              <input
                type="text"
                value={piva}
                onChange={(e) => setPiva(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                maxLength={11}
                placeholder="12345678901"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500">Codice ATECO</label>
              <input
                type="text"
                value={codiceAteco}
                onChange={(e) => setCodiceAteco(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                placeholder="62.01.00"
              />
            </div>
          </div>

          <div className="mt-6">
            <button
              onClick={handleSave}
              disabled={updateProfile.isPending}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              <Save className="h-4 w-4" />
              {updateProfile.isPending ? 'Salvataggio...' : 'Salva profilo'}
            </button>
            {saved && (
              <span className="ml-3 text-sm text-green-600">Salvato!</span>
            )}
          </div>
        </Card>

        {/* Right column */}
        <div className="space-y-6">
          {/* SPID Connection */}
          <Card>
            <h2 className="mb-4 text-lg font-semibold text-gray-900">Cassetto Fiscale</h2>
            <div className="flex items-center justify-between rounded-lg border border-gray-200 p-4">
              <div className="flex items-center gap-3">
                <Shield className="h-6 w-6 text-blue-600" />
                <div>
                  <p className="text-sm font-medium text-gray-900">SPID / CIE</p>
                  <p className="text-xs text-gray-500">
                    {spidConnected ? 'Cassetto fiscale collegato' : 'Collega per importare le fatture'}
                  </p>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  {spidConnected && <StatusBadge status="active" />}
                  <button
                    onClick={handleConnectSpid}
                    disabled={spidLoading}
                    className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    {spidLoading ? (
                      <RefreshCw className="h-4 w-4 animate-spin" />
                    ) : (
                      <ExternalLink className="h-4 w-4" />
                    )}
                    {showSpidSelector ? 'Conferma' : spidConnected ? 'Ricollega' : 'Collega SPID'}
                  </button>
                </div>
                {showSpidSelector && (
                  <select
                    value={spidProvider}
                    onChange={(e) => setSpidProvider(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  >
                    <option value="poste">PosteID</option>
                    <option value="aruba">Aruba SPID</option>
                    <option value="cie">CIE (Carta d'Identita)</option>
                    <option value="namirial">Namirial</option>
                    <option value="teamsystem">TeamSystem</option>
                    <option value="lepida">Lepida</option>
                  </select>
                )}
              </div>
            </div>
          </Card>

          {/* SPID QR Code Modal */}
          {(spidQrCode || spidMessage) && (
            <Card>
              <div className="text-center">
                {spidQrCode && (
                  <>
                    <h3 className="mb-2 text-lg font-semibold text-gray-900">Autenticazione SPID</h3>
                    <p className="mb-4 text-sm text-gray-500">
                      Scansiona il QR code con la tua app SPID (Aruba, PosteID, etc.)
                    </p>
                    <div className="mx-auto mb-4 inline-block rounded-xl border-2 border-blue-100 bg-white p-4">
                      <img src={spidQrCode} alt="QR Code SPID" className="h-48 w-48" />
                    </div>
                    {spidPolling && (
                      <div className="flex items-center justify-center gap-2 text-sm text-blue-600">
                        <RefreshCw className="h-4 w-4 animate-spin" />
                        In attesa dell'autenticazione...
                      </div>
                    )}
                  </>
                )}
                {spidMessage && !spidQrCode && (
                  <p className={`text-sm font-medium ${spidMessage.includes('successo') ? 'text-green-600' : spidMessage.includes('fallita') || spidMessage.includes('scaduto') ? 'text-red-600' : 'text-blue-600'}`}>
                    {spidMessage}
                  </p>
                )}
              </div>
            </Card>
          )}

          {/* Bank Connection */}
          <Card>
            <h2 className="mb-4 text-lg font-semibold text-gray-900">Conto Bancario</h2>
            <p className="mb-3 text-xs text-gray-500">
              Collega uno o piu conti via Open Banking PSD2 (400+ banche italiane)
            </p>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-500">IBAN</label>
                <input
                  type="text"
                  value={bankIban}
                  onChange={(e) => setBankIban(e.target.value.toUpperCase())}
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  placeholder="IT60X0542811101000000123456"
                  maxLength={34}
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500">Nome banca (opzionale)</label>
                <input
                  type="text"
                  value={bankName}
                  onChange={(e) => setBankName(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  placeholder="es. Intesa Sanpaolo"
                />
              </div>
              <button
                onClick={handleConnectBank}
                disabled={bankLoading || !bankIban}
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                <CreditCard className="h-4 w-4" />
                {bankLoading ? 'Collegamento...' : 'Collega conto'}
              </button>
              {bankMessage && (
                <p className={`text-sm ${bankMessage.includes('successo') ? 'text-green-600' : 'text-amber-600'}`}>
                  {bankMessage}
                </p>
              )}
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
