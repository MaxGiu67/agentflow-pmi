import { useState } from 'react'
import { Link2, RefreshCw, AlertTriangle, CheckCircle2, Clock, Ban } from 'lucide-react'
import {
  useBankConnections,
  useInitBankConnection,
  useSyncBankConnection,
  useReconnectBankConnection,
  type BankConnection,
} from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'

type StatusConfig = {
  label: string
  color: string
  icon: typeof CheckCircle2
}

const STATUS_CONFIG: Record<BankConnection['status'], StatusConfig> = {
  pending: { label: 'In attesa consenso', color: 'bg-yellow-100 text-yellow-800', icon: Clock },
  active: { label: 'Attivo', color: 'bg-green-100 text-green-800', icon: CheckCircle2 },
  expired: { label: 'Consenso scaduto', color: 'bg-red-100 text-red-800', icon: AlertTriangle },
  disabled: { label: 'Disabilitato', color: 'bg-gray-100 text-gray-700', icon: Ban },
}

const NOTICE_LABEL: Record<number, string> = {
  0: '20 giorni alla scadenza',
  1: '10 giorni alla scadenza',
  2: 'Scade oggi',
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleDateString('it-IT', { day: '2-digit', month: 'short', year: 'numeric' })
}

function StatusBadge({ conn }: { conn: BankConnection }) {
  const cfg = STATUS_CONFIG[conn.status]
  const Icon = cfg.icon
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${cfg.color}`}
    >
      <Icon className="h-3.5 w-3.5" />
      {cfg.label}
    </span>
  )
}

function NoticeBadge({ level }: { level: number | null }) {
  if (level === null) return null
  const color = level === 2 ? 'bg-red-100 text-red-800' : 'bg-orange-100 text-orange-800'
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${color}`}>
      <AlertTriangle className="h-3.5 w-3.5" />
      {NOTICE_LABEL[level] ?? `Notice ${level}`}
    </span>
  )
}

export default function BankConnectionsPage() {
  const { data, isLoading, error } = useBankConnections()
  const initConn = useInitBankConnection()
  const syncConn = useSyncBankConnection()
  const reconnect = useReconnectBankConnection()

  const [busyId, setBusyId] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [backfillFor, setBackfillFor] = useState<string | null>(null)

  const handleInit = async () => {
    setErr(null)
    setBusyId('init')
    // Pre-open a new tab synchronously inside the click handler so popup blockers
    // don't block it. We'll set its URL when the API responds.
    const newTab = window.open('about:blank', '_blank', 'noopener,noreferrer')
    try {
      const returnUrl = `${window.location.origin}/banca/connessioni?callback=1`
      const res = await initConn.mutateAsync({ return_url: returnUrl })
      if (res.connect_url) {
        if (newTab) {
          newTab.location.href = res.connect_url
        } else {
          // popup blocked → fallback: open in same tab
          window.location.href = res.connect_url
        }
      } else if (newTab) {
        newTab.close()
      }
    } catch (e: unknown) {
      if (newTab) newTab.close()
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setErr(detail ?? 'Impossibile avviare la connessione')
    } finally {
      setBusyId(null)
    }
  }

  const handleSync = async (id: string, since?: string, until?: string) => {
    setErr(null)
    setBusyId(id)
    try {
      const r = await syncConn.mutateAsync({ connectionId: id, since, until })
      const newTx = (r as { tx_created?: number }).tx_created ?? 0
      const message = since
        ? `Backfill completato: ${newTx} movimenti scaricati dal ${since}.`
        : `Aggiornamento ok: ${newTx} nuovi movimenti.`
      setErr(null)
      // Use err state as a feedback channel (success will be styled differently if needed)
      if (newTx === 0) setErr(message + ' (Nessuna nuova transazione)')
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setErr(detail ?? 'Sync fallito')
    } finally {
      setBusyId(null)
    }
  }

  const handleReconnect = async (id: string) => {
    setErr(null)
    setBusyId(id)
    const newTab = window.open('about:blank', '_blank', 'noopener,noreferrer')
    try {
      const res = await reconnect.mutateAsync(id)
      if (res.reconnect_url) {
        if (newTab) {
          newTab.location.href = res.reconnect_url
        } else {
          window.location.href = res.reconnect_url
        }
      } else if (newTab) {
        newTab.close()
      }
    } catch (e: unknown) {
      if (newTab) newTab.close()
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setErr(detail ?? 'Reconnect fallito')
    } finally {
      setBusyId(null)
    }
  }

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />
  if (error) {
    return (
      <div className="rounded-lg bg-red-50 p-4 text-red-900">
        Errore nel caricamento delle connessioni bancarie.
      </div>
    )
  }

  const connections = data?.items ?? []

  return (
    <div>
      <PageHeader
        title="Connessioni bancarie"
        subtitle="Open Banking PSD2 via A-Cube — consenso 90 giorni, rinnovo automatico"
        actions={
          <button
            onClick={handleInit}
            disabled={busyId === 'init'}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            <Link2 className="h-4 w-4" />
            {busyId === 'init' ? 'Avvio…' : 'Collega conto'}
          </button>
        }
      />

      {err && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800">
          {err}
        </div>
      )}

      {connections.length === 0 ? (
        <EmptyState
          icon={<Link2 className="h-12 w-12" />}
          title="Nessuna banca collegata"
          description="Collega il tuo conto bancario via PSD2 per abilitare sync automatico e riconciliazione fatture."
          action={
            <button
              onClick={handleInit}
              disabled={busyId === 'init'}
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Collega il primo conto
            </button>
          }
        />
      ) : (
        <div className="space-y-4">
          {connections.map((conn) => {
            const isBusy = busyId === conn.id
            const needsReconnect =
              conn.status === 'expired' || conn.notice_level !== null
            return (
              <Card key={conn.id}>
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-lg font-semibold text-gray-900">
                        {conn.business_name ?? conn.fiscal_id}
                      </h3>
                      <StatusBadge conn={conn} />
                      <NoticeBadge level={conn.notice_level} />
                      {conn.environment === 'sandbox' && (
                        <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-800">
                          Sandbox
                        </span>
                      )}
                    </div>
                    <dl className="mt-2 grid grid-cols-1 gap-x-6 gap-y-1 text-sm text-gray-600 md:grid-cols-3">
                      <div>
                        <dt className="text-xs uppercase tracking-wide text-gray-400">P.IVA</dt>
                        <dd>{conn.fiscal_id}</dd>
                      </div>
                      <div>
                        <dt className="text-xs uppercase tracking-wide text-gray-400">
                          Consenso scade
                        </dt>
                        <dd>{formatDate(conn.consent_expires_at)}</dd>
                      </div>
                      <div>
                        <dt className="text-xs uppercase tracking-wide text-gray-400">
                          Ultimo webhook
                        </dt>
                        <dd>{formatDate(conn.last_reconnect_webhook_at)}</dd>
                      </div>
                    </dl>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {conn.status === 'active' && (
                      <>
                        <button
                          onClick={() => handleSync(conn.id)}
                          disabled={isBusy}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-60"
                          title="Aggiorna delta dall'ultimo sync"
                        >
                          <RefreshCw className={`h-4 w-4 ${isBusy ? 'animate-spin' : ''}`} />
                          {isBusy ? 'Sync…' : 'Aggiorna'}
                        </button>
                        <button
                          onClick={() => setBackfillFor(conn.id)}
                          disabled={isBusy}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-blue-300 bg-blue-50 px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-60"
                          title="Scarica storico con range custom"
                        >
                          📥 Backfill storico
                        </button>
                      </>
                    )}
                    {needsReconnect && (
                      <button
                        onClick={() => handleReconnect(conn.id)}
                        disabled={isBusy}
                        className="inline-flex items-center gap-1.5 rounded-lg bg-orange-600 px-3 py-2 text-sm font-medium text-white hover:bg-orange-700 disabled:opacity-60"
                      >
                        <AlertTriangle className="h-4 w-4" />
                        {isBusy ? 'Attendi…' : 'Rinnova consenso'}
                      </button>
                    )}
                  </div>
                </div>
              </Card>
            )
          })}
        </div>
      )}

      {backfillFor && (
        <BackfillModal
          onClose={() => setBackfillFor(null)}
          onSubmit={async (since, until) => {
            await handleSync(backfillFor, since, until || undefined)
            setBackfillFor(null)
          }}
          isLoading={busyId === backfillFor}
        />
      )}
    </div>
  )
}

