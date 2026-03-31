import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
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
  ArrowDown,
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
  budget_lines: Array<{ category: string; annual_proposed: number; monthly_proposed: number }>
}

interface SectorQuestions {
  sector_id: string
  label: string
  questions: Array<{ id: string; text: string; type: string }>
  cost_structure: Record<string, { label: string; pct_min: number; pct_max: number; default: number }>
}

// ── Helpers ──

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(value)
}

function formatPct(value: number): string {
  return `${value.toFixed(1)}%`
}

// ── Step Components ──

const STEPS = [
  { label: 'Settore', icon: Building2 },
  { label: 'Dati base', icon: Users },
  { label: 'Dettagli', icon: FileSpreadsheet },
  { label: 'Risultato', icon: TrendingUp },
]

// Step 1: Sector selection
function StepSector({
  sectors,
  selected,
  onSelect,
}: {
  sectors: Sector[]
  selected: string
  onSelect: (id: string) => void
}) {
  return (
    <div>
      <h2 className="mb-2 text-xl font-bold text-slate-800">In che settore opera la tua azienda?</h2>
      <p className="mb-6 text-sm text-slate-500">
        Seleziona il settore per ricevere benchmark e domande personalizzate.
      </p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {sectors.map((s) => (
          <button
            key={s.id}
            onClick={() => onSelect(s.id)}
            className={cn(
              'flex items-center gap-3 rounded-xl border-2 px-4 py-4 text-left transition-all',
              selected === s.id
                ? 'border-blue-500 bg-blue-50 shadow-md'
                : 'border-slate-200 bg-white hover:border-blue-300 hover:bg-blue-50/50',
            )}
          >
            <div className={cn(
              'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg',
              selected === s.id ? 'bg-blue-500 text-white' : 'bg-slate-100 text-slate-500',
            )}>
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

// Step 2: Base data
function StepBaseData({
  fatturato,
  dipendenti,
  ral,
  year,
  onFatturato,
  onDipendenti,
  onRal,
  onYear,
  historyData,
}: {
  fatturato: string
  dipendenti: string
  ral: string
  year: number
  onFatturato: (v: string) => void
  onDipendenti: (v: string) => void
  onRal: (v: string) => void
  onYear: (v: number) => void
  historyData: { has_history: boolean; fatturato_prev: number; prev_year: number } | null
}) {
  return (
    <div>
      <h2 className="mb-2 text-xl font-bold text-slate-800">Dati di base</h2>
      <p className="mb-6 text-sm text-slate-500">
        Inserisci i numeri principali. Se non li sai con precisione, una stima va benissimo.
      </p>

      {historyData?.has_history && (
        <div className="mb-6 rounded-lg border border-blue-200 bg-blue-50 p-4">
          <p className="text-sm text-blue-800">
            <Sparkles className="mr-1 inline h-4 w-4" />
            Abbiamo trovato dati del {historyData.prev_year}: fatturato{' '}
            <strong>{formatCurrency(historyData.fatturato_prev)}</strong>. Vuoi partire da qui?
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
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Anno budget
          </label>
          <select
            value={year}
            onChange={(e) => onYear(Number(e.target.value))}
            className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {[2025, 2026, 2027].map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">
            Fatturato previsto (annuale)
          </label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-slate-400">EUR</span>
            <input
              type="number"
              value={fatturato}
              onChange={(e) => onFatturato(e.target.value)}
              placeholder="500000"
              className="w-full rounded-lg border border-slate-300 py-2.5 pl-12 pr-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              Numero dipendenti
            </label>
            <input
              type="number"
              value={dipendenti}
              onChange={(e) => onDipendenti(e.target.value)}
              placeholder="5"
              min={0}
              className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              RAL media (lordo annuo)
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-slate-400">EUR</span>
              <input
                type="number"
                value={ral}
                onChange={(e) => onRal(e.target.value)}
                placeholder="35000"
                className="w-full rounded-lg border border-slate-300 py-2.5 pl-12 pr-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// Step 3: Sector-specific questions + cost adjustments
function StepDetails({
  questions,
  answers,
  onAnswer,
  costStructure,
  fatturato,
  overrides,
  onOverride,
}: {
  questions: SectorQuestions | null
  answers: Record<string, string>
  onAnswer: (id: string, value: string) => void
  costStructure: Record<string, { label: string; default: number }> | null
  fatturato: number
  overrides: Record<string, string>
  onOverride: (id: string, value: string) => void
}) {
  if (!questions) return <p className="text-slate-500">Caricamento domande...</p>

  return (
    <div>
      <h2 className="mb-2 text-xl font-bold text-slate-800">Dettagli {questions.label}</h2>
      <p className="mb-6 text-sm text-slate-500">
        Rispondi a queste domande per personalizzare il budget. Se non sai un numero, lascia vuoto e usiamo il benchmark di settore.
      </p>

      {/* Sector questions */}
      <div className="mb-8 space-y-4">
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
        <>
          <h3 className="mb-3 text-sm font-semibold text-slate-700">
            Aggiusta i costi (opzionale)
          </h3>
          <p className="mb-4 text-xs text-slate-500">
            I valori sono calcolati dai benchmark di settore. Modifica solo quelli che conosci con precisione.
          </p>
          <div className="space-y-3">
            {Object.entries(costStructure).filter(([k]) => k !== 'personale').map(([catId, cat]) => {
              const defaultAmount = Math.round(fatturato * cat.default)
              return (
                <div key={catId} className="flex items-center gap-3">
                  <span className="w-48 shrink-0 text-sm text-slate-600">{cat.label}</span>
                  <div className="relative flex-1">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-slate-400">EUR</span>
                    <input
                      type="number"
                      value={overrides[catId] ?? ''}
                      onChange={(e) => onOverride(catId, e.target.value)}
                      placeholder={String(defaultAmount)}
                      className="w-full rounded-lg border border-slate-200 py-2 pl-12 pr-3 text-sm focus:border-blue-500 focus:outline-none"
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}

// Step 4: CE Preview + Save
function StepResult({
  preview,
  isLoading,
  onSave,
  isSaving,
}: {
  preview: CEPreview | null
  isLoading: boolean
  onSave: () => void
  isSaving: boolean
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

  const verdictColor =
    preview.ebitda_verdict === 'above' ? 'text-green-600' :
    preview.ebitda_verdict === 'below' ? 'text-red-600' : 'text-blue-600'

  return (
    <div>
      <h2 className="mb-2 text-xl font-bold text-slate-800">
        Conto Economico Previsionale {preview.year}
      </h2>
      <p className="mb-6 text-sm text-slate-500">{preview.sector_label}</p>

      {/* KPI summary */}
      <div className="mb-6 grid grid-cols-3 gap-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4 text-center shadow-sm">
          <p className="text-xs font-medium uppercase text-slate-500">Ricavi</p>
          <p className="mt-1 text-xl font-bold text-slate-800">{formatCurrency(preview.ricavi)}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4 text-center shadow-sm">
          <p className="text-xs font-medium uppercase text-slate-500">Costi</p>
          <p className="mt-1 text-xl font-bold text-slate-800">{formatCurrency(preview.total_costi)}</p>
        </div>
        <div className={cn(
          'rounded-xl border-2 p-4 text-center shadow-sm',
          preview.ebitda >= 0 ? 'border-green-300 bg-green-50' : 'border-red-300 bg-red-50',
        )}>
          <p className="text-xs font-medium uppercase text-slate-500">EBITDA</p>
          <p className={cn('mt-1 text-xl font-bold', preview.ebitda >= 0 ? 'text-green-700' : 'text-red-700')}>
            {formatCurrency(preview.ebitda)}
          </p>
          <p className={cn('text-xs font-medium', verdictColor)}>
            {formatPct(preview.ebitda_pct)} (benchmark: {preview.ebitda_benchmark})
          </p>
        </div>
      </div>

      {/* Advice */}
      <div className={cn(
        'mb-6 rounded-lg border p-4',
        preview.ebitda_verdict === 'above' ? 'border-green-200 bg-green-50' :
        preview.ebitda_verdict === 'below' ? 'border-red-200 bg-red-50' : 'border-blue-200 bg-blue-50',
      )}>
        <p className={cn('text-sm', verdictColor)}>
          {preview.ebitda_verdict === 'above' && <CheckCircle2 className="mr-1 inline h-4 w-4" />}
          {preview.ebitda_verdict === 'below' && <AlertTriangle className="mr-1 inline h-4 w-4" />}
          {preview.ebitda_verdict === 'ok' && <Sparkles className="mr-1 inline h-4 w-4" />}
          {preview.ebitda_advice}
        </p>
      </div>

      {/* Cost breakdown table */}
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
              <td className="px-4 py-2 text-right font-semibold text-green-700">{formatCurrency(preview.ricavi)}</td>
              <td className="px-4 py-2 text-right text-green-600">{formatCurrency(preview.ricavi / 12)}</td>
              <td className="px-4 py-2 text-right text-green-600">100%</td>
              <td className="px-4 py-2 text-right text-slate-400">-</td>
            </tr>
            {/* Cost rows */}
            {preview.cost_lines.map((cl) => (
              <tr key={cl.category} className="border-t border-slate-100">
                <td className="px-4 py-2 text-slate-700">{cl.label}</td>
                <td className="px-4 py-2 text-right text-slate-800">{formatCurrency(cl.amount)}</td>
                <td className="px-4 py-2 text-right text-slate-500">{formatCurrency(cl.monthly)}</td>
                <td className={cn(
                  'px-4 py-2 text-right font-medium',
                  cl.severity === 'high' ? 'text-red-600' : cl.severity === 'low' ? 'text-blue-600' : 'text-slate-600',
                )}>
                  {formatPct(cl.pct_on_revenue)}
                  {cl.severity === 'high' && <ArrowDown className="ml-1 inline h-3 w-3 rotate-180 text-red-500" />}
                </td>
                <td className="px-4 py-2 text-right text-xs text-slate-400">
                  {formatPct(cl.benchmark_min)}-{formatPct(cl.benchmark_max)}
                </td>
              </tr>
            ))}
            {/* Totals */}
            <tr className="border-t-2 border-slate-300 bg-slate-50 font-semibold">
              <td className="px-4 py-2">Totale Costi</td>
              <td className="px-4 py-2 text-right">{formatCurrency(preview.total_costi)}</td>
              <td className="px-4 py-2 text-right text-slate-500">{formatCurrency(preview.total_costi / 12)}</td>
              <td className="px-4 py-2 text-right">{formatPct(preview.total_costi / preview.ricavi * 100)}</td>
              <td />
            </tr>
            <tr className={cn('border-t border-slate-200 font-bold', preview.ebitda >= 0 ? 'bg-green-50' : 'bg-red-50')}>
              <td className="px-4 py-2.5">EBITDA</td>
              <td className={cn('px-4 py-2.5 text-right', preview.ebitda >= 0 ? 'text-green-700' : 'text-red-700')}>
                {formatCurrency(preview.ebitda)}
              </td>
              <td className="px-4 py-2.5 text-right text-slate-500">{formatCurrency(preview.ebitda / 12)}</td>
              <td className={cn('px-4 py-2.5 text-right', verdictColor)}>{formatPct(preview.ebitda_pct)}</td>
              <td className="px-4 py-2.5 text-right text-xs text-slate-400">{preview.ebitda_benchmark}</td>
            </tr>
            {/* Imposte */}
            <tr className="border-t border-slate-100 text-slate-500">
              <td className="px-4 py-2">IRES (24%)</td>
              <td className="px-4 py-2 text-right">{formatCurrency(preview.ires)}</td>
              <td colSpan={3} />
            </tr>
            <tr className="border-t border-slate-100 text-slate-500">
              <td className="px-4 py-2">IRAP (3.9%)</td>
              <td className="px-4 py-2 text-right">{formatCurrency(preview.irap)}</td>
              <td colSpan={3} />
            </tr>
            <tr className="border-t-2 border-slate-300 font-bold">
              <td className="px-4 py-2.5">Utile Netto</td>
              <td className={cn('px-4 py-2.5 text-right', preview.utile_netto >= 0 ? 'text-green-700' : 'text-red-700')}>
                {formatCurrency(preview.utile_netto)}
              </td>
              <td colSpan={3} />
            </tr>
          </tbody>
        </table>
      </div>

      {/* Save button */}
      <button
        onClick={onSave}
        disabled={isSaving}
        className="w-full rounded-xl bg-green-600 px-6 py-3 text-base font-semibold text-white shadow-md transition-colors hover:bg-green-700 disabled:opacity-50"
      >
        {isSaving ? 'Salvataggio...' : 'Conferma e salva il budget'}
      </button>
    </div>
  )
}

// ── Main Wizard ──

export default function BudgetWizardPage() {
  const navigate = useNavigate()
  const currentYear = new Date().getFullYear()

  // Wizard state
  const [step, setStep] = useState(0)
  const [sectorId, setSectorId] = useState('')
  const [fatturato, setFatturato] = useState('')
  const [dipendenti, setDipendenti] = useState('')
  const [ral, setRal] = useState('')
  const [year, setYear] = useState(currentYear + 1)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [overrides, setOverrides] = useState<Record<string, string>>({})
  const [preview, setPreview] = useState<CEPreview | null>(null)
  const [saved, setSaved] = useState(false)

  // API queries
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

  const generateMutation = useMutation({
    mutationFn: async (data: {
      sector_id: string
      fatturato: number
      n_dipendenti: number
      ral_media: number
      year: number
      overrides: Record<string, number>
    }) => (await api.post('/controller/budget/wizard/generate', data)).data,
    onSuccess: (data) => setPreview(data),
  })

  const saveMutation = useMutation({
    mutationFn: async (data: { year: number; budget_lines: CEPreview['budget_lines'] }) =>
      (await api.post('/controller/budget/wizard/save', data)).data,
    onSuccess: () => setSaved(true),
  })

  // Generate preview when entering step 3
  useEffect(() => {
    if (step === 3 && sectorId && fatturato) {
      const numOverrides: Record<string, number> = {}
      for (const [k, v] of Object.entries(overrides)) {
        if (v) numOverrides[k] = Number(v)
      }
      generateMutation.mutate({
        sector_id: sectorId,
        fatturato: Number(fatturato),
        n_dipendenti: Number(dipendenti) || 0,
        ral_media: Number(ral) || 0,
        year,
        overrides: numOverrides,
      })
    }
  }, [step]) // eslint-disable-line react-hooks/exhaustive-deps

  // Validation
  const canNext = [
    () => !!sectorId,
    () => !!fatturato && Number(fatturato) > 0,
    () => true, // details are optional
    () => !!preview,
  ]

  function handleNext() {
    if (step < STEPS.length - 1) setStep(step + 1)
  }

  function handleBack() {
    if (step > 0) setStep(step - 1)
  }

  function handleSave() {
    if (preview) {
      saveMutation.mutate({ year: preview.year, budget_lines: preview.budget_lines })
    }
  }

  // Saved success screen
  if (saved) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-20 text-center">
        <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
          <Check className="h-8 w-8 text-green-600" />
        </div>
        <h1 className="mb-2 text-2xl font-bold text-slate-800">Budget {year} salvato!</h1>
        <p className="mb-8 text-slate-500">
          Il tuo piano economico e attivo. Puoi monitorare budget vs consuntivo dalla dashboard.
        </p>
        <div className="flex justify-center gap-4">
          <button
            onClick={() => navigate('/dashboard')}
            className="rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white hover:bg-blue-700"
          >
            Vai alla Dashboard
          </button>
          <button
            onClick={() => navigate('/setup')}
            className="rounded-xl border border-slate-300 px-6 py-3 font-semibold text-slate-700 hover:bg-slate-50"
          >
            Torna al Setup
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl px-4 pb-12">
      <PageHeader
        title="Crea il tuo Budget"
        subtitle="Il wizard ti guida passo-passo nella creazione del piano economico"
      />

      {/* Step progress */}
      <div className="mb-8 flex items-center justify-between">
        {STEPS.map((s, i) => {
          const Icon = s.icon
          const isActive = i === step
          const isDone = i < step
          return (
            <div key={i} className="flex flex-1 items-center">
              <div className="flex flex-col items-center">
                <div className={cn(
                  'flex h-10 w-10 items-center justify-center rounded-full border-2 transition-all',
                  isDone ? 'border-green-500 bg-green-500 text-white' :
                  isActive ? 'border-blue-500 bg-blue-500 text-white' :
                  'border-slate-300 bg-white text-slate-400',
                )}>
                  {isDone ? <Check className="h-5 w-5" /> : <Icon className="h-5 w-5" />}
                </div>
                <span className={cn(
                  'mt-1.5 text-xs font-medium',
                  isActive ? 'text-blue-600' : isDone ? 'text-green-600' : 'text-slate-400',
                )}>
                  {s.label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div className={cn(
                  'mx-2 h-0.5 flex-1',
                  i < step ? 'bg-green-400' : 'bg-slate-200',
                )} />
              )}
            </div>
          )
        })}
      </div>

      {/* Step content */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        {step === 0 && (
          <StepSector
            sectors={sectors ?? []}
            selected={sectorId}
            onSelect={setSectorId}
          />
        )}
        {step === 1 && (
          <StepBaseData
            fatturato={fatturato}
            dipendenti={dipendenti}
            ral={ral}
            year={year}
            onFatturato={setFatturato}
            onDipendenti={setDipendenti}
            onRal={setRal}
            onYear={setYear}
            historyData={historyData ?? null}
          />
        )}
        {step === 2 && (
          <StepDetails
            questions={questions ?? null}
            answers={answers}
            onAnswer={(id, val) => setAnswers((prev) => ({ ...prev, [id]: val }))}
            costStructure={questions?.cost_structure ?? null}
            fatturato={Number(fatturato) || 0}
            overrides={overrides}
            onOverride={(id, val) => setOverrides((prev) => ({ ...prev, [id]: val }))}
          />
        )}
        {step === 3 && (
          <StepResult
            preview={preview}
            isLoading={generateMutation.isPending}
            onSave={handleSave}
            isSaving={saveMutation.isPending}
          />
        )}
      </div>

      {/* Navigation */}
      <div className="mt-6 flex items-center justify-between">
        <button
          onClick={handleBack}
          disabled={step === 0}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-30"
        >
          <ArrowLeft className="h-4 w-4" /> Indietro
        </button>

        {step < STEPS.length - 1 && (
          <button
            onClick={handleNext}
            disabled={!canNext[step]()}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-30"
          >
            Avanti <ArrowRight className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  )
}
