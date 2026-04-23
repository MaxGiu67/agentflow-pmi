import { useEffect, useState } from 'react'
import { CheckCircle2, XCircle, Mail, RefreshCw, HelpCircle } from 'lucide-react'
import {
  usePecProviders,
  usePecConfig,
  useSavePecConfig,
  useTestPecConfig,
  type PecProviderPreset,
} from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import LoadingSpinner from '../../components/ui/LoadingSpinner'

export default function PecConfigPage() {
  const { data: providers } = usePecProviders()
  const { data: config, isLoading } = usePecConfig()
  const saveConfig = useSavePecConfig()
  const testConfig = useTestPecConfig()

  const [provider, setProvider] = useState('aruba')
  const [pecAddress, setPecAddress] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showCustom, setShowCustom] = useState(false)
  const [smtpHost, setSmtpHost] = useState('')
  const [smtpPort, setSmtpPort] = useState<number>(465)
  const [imapHost, setImapHost] = useState('')
  const [imapPort, setImapPort] = useState<number>(993)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [showGuide, setShowGuide] = useState(false)

  useEffect(() => {
    if (config) {
      setProvider(config.provider)
      setPecAddress(config.pec_address)
      setUsername(config.username)
      setSmtpHost(config.smtp_host)
      setSmtpPort(config.smtp_port)
      setImapHost(config.imap_host)
      setImapPort(config.imap_port)
      setShowCustom(config.provider === 'custom')
    }
  }, [config])

  const selectedPreset = providers?.find((p) => p.code === provider)

  useEffect(() => {
    if (!showCustom && selectedPreset) {
      setSmtpHost(selectedPreset.smtp_host)
      setSmtpPort(selectedPreset.smtp_port)
      setImapHost(selectedPreset.imap_host)
      setImapPort(selectedPreset.imap_port)
    }
  }, [provider, selectedPreset, showCustom])

  const handleSave = async () => {
    setError(null)
    setSuccess(null)
    if (!pecAddress || !username || !password) {
      setError('Compila indirizzo PEC, username e password')
      return
    }
    try {
      await saveConfig.mutateAsync({
        provider: showCustom ? 'custom' : provider,
        pec_address: pecAddress,
        username,
        password,
        smtp_host: showCustom ? smtpHost : undefined,
        smtp_port: showCustom ? smtpPort : undefined,
        imap_host: showCustom ? imapHost : undefined,
        imap_port: showCustom ? imapPort : undefined,
      })
      setSuccess('Configurazione salvata — premi "Testa connessione" per verificare')
      setPassword('')
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail ?? 'Errore salvataggio')
    }
  }

  const handleTest = async () => {
    setError(null)
    setSuccess(null)
    try {
      const r = await testConfig.mutateAsync()
      if (r.smtp_ok && r.imap_ok) {
        setSuccess('SMTP e IMAP OK — PEC configurata correttamente')
      } else {
        setError(
          `Problema connessione: SMTP ${r.smtp_ok ? 'OK' : 'KO'}, IMAP ${r.imap_ok ? 'OK' : 'KO'}. ${r.error ?? ''}`,
        )
      }
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(detail ?? 'Errore test connessione')
    }
  }

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  return (
    <div>
      <PageHeader
        title="Configurazione PEC"
        subtitle="Configura la tua PEC per inviare fatture elettroniche al Sistema di Interscambio (SDI)"
      />

      {config && (
        <Card className="mb-4">
          <div className="flex items-center gap-3">
            {config.verified ? (
              <CheckCircle2 className="h-5 w-5 text-green-600" />
            ) : (
              <XCircle className="h-5 w-5 text-gray-400" />
            )}
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">
                {config.pec_address}
                <span className="ml-2 text-xs text-gray-500">
                  ({providers?.find((p) => p.code === config.provider)?.label ?? config.provider})
                </span>
              </p>
              <p className="text-xs text-gray-500">
                {config.verified
                  ? `Ultimo test OK — ${config.last_test_at ? new Date(config.last_test_at).toLocaleString('it-IT') : ''}`
                  : 'Non ancora verificata'}
              </p>
              {config.last_test_error && (
                <p className="mt-1 text-xs text-red-600">{config.last_test_error}</p>
              )}
            </div>
          </div>
        </Card>
      )}

      <Card>
        <h3 className="mb-4 text-lg font-semibold">Credenziali PEC</h3>

        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-gray-700">Provider</label>
            <select
              value={provider}
              onChange={(e) => {
                const v = e.target.value
                setProvider(v)
                setShowCustom(v === 'custom')
              }}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            >
              {providers?.map((p: PecProviderPreset) => (
                <option key={p.code} value={p.code}>
                  {p.label}
                </option>
              ))}
              <option value="custom">Altro / Configurazione manuale</option>
            </select>
            {selectedPreset?.docs && !showCustom && (
              <a
                href={selectedPreset.docs}
                target="_blank"
                rel="noreferrer"
                className="mt-1 inline-block text-xs text-blue-600 hover:underline"
              >
                Documentazione {selectedPreset.label}
              </a>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Indirizzo PEC *</label>
            <input
              type="email"
              value={pecAddress}
              onChange={(e) => setPecAddress(e.target.value)}
              placeholder="nomecompleto@pec.tuodominio.it"
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Username *</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Spesso uguale all'indirizzo PEC"
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Password *</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={config ? '••••••••••• (lascia vuoto per non cambiare)' : 'Password PEC'}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
            <p className="mt-1 text-xs text-gray-500">Cifrata AES-256 prima di salvare</p>
          </div>
        </div>

        {showCustom && (
          <div className="mt-4 grid gap-4 rounded-lg border border-gray-200 bg-gray-50 p-4 md:grid-cols-2">
            <div>
              <label className="block text-xs font-medium text-gray-600">SMTP host</label>
              <input
                type="text"
                value={smtpHost}
                onChange={(e) => setSmtpHost(e.target.value)}
                className="mt-1 w-full rounded border border-gray-300 px-2 py-1 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600">SMTP port (SSL)</label>
              <input
                type="number"
                value={smtpPort}
                onChange={(e) => setSmtpPort(Number(e.target.value))}
                className="mt-1 w-full rounded border border-gray-300 px-2 py-1 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600">IMAP host</label>
              <input
                type="text"
                value={imapHost}
                onChange={(e) => setImapHost(e.target.value)}
                className="mt-1 w-full rounded border border-gray-300 px-2 py-1 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600">IMAP port (SSL)</label>
              <input
                type="number"
                value={imapPort}
                onChange={(e) => setImapPort(Number(e.target.value))}
                className="mt-1 w-full rounded border border-gray-300 px-2 py-1 text-sm"
              />
            </div>
          </div>
        )}

        {error && (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800">
            {error}
          </div>
        )}
        {success && (
          <div className="mt-4 rounded-lg border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-800">
            {success}
          </div>
        )}

        <div className="mt-4 flex flex-wrap gap-2">
          <button
            onClick={handleSave}
            disabled={saveConfig.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
            <Mail className="h-4 w-4" />
            {saveConfig.isPending ? 'Salvataggio…' : 'Salva configurazione'}
          </button>
          <button
            onClick={handleTest}
            disabled={!config || testConfig.isPending}
            className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-60"
          >
            <RefreshCw className={`h-4 w-4 ${testConfig.isPending ? 'animate-spin' : ''}`} />
            Testa connessione
          </button>
        </div>
      </Card>

      <Card className="mt-4">
        <button
          onClick={() => setShowGuide(!showGuide)}
          className="flex w-full items-center justify-between text-left"
        >
          <div className="flex items-center gap-2">
            <HelpCircle className="h-5 w-5 text-blue-600" />
            <h3 className="text-lg font-semibold">Come firmare l'XML e inviare al SDI</h3>
          </div>
          <span className="text-sm text-gray-500">{showGuide ? 'Chiudi ▲' : 'Apri ▼'}</span>
        </button>

        {showGuide && (
          <div className="mt-4 space-y-4 text-sm text-gray-700">
            <div>
              <h4 className="mb-1 font-semibold">1. Scarica l'XML</h4>
              <p>
                Nella pagina dettaglio fattura clicca <b>Scarica XML</b>. Il file avrà il nome
                standard <code>IT{'{piva}'}_{'{numero}'}.xml</code>.
              </p>
            </div>

            <div>
              <h4 className="mb-1 font-semibold">2. Firma il file con firma digitale CAdES</h4>
              <p className="mb-2">Serve una firma digitale (Smart Card, ArubaKey, Firma Remota). 3 strumenti a scelta:</p>
              <ul className="ml-4 list-disc space-y-1">
                <li>
                  <b>Firma Remota in browser</b> (cross-platform, €30-40/anno):{' '}
                  <a
                    href="https://webtools.firma.aruba.it"
                    target="_blank"
                    rel="noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    webtools.firma.aruba.it
                  </a>
                  {' · '}
                  <a
                    href="https://www.firma.infocert.it"
                    target="_blank"
                    rel="noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    InfoCert GoSign
                  </a>
                </li>
                <li>
                  <b>Windows</b>: ArubaSign, DikeGoSign, FirmaCerta — doppio click sul file XML → PIN → salvi
                  .p7m nella stessa cartella
                </li>
                <li>
                  <b>Mac OSX</b>:{' '}
                  <a
                    href="https://www.firma.infocert.it/installazione/dike_gosign_mac.php"
                    target="_blank"
                    rel="noreferrer"
                    className="text-blue-600 hover:underline"
                  >
                    DikeGoSign per Mac
                  </a>
                  , ArubaSign Mac — app native firmate Apple
                </li>
              </ul>
              <p className="mt-2 text-xs text-gray-500">
                Il file firmato avrà nome <code>IT{'{piva}'}_{'{numero}'}.xml.p7m</code>
              </p>
            </div>

            <div>
              <h4 className="mb-1 font-semibold">3. Carica il .p7m e invia al SDI</h4>
              <p>
                Torna sulla fattura → clicca <b>Carica .p7m firmato</b> → poi <b>Invia a SDI via PEC</b>. Il
                sistema invia la PEC a{' '}
                <code>sdi01@pec.fatturapa.it</code> usando le credenziali qui sopra.
              </p>
            </div>

            <div>
              <h4 className="mb-1 font-semibold">4. Ricevute SDI</h4>
              <p>
                SDI risponde sulla tua PEC con email da <code>servizisdi@pec.fatturapa.it</code>. Nella pagina
                fatture puoi premere <b>Controlla ricevute</b> e il sistema legge le PEC in arrivo e aggiorna
                lo stato della fattura automaticamente (consegnata, scartata, mancata consegna).
              </p>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
