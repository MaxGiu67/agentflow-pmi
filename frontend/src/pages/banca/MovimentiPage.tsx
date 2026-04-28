import { Fragment, useEffect, useMemo, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Sparkles,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Search,
  X as XIcon,
  Filter,
} from 'lucide-react'
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

// Subcategorie che meritano un badge più specifico (override del parent)
const SUBCATEGORY_LABELS: Record<string, { label: string; color: string }> = {
  compenso: { label: 'Compenso', color: 'bg-violet-100 text-violet-800' },
  stipendio: { label: 'Stipendio', color: 'bg-purple-100 text-purple-800' },
  tfr: { label: 'TFR', color: 'bg-fuchsia-100 text-fuchsia-800' },
  contributi: { label: 'INPS/INAIL', color: 'bg-pink-100 text-pink-800' },
  commissione_bonifico: { label: 'Comm. bonifico', color: 'bg-gray-100 text-gray-700' },
  commissione: { label: 'Commissione', color: 'bg-gray-100 text-gray-700' },
  canone: { label: 'Canone', color: 'bg-slate-100 text-slate-700' },
  polizza: { label: 'Polizza', color: 'bg-cyan-100 text-cyan-800' },
  imposta_bollo: { label: 'Bollo', color: 'bg-rose-100 text-rose-800' },
  rata_mutuo: { label: 'Rata mutuo', color: 'bg-amber-100 text-amber-800' },
  rata_prestito: { label: 'Rata prestito', color: 'bg-amber-100 text-amber-800' },
  leasing: { label: 'Leasing', color: 'bg-amber-100 text-amber-800' },
  giroconto: { label: 'Giroconto', color: 'bg-blue-100 text-blue-800' },
  bonifico: { label: 'Bonifico', color: 'bg-sky-100 text-sky-800' },
  f24: { label: 'F24', color: 'bg-red-100 text-red-800' },
  iva: { label: 'IVA', color: 'bg-red-100 text-red-800' },
}

