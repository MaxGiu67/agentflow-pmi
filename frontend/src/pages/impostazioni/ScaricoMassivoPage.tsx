import { useState } from 'react'
import {
  RefreshCw,
  ExternalLink,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Ban,
  Rocket,
  KeyRound,
  X,
} from 'lucide-react'
import {
  useDelegaGuide,
  useMyScaricoConfig,
  useSyncMyScarico,
  useMyDownloadedInvoices,
  useStartMyOnboarding,
  useSaveAppointeeCredentials,
} from '../../api/hooks'
import { useAuthStore } from '../../store/auth'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import LoadingSpinner from '../../components/ui/LoadingSpinner'

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: typeof CheckCircle2 }> = {
  pending: { label: 'Delega pendente', color: 'bg-yellow-100 text-yellow-800', icon: Clock },
  active: { label: 'Sync attivo', color: 'bg-green-100 text-green-800', icon: CheckCircle2 },
  expired: { label: 'Delega scaduta', color: 'bg-red-100 text-red-800', icon: AlertTriangle },
  error: { label: 'Errore sync', color: 'bg-red-100 text-red-800', icon: AlertTriangle },
  disabled: { label: 'Disabilitato', color: 'bg-gray-100 text-gray-700', icon: Ban },
}

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending
  const Icon = cfg.icon
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${cfg.color}`}>
      <Icon className="h-3.5 w-3.5" />
      {cfg.label}
    </span>
  )
}

function formatCurrency(n: number | null): string {
  if (n == null) return '—'
  return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(n)
}

function formatDate(s: string | null): string {
  if (!s) return '—'
  try {
    return new Date(s).toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' })
  } catch {
    return s
  }
}

export default function ScaricoMassivoPage() {
  const isSuperAdmin = useAuthStore((s) => s.user?.is_super_admin ?? false)
  const { data: cfg, isLoading: cfgLoading, error: cfgError } = useMyScaricoConfig()
  const [onboardingMode, setOnboardingMode] = useState<'appointee' | 'proxy_delega'>(
    'proxy_delega',
  )
  const { data: guide } = useDelegaGuide(onboardingMode)
  const { data: invoicesData } = useMyDownloadedInvoices()
  const sync = useSyncMyScarico()
  const startOnboarding = useStartMyOnboarding()
  const saveCredentials = useSaveAppointeeCredentials()

  const [syncMessage, setSyncMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [onboardingMessage, setOnboardingMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)
  const [credModalOpen, setCredModalOpen] = useState(false)
  const [credForm, setCredForm] = useState({ appointee_fiscal_id: '', password: '', pin: '' })
  const [credMessage, setCredMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const handleSaveCredentials = async (e: React.FormEvent) => {
    e.preventDefault()
    setCredMessage(null)
    try {
      const r = await saveCredentials.mutateAsync(credForm)
      setCredMessage({ type: 'success', text: r.message })
      setCredForm({ appointee_fiscal_id: '', password: '', pin: '' })
      setTimeout(() => setCredModalOpen(false), 1500)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setCredMessage({ type: 'error', text: detail ?? 'Errore salvataggio credenziali' })
    }
  }

  const handleStartOnboarding = async () => {
    setOnboardingMessage(null)
    try {
      const r = await startOnboarding.mutateAsync({
        backfillArchive: true,
        mode: onboardingMode,
      })
      setOnboardingMessage({
        type: 'success',
        text: r.message || 'Onboarding A-Cube avviato. Primo scarico massivo entro 72h.',
      })
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setOnboardingMessage({ type: 'error', text: detail ?? 'Onboarding fallito' })
    }
  }

  const handleSync = async () => {
    setSyncMessage(null)
    try {
      const r = await sync.mutateAsync()
      setSyncMessage({
        type: 'success',
        text: r.message || `Sync completato: ${r.new_invoices} nuove fatture su ${r.total_scanned}`,
      })
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setSyncMessage({ type: 'error', text: detail ?? 'Sync fallito' })
    }
  }

  if (cfgLoading) return <LoadingSpinner className="mt-20" size="lg" />

  if (cfgError) {
    const detail = (cfgError as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    return (
      <div>
        <PageHeader title="Sincronizzazione cassetto fiscale" subtitle="A-Cube — Scarico massivo automatico" />
        <Card className="border-yellow-200 bg-yellow-50">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 shrink-0 text-yellow-600" />
            <div>
              <p className="font-medium text-gray-900">Configurazione non disponibile</p>
              <p className="mt-1 text-sm text-gray-700">{detail ?? 'Verifica i dati anagrafici della tua azienda.'}</p>
              <a href="/profilo" className="mt-2 inline-block text-sm text-blue-600 hover:underline">
                Vai al profilo aziendale →
              </a>
            </div>
          </div>
        </Card>
      </div>
    )
  }

  if (!cfg) return null

  const invoices = invoicesData?.items ?? []

  return (
    <div>
      <PageHeader
        title="Sincronizzazione cassetto fiscale"
        subtitle="Scarica automaticamente le tue fatture dal cassetto fiscale via A-Cube"
        actions={
          <div className="flex flex-wrap gap-2">
            {isSuperAdmin && (
              <button
                onClick={() => setCredModalOpen(true)}
                className="inline-flex items-center gap-2 rounded-lg border border-purple-200 bg-purple-50 px-4 py-2 text-sm font-medium text-purple-700 hover:bg-purple-100"
                title="Super admin · Salva credenziali Fisconline dell'incaricato su A-Cube"
              >
                <KeyRound className="h-4 w-4" />
                Credenziali appointee
              </button>
            )}
            {!cfg.acube_config_id && (
              <button
                onClick={handleStartOnboarding}
                disabled={startOnboarding.isPending}
                className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-60"
                title="Da premere DOPO aver completato l'incarico sul portale AdE"
              >
                <Rocket className={`h-4 w-4 ${startOnboarding.isPending ? 'animate-pulse' : ''}`} />
                {startOnboarding.isPending ? 'Avvio in corso…' : 'Avvia onboarding A-Cube'}
              </button>
            )}
            <button
              onClick={handleSync}
              disabled={sync.isPending || !cfg.acube_config_id}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
            >
              <RefreshCw className={`h-4 w-4 ${sync.isPending ? 'animate-spin' : ''}`} />
              {sync.isPending ? 'Sync in corso…' : 'Sync ora'}
            </button>
          </div>
        }
      />

      {/* Status card — your company */}
      <Card className="mb-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-lg font-semibold text-gray-900">{cfg.client_name}</h3>
              <StatusBadge status={cfg.status} />
              <span className="text-xs text-gray-500">P.IVA {cfg.client_fiscal_id}</span>
            </div>
            <dl className="mt-3 grid grid-cols-1 gap-x-6 gap-y-1 text-sm text-gray-600 md:grid-cols-3">
              <div>
                <dt className="text-xs uppercase tracking-wide text-gray-400">Ambiente A-Cube</dt>
                <dd>{cfg.environment === 'production' ? 'Produzione' : 'Sandbox (test)'}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-gray-400">Ultimo sync</dt>
                <dd>{cfg.last_sync_at ? new Date(cfg.last_sync_at).toLocaleString('it-IT') : 'Mai'}</dd>
              </div>
              <div>
                <dt className="text-xs uppercase tracking-wide text-gray-400">Fatture sync (anno)</dt>
                <dd>
                  {cfg.invoices_downloaded_ytd} (totale: {cfg.invoices_downloaded_total})
                </dd>
              </div>
            </dl>
            {cfg.last_sync_error && (
              <p className="mt-2 rounded bg-yellow-50 px-2 py-1 text-xs text-yellow-800">{cfg.last_sync_error}</p>
            )}
            {cfg.last_sync_new_count !== null && cfg.last_sync_new_count !== undefined && (
              <p className="mt-2 text-xs text-green-700">
                Ultimo sync: {cfg.last_sync_new_count} nuove fatture
              </p>
            )}
          </div>
        </div>
      </Card>

      {onboardingMessage && (
        <div
          className={`mb-4 rounded-lg border px-4 py-3 text-sm ${
            onboardingMessage.type === 'success'
              ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
              : 'border-red-200 bg-red-50 text-red-800'
          }`}
        >
          {onboardingMessage.text}
        </div>
      )}

      {syncMessage && (
        <div
          className={`mb-4 rounded-lg border px-4 py-3 text-sm ${
            syncMessage.type === 'success'
              ? 'border-green-200 bg-green-50 text-green-800'
              : 'border-red-200 bg-red-50 text-red-800'
          }`}
        >
          {syncMessage.text}
        </div>
      )}

      {/* Downloaded invoices table */}
      <Card>
        <h3 className="mb-3 text-base font-semibold text-gray-900">
          Fatture scaricate ({invoices.length})
        </h3>
        {invoices.length === 0 ? (
          <p className="text-sm text-gray-500">
            Nessuna fattura ancora scaricata. Verifica che la delega A-Cube sul portale AdE sia attiva, poi
            premi "Sync ora".
          </p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Numero</th>
                  <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Data</th>
                  <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Tipo</th>
                  <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Direzione</th>
                  <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Controparte</th>
                  <th className="px-3 py-2 text-right text-xs font-medium uppercase text-gray-500">Importo</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {invoices.map((inv) => (
                  <tr key={inv.id}>
                    <td className="whitespace-nowrap px-3 py-2 font-medium text-gray-900">
                      {inv.numero_fattura ?? '—'}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2 text-gray-700">{formatDate(inv.data_fattura)}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-gray-700">{inv.tipo_documento ?? '—'}</td>
                    <td className="whitespace-nowrap px-3 py-2">
                      <span
                        className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                          inv.direction === 'active'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-orange-100 text-orange-800'
                        }`}
                      >
                        {inv.direction === 'active' ? '↑ Emessa' : '↓ Ricevuta'}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-gray-700">{inv.controparte_nome ?? '—'}</td>
                    <td className="whitespace-nowrap px-3 py-2 text-right font-medium text-gray-900">
                      {formatCurrency(inv.importo_totale)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {credModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <div className="mb-4 flex items-start justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Credenziali Fisconline incaricato</h3>
                <p className="mt-1 text-xs text-gray-500">
                  Salvate cifrate su A-Cube. Non vengono persistite in AgentFlow.
                </p>
              </div>
              <button
                onClick={() => setCredModalOpen(false)}
                className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                aria-label="Chiudi"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSaveCredentials} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700">Codice fiscale incaricato</label>
                <input
                  type="text"
                  required
                  value={credForm.appointee_fiscal_id}
                  onChange={(e) =>
                    setCredForm({ ...credForm, appointee_fiscal_id: e.target.value.toUpperCase() })
                  }
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono uppercase focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  placeholder="GRLMSM67T11H501Z"
                  maxLength={16}
                  autoComplete="off"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700">PIN (10 cifre)</label>
                <input
                  type="password"
                  required
                  inputMode="numeric"
                  pattern="[0-9]{10}"
                  value={credForm.pin}
                  onChange={(e) => setCredForm({ ...credForm, pin: e.target.value.replace(/\D/g, '') })}
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  maxLength={10}
                  autoComplete="off"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700">Password Fisconline</label>
                <input
                  type="password"
                  required
                  value={credForm.password}
                  onChange={(e) => setCredForm({ ...credForm, password: e.target.value })}
                  className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  minLength={8}
                  maxLength={64}
                  autoComplete="new-password"
                />
              </div>

              {credMessage && (
                <div
                  className={`rounded border px-3 py-2 text-sm ${
                    credMessage.type === 'success'
                      ? 'border-green-200 bg-green-50 text-green-800'
                      : 'border-red-200 bg-red-50 text-red-800'
                  }`}
                >
                  {credMessage.text}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setCredModalOpen(false)}
                  className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Annulla
                </button>
                <button
                  type="submit"
                  disabled={saveCredentials.isPending}
                  className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
                >
                  {saveCredentials.isPending ? 'Salvataggio…' : 'Salva su A-Cube'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Mode selector + delega guide — visible when not yet active */}
      {guide && cfg.status === 'pending' && (
        <Card className="mt-6">
          <h3 className="mb-3 text-lg font-semibold text-gray-900">Come abilitare lo scarico</h3>

          <div className="mb-4 rounded-lg border border-gray-200 bg-gray-50 p-3">
            <p className="mb-2 text-sm font-medium text-gray-900">
              Scegli la modalità in base al tuo ruolo nella società:
            </p>
            <div className="space-y-2">
              <label className="flex cursor-pointer items-start gap-2 rounded p-2 hover:bg-white">
                <input
                  type="radio"
                  name="onboarding_mode"
                  value="proxy_delega"
                  checked={onboardingMode === 'proxy_delega'}
                  onChange={() => setOnboardingMode('proxy_delega')}
                  className="mt-1"
                />
                <div className="text-sm">
                  <div className="font-medium text-gray-900">
                    Sono Amministratore / Gestore della società (consigliato)
                  </div>
                  <div className="text-xs text-gray-600">
                    Delega Unificata ad A-Cube SRL — usato per amministratori unici e gestori AdE
                  </div>
                </div>
              </label>
              <label className="flex cursor-pointer items-start gap-2 rounded p-2 hover:bg-white">
                <input
                  type="radio"
                  name="onboarding_mode"
                  value="appointee"
                  checked={onboardingMode === 'appointee'}
                  onChange={() => setOnboardingMode('appointee')}
                  className="mt-1"
                />
                <div className="text-sm">
                  <div className="font-medium text-gray-900">
                    Sono Operatore Incaricato esterno
                  </div>
                  <div className="text-xs text-gray-600">
                    Incarico al CF persona fisica registrato come Incaricato sul cassetto
                  </div>
                </div>
              </label>
            </div>
          </div>

          <p className="mb-3 text-sm text-gray-600">
            Per consentire ad A-Cube di leggere il tuo cassetto fiscale, devi
            {onboardingMode === 'proxy_delega' ? ' delegarlo' : ' incaricarlo'} sul portale AdE.
            È gratuito, vale fino al 31/12 del 4° anno successivo, e può essere revocato in
            qualsiasi momento.
          </p>
          <a
            href={guide.portale_ade_url}
            target="_blank"
            rel="noreferrer"
            className="mb-3 inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
          >
            <ExternalLink className="h-4 w-4" />
            Apri portale Agenzia Entrate
          </a>
          <div className="rounded-lg bg-gray-50 p-3">
            <p className="text-sm font-medium text-gray-900">
              {onboardingMode === 'proxy_delega'
                ? 'Codice fiscale del delegato (A-Cube SRL):'
                : 'Codice fiscale da incaricare:'}{' '}
              <code className="rounded bg-white px-2 py-0.5">{guide.acube_fiscal_id}</code>
            </p>
          </div>

          <ol className="mt-4 space-y-2">
            {guide.steps.map((s, i) => (
              <li key={i} className="flex gap-3 text-sm text-gray-700">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100 text-xs font-semibold text-blue-700">
                  {i + 1}
                </span>
                <span>{s}</span>
              </li>
            ))}
          </ol>

          <div className="mt-4 rounded-lg border border-gray-200 p-3">
            <p className="mb-2 text-sm font-medium text-gray-900">Servizi da spuntare:</p>
            <ul className="space-y-1 text-sm text-gray-700">
              {guide.services_to_delegate.map((s) => (
                <li key={s} className="flex items-start gap-2">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-600" />
                  {s}
                </li>
              ))}
            </ul>
          </div>
        </Card>
      )}
    </div>
  )
}
