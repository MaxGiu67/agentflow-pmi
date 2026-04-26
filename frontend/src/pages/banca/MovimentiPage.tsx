import { Fragment, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Sparkles, RefreshCw, ChevronDown, ChevronRight } from 'lucide-react'
import { useBankTransactions } from '../../api/hooks'
import api from '../../api/client'
import { formatCurrency, formatDate } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'

type TxRow = Record<string, unknown>

const CATEGORY_LABELS: Record<string, { label: string; color: string }> = {
  income_invoice: { label: 'Entrata fattura', color: 'bg-green-100 text-green-800' },
  expense_invoice: { label: 'Uscita fattura', color: 'bg-orange-100 text-orange-800' },
  payroll: { label: 'Stipendio', color: 'bg-purple-100 text-purple-800' },
  tax_f24: { label: 'F24', color: 'bg-red-100 text-red-800' },
  tax_iva: { label: 'IVA', color: 'bg-red-100 text-red-800' },
  fee: { label: 'Commissione', color: 'bg-gray-100 text-gray-800' },
  transfer: { label: 'Giroconto', color: 'bg-blue-100 text-blue-800' },
  loan_payment: { label: 'Rata prestito', color: 'bg-amber-100 text-amber-800' },
  interest: { label: 'Interessi', color: 'bg-indigo-100 text-indigo-800' },
  atm: { label: 'ATM', color: 'bg-gray-100 text-gray-800' },
  pos: { label: 'POS', color: 'bg-gray-100 text-gray-800' },
  sepa_dd: { label: 'SDD', color: 'bg-gray-100 text-gray-800' },
  refund: { label: 'Rimborso', color: 'bg-teal-100 text-teal-800' },
  other: { label: 'Altro', color: 'bg-gray-100 text-gray-600' },
}

