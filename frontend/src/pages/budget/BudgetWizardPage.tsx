import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Building2,
  Users,
  TrendingUp,
  FileSpreadsheet,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  Plus,
  Trash2,
  Pencil,
} from 'lucide-react'
import { cn } from '../../lib/utils'
import api from '../../api/client'
import PageHeader from '../../components/ui/PageHeader'

// ── Types ──

interface Sector {
  id: string
  label: string
  ebitda_range: string
}

interface CostLine {
  category: string
  label: string
  amount: number
  monthly: number
  pct_on_revenue: number
  benchmark_min: number
  benchmark_max: number
  severity: string
}

interface CEPreview {
  year: number
  sector_id: string
  sector_label: string
  ricavi: number
  ricavi_totali: number
  extra_revenues: Array<{ label: string; amount: number }>
  cost_lines: CostLine[]
  total_costi: number
  ebitda: number
  ebitda_pct: number
  ebitda_benchmark: string
  ebitda_verdict: string
  ebitda_advice: string
  ires: number
  irap: number
  imposte: number
  utile_netto: number
  n_dipendenti: number
  ral_media: number
  costo_personale_diretto: number | null
  budget_lines: Array<{ category: string; label: string; annual_proposed: number; monthly_proposed: number }>
}

interface SectorQuestions {
  sector_id: string
  label: string
  questions: Array<{ id: string; text: string; type: string }>
  cost_structure: Record<string, { label: string; pct_min: number; pct_max: number; default: number }>
}

interface CustomLine {
  label: string
  amount: string
}

// ── Helpers ──

function fmtCur(value: number): string {
  return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(value)
}

function fmtPct(value: number): string {
  return `${value.toFixed(1)}%`
}

function recalculate(preview: CEPreview): CEPreview {
  const ricaviTotali = preview.ricavi + preview.extra_revenues.reduce((s, r) => s + r.amount, 0)
  const totalCosti = preview.cost_lines.reduce((s, c) => s + c.amount, 0)
  const ebitda = ricaviTotali - totalCosti
  const ebitdaPct = ricaviTotali > 0 ? (ebitda / ricaviTotali) * 100 : 0
  const personale = preview.cost_lines.find((c) => c.category === 'personale')?.amount ?? 0
  const irapBase = ricaviTotali - totalCosti + personale
  const irap = Math.max(0, irapBase) * 0.039
  const ires = Math.max(0, ebitda) * 0.24

  // Rebuild budget_lines
  const budgetLines: CEPreview['budget_lines'] = [
    { category: 'ricavi', label: 'Ricavi', annual_proposed: preview.ricavi, monthly_proposed: Math.round(preview.ricavi / 12) },
  ]
  preview.extra_revenues.forEach((er, i) => {
    if (er.amount > 0) budgetLines.push({ category: `ricavi_extra_${i}`, label: er.label, annual_proposed: er.amount, monthly_proposed: Math.round(er.amount / 12) })
  })
  preview.cost_lines.forEach((cl) => {
    budgetLines.push({ category: cl.category, label: cl.label, annual_proposed: cl.amount, monthly_proposed: Math.round(cl.amount / 12) })
  })

  return {
    ...preview,
    ricavi_totali: ricaviTotali,
    total_costi: Math.round(totalCosti * 100) / 100,
    ebitda: Math.round(ebitda * 100) / 100,
    ebitda_pct: Math.round(ebitdaPct * 10) / 10,
    ires: Math.round(ires * 100) / 100,
    irap: Math.round(irap * 100) / 100,
    imposte: Math.round((ires + irap) * 100) / 100,
    utile_netto: Math.round((ebitda - ires - irap) * 100) / 100,
    cost_lines: preview.cost_lines.map((cl) => ({
      ...cl,
      monthly: Math.round(cl.amount / 12),
      pct_on_revenue: ricaviTotali > 0 ? Math.round((cl.amount / ricaviTotali) * 1000) / 10 : 0,
    })),
    budget_lines: budgetLines,
  }
}

// ── Editable Cell ──