function CategoryBadge({
  category,
  subcategory,
}: {
  category: string | null
  subcategory?: string | null
}) {
  // Subcategory ha priorità: distingue "compenso" da "stipendio" in payroll, ecc.
  if (subcategory && SUBCATEGORY_LABELS[subcategory]) {
    const cfg = SUBCATEGORY_LABELS[subcategory]
    return (
      <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${cfg.color}`}>
        {cfg.label}
      </span>
    )
  }
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

  // Filtri
  const [search, setSearch] = useState('')
  const [searchApplied, setSearchApplied] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [directionFilter, setDirectionFilter] = useState<'' | 'in' | 'out'>('')
  const [yearFilter, setYearFilter] = useState<number | ''>('')
  const [showFilters, setShowFilters] = useState(false)

  // Paginazione
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => {
      setSearchApplied(search.trim().toLowerCase())
      setPage(1)
    }, 300)
    return () => clearTimeout(t)
  }, [search])

  // Reset page on filter change
  useEffect(() => {
    setPage(1)
  }, [categoryFilter, directionFilter, yearFilter])

  // ⚠️ TUTTI gli hook DEVONO essere prima di qualsiasi early return (rules of hooks).
  const allTransactions: TxRow[] = useMemo(() => data?.items ?? [], [data])

  const yearsAvailable = useMemo(
    () =>
      Array.from(
        new Set(
          allTransactions.map((t) => (t.date as string)?.slice(0, 4)).filter(Boolean) as string[],
        ),
      )
        .sort()
        .reverse(),
    [allTransactions],
  )

  const transactions = useMemo(
    () =>
      allTransactions.filter((tx) => {
        if (categoryFilter && tx.parsed_category !== categoryFilter) return false
        if (directionFilter === 'in' && (tx.amount as number) < 0) return false
        if (directionFilter === 'out' && (tx.amount as number) >= 0) return false
        if (yearFilter && !(tx.date as string)?.startsWith(String(yearFilter))) return false
        if (searchApplied) {
          const haystack = [
            tx.parsed_counterparty,
            tx.counterpart,
            tx.description,
            tx.parsed_invoice_ref,
          ]
            .filter(Boolean)
            .map((s) => String(s).toLowerCase())
            .join(' ')
          if (!haystack.includes(searchApplied)) return false
        }
        return true
      }),
    [allTransactions, categoryFilter, directionFilter, yearFilter, searchApplied],
  )

  const totalFiltered = transactions.length
  const totalPages = Math.max(1, Math.ceil(totalFiltered / pageSize))
  const pageStart = (page - 1) * pageSize
  const pagedTx = transactions.slice(pageStart, pageStart + pageSize)
  const startRecord = totalFiltered === 0 ? 0 : pageStart + 1
  const endRecord = Math.min(pageStart + pageSize, totalFiltered)

  const totals = useMemo(
    () => ({
      in: transactions.filter((t) => (t.amount as number) > 0).reduce((s, t) => s + (t.amount as number), 0),
      out: transactions.filter((t) => (t.amount as number) < 0).reduce((s, t) => s + (t.amount as number), 0),
    }),
    [transactions],
  )

  const allCategories = useMemo(
    () => Array.from(new Set(allTransactions.map((t) => t.parsed_category as string).filter(Boolean))),
    [allTransactions],
  )

  // Hooks finished — early return safe now.
  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

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


  return (
    <div>
      <PageHeader
        title="Movimenti bancari"
        subtitle={`${totalFiltered} movimenti${totalFiltered !== allTransactions.length ? ` (di ${allTransactions.length})` : ''} — Entrate ${formatCurrency(totals.in)} · Uscite ${formatCurrency(totals.out)}`}
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

      {/* Filtri */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Cerca controparte, descrizione, fattura…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-lg border border-gray-300 py-2 pl-9 pr-9 text-sm focus:border-blue-500 focus:outline-none"
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
              aria-label="Cancella"
            >
              <XIcon className="h-4 w-4" />
            </button>
          )}
        </div>
        <button
          onClick={() => setDirectionFilter(directionFilter === 'in' ? '' : 'in')}
          className={`rounded-lg border px-3 py-2 text-sm font-medium ${
            directionFilter === 'in'
              ? 'border-green-500 bg-green-50 text-green-700'
              : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
          }`}
        >
          ↑ Entrate
        </button>
        <button
          onClick={() => setDirectionFilter(directionFilter === 'out' ? '' : 'out')}
          className={`rounded-lg border px-3 py-2 text-sm font-medium ${
            directionFilter === 'out'
              ? 'border-red-500 bg-red-50 text-red-700'
              : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
          }`}
        >
          ↓ Uscite
        </button>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          <Filter className="h-4 w-4" />
          Filtri
          {(categoryFilter || yearFilter) && (
            <span className="inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-blue-600 px-1.5 text-xs font-semibold text-white">
              {[categoryFilter, yearFilter].filter(Boolean).length}
            </span>
          )}
        </button>
      </div>

      {showFilters && (
        <div className="mb-4 flex flex-wrap items-end gap-4 rounded-lg border border-gray-200 bg-white p-4">
          <div>
            <label className="block text-xs font-medium text-gray-500">Categoria</label>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="mt-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="">Tutte</option>
              {allCategories.map((c) => (
                <option key={c} value={c}>
                  {CATEGORY_LABELS[c]?.label || c}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500">Anno</label>
            <select
              value={yearFilter}
              onChange={(e) =>
                setYearFilter(e.target.value === '' ? '' : Number(e.target.value))
              }
              className="mt-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="">Tutti</option>
              {yearsAvailable.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </div>
          {(categoryFilter || yearFilter || directionFilter || searchApplied) && (
            <button
              onClick={() => {
                setCategoryFilter('')
                setYearFilter('')
                setDirectionFilter('')
                setSearch('')
              }}
              className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
            >
              Pulisci tutti
            </button>
          )}
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
            {pagedTx.map((tx) => {
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
                      <CategoryBadge
                        category={(tx.parsed_category as string) ?? null}
                        subcategory={(tx.parsed_subcategory as string) ?? null}
                      />
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

      {totalFiltered === 0 && allTransactions.length === 0 && (
        <p className="mt-6 text-center text-sm text-gray-500">
          Nessun movimento. Vai su <a href="/banca/connessioni" className="text-blue-600 hover:underline">Open Banking</a> e clicca "Aggiorna".
        </p>
      )}

      {totalFiltered === 0 && allTransactions.length > 0 && (
        <p className="mt-6 text-center text-sm text-gray-500">
          Nessun movimento corrisponde ai filtri. Prova a pulire i filtri.
        </p>
      )}

      {/* Paginazione */}
      {totalFiltered > 0 && (
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <p className="text-sm text-gray-500">
              {startRecord}–{endRecord} di {totalFiltered}
            </p>
            <div className="flex items-center gap-1">
              <span className="text-xs text-gray-400">Righe:</span>
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value))
                  setPage(1)
                }}
                className="rounded border border-gray-300 px-2 py-1 text-xs focus:border-blue-500 focus:outline-none"
              >
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={200}>200</option>
              </select>
            </div>
          </div>
          {totalPages > 1 && (
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage(1)}
                disabled={page <= 1}
                className="rounded border border-gray-300 px-2 py-1 text-xs disabled:opacity-40"
              >
                ««
              </button>
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page <= 1}
                className="rounded border border-gray-300 px-3 py-1 text-xs disabled:opacity-40"
              >
                ‹ Prec.
              </button>
              <span className="px-3 text-sm font-medium text-gray-700">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage(Math.min(totalPages, page + 1))}
                disabled={page >= totalPages}
                className="rounded border border-gray-300 px-3 py-1 text-xs disabled:opacity-40"
              >
                Succ. ›
              </button>
              <button
                onClick={() => setPage(totalPages)}
                disabled={page >= totalPages}
                className="rounded border border-gray-300 px-2 py-1 text-xs disabled:opacity-40"
              >
                »»
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
