import { useState } from 'react'
import {
  Plus,
  RefreshCw,
  Trash2,
  ExternalLink,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Ban,
  Info,
} from 'lucide-react'
import {
  useScaricoConfigs,
  useDelegaGuide,
  useRegisterClient,
  useDeleteScaricoConfig,
  useSyncScarico,
  useDownloadedInvoices,
  type ScaricoConfig,
} from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'

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

function ConfigCard({
  c,
  isBusy,
  onSync,
  onDelete,
}: {
  c: ScaricoConfig
  isBusy: boolean
  onSync: () => void
  onDelete: () => void
}) {
  const [showInvoices, setShowInvoices] = useState(false)
  const { data: invoicesData, isLoading: invoicesLoading } = useDownloadedInvoices(showInvoices ? c.id : null)
  const invoices = invoicesData?.items ?? []

  return (
    <Card>
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-lg font-semibold text-gray-900">{c.client_name}</h3>
            <StatusBadge status={c.status} />
            <span className="text-xs text-gray-500">{c.client_fiscal_id}</span>
          </div>
          <dl className="mt-2 grid grid-cols-1 gap-x-6 gap-y-1 text-sm text-gray-600 md:grid-cols-3">
            <div>
              <dt className="text-xs uppercase tracking-wide text-gray-400">Modalità</dt>
              <dd>{c.onboarding_mode}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-gray-400">Ultimo sync</dt>
              <dd>{c.last_sync_at ? new Date(c.last_sync_at).toLocaleString('it-IT') : '—'}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-gray-400">Fatture scaricate (anno)</dt>
              <dd>
                {c.invoices_downloaded_ytd} / 5.000 (tot: {c.invoices_downloaded_total})
              </dd>
            </div>
          </dl>
          {c.last_sync_error && (
            <p className="mt-2 rounded bg-yellow-50 px-2 py-1 text-xs text-yellow-800">{c.last_sync_error}</p>
          )}
          {c.last_sync_new_count !== null && c.last_sync_new_count !== undefined && (
            <p className="mt-2 text-xs text-green-700">
              Ultimo sync: {c.last_sync_new_count} nuove fatture
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={onSync}
            disabled={isBusy}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-60"
          >
            <RefreshCw className={`h-4 w-4 ${isBusy ? 'animate-spin' : ''}`} />
            {isBusy ? 'Sync…' : 'Sync ora'}
          </button>
          <button
            onClick={onDelete}
            disabled={isBusy}
            className="inline-flex items-center gap-1.5 rounded-lg border border-red-300 bg-white px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-60"
          >
            <Trash2 className="h-4 w-4" />
            Rimuovi
          </button>
        </div>
      </div>

      <div className="mt-4 border-t border-gray-100 pt-3">
        <button
          onClick={() => setShowInvoices(!showInvoices)}
          className="flex items-center gap-1 text-sm font-medium text-blue-600 hover:underline"
        >
          {showInvoices ? '▲ Nascondi fatture scaricate' : `▼ Mostra fatture scaricate (${c.invoices_downloaded_total})`}
        </button>

        {showInvoices && (
          <div className="mt-3">
            {invoicesLoading ? (
              <p className="text-sm text-gray-500">Caricamento…</p>
            ) : invoices.length === 0 ? (
              <p className="text-sm text-gray-500">
                Nessuna fattura scaricata. Click "Sync ora" per recuperarle da A-Cube.
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
                      <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">Codice SDI</th>
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
                        <td className="whitespace-nowrap px-3 py-2 text-xs text-gray-500">
                          {inv.codice_univoco_sdi.length > 30
                            ? inv.codice_univoco_sdi.slice(0, 30) + '…'
                            : inv.codice_univoco_sdi}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  )
}

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: typeof CheckCircle2 }> = {
  pending: { label: 'Delega pendente', color: 'bg-yellow-100 text-yellow-800', icon: Clock },
  active: { label: 'Attivo', color: 'bg-green-100 text-green-800', icon: CheckCircle2 },
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

export default function ScaricoMassivoPage() {
  const { data: configData, isLoading } = useScaricoConfigs()
  const { data: guide } = useDelegaGuide()
  const registerClient = useRegisterClient()
  const deleteConfig = useDeleteScaricoConfig()
  const syncConfig = useSyncScarico()

  const [showForm, setShowForm] = useState(false)
  const [fiscalId, setFiscalId] = useState('')
  const [clientName, setClientName] = useState('')
  const [formError, setFormError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [syncMessage, setSyncMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(
    null,
  )

  const configs = configData?.items ?? []

  const handleRegister = async () => {
    setFormError(null)
    if (!fiscalId || !clientName) {
      setFormError('Compila P.IVA/CF e denominazione')
      return
    }
    try {
      await registerClient.mutateAsync({
        client_fiscal_id: fiscalId.trim(),
        client_name: clientName.trim(),
        onboarding_mode: 'proxy',
      })
      setFiscalId('')
      setClientName('')
      setShowForm(false)
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setFormError(detail ?? 'Errore registrazione')
    }
  }

  const handleDelete = async (c: ScaricoConfig) => {
    if (!confirm(`Rimuovere la registrazione per ${c.client_name} (${c.client_fiscal_id})?`)) return
    setBusyId(c.id)
    try {
      await deleteConfig.mutateAsync(c.id)
    } finally {
      setBusyId(null)
    }
  }

  const handleSync = async (c: ScaricoConfig) => {
    setSyncMessage(null)
    setBusyId(c.id)
    try {
      const r = await syncConfig.mutateAsync(c.id)
      setSyncMessage({
        type: 'success',
        text: `Sync ${c.client_name}: ${(r as { new_invoices?: number }).new_invoices ?? 0} nuove fatture`,
      })
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setSyncMessage({ type: 'error', text: detail ?? 'Sync fallito' })
    } finally {
      setBusyId(null)
    }
  }

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  return (
    <div>
      <PageHeader
        title="Scarico Massivo Fatture"
        subtitle="Scarica automaticamente le fatture dal cassetto fiscale dei tuoi clienti via A-Cube"
        actions={
          <button
            onClick={() => setShowForm(!showForm)}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            <Plus className="h-4 w-4" />
            Registra cliente
          </button>
        }
      />

      <Card className="mb-4 border-green-200 bg-green-50/40">
        <div className="flex items-start gap-3">
          <CheckCircle2 className="h-5 w-5 shrink-0 text-green-600" />
          <div className="text-sm text-gray-700">
            <p className="font-medium">Integrazione A-Cube attiva</p>
            <p className="mt-1">
              Sandbox A-Cube collegato. Per ogni cliente: registra la P.IVA → fai delega sul portale AdE
              (codice fiscale delegato <code className="rounded bg-white px-1">10442360961</code>) → click
              "Sync ora" per scaricare le fatture dal cassetto fiscale.
            </p>
          </div>
        </div>
      </Card>

      {syncMessage && (
        <div
          className={`mb-4 rounded-lg border px-4 py-2 text-sm ${
            syncMessage.type === 'success'
              ? 'border-green-200 bg-green-50 text-green-800'
              : 'border-red-200 bg-red-50 text-red-800'
          }`}
        >
          {syncMessage.text}
        </div>
      )}

      {showForm && (
        <Card className="mb-4">
          <h3 className="mb-3 text-base font-semibold">Nuovo cliente da monitorare</h3>
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-gray-700">P.IVA / Codice Fiscale *</label>
              <input
                type="text"
                value={fiscalId}
                onChange={(e) => setFiscalId(e.target.value)}
                placeholder="12345678901"
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Denominazione *</label>
              <input
                type="text"
                value={clientName}
                onChange={(e) => setClientName(e.target.value)}
                placeholder="TAAL S.r.l."
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>
          {formError && <p className="mt-2 text-sm text-red-600">{formError}</p>}
          <div className="mt-3 flex gap-2">
            <button
              onClick={handleRegister}
              disabled={registerClient.isPending}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
            >
              {registerClient.isPending ? 'Salvataggio…' : 'Registra'}
            </button>
            <button
              onClick={() => {
                setShowForm(false)
                setFormError(null)
              }}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Annulla
            </button>
          </div>
        </Card>
      )}

      {configs.length === 0 ? (
        <EmptyState
          title="Nessun cliente registrato"
          description="Registra un cliente e segui la procedura di delega AdE per iniziare lo scarico massivo delle sue fatture."
          action={
            <button
              onClick={() => setShowForm(true)}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Registra il primo cliente
            </button>
          }
        />
      ) : (
        <div className="space-y-3">
          {configs.map((c) => (
            <ConfigCard
              key={c.id}
              c={c}
              isBusy={busyId === c.id}
              onSync={() => handleSync(c)}
              onDelete={() => handleDelete(c)}
            />
          ))}
        </div>
      )}

      {/* Delega guide */}
      {guide && (
        <Card className="mt-6">
          <h3 className="mb-3 text-lg font-semibold text-gray-900">Procedura delega AdE (proxy mode)</h3>
          <p className="mb-3 text-sm text-gray-600">
            Per ogni cliente devi far fare questa procedura sul portale AdE (una volta sola, dura fino al 31/12
            del 4° anno successivo). Dopo la delega, A-Cube può scaricare le fatture del cliente automaticamente.
          </p>
          <a
            href={guide.portale_ade_url}
            target="_blank"
            rel="noreferrer"
            className="mb-3 inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
          >
            <ExternalLink className="h-4 w-4" />
            Apri portale AdE
          </a>
          <div className="rounded-lg bg-gray-50 p-3">
            <p className="text-sm font-medium text-gray-900">
              Codice fiscale da delegare: <code className="rounded bg-white px-2 py-0.5">{guide.acube_fiscal_id}</code>
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
