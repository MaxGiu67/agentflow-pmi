import { useState } from 'react'
import {
  RefreshCw,
  ExternalLink,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Ban,
} from 'lucide-react'
import {
  useDelegaGuide,
  useMyScaricoConfig,
  useSyncMyScarico,
  useMyDownloadedInvoices,
} from '../../api/hooks'
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
  const { data: cfg, isLoading: cfgLoading, error: cfgError } = useMyScaricoConfig()
  const { data: guide } = useDelegaGuide()
  const { data: invoicesData } = useMyDownloadedInvoices()
  const sync = useSyncMyScarico()

  const [syncMessage, setSyncMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

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
          <button
            onClick={handleSync}
            disabled={sync.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            <RefreshCw className={`h-4 w-4 ${sync.isPending ? 'animate-spin' : ''}`} />
            {sync.isPending ? 'Sync in corso…' : 'Sync ora'}
          </button>
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

      {/* Delega guide — collapsed by default */}
      {guide && cfg.status === 'pending' && (
        <Card className="mt-6">
          <h3 className="mb-3 text-lg font-semibold text-gray-900">Come abilitare lo scarico</h3>
          <p className="mb-3 text-sm text-gray-600">
            Per consentire ad A-Cube di leggere il tuo cassetto fiscale, devi delegarlo sul portale AdE.
            La delega è gratuita, vale fino al 31/12 del 4° anno successivo, e può essere revocata in
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
              Codice fiscale da delegare:{' '}
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