function BackfillModal({
  onClose,
  onSubmit,
  isLoading,
}: {
  onClose: () => void
  onSubmit: (since: string, until: string) => void | Promise<void>
  isLoading: boolean
}) {
  const today = new Date().toISOString().slice(0, 10)
  const oneYearAgo = (() => {
    const d = new Date()
    d.setFullYear(d.getFullYear() - 1)
    return d.toISOString().slice(0, 10)
  })()
  const [since, setSince] = useState<string>(oneYearAgo)
  const [until, setUntil] = useState<string>(today)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
        <h3 className="text-lg font-semibold text-gray-900">Scarica storico movimenti</h3>
        <p className="mt-1 text-sm text-gray-600">
          Seleziona il periodo da scaricare. Le banche italiane tipicamente espongono fino a
          12-24 mesi di storico (il limite dipende dalla banca). Default: ultimi 12 mesi.
        </p>

        <div className="mt-4 grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-700">Da (incluso)</label>
            <input
              type="date"
              value={since}
              onChange={(e) => setSince(e.target.value)}
              max={until}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700">A (incluso)</label>
            <input
              type="date"
              value={until}
              onChange={(e) => setUntil(e.target.value)}
              min={since}
              max={today}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          <button
            onClick={() => {
              const d = new Date()
              d.setMonth(d.getMonth() - 3)
              setSince(d.toISOString().slice(0, 10))
            }}
            className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-700 hover:bg-gray-50"
          >
            Ultimi 3 mesi
          </button>
          <button
            onClick={() => setSince(oneYearAgo)}
            className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-700 hover:bg-gray-50"
          >
            Ultimi 12 mesi
          </button>
          <button
            onClick={() => {
              const d = new Date()
              d.setFullYear(d.getFullYear() - 2)
              setSince(d.toISOString().slice(0, 10))
            }}
            className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-700 hover:bg-gray-50"
          >
            Ultimi 2 anni
          </button>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button
            onClick={onClose}
            disabled={isLoading}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            Annulla
          </button>
          <button
            onClick={() => onSubmit(since, until)}
            disabled={isLoading || !since}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {isLoading ? 'Scarico in corso…' : 'Scarica storico'}
          </button>
        </div>
      </div>
    </div>
  )
}
