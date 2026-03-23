import { CheckCircle, Link as LinkIcon } from 'lucide-react'
import { usePendingReconciliation, useMatchTransaction } from '../../api/hooks'
import { formatCurrency, formatDate } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'

export default function RiconciliazionePage() {
  const { data, isLoading } = usePendingReconciliation()
  const matchMutation = useMatchTransaction()

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const pendingItems = data?.items ?? []

  const handleMatch = (txId: string, invoiceId: string) => {
    matchMutation.mutate({ txId, invoice_id: invoiceId })
  }

  return (
    <div>
      <PageHeader
        title="Riconciliazione"
        subtitle="Abbinamento movimenti bancari con fatture"
      />

      {pendingItems.length === 0 ? (
        <EmptyState
          title="Tutto riconciliato!"
          description="Non ci sono movimenti in attesa di riconciliazione."
          icon={<CheckCircle className="h-12 w-12 text-green-500" />}
        />
      ) : (
        <div className="space-y-4">
          {pendingItems.map((item: Record<string, unknown>) => (
            <Card key={item.transaction_id as string}>
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
                {/* Transaction info */}
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <LinkIcon className="h-4 w-4 text-gray-400" />
                    <span className="text-sm font-medium text-gray-900">
                      Movimento: {formatDate(item.transaction_date as string)}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-gray-600">{item.transaction_description as string}</p>
                  <p className="mt-1 text-lg font-semibold text-gray-900">
                    {formatCurrency(item.transaction_amount as number)}
                  </p>
                </div>

                {/* Suggestions */}
                <div className="flex-1">
                  <p className="mb-2 text-xs font-medium uppercase text-gray-500">Suggerimenti</p>
                  {(item.suggestions as Record<string, unknown>[] | undefined)?.length ? (
                    <div className="space-y-2">
                      {(item.suggestions as Record<string, unknown>[]).map((sug, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between rounded-lg border border-gray-200 p-3"
                        >
                          <div>
                            <p className="text-sm font-medium text-gray-900">{sug.emittente as string}</p>
                            <p className="text-xs text-gray-500">
                              {formatCurrency(sug.amount as number)} - Confidenza: {Math.round((sug.confidence as number) * 100)}%
                            </p>
                          </div>
                          <button
                            onClick={() =>
                              handleMatch(item.transaction_id as string, sug.invoice_id as string)
                            }
                            disabled={matchMutation.isPending}
                            className="rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50"
                          >
                            Abbina
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">Nessun suggerimento disponibile</p>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
