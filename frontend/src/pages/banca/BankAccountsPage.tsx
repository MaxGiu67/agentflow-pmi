import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Landmark, Plus, RefreshCw, CreditCard } from 'lucide-react'
import { useBankAccounts, useConnectBank } from '../../api/hooks'
import { formatCurrency } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import StatusBadge from '../../components/ui/StatusBadge'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'

export default function BankAccountsPage() {
  const navigate = useNavigate()
  const { data, isLoading } = useBankAccounts()
  const connectBank = useConnectBank()
  const [showConnect, setShowConnect] = useState(false)
  const [iban, setIban] = useState('')
  const [bankName, setBankName] = useState('')
  const [connectError, setConnectError] = useState('')

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
                <button className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50">
                  <RefreshCw className="h-3 w-3" />
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
