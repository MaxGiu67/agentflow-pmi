import { useState } from 'react'
import { CheckCircle, Edit3 } from 'lucide-react'
import { usePendingReview, useVerifyInvoice } from '../../api/hooks'
import { formatCurrency, formatDate } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'

export default function VerificaPage() {
  const [page, setPage] = useState(1)
  const { data, isLoading } = usePendingReview(page, 20)
  const verifyMutation = useVerifyInvoice()
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editCategory, setEditCategory] = useState('')

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const invoices = data?.items ?? []
  const totalPages = data?.total_pages ?? 1

  const handleConfirm = (invoiceId: string) => {
    verifyMutation.mutate({ invoiceId, confirmed: true })
  }

  const handleCorrect = (invoiceId: string) => {
    if (!editCategory.trim()) return
    verifyMutation.mutate({ invoiceId, category: editCategory, confirmed: true })
    setEditingId(null)
    setEditCategory('')
  }

  return (
    <div>
      <PageHeader
        title="Verifica fatture"
        subtitle="Conferma o correggi la categorizzazione automatica"
      />

      {invoices.length === 0 ? (
        <EmptyState
          title="Nessuna fattura da verificare"
          description="Tutte le fatture sono state verificate"
          icon={<CheckCircle className="h-12 w-12 text-green-500" />}
        />
      ) : (
        <div className="space-y-4">
          {invoices.map((inv: Record<string, unknown>) => (
            <Card key={inv.id as string}>
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-gray-900">
                      {inv.emittente as string}
                    </span>
                    <span className="text-xs text-gray-500">
                      {formatDate(inv.date as string)}
                    </span>
                  </div>
                  <p className="mt-1 text-lg font-semibold text-gray-900">
                    {formatCurrency(inv.total_amount as number)}
                  </p>
                  <div className="mt-2 flex items-center gap-2">
                    <span className="text-sm text-gray-500">Categoria suggerita:</span>
                    <span className="rounded-md bg-blue-50 px-2 py-0.5 text-sm font-medium text-blue-700">
                      {inv.category as string || 'Non categorizzata'}
                    </span>
                    {inv.category_confidence != null && (
                      <span className="text-xs text-gray-400">
                        ({Math.round((inv.category_confidence as number) * 100)}% confidenza)
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {editingId === (inv.id as string) ? (
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={editCategory}
                        onChange={(e) => setEditCategory(e.target.value)}
                        placeholder="Nuova categoria"
                        className="w-48 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
                      />
                      <button
                        onClick={() => handleCorrect(inv.id as string)}
                        disabled={verifyMutation.isPending}
                        className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                      >
                        Salva
                      </button>
                      <button
                        onClick={() => { setEditingId(null); setEditCategory('') }}
                        className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
                      >
                        Annulla
                      </button>
                    </div>
                  ) : (
                    <>
                      <button
                        onClick={() => {
                          setEditingId(inv.id as string)
                          setEditCategory((inv.category as string) ?? '')
                        }}
                        className="inline-flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
                      >
                        <Edit3 className="h-4 w-4" />
                        Correggi
                      </button>
                      <button
                        onClick={() => handleConfirm(inv.id as string)}
                        disabled={verifyMutation.isPending}
                        className="inline-flex items-center gap-1 rounded-lg bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
                      >
                        <CheckCircle className="h-4 w-4" />
                        Conferma
                      </button>
                    </>
                  )}
                </div>
              </div>
            </Card>
          ))}

          {totalPages > 1 && (
            <div className="flex justify-center gap-2 py-4">
              <button
                onClick={() => setPage(page - 1)}
                disabled={page <= 1}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm disabled:opacity-50"
              >
                Precedente
              </button>
              <span className="flex items-center px-3 text-sm text-gray-600">
                Pagina {page} di {totalPages}
              </span>
              <button
                onClick={() => setPage(page + 1)}
                disabled={page >= totalPages}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm disabled:opacity-50"
              >
                Successiva
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
