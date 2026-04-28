import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Landmark, Plus, RefreshCw, CreditCard } from 'lucide-react'
import {
  useBankAccounts,
  useConnectBank,
  useSyncBankConnection,
} from '../../api/hooks'
import api from '../../api/client'
import { formatCurrency } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import StatusBadge from '../../components/ui/StatusBadge'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'

export default function BankAccountsPage() {
  const navigate = useNavigate()
  const { data, isLoading, refetch } = useBankAccounts()
  const connectBank = useConnectBank()
  const syncConn = useSyncBankConnection()
  const [showConnect, setShowConnect] = useState(false)
  const [iban, setIban] = useState('')
  const [bankName, setBankName] = useState('')
  const [connectError, setConnectError] = useState('')
  const [syncingId, setSyncingId] = useState<string | null>(null)
  const [syncMsg, setSyncMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const handleSync = async (account: { id: string; acube_connection_id: string | null }) => {
    if (!account.acube_connection_id) {
      setSyncMsg({ type: 'error', text: 'Conto non collegato via Open Banking — impossibile aggiornare.' })
      return
    }
    setSyncingId(account.id)
    setSyncMsg(null)
    try {
      const r = await syncConn.mutateAsync({ connectionId: account.acube_connection_id })
      const newTx = r?.transactions?.new_transactions ?? r?.new_transactions ?? 0
      setSyncMsg({
        type: 'success',
        text: newTx > 0 ? `Aggiornato: ${newTx} nuovi movimenti.` : 'Nessun nuovo movimento.',
      })
      // Trigger AI parsing in background — non blocca l'utente
      api
        .post(`/banking/connections/${account.acube_connection_id}/parse`, {})
        .catch(() => {})
      refetch()
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setSyncMsg({ type: 'error', text: detail ?? 'Sync fallito. Riprova o riconnetti il conto.' })
    } finally {
      setSyncingId(null)
    }
  }

  const handleConnect = async () => {
    setConnectError('')
    try {
      await connectBank.mutateAsync({ iban, bank_name: bankName })
      setShowConnect(false)
      setIban('')
      setBankName('')
    } catch (err: unknown) {
      setConnectError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          'Errore nella connessione'
      )
    }
  }

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const accounts = data?.items ?? []

  return (
    <div>
      <PageHeader
        title="Banca"
        subtitle="Conti correnti collegati e operazioni"
        actions={
          <div className="flex gap-2">
            <button
              onClick={() => navigate('/banca/cashflow')}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cash Flow
            </button>
            <button
              onClick={() => navigate('/banca/riconciliazione')}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Riconciliazione
            </button>
            <button
              onClick={() => setShowConnect(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" />
              Collega conto
            </button>
          </div>
        }
      />

      {syncMsg && (
        <div
          className={`mb-4 rounded-lg border px-4 py-3 text-sm ${
            syncMsg.type === 'success'
              ? 'border-green-200 bg-green-50 text-green-800'
              : 'border-red-200 bg-red-50 text-red-800'
          }`}
        >
          {syncMsg.text}
        </div>
      )}

      {showConnect && (
        <Card className="mb-6">
          <h3 className="mb-4 text-lg font-semibold">Collega conto bancario</h3>
          {connectError && (
            <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{connectError}</div>
          )}
          <div className="flex flex-wrap gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500">IBAN</label>
              <input
                type="text"
                value={iban}
                onChange={(e) => setIban(e.target.value)}
                className="mt-1 w-64 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
                placeholder="IT60X0542811101000000123456"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500">Nome banca</label>
              <input
                type="text"
                value={bankName}
                onChange={(e) => setBankName(e.target.value)}
                className="mt-1 w-48 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
                placeholder="Intesa Sanpaolo"
              />
            </div>
            <div className="flex items-end gap-2">
              <button
                onClick={handleConnect}
                disabled={!iban || !bankName || connectBank.isPending}
                className="rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {connectBank.isPending ? 'Collegamento...' : 'Collega'}
              </button>
              <button
                onClick={() => setShowConnect(false)}
                className="rounded-lg border border-gray-300 px-4 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
              >
                Annulla
              </button>
            </div>
          </div>
        </Card>
      )}

      {accounts.length === 0 ? (
        <EmptyState
          title="Nessun conto collegato"
          description="Collega il tuo conto bancario per sincronizzare i movimenti."
          icon={<Landmark className="h-12 w-12" />}
          action={
            <button
              onClick={() => setShowConnect(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" />
              Collega conto
            </button>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {accounts.map((account: Record<string, unknown>) => (
            <Card
              key={account.id as string}
              className="cursor-pointer transition-shadow hover:shadow-md"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50">
                    <CreditCard className="h-5 w-5 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-gray-900">{account.bank_name as string}</p>
                    <p className="font-mono text-xs text-gray-500">{account.iban as string}</p>
                  </div>
                </div>
                <StatusBadge status={account.status as string} />
              </div>
              {account.balance != null && (
                <div className="mt-4 border-t border-gray-100 pt-3">
                  <p className="text-xs text-gray-500">Saldo</p>
                  <p className="text-xl font-bold text-gray-900">
                    {formatCurrency(account.balance as number)}
                  </p>
                </div>
              )}
              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => navigate(`/banca/movimenti/${account.id}`)}
                  className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
                >
                  Movimenti
                </button>
                <button
                  onClick={() => handleSync(account)}
                  disabled={syncingId === account.id || !account.acube_connection_id}
                  title={
                    account.acube_connection_id
                      ? "Aggiorna i movimenti via Open Banking"
                      : "Conto non collegato via Open Banking"
                  }
                  className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                >
                  <RefreshCw
                    className={`h-3 w-3 ${syncingId === account.id ? 'animate-spin' : ''}`}
                  />
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