function EditableCell({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')

  if (editing) {
    return (
      <input
        type="number"
        autoFocus
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={() => { onChange(Number(draft) || 0); setEditing(false) }}
        onKeyDown={(e) => { if (e.key === 'Enter') { onChange(Number(draft) || 0); setEditing(false) } }}
        className="w-24 rounded border border-blue-400 px-1 py-0.5 text-right text-sm focus:outline-none"
      />
    )
  }
  return (
    <button
      onClick={() => { setDraft(String(Math.round(value))); setEditing(true) }}
      className="group inline-flex items-center gap-1 rounded px-1 py-0.5 hover:bg-blue-50"
      title="Clicca per modificare"
    >
      <span>{fmtCur(value)}</span>
      <Pencil className="h-3 w-3 text-slate-300 group-hover:text-blue-500" />
    </button>
  )
}

// ── Step Components ──

const STEPS = [
  { label: 'Settore', icon: Building2 },
  { label: 'Dati base', icon: Users },
  { label: 'Dettagli', icon: FileSpreadsheet },
  { label: 'Risultato', icon: TrendingUp },
]

// Step 0: Sector
function StepSector({ sectors, selected, onSelect }: { sectors: Sector[]; selected: string; onSelect: (id: string) => void }) {
  return (
    <div>
      <h2 className="mb-2 text-xl font-bold text-slate-800">In che settore opera la tua azienda?</h2>
      <p className="mb-6 text-sm text-slate-500">Seleziona il settore per benchmark e domande personalizzate.</p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {sectors.map((s) => (
          <button
            key={s.id}
            onClick={() => onSelect(s.id)}
            className={cn(
              'flex items-center gap-3 rounded-xl border-2 px-4 py-4 text-left transition-all',
              selected === s.id ? 'border-blue-500 bg-blue-50 shadow-md' : 'border-slate-200 bg-white hover:border-blue-300',
            )}
          >
            <div className={cn('flex h-10 w-10 shrink-0 items-center justify-center rounded-lg', selected === s.id ? 'bg-blue-500 text-white' : 'bg-slate-100 text-slate-500')}>
              <Building2 className="h-5 w-5" />
            </div>
            <div>
              <p className="font-semibold text-slate-800">{s.label}</p>
              <p className="text-xs text-slate-500">EBITDA tipico: {s.ebitda_range}</p>
            </div>
            {selected === s.id && <Check className="ml-auto h-5 w-5 text-blue-500" />}
          </button>
        ))}
      </div>
    </div>
  )
}

// Step 1: Base data with personnel toggle
function StepBaseData({
  fatturato, dipendenti, ral, year, personnelMode, costoPersonale,
  onFatturato, onDipendenti, onRal, onYear, onPersonnelMode, onCostoPersonale,
  historyData,
}: {
  fatturato: string; dipendenti: string; ral: string; year: number
  personnelMode: 'calc' | 'direct'; costoPersonale: string
  onFatturato: (v: string) => void; onDipendenti: (v: string) => void
  onRal: (v: string) => void; onYear: (v: number) => void
  onPersonnelMode: (v: 'calc' | 'direct') => void; onCostoPersonale: (v: string) => void
  historyData: { has_history: boolean; fatturato_prev: number; prev_year: number } | null
}) {
  return (
    <div>
      <h2 className="mb-2 text-xl font-bold text-slate-800">Dati di base</h2>
      <p className="mb-6 text-sm text-slate-500">Se non sai un numero con precisione, una stima va benissimo.</p>

      {historyData?.has_history && (
        <div className="mb-6 rounded-lg border border-blue-200 bg-blue-50 p-4">
          <p className="text-sm text-blue-800">
            <Sparkles className="mr-1 inline h-4 w-4" />
            Dati del {historyData.prev_year}: fatturato <strong>{fmtCur(historyData.fatturato_prev)}</strong>.
          </p>
          <button
            onClick={() => onFatturato(String(Math.round(historyData.fatturato_prev * 1.05)))}
            className="mt-2 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
          >
            Usa fatturato {historyData.prev_year} +5%
          </button>
        </div>
      )}

      <div className="space-y-5">
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Anno budget</label>
          <select value={year} onChange={(e) => onYear(Number(e.target.value))} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500">
            {[2025, 2026, 2027].map((y) => <option key={y} value={y}>{y}</option>)}
          </select>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Fatturato previsto (annuale)</label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-slate-400">EUR</span>
            <input type="number" value={fatturato} onChange={(e) => onFatturato(e.target.value)} placeholder="500000" className="w-full rounded-lg border border-slate-300 py-2.5 pl-12 pr-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" />
          </div>
        </div>

        {/* Personnel toggle */}
        <div>
          <label className="mb-2 block text-sm font-medium text-slate-700">Costo del personale</label>
          <div className="mb-3 flex gap-2">
            <button
              onClick={() => onPersonnelMode('calc')}
              className={cn('rounded-lg border px-3 py-1.5 text-xs font-medium transition-all', personnelMode === 'calc' ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-slate-200 text-slate-600 hover:bg-slate-50')}
            >
              Calcola da dipendenti e RAL
            </button>
            <button
              onClick={() => onPersonnelMode('direct')}
              className={cn('rounded-lg border px-3 py-1.5 text-xs font-medium transition-all', personnelMode === 'direct' ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-slate-200 text-slate-600 hover:bg-slate-50')}
            >
              Inserisci costo totale
            </button>
          </div>

          {personnelMode === 'calc' ? (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="mb-1 block text-xs text-slate-500">Numero dipendenti</label>
                <input type="number" value={dipendenti} onChange={(e) => onDipendenti(e.target.value)} placeholder="5" min={0} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" />
              </div>
              <div>
                <label className="mb-1 block text-xs text-slate-500">RAL media (lordo annuo)</label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-slate-400">EUR</span>
                  <input type="number" value={ral} onChange={(e) => onRal(e.target.value)} placeholder="35000" className="w-full rounded-lg border border-slate-300 py-2.5 pl-12 pr-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" />
                </div>
              </div>
              {dipendenti && ral && Number(dipendenti) > 0 && Number(ral) > 0 && (
                <p className="col-span-2 text-xs text-slate-500">
                  Costo azienda stimato: <strong>{fmtCur(Number(ral) * 1.3691 * Number(dipendenti))}</strong> (RAL + INPS 30% + INAIL 1% + TFR 6.91%)
                </p>
              )}
            </div>
          ) : (
            <div>
              <label className="mb-1 block text-xs text-slate-500">Costo personale annuo totale</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-slate-400">EUR</span>
                <input type="number" value={costoPersonale} onChange={(e) => onCostoPersonale(e.target.value)} placeholder="250000" className="w-full rounded-lg border border-slate-300 py-2.5 pl-12 pr-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Step 2: Details with custom lines
function StepDetails({
  questions, answers, onAnswer,
  costStructure, fatturato, overrides, onOverride,
  customCosts, onCustomCosts,
  extraRevenues, onExtraRevenues,
}: {
  questions: SectorQuestions | null
  answers: Record<string, string>; onAnswer: (id: string, value: string) => void
  costStructure: Record<string, { label: string; default: number }> | null
  fatturato: number; overrides: Record<string, string>; onOverride: (id: string, value: string) => void
  customCosts: CustomLine[]; onCustomCosts: (v: CustomLine[]) => void
  extraRevenues: CustomLine[]; onExtraRevenues: (v: CustomLine[]) => void
}) {
  if (!questions) return <p className="text-slate-500">Caricamento domande...</p>

  return (
    <div>
      <h2 className="mb-2 text-xl font-bold text-slate-800">Dettagli {questions.label}</h2>
      <p className="mb-6 text-sm text-slate-500">Se non sai un numero, lascia vuoto e usiamo il benchmark di settore.</p>

      {/* Sector questions */}
      <div className="mb-6 space-y-4">
        {questions.questions.map((q) => (
          <div key={q.id}>
            <label className="mb-1 block text-sm font-medium text-slate-700">{q.text}</label>
            <input
              type={q.type === 'number' ? 'number' : 'text'}
              value={answers[q.id] ?? ''}
              onChange={(e) => onAnswer(q.id, e.target.value)}
              placeholder={q.type === 'currency' ? 'EUR...' : q.type === 'percentage' ? '%...' : '...'}
              className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        ))}
      </div>

      {/* Cost overrides */}
      {costStructure && fatturato > 0 && (
        <div className="mb-6">
          <h3 className="mb-3 text-sm font-semibold text-slate-700">Costi da settore (aggiusta se conosci il valore)</h3>
          <div className="space-y-2">
            {Object.entries(costStructure).filter(([k]) => k !== 'personale').map(([catId, cat]) => (
              <div key={catId} className="flex items-center gap-3">
                <span className="w-48 shrink-0 text-sm text-slate-600">{cat.label}</span>
                <div className="relative flex-1">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-slate-400">EUR</span>
                  <input type="number" value={overrides[catId] ?? ''} onChange={(e) => onOverride(catId, e.target.value)} placeholder={String(Math.round(fatturato * cat.default))} className="w-full rounded-lg border border-slate-200 py-2 pl-12 pr-3 text-sm focus:border-blue-500 focus:outline-none" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Custom costs (+/-) */}
      <div className="mb-6">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-700">Costi aggiuntivi</h3>
          <button onClick={() => onCustomCosts([...customCosts, { label: '', amount: '' }])} className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50">
            <Plus className="h-3.5 w-3.5" /> Aggiungi voce
          </button>
        </div>
        <p className="mb-3 text-xs text-slate-400">Es: Interessi bancari, Consulenze legali, Assicurazioni</p>
        {customCosts.map((cc, i) => (
          <div key={i} className="mb-2 flex items-center gap-2">
            <input type="text" value={cc.label} onChange={(e) => { const arr = [...customCosts]; arr[i] = { ...arr[i], label: e.target.value }; onCustomCosts(arr) }} placeholder="Nome voce..." className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
            <div className="relative w-36">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-slate-400">EUR</span>
              <input type="number" value={cc.amount} onChange={(e) => { const arr = [...customCosts]; arr[i] = { ...arr[i], amount: e.target.value }; onCustomCosts(arr) }} placeholder="0" className="w-full rounded-lg border border-slate-200 py-2 pl-12 pr-3 text-sm focus:border-blue-500 focus:outline-none" />
            </div>
            <button onClick={() => onCustomCosts(customCosts.filter((_, j) => j !== i))} className="rounded p-1 text-slate-400 hover:bg-red-50 hover:text-red-500">
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>

      {/* Extra revenues (+/-) */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-700">Ricavi extra</h3>
          <button onClick={() => onExtraRevenues([...extraRevenues, { label: '', amount: '' }])} className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50">
            <Plus className="h-3.5 w-3.5" /> Aggiungi ricavo
          </button>
        </div>
        <p className="mb-3 text-xs text-slate-400">Es: Nuovi progetti, Contributi, Affitti attivi</p>
        {extraRevenues.map((er, i) => (
          <div key={i} className="mb-2 flex items-center gap-2">
            <input type="text" value={er.label} onChange={(e) => { const arr = [...extraRevenues]; arr[i] = { ...arr[i], label: e.target.value }; onExtraRevenues(arr) }} placeholder="Nome ricavo..." className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
            <div className="relative w-36">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-slate-400">EUR</span>
              <input type="number" value={er.amount} onChange={(e) => { const arr = [...extraRevenues]; arr[i] = { ...arr[i], amount: e.target.value }; onExtraRevenues(arr) }} placeholder="0" className="w-full rounded-lg border border-slate-200 py-2 pl-12 pr-3 text-sm focus:border-blue-500 focus:outline-none" />
            </div>
            <button onClick={() => onExtraRevenues(extraRevenues.filter((_, j) => j !== i))} className="rounded p-1 text-slate-400 hover:bg-red-50 hover:text-red-500">
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

// Step 3: Editable CE Preview + Save
function StepResult({
  preview, isLoading, onUpdatePreview, onSave, isSaving,
}: {
  preview: CEPreview | null; isLoading: boolean
  onUpdatePreview: (p: CEPreview) => void; onSave: () => void; isSaving: boolean
}) {
  if (isLoading) {
    return (
      <div className="flex flex-col items-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
        <p className="mt-4 text-sm text-slate-500">Generazione CE previsionale...</p>
      </div>
    )
  }
  if (!preview) return <p className="text-slate-500">Nessuna preview disponibile.</p>

  const verdictColor = preview.ebitda_verdict === 'above' ? 'text-green-600' : preview.ebitda_verdict === 'below' ? 'text-red-600' : 'text-blue-600'

  function updateCostLine(index: number, newAmount: number) {
    const updated = { ...preview! }
    updated.cost_lines = [...updated.cost_lines]
    updated.cost_lines[index] = { ...updated.cost_lines[index], amount: newAmount }
    onUpdatePreview(recalculate(updated))
  }

  function updateRicavi(newAmount: number) {
    onUpdatePreview(recalculate({ ...preview!, ricavi: newAmount }))
  }

  function updateExtraRevenue(index: number, newAmount: number) {
    const updated = { ...preview! }
    updated.extra_revenues = [...updated.extra_revenues]
    updated.extra_revenues[index] = { ...updated.extra_revenues[index], amount: newAmount }
    onUpdatePreview(recalculate(updated))
  }

  return (
    <div>
      <h2 className="mb-2 text-xl font-bold text-slate-800">Conto Economico Previsionale {preview.year}</h2>
      <p className="mb-1 text-sm text-slate-500">{preview.sector_label}</p>
      <p className="mb-6 text-xs text-slate-400">Clicca su qualsiasi importo per modificarlo. I totali si ricalcolano automaticamente.</p>

      {/* KPI summary */}
      <div className="mb-6 grid grid-cols-3 gap-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4 text-center shadow-sm">
          <p className="text-xs font-medium uppercase text-slate-500">Ricavi totali</p>
          <p className="mt-1 text-xl font-bold text-slate-800">{fmtCur(preview.ricavi_totali)}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 text-center shadow-sm">
          <p className="text-xs font-medium uppercase text-slate-500">Costi</p>
          <p className="mt-1 text-xl font-bold text-slate-800">{fmtCur(preview.total_costi)}</p>
        </div>
        <div className={cn('rounded-xl border-2 p-4 text-center shadow-sm', preview.ebitda >= 0 ? 'border-green-300 bg-green-50' : 'border-red-300 bg-red-50')}>
          <p className="text-xs font-medium uppercase text-slate-500">EBITDA</p>
          <p className={cn('mt-1 text-xl font-bold', preview.ebitda >= 0 ? 'text-green-700' : 'text-red-700')}>{fmtCur(preview.ebitda)}</p>
          <p className={cn('text-xs font-medium', verdictColor)}>{fmtPct(preview.ebitda_pct)} (bench: {preview.ebitda_benchmark})</p>
        </div>
      </div>

      {/* Advice */}
      <div className={cn('mb-6 rounded-lg border p-4', preview.ebitda_verdict === 'above' ? 'border-green-200 bg-green-50' : preview.ebitda_verdict === 'below' ? 'border-red-200 bg-red-50' : 'border-blue-200 bg-blue-50')}>
        <p className={cn('text-sm', verdictColor)}>
          {preview.ebitda_verdict === 'above' && <CheckCircle2 className="mr-1 inline h-4 w-4" />}
          {preview.ebitda_verdict === 'below' && <AlertTriangle className="mr-1 inline h-4 w-4" />}
          {preview.ebitda_verdict === 'ok' && <Sparkles className="mr-1 inline h-4 w-4" />}
          {preview.ebitda_advice}
        </p>
      </div>

      {/* Editable table */}
      <div className="mb-6 overflow-hidden rounded-xl border border-slate-200">
        <table className="w-full text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-2.5 text-left font-medium text-slate-600">Voce</th>
              <th className="px-4 py-2.5 text-right font-medium text-slate-600">Annuale</th>
              <th className="px-4 py-2.5 text-right font-medium text-slate-600">Mensile</th>
              <th className="px-4 py-2.5 text-right font-medium text-slate-600">% Ricavi</th>
              <th className="px-4 py-2.5 text-right font-medium text-slate-600">Benchmark</th>
            </tr>
          </thead>
          <tbody>
            {/* Ricavi row */}
            <tr className="border-t border-slate-100 bg-green-50/50">
              <td className="px-4 py-2 font-semibold text-green-700">Ricavi</td>
              <td className="px-4 py-2 text-right font-semibold text-green-700"><EditableCell value={preview.ricavi} onChange={updateRicavi} /></td>
              <td className="px-4 py-2 text-right text-green-600">{fmtCur(preview.ricavi / 12)}</td>
              <td className="px-4 py-2 text-right text-green-600">-</td>
              <td className="px-4 py-2 text-right text-slate-400">-</td>
            </tr>
            {/* Extra revenue rows */}
            {preview.extra_revenues.map((er, i) => (
              <tr key={`er-${i}`} className="border-t border-slate-100 bg-green-50/30">
                <td className="px-4 py-2 text-green-600">{er.label}</td>
                <td className="px-4 py-2 text-right text-green-600"><EditableCell value={er.amount} onChange={(v) => updateExtraRevenue(i, v)} /></td>
                <td className="px-4 py-2 text-right text-green-500">{fmtCur(er.amount / 12)}</td>
                <td className="px-4 py-2 text-right text-slate-400">extra</td>
                <td className="px-4 py-2 text-right text-slate-400">-</td>
              </tr>
            ))}
            {/* Cost rows */}
            {preview.cost_lines.map((cl, i) => (
              <tr key={cl.category} className="border-t border-slate-100">
                <td className="px-4 py-2 text-slate-700">{cl.label}</td>
                <td className="px-4 py-2 text-right text-slate-800"><EditableCell value={cl.amount} onChange={(v) => updateCostLine(i, v)} /></td>
                <td className="px-4 py-2 text-right text-slate-500">{fmtCur(cl.monthly)}</td>
                <td className={cn('px-4 py-2 text-right font-medium', cl.severity === 'high' ? 'text-red-600' : cl.severity === 'low' ? 'text-blue-600' : 'text-slate-600')}>{fmtPct(cl.pct_on_revenue)}</td>
                <td className="px-4 py-2 text-right text-xs text-slate-400">{cl.benchmark_max > 0 ? `${fmtPct(cl.benchmark_min)}-${fmtPct(cl.benchmark_max)}` : 'custom'}</td>
              </tr>
            ))}
            {/* Totals */}
            <tr className="border-t-2 border-slate-300 bg-slate-50 font-semibold">
              <td className="px-4 py-2">Totale Costi</td>
              <td className="px-4 py-2 text-right">{fmtCur(preview.total_costi)}</td>
              <td className="px-4 py-2 text-right text-slate-500">{fmtCur(preview.total_costi / 12)}</td>
              <td className="px-4 py-2 text-right">{fmtPct(preview.ricavi_totali > 0 ? (preview.total_costi / preview.ricavi_totali) * 100 : 0)}</td>
              <td />
            </tr>
            <tr className={cn('border-t border-slate-200 font-bold', preview.ebitda >= 0 ? 'bg-green-50' : 'bg-red-50')}>
              <td className="px-4 py-2.5">EBITDA</td>
              <td className={cn('px-4 py-2.5 text-right', preview.ebitda >= 0 ? 'text-green-700' : 'text-red-700')}>{fmtCur(preview.ebitda)}</td>
              <td className="px-4 py-2.5 text-right text-slate-500">{fmtCur(preview.ebitda / 12)}</td>
              <td className={cn('px-4 py-2.5 text-right', verdictColor)}>{fmtPct(preview.ebitda_pct)}</td>
              <td className="px-4 py-2.5 text-right text-xs text-slate-400">{preview.ebitda_benchmark}</td>
            </tr>
            <tr className="border-t border-slate-100 text-slate-500">
              <td className="px-4 py-2">IRES (24%)</td><td className="px-4 py-2 text-right">{fmtCur(preview.ires)}</td><td colSpan={3} />
            </tr>
            <tr className="border-t border-slate-100 text-slate-500">
              <td className="px-4 py-2">IRAP (3.9%)</td><td className="px-4 py-2 text-right">{fmtCur(preview.irap)}</td><td colSpan={3} />
            </tr>
            <tr className="border-t-2 border-slate-300 font-bold">
              <td className="px-4 py-2.5">Utile Netto</td>
              <td className={cn('px-4 py-2.5 text-right', preview.utile_netto >= 0 ? 'text-green-700' : 'text-red-700')}>{fmtCur(preview.utile_netto)}</td>
              <td colSpan={3} />
            </tr>
          </tbody>
        </table>
      </div>

      <button onClick={onSave} disabled={isSaving} className="w-full rounded-xl bg-green-600 px-6 py-3 text-base font-semibold text-white shadow-md transition-colors hover:bg-green-700 disabled:opacity-50">
        {isSaving ? 'Salvataggio...' : 'Conferma e salva il budget'}
      </button>
    </div>
  )
}

// ── Main Wizard ──

export default function BudgetWizardPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const editMode = searchParams.get('edit') === 'true'
  const urlYear = searchParams.get('year')
  const currentYear = new Date().getFullYear()

  // Wizard state
  const [step, setStep] = useState(0)
  const [sectorId, setSectorId] = useState('')
  const [fatturato, setFatturato] = useState('')
  const [dipendenti, setDipendenti] = useState('')
  const [ral, setRal] = useState('')
  const [year, setYear] = useState(urlYear ? parseInt(urlYear, 10) : currentYear + 1)
  const [personnelMode, setPersonnelMode] = useState<'calc' | 'direct'>('calc')
  const [costoPersonale, setCostoPersonale] = useState('')
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [overrides, setOverrides] = useState<Record<string, string>>({})
  const [customCosts, setCustomCosts] = useState<CustomLine[]>([])
  const [extraRevenues, setExtraRevenues] = useState<CustomLine[]>([])
  const [preview, setPreview] = useState<CEPreview | null>(null)
  const [saved, setSaved] = useState(false)

  // API
  const { data: sectors } = useQuery<Sector[]>({
    queryKey: ['budget-wizard-sectors'],
    queryFn: async () => (await api.get('/controller/budget/wizard/sectors')).data,
  })
  const { data: historyData } = useQuery({
    queryKey: ['budget-wizard-history', year],
    queryFn: async () => (await api.get(`/controller/budget/wizard/history?year=${year}`)).data,
  })
  const { data: questions } = useQuery<SectorQuestions>({
    queryKey: ['budget-wizard-questions', sectorId],
    queryFn: async () => (await api.get(`/controller/budget/wizard/questions?sector=${sectorId}`)).data,
    enabled: !!sectorId,
  })

  // Load existing budget for edit mode
  const { data: loadedBudget } = useQuery({
    queryKey: ['budget-wizard-load', year],
    queryFn: async () => (await api.get(`/controller/budget/wizard/load?year=${year}`)).data,
    enabled: editMode,
  })

  // Hydrate wizard from loaded budget
  useEffect(() => {
    if (editMode && loadedBudget?.has_data && loadedBudget.meta) {
      const m = loadedBudget.meta
      if (m.sector_id) setSectorId(m.sector_id)
      if (m.fatturato) setFatturato(String(m.fatturato))
      if (m.n_dipendenti) setDipendenti(String(m.n_dipendenti))
      if (m.ral_media) setRal(String(m.ral_media))
      if (m.personnel_mode) setPersonnelMode(m.personnel_mode)
      if (m.costo_personale_diretto) setCostoPersonale(String(m.costo_personale_diretto))
      if (m.overrides) {
        const ov: Record<string, string> = {}
        for (const [k, v] of Object.entries(m.overrides)) ov[k] = String(v)
        setOverrides(ov)
      }
      if (m.custom_costs) setCustomCosts(m.custom_costs.map((c: { label: string; amount: number }) => ({ label: c.label, amount: String(c.amount) })))
      if (m.extra_revenues) setExtraRevenues(m.extra_revenues.map((r: { label: string; amount: number }) => ({ label: r.label, amount: String(r.amount) })))
      setStep(3) // Jump to result for editing
    }
  }, [editMode, loadedBudget])

  const generateMutation = useMutation({
    mutationFn: async (data: Record<string, unknown>) => (await api.post('/controller/budget/wizard/generate', data)).data,
    onSuccess: (data) => setPreview(data),
  })

  const saveMutation = useMutation({
    mutationFn: async (data: { year: number; budget_lines: CEPreview['budget_lines']; meta: Record<string, unknown> }) =>
      (await api.post('/controller/budget/wizard/save', data)).data,
    onSuccess: () => setSaved(true),
  })

  // Generate preview when entering step 3
  const triggerGenerate = useCallback(() => {
    if (!sectorId || !fatturato) return
    const numOverrides: Record<string, number> = {}
    for (const [k, v] of Object.entries(overrides)) { if (v) numOverrides[k] = Number(v) }

    generateMutation.mutate({
      sector_id: sectorId,
      fatturato: Number(fatturato),
      n_dipendenti: Number(dipendenti) || 0,
      ral_media: Number(ral) || 0,
      year,
      overrides: numOverrides,
      costo_personale_diretto: personnelMode === 'direct' ? Number(costoPersonale) || 0 : null,
      custom_costs: customCosts.filter((c) => c.label && c.amount).map((c) => ({ label: c.label, amount: Number(c.amount) })),
      extra_revenues: extraRevenues.filter((r) => r.label && r.amount).map((r) => ({ label: r.label, amount: Number(r.amount) })),
    })
  }, [sectorId, fatturato, dipendenti, ral, year, overrides, personnelMode, costoPersonale, customCosts, extraRevenues]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (step === 3 && !editMode) triggerGenerate()
  }, [step]) // eslint-disable-line react-hooks/exhaustive-deps

  // Edit mode: generate on mount if we have meta but no preview yet
  useEffect(() => {
    if (editMode && step === 3 && !preview && sectorId && fatturato) {
      triggerGenerate()
    }
  }, [editMode, step, preview, sectorId, fatturato]) // eslint-disable-line react-hooks/exhaustive-deps

  const canNext = [
    () => !!sectorId,
    () => !!fatturato && Number(fatturato) > 0,
    () => true,
    () => !!preview,
  ]

  function handleSave() {
    if (!preview) return
    saveMutation.mutate({
      year: preview.year,
      budget_lines: preview.budget_lines,
      meta: {
        sector_id: sectorId,
        fatturato: Number(fatturato),
        n_dipendenti: Number(dipendenti) || 0,
        ral_media: Number(ral) || 0,
        costo_personale_diretto: personnelMode === 'direct' ? Number(costoPersonale) || null : null,
        personnel_mode: personnelMode,
        overrides: Object.fromEntries(Object.entries(overrides).filter(([, v]) => v).map(([k, v]) => [k, Number(v)])),
        custom_costs: customCosts.filter((c) => c.label && c.amount).map((c) => ({ label: c.label, amount: Number(c.amount) })),
        extra_revenues: extraRevenues.filter((r) => r.label && r.amount).map((r) => ({ label: r.label, amount: Number(r.amount) })),
      },
    })
  }

  // Success screen
  if (saved) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-20 text-center">
        <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
          <Check className="h-8 w-8 text-green-600" />
        </div>
        <h1 className="mb-2 text-2xl font-bold text-slate-800">Budget {year} salvato!</h1>
        <p className="mb-8 text-slate-500">Il tuo piano economico e attivo. Puoi monitorare budget vs consuntivo dalla dashboard.</p>
        <div className="flex flex-wrap justify-center gap-4">
          <button onClick={() => navigate('/budgets')} className="rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-700">Torna ai Budget</button>
          <button onClick={() => navigate('/ceo/budget')} className="rounded-xl border border-slate-300 px-6 py-3 font-semibold text-slate-700 hover:bg-slate-50">Vai al Consuntivo</button>
          <button onClick={() => { setSaved(false); setStep(3) }} className="rounded-xl border border-slate-300 px-6 py-3 font-semibold text-slate-700 hover:bg-slate-50">
            <Pencil className="mr-1 inline h-4 w-4" /> Modifica budget
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl px-4 pb-12">
      <PageHeader title="Crea il tuo Budget" subtitle="Il wizard ti guida passo-passo nella creazione del piano economico" />

      {/* Progress */}
      <div className="mb-8 flex items-center justify-between">
        {STEPS.map((s, i) => {
          const Icon = s.icon
          const isActive = i === step
          const isDone = i < step
          return (
            <div key={i} className="flex flex-1 items-center">
              <div className="flex flex-col items-center">
                <div className={cn('flex h-10 w-10 items-center justify-center rounded-full border-2 transition-all', isDone ? 'border-green-500 bg-green-500 text-white' : isActive ? 'border-blue-500 bg-blue-500 text-white' : 'border-slate-300 bg-white text-slate-400')}>
                  {isDone ? <Check className="h-5 w-5" /> : <Icon className="h-5 w-5" />}
                </div>
                <span className={cn('mt-1.5 text-xs font-medium', isActive ? 'text-blue-600' : isDone ? 'text-green-600' : 'text-slate-400')}>{s.label}</span>
              </div>
              {i < STEPS.length - 1 && <div className={cn('mx-2 h-0.5 flex-1', i < step ? 'bg-green-400' : 'bg-slate-200')} />}
            </div>
          )
        })}
      </div>

      {/* Content */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        {step === 0 && <StepSector sectors={sectors ?? []} selected={sectorId} onSelect={setSectorId} />}
        {step === 1 && (
          <StepBaseData
            fatturato={fatturato} dipendenti={dipendenti} ral={ral} year={year}
            personnelMode={personnelMode} costoPersonale={costoPersonale}
            onFatturato={setFatturato} onDipendenti={setDipendenti} onRal={setRal}
            onYear={setYear} onPersonnelMode={setPersonnelMode} onCostoPersonale={setCostoPersonale}
            historyData={historyData ?? null}
          />
        )}
        {step === 2 && (
          <StepDetails
            questions={questions ?? null} answers={answers} onAnswer={(id, val) => setAnswers((p) => ({ ...p, [id]: val }))}
            costStructure={questions?.cost_structure ?? null} fatturato={Number(fatturato) || 0}
            overrides={overrides} onOverride={(id, val) => setOverrides((p) => ({ ...p, [id]: val }))}
            customCosts={customCosts} onCustomCosts={setCustomCosts}
            extraRevenues={extraRevenues} onExtraRevenues={setExtraRevenues}
          />
        )}
        {step === 3 && (
          <StepResult
            preview={preview} isLoading={generateMutation.isPending}
            onUpdatePreview={setPreview} onSave={handleSave} isSaving={saveMutation.isPending}
          />
        )}
      </div>

      {/* Navigation */}
      <div className="mt-6 flex items-center justify-between">
        <button onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0} className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-30">
          <ArrowLeft className="h-4 w-4" /> Indietro
        </button>
        {step < STEPS.length - 1 && (
          <button onClick={() => setStep(step + 1)} disabled={!canNext[step]()} className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-30">
            Avanti <ArrowRight className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  )
}
