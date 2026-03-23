import { useState } from 'react'
import { Plus, CheckCircle, XCircle } from 'lucide-react'
import { useExpenses, useCreateExpense, useApproveExpense, useRejectExpense } from '../../api/hooks'
import { formatCurrency, formatDate } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import DataTable, { type Column } from '../../components/ui/DataTable'
import StatusBadge from '../../components/ui/StatusBadge'
import LoadingSpinner from '../../components/ui/LoadingSpinner'

type ExpenseRow = Record<string, unknown>

export default function SpesePage() {
  const { data, isLoading } = useExpenses()
  const createExpense = useCreateExpense()
  const approveExpense = useApproveExpense()
  const rejectExpense = useRejectExpense()
  const [showCreate, setShowCreate] = useState(false)
  const [description, setDescription] = useState('')
  const [amount, setAmount] = useState('')
  const [category, setCategory] = useState('')
  const [expenseDate, setExpenseDate] = useState(new Date().toISOString().slice(0, 10))
  const [rejectId, setRejectId] = useState<string | null>(null)
  const [rejectReason, setRejectReason] = useState('')

  const handleCreate = () => {
    createExpense.mutate({
      description,
      amount: parseFloat(amount),
      category,
      expense_date: expenseDate,
      currency: 'EUR',
    })
    setShowCreate(false)
    setDescription('')
    setAmount('')
    setCategory('')
  }

  const handleReject = (expenseId: string) => {
    if (!rejectReason.trim()) return
    rejectExpense.mutate({ expenseId, reason: rejectReason })
    setRejectId(null)
    setRejectReason('')
  }

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const expenses = data?.items ?? []

  const columns: Column<ExpenseRow>[] = [
    {
      key: 'expense_date',
      header: 'Data',
      sortable: true,
      render: (row) => formatDate(row.expense_date as string),
    },
    { key: 'description', header: 'Descrizione' },
    { key: 'category', header: 'Categoria' },
    {
      key: 'amount',
      header: 'Importo',
      render: (row) => formatCurrency(row.amount as number),
      className: 'text-right',
    },
    {
      key: 'currency',
      header: 'Valuta',
      render: (row) => (row.currency as string) ?? 'EUR',
    },
    {
      key: 'status',
      header: 'Stato',
      render: (row) => <StatusBadge status={row.status as string} />,
    },
    {
      key: 'actions',
      header: '',
      render: (row) => {
        if (row.status === 'pending') {
          return (
            <div className="flex gap-1">
              <button
                onClick={(e) => { e.stopPropagation(); approveExpense.mutate(row.id as string) }}
                className="rounded p-1 text-green-600 hover:bg-green-50"
                title="Approva"
              >
                <CheckCircle className="h-4 w-4" />
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); setRejectId(row.id as string) }}
                className="rounded p-1 text-red-600 hover:bg-red-50"
                title="Rifiuta"
              >
                <XCircle className="h-4 w-4" />
              </button>
            </div>
          )
        }
        return null
      },
    },
  ]

  return (
    <div>
      <PageHeader
        title="Note Spese"
        subtitle="Gestione spese e rimborsi"
        actions={
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            Nuova spesa
          </button>
        }
      />

      {showCreate && (
        <Card className="mb-6">
          <h3 className="mb-4 text-lg font-semibold">Nuova nota spese</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-medium text-gray-500">Descrizione</label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500">Importo</label>
              <input
                type="number"
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500">Categoria</label>
              <input
                type="text"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
                placeholder="Viaggio, Pranzo, Materiale..."
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500">Data</label>
              <input
                type="date"
                value={expenseDate}
                onChange={(e) => setExpenseDate(e.target.value)}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <button
              onClick={handleCreate}
              disabled={!description || !amount || createExpense.isPending}
              className="rounded-lg bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {createExpense.isPending ? 'Salvataggio...' : 'Salva'}
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="rounded-lg border border-gray-300 px-4 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
            >
              Annulla
            </button>
          </div>
        </Card>
      )}

      {/* Reject modal */}
      {rejectId && (
        <Card className="mb-6">
          <h3 className="mb-3 text-lg font-semibold text-red-600">Rifiuta spesa</h3>
          <div className="mb-3">
            <label className="block text-xs font-medium text-gray-500">Motivazione</label>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              rows={3}
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => handleReject(rejectId)}
              disabled={!rejectReason.trim()}
              className="rounded-lg bg-red-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
            >
              Rifiuta
            </button>
            <button
              onClick={() => { setRejectId(null); setRejectReason('') }}
              className="rounded-lg border border-gray-300 px-4 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
            >
              Annulla
            </button>
          </div>
        </Card>
      )}

      <DataTable<ExpenseRow>
        columns={columns}
        data={expenses}
        rowKey={(row) => row.id as string}
        emptyMessage="Nessuna nota spese"
      />
    </div>
  )
}