function CategoryBadge({ category }: { category: string | null }) {
  const cfg = (category && CATEGORY_LABELS[category]) || CATEGORY_LABELS.other
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${cfg.color}`}>
      {cfg.label}
    </span>
  )
}

function ConfidenceBadge({ confidence, method }: { confidence: number | null; method: string | null }) {
  if (confidence == null) return null
  const pct = Math.round(confidence * 100)
  const color =
    pct >= 80
      ? 'bg-green-50 text-green-700 border-green-200'
      : pct >= 50
        ? 'bg-yellow-50 text-yellow-700 border-yellow-200'
        : 'bg-red-50 text-red-700 border-red-200'
  return (
    <span
      className={`inline-flex rounded border px-1.5 py-0.5 text-[10px] font-medium ${color}`}
      title={`Metodo: ${method ?? 'rules'}`}
    >
      {pct}% {method === 'llm' ? '✨' : method === 'manual' ? '✓' : ''}
    </span>
  )
}

export default function MovimentiPage() {
  const { accountId } = useParams<{ accountId: string }>()
  const navigate = useNavigate()
  const { data, isLoading, refetch } = useBankTransactions(accountId ?? '')
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [parsing, setParsing] = useState(false)
  const [parseMsg, setParseMsg] = useState<string | null>(null)

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const transactions: TxRow[] = data?.items ?? []

  const toggle = (id: string) => {
    setExpanded((s) => {
      const next = new Set(s)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleParseAll = async () => {
    setParsing(true)
    setParseMsg(null)
    try {
      // Find connection_id from first tx → account → connection
      // Simplification: we trigger parse via the bank-account's connection
      // by calling the parse endpoint with the connection id from the first tx
      const connId = (transactions[0] as { acube_connection_id?: string })?.acube_connection_id
      if (!connId) {
        // Fallback: chiama via account -> serve fetch separato
        const accRes = await api.get(`/bank-accounts/${accountId}`)
        const acc = accRes.data as { acube_connection_id?: string }
        if (!acc.acube_connection_id) {
          setParseMsg('Connection ID non trovato — sync prima')
          return
        }
        const r = await api.post(
          `/banking/connections/${acc.acube_connection_id}/parse?use_llm=true&force=true`,
        )
        setParseMsg((r.data as { message: string }).message)
      } else {
        const r = await api.post(
          `/banking/connections/${connId}/parse?use_llm=true&force=true`,
        )
        setParseMsg((r.data as { message: string }).message)
      }
      await refetch()
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setParseMsg(detail ?? 'Re-parse fallito')
    } finally {
      setParsing(false)
    }
  }

  const totals = {
    in: transactions.filter((t) => (t.amount as number) > 0).reduce((s, t) => s + (t.amount as number), 0),
    out: transactions.filter((t) => (t.amount as number) < 0).reduce((s, t) => s + (t.amount as number), 0),
  }

  return (
    <div>
      <PageHeader
        title="Movimenti bancari"
        subtitle={`${transactions.length} movimenti — Entrate ${formatCurrency(totals.in)} · Uscite ${formatCurrency(totals.out)}`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={handleParseAll}
              disabled={parsing}
              className="inline-flex items-center gap-1.5 rounded-lg border border-purple-300 bg-purple-50 px-3 py-2 text-sm font-medium text-purple-700 hover:bg-purple-100 disabled:opacity-60"
              title="Re-classifica con AI (usa LLM per low-confidence)"
            >
              <Sparkles className={`h-4 w-4 ${parsing ? 'animate-pulse' : ''}`} />
              {parsing ? 'AI in corso…' : 'Classifica con AI'}
            </button>
            <button
              onClick={() => refetch()}
              className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              <RefreshCw className="h-4 w-4" />
              Ricarica
            </button>
            <button
              onClick={() => navigate('/banca')}
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              <ArrowLeft className="h-4 w-4" />
              Indietro
            </button>
          </div>
        }
      />

      {parseMsg && (
        <div className="mb-4 rounded-lg border border-purple-200 bg-purple-50 px-4 py-2 text-sm text-purple-800">
          ✨ {parseMsg}
        </div>
      )}

      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="w-8 px-2 py-3"></th>
              <th className="px-3 py-3 text-left text-xs font-medium uppercase text-gray-500">Data</th>
              <th className="px-3 py-3 text-left text-xs font-medium uppercase text-gray-500">Controparte</th>
              <th className="px-3 py-3 text-left text-xs font-medium uppercase text-gray-500">Categoria</th>
              <th className="px-3 py-3 text-left text-xs font-medium uppercase text-gray-500">Rif. Fattura</th>
              <th className="px-3 py-3 text-right text-xs font-medium uppercase text-gray-500">Importo</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {transactions.map((tx) => {
              const id = tx.id as string
              const isExpanded = expanded.has(id)
              const amount = tx.amount as number
              const counterparty = (tx.parsed_counterparty as string) || (tx.counterpart as string) || '—'
              return (
                <Fragment key={id}>
                  <tr className="hover:bg-gray-50">
                    <td className="px-2 py-3">
                      <button
                        onClick={() => toggle(id)}
                        className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                      >
                        {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                      </button>
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 text-sm text-gray-700">
                      {formatDate(tx.date as string)}
                    </td>
                    <td className="px-3 py-3 text-sm">
                      <div className="font-medium text-gray-900">{counterparty}</div>
                      {tx.parsed_confidence != null && (
                        <ConfidenceBadge
                          confidence={tx.parsed_confidence as number}
                          method={tx.parsed_method as string}
                        />
                      )}
                    </td>
                    <td className="px-3 py-3 text-sm">
                      <CategoryBadge category={(tx.parsed_category as string) ?? null} />
                      {tx.parsed_subcategory ? (
                        <div className="mt-0.5 text-[10px] text-gray-500">
                          {String(tx.parsed_subcategory)}
                        </div>
                      ) : null}
                    </td>
                    <td className="px-3 py-3 text-sm text-gray-700">
                      {(tx.parsed_invoice_ref as string) || '—'}
                    </td>
                    <td
                      className={`whitespace-nowrap px-3 py-3 text-right text-sm font-semibold ${
                        amount >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}
                    >
                      {amount >= 0 ? '+' : ''}
                      {formatCurrency(amount)}
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr className="bg-gray-50">
                      <td colSpan={6} className="px-6 py-3">
                        <div className="text-xs text-gray-700">
                          <p className="mb-1 font-semibold text-gray-500">Descrizione originale (banca):</p>
                          <p className="whitespace-pre-wrap font-mono text-[11px] text-gray-700">
                            {(tx.description as string) || '—'}
                          </p>
                          {(tx.parsed_counterparty_iban as string) && (
                            <p className="mt-2">
                              <span className="font-semibold text-gray-500">IBAN controparte:</span>{' '}
                              <code>{tx.parsed_counterparty_iban as string}</code>
                            </p>
                          )}
                          {(tx.parsed_notes as string) && (
                            <p className="mt-2">
                              <span className="font-semibold text-gray-500">Note AI:</span>{' '}
                              {tx.parsed_notes as string}
                            </p>
                          )}
                          {(tx.enriched_cro as string) && (
                            <p className="mt-1 text-gray-500">CRO: {tx.enriched_cro as string}</p>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>

      {transactions.length === 0 && (
        <p className="mt-6 text-center text-sm text-gray-500">
          Nessun movimento. Vai su <a href="/banca/connessioni" className="text-blue-600 hover:underline">Open Banking</a> e clicca "Aggiorna".
        </p>
      )}
    </div>
  )
}
