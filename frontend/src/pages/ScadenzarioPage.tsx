import { useState } from 'react'
import {
  useScadenzarioAttivo, useScadenzarioPassivo, useGenerateScadenze,
  useChiudiScadenza, useSegnaInsoluto, useCashFlow, useCashFlowPerBanca,
} from '../api/hooks'
import { formatCurrency } from '../lib/utils'
import PageHeader from '../components/ui/PageHeader'
import PageMeta from '../components/ui/PageMeta'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import EmptyState from '../components/ui/EmptyState'
import Badge from '../components/ui/Badge'
import { CalendarClock, RefreshCw, TrendingUp, Landmark, Search, X, Ban, CheckCircle } from 'lucide-react'

const STATO_COLORS: Record<string, 'success' | 'warning' | 'error' | 'info' | 'default'> = {
  aperto: 'default',
  pagato: 'success',
  incassato: 'success',
  parziale: 'warning',
  insoluto: 'error',
}

export default function ScadenzarioPage() {
  const [tab, setTab] = useState<'attivo' | 'passivo' | 'cashflow'>('attivo')
  const [statoFilter, setStatoFilter] = useState('')
  const [searchFilter, setSearchFilter] = useState('')
  const [cfGiorni, setCfGiorni] = useState(30)
  const [showChiudiId, setShowChiudiId] = useState<string | null>(null)
  const [chiudiImporto, setChiudiImporto] = useState('')
  const [chiudiData, setChiudiData] = useState(new Date().toISOString().split('T')[0])

  const attivo = useScadenzarioAttivo(statoFilter, searchFilter)
  const passivo = useScadenzarioPassivo(statoFilter, searchFilter)
  const generateScadenze = useGenerateScadenze()
  const chiudiScadenza = useChiudiScadenza()
  const segnaInsoluto = useSegnaInsoluto()
  const cashFlow = useCashFlow(cfGiorni)
  const cashFlowBanca = useCashFlowPerBanca(cfGiorni)

  const currentData = tab === 'attivo' ? attivo.data : passivo.data
  const isLoading = tab === 'attivo' ? attivo.isLoading : tab === 'passivo' ? passivo.isLoading : cashFlow.isLoading

  const handleChiudi = async (id: string) => {
    await chiudiScadenza.mutateAsync({
      id,
      importo_pagato: parseFloat(chiudiImporto),
      data_pagamento: chiudiData,
    })
    setShowChiudiId(null)
    setChiudiImporto('')
  }

  return (
    <div className="space-y-4">
      <PageMeta title="Scadenzario" />
      <PageHeader
        title="Scadenzario"
        subtitle="Gestione scadenze attive e passive"
        actions={
          <button
            onClick={() => generateScadenze.mutate()}
            disabled={generateScadenze.isPending}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${generateScadenze.isPending ? 'animate-spin' : ''}`} />
            Genera scadenze
          </button>
        }
      />

      {/* Tabs */}
      <div className="flex gap-1 rounded-xl bg-gray-100 p-1">
        {([
          { key: 'attivo' as const, label: 'Crediti', icon: TrendingUp },
          { key: 'passivo' as const, label: 'Debiti', icon: CalendarClock },
          { key: 'cashflow' as const, label: 'Cash Flow', icon: Landmark },
        ]).map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => { setTab(key); setStatoFilter(''); setSearchFilter('') }}
            className={`flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              tab === key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <Icon className="h-4 w-4" />
            <span className="hidden sm:inline">{label}</span>
          </button>
        ))}
      </div>

      {/* Cash Flow Tab */}
      {tab === 'cashflow' ? (
        <div className="space-y-4">
          <div className="flex gap-2">
            {[30, 60, 90].map((g) => (
              <button key={g} onClick={() => setCfGiorni(g)}
                className={`rounded-lg px-4 py-2 text-sm font-medium ${cfGiorni === g ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
              >{g}gg</button>
            ))}
          </div>

          {cashFlow.isLoading ? <LoadingSpinner /> : cashFlow.data && (
            <>
              <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
                <div className="rounded-xl border border-gray-200 bg-white p-4">
                  <p className="text-[10px] font-semibold text-gray-400 uppercase">Saldo banca</p>
                  <p className="mt-1 text-xl font-bold text-gray-900">{formatCurrency(cashFlow.data.saldo_banca_attuale)}</p>
                </div>
                <div className="rounded-xl border border-green-200 bg-green-50 p-4">
                  <p className="text-[10px] font-semibold text-green-500 uppercase">Incassi</p>
                  <p className="mt-1 text-xl font-bold text-green-700">+{formatCurrency(cashFlow.data.incassi_previsti)}</p>
                </div>
                <div className="rounded-xl border border-red-200 bg-red-50 p-4">
                  <p className="text-[10px] font-semibold text-red-500 uppercase">Pagamenti</p>
                  <p className="mt-1 text-xl font-bold text-red-700">-{formatCurrency(cashFlow.data.pagamenti_previsti)}</p>
                </div>
                <div className={`rounded-xl border p-4 ${cashFlow.data.saldo_previsto >= 0 ? 'border-blue-200 bg-blue-50' : 'border-red-300 bg-red-100'}`}>
                  <p className="text-[10px] font-semibold uppercase" style={{ color: cashFlow.data.saldo_previsto >= 0 ? '#3b82f6' : '#ef4444' }}>Previsto</p>
                  <p className="mt-1 text-xl font-bold" style={{ color: cashFlow.data.saldo_previsto >= 0 ? '#1d4ed8' : '#dc2626' }}>
                    {formatCurrency(cashFlow.data.saldo_previsto)}
                  </p>
                </div>
              </div>

              {cashFlow.data.alert && (
                <div className="rounded-xl border border-red-300 bg-red-50 p-4 text-sm text-red-700">{cashFlow.data.alert.messaggio}</div>
              )}

              {cashFlow.data.breakdown?.length > 0 && (
                <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">Settimana</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-green-500">Incassi</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-red-500">Pagamenti</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500">Saldo</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {cashFlow.data.breakdown.map((w: any, i: number) => (
                        <tr key={i}>
                          <td className="px-4 py-2 text-sm text-gray-600">{w.settimana}</td>
                          <td className="px-4 py-2 text-right text-sm text-green-600">+{formatCurrency(w.incassi)}</td>
                          <td className="px-4 py-2 text-right text-sm text-red-600">-{formatCurrency(w.pagamenti)}</td>
                          <td className={`px-4 py-2 text-right text-sm font-medium ${w.saldo_progressivo >= 0 ? 'text-gray-900' : 'text-red-600'}`}>
                            {formatCurrency(w.saldo_progressivo)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {cashFlowBanca.data?.length > 0 && (
                <div>
                  <h3 className="mb-2 text-sm font-semibold text-gray-400 uppercase">Per banca</h3>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {cashFlowBanca.data.map((b: any) => (
                      <div key={b.bank_id} className="rounded-xl border border-gray-200 bg-white p-4">
                        <p className="font-medium text-gray-900">{b.bank_name}</p>
                        <p className="text-xs text-gray-400 truncate">{b.iban}</p>
                        <div className="mt-2 flex justify-between text-sm">
                          <span className="text-gray-400">Previsto:</span>
                          <span className={`font-bold ${b.saldo_previsto >= 0 ? 'text-blue-600' : 'text-red-600'}`}>{formatCurrency(b.saldo_previsto)}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      ) : (
        /* Attivo / Passivo */
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <div className="relative flex-1 min-w-48">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input value={searchFilter} onChange={(e) => setSearchFilter(e.target.value)}
                placeholder="Cerca controparte..." className="w-full rounded-lg border border-gray-300 pl-10 pr-4 py-2 text-sm" />
            </div>
            <select value={statoFilter} onChange={(e) => setStatoFilter(e.target.value)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              <option value="">Tutti</option>
              <option value="aperto">Aperto</option>
              <option value="pagato">{tab === 'attivo' ? 'Incassato' : 'Pagato'}</option>
              <option value="parziale">Parziale</option>
              {tab === 'attivo' && <option value="insoluto">Insoluto</option>}
            </select>
          </div>

          {currentData?.totals && Object.keys(currentData.totals).length > 0 && (
            <div className="flex flex-wrap gap-2">
              {Object.entries(currentData.totals).map(([stato, totale]) => (
                <div key={stato} className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs">
                  <span className="text-gray-400 capitalize">{stato}:</span> <span className="font-semibold">{formatCurrency(totale as number)}</span>
                </div>
              ))}
            </div>
          )}

          {isLoading ? <LoadingSpinner /> : !currentData?.items?.length ? (
            <EmptyState icon={CalendarClock} title="Nessuna scadenza" description="Non ci sono scadenze." />
          ) : (
            <div className="space-y-2">
              {currentData.items.map((s: any) => (
                <div key={s.id} className={`rounded-xl border bg-white p-3 sm:p-4 ${
                  s.colore === 'red' ? 'border-red-300' : s.colore === 'yellow' ? 'border-amber-300' : 'border-gray-200'
                }`}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <p className="font-medium text-gray-900 text-sm truncate">{s.controparte}</p>
                        <Badge variant={STATO_COLORS[s.stato] || 'default'}>{s.stato}</Badge>
                        {s.anticipata && <Badge variant="info">Anticipata</Badge>}
                      </div>
                      <div className="mt-1 flex flex-wrap gap-x-3 text-[11px] text-gray-400">
                        <span>{s.data_scadenza}</span>
                        <span>{s.giorni_residui > 0 ? `${s.giorni_residui}gg` : s.giorni_residui < 0 ? `${Math.abs(s.giorni_residui)}gg fa` : 'oggi'}</span>
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-base font-bold text-gray-900">{formatCurrency(s.importo_lordo)}</p>
                      <p className="text-[10px] text-gray-400">netto {formatCurrency(s.importo_netto)}</p>
                    </div>
                  </div>

                  {s.stato === 'aperto' && (
                    <div className="mt-2 flex gap-2">
                      <button onClick={() => { setShowChiudiId(s.id); setChiudiImporto(String(s.importo_lordo)) }}
                        className="inline-flex items-center gap-1 rounded-lg bg-green-50 px-2.5 py-1 text-xs font-medium text-green-700 hover:bg-green-100">
                        <CheckCircle className="h-3 w-3" /> {tab === 'attivo' ? 'Incassa' : 'Paga'}
                      </button>
                      {tab === 'attivo' && s.giorni_residui < 0 && (
                        <button onClick={() => segnaInsoluto.mutate(s.id)}
                          className="inline-flex items-center gap-1 rounded-lg bg-red-50 px-2.5 py-1 text-xs font-medium text-red-700 hover:bg-red-100">
                          <Ban className="h-3 w-3" /> Insoluto
                        </button>
                      )}
                    </div>
                  )}

                  {showChiudiId === s.id && (
                    <div className="mt-2 flex flex-wrap items-end gap-2 rounded-lg bg-gray-50 p-2">
                      <div className="flex-1 min-w-28">
                        <label className="text-[10px] text-gray-400">Importo</label>
                        <input type="number" value={chiudiImporto} onChange={(e) => setChiudiImporto(e.target.value)}
                          className="mt-0.5 w-full rounded border border-gray-300 px-2 py-1 text-sm" step="0.01" />
                      </div>
                      <div className="flex-1 min-w-28">
                        <label className="text-[10px] text-gray-400">Data</label>
                        <input type="date" value={chiudiData} onChange={(e) => setChiudiData(e.target.value)}
                          className="mt-0.5 w-full rounded border border-gray-300 px-2 py-1 text-sm" />
                      </div>
                      <button onClick={() => handleChiudi(s.id)} disabled={chiudiScadenza.isPending}
                        className="rounded bg-green-600 px-3 py-1 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-50">OK</button>
                      <button onClick={() => setShowChiudiId(null)} className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-400 hover:bg-gray-100">
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
