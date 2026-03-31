import { useNavigate } from 'react-router-dom'
import { useEffect, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FileText,
  Landmark,
  Users,
  Receipt,
  FileSpreadsheet,
  Target,
  Lock,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Sparkles,
} from 'lucide-react'
import { useCompletenessScore, useBudgetVsActual } from '../api/hooks'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import { cn } from '../lib/utils'

// ── Types ──

type PieceStatus = 'locked' | 'ready' | 'active' | 'warning'

interface PuzzlePieceConfig {
  id: string
  sourceType: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  route: string
  lockedRoute?: string
  dependsOn?: string[]
  required: boolean
}

interface SourceData {
  source_type: string
  status: string
  label?: string
  record_count?: number
  last_sync?: string
  summary?: string
}

interface CompletenessData {
  sources: SourceData[]
  connected_count: number
  total_sources: number
}

// ── Piece Configurations ──

const PUZZLE_PIECES: PuzzlePieceConfig[] = [
  {
    id: 'fatture',
    sourceType: 'fatture',
    label: 'Fatture',
    icon: FileText,
    route: '/fatture',
    lockedRoute: '/chat?msg=Aiutami+a+configurare+le+fatture+dal+cassetto+fiscale',
    required: true,
  },
  {
    id: 'banca',
    sourceType: 'banca',
    label: 'Banca',
    icon: Landmark,
    route: '/banca',
    lockedRoute: '/chat?msg=Aiutami+a+collegare+il+conto+bancario+per+vedere+movimenti+e+cash+flow',
    required: true,
  },
  {
    id: 'paghe',
    sourceType: 'paghe',
    label: 'Paghe',
    icon: Users,
    route: '/personale',
    lockedRoute: '/chat?msg=Aiutami+a+importare+i+costi+del+personale+dal+PDF+delle+paghe',
    required: false,
  },
  {
    id: 'corrispettivi',
    sourceType: 'corrispettivi',
    label: 'Corrispettivi',
    icon: Receipt,
    route: '/corrispettivi',
    lockedRoute: '/chat?msg=Aiutami+a+configurare+i+corrispettivi+telematici',
    required: false,
  },
  {
    id: 'bilancio',
    sourceType: 'bilancio',
    label: 'Bilancio',
    icon: FileSpreadsheet,
    route: '/contabilita/bilancio',
    lockedRoute: '/chat?msg=Aiutami+a+importare+i+saldi+iniziali+del+bilancio+per+aprire+i+conti',
    required: false,
  },
  {
    id: 'budget',
    sourceType: 'budget',
    label: 'Budget',
    icon: Target,
    route: '/controller',
    lockedRoute: '/chat?msg=Aiutami+a+creare+il+budget+annuale+per+la+mia+azienda',
    dependsOn: ['fatture'],
    required: true,
  },
]

const REQUIRED_PIECES = PUZZLE_PIECES.filter((p) => p.required).map((p) => p.id)

// ── Helpers ──

function getSubtitle(
  piece: PuzzlePieceConfig,
  source: SourceData | undefined,
  status: PieceStatus,
): string {
  if (status === 'locked') {
    const deps = piece.dependsOn ?? []
    const depLabels = deps.map((d) => PUZZLE_PIECES.find((p) => p.id === d)?.label ?? d)
    return `Richiede ${depLabels.join(', ')}`
  }
  if (status === 'ready') return 'Da configurare'
  if (status === 'warning') return source?.summary ?? 'Dati non aggiornati'
  return source?.summary ?? 'Collegato'
}

function resolveStatus(
  piece: PuzzlePieceConfig,
  source: SourceData | undefined,
  activeIds: Set<string>,
): PieceStatus {
  if (piece.dependsOn) {
    const unmet = piece.dependsOn.some((dep) => !activeIds.has(dep))
    if (unmet) return 'locked'
  }
  if (!source) return 'ready'
  const s = source.status
  if (s === 'connected' || s === 'active') {
    if (source.last_sync) {
      const daysSinceSync =
        (Date.now() - new Date(source.last_sync).getTime()) / (1000 * 60 * 60 * 24)
      if (daysSinceSync > 30) return 'warning'
    }
    return 'active'
  }
  if (s === 'warning' || s === 'stale' || s === 'error') return 'warning'
  return 'ready'
}

// ── SVG Puzzle Path Generation ──

const CW = 200 // cell width
const CH = 200 // cell height
const TD = 28 // tab depth (protrusion)
const TW = 22 // tab half-width at opening

function generatePiecePath(col: number, row: number): string {
  const x = col * CW
  const y = row * CH

  const top = row === 0 ? 'flat' : 'notch'
  const right = col === 2 ? 'flat' : 'tab'
  const bottom = row === 1 ? 'flat' : 'tab'
  const left = col === 0 ? 'flat' : 'notch'

  let d = `M ${x} ${y}`

  // Top edge (left to right)
  if (top === 'flat') {
    d += ` L ${x + CW} ${y}`
  } else {
    const mx = x + CW / 2
    d += ` L ${mx - TW} ${y}`
    d += ` C ${mx - TW},${y + TD * 0.5} ${mx - TW * 0.6},${y + TD} ${mx},${y + TD}`
    d += ` C ${mx + TW * 0.6},${y + TD} ${mx + TW},${y + TD * 0.5} ${mx + TW},${y}`
    d += ` L ${x + CW} ${y}`
  }

  // Right edge (top to bottom)
  if (right === 'flat') {
    d += ` L ${x + CW} ${y + CH}`
  } else {
    const my = y + CH / 2
    d += ` L ${x + CW} ${my - TW}`
    d += ` C ${x + CW + TD * 0.5},${my - TW} ${x + CW + TD},${my - TW * 0.6} ${x + CW + TD},${my}`
    d += ` C ${x + CW + TD},${my + TW * 0.6} ${x + CW + TD * 0.5},${my + TW} ${x + CW},${my + TW}`
    d += ` L ${x + CW} ${y + CH}`
  }

  // Bottom edge (right to left)
  if (bottom === 'flat') {
    d += ` L ${x} ${y + CH}`
  } else {
    const mx = x + CW / 2
    d += ` L ${mx + TW} ${y + CH}`
    d += ` C ${mx + TW},${y + CH + TD * 0.5} ${mx + TW * 0.6},${y + CH + TD} ${mx},${y + CH + TD}`
    d += ` C ${mx - TW * 0.6},${y + CH + TD} ${mx - TW},${y + CH + TD * 0.5} ${mx - TW},${y + CH}`
    d += ` L ${x} ${y + CH}`
  }

  // Left edge (bottom to top)
  if (left === 'flat') {
    d += ` L ${x} ${y}`
  } else {
    const my = y + CH / 2
    d += ` L ${x} ${my + TW}`
    d += ` C ${x + TD * 0.5},${my + TW} ${x + TD},${my + TW * 0.6} ${x + TD},${my}`
    d += ` C ${x + TD},${my - TW * 0.6} ${x + TD * 0.5},${my - TW} ${x},${my - TW}`
    d += ` L ${x} ${y}`
  }

  d += ' Z'
  return d
}

// ── Status Colors ──

const STATUS_STYLE: Record<
  PieceStatus,
  { fill: string; stroke: string; textColor: string; iconBg: string; iconColor: string }
> = {
  active: {
    fill: '#dcfce7',
    stroke: '#4ade80',
    textColor: 'text-green-700',
    iconBg: 'bg-green-500',
    iconColor: 'text-white',
  },
  ready: {
    fill: '#dbeafe',
    stroke: '#60a5fa',
    textColor: 'text-blue-700',
    iconBg: 'bg-blue-500',
    iconColor: 'text-white',
  },
  locked: {
    fill: '#f1f5f9',
    stroke: '#cbd5e1',
    textColor: 'text-slate-400',
    iconBg: 'bg-slate-300',
    iconColor: 'text-slate-500',
  },
  warning: {
    fill: '#fef3c7',
    stroke: '#fbbf24',
    textColor: 'text-amber-700',
    iconBg: 'bg-amber-400',
    iconColor: 'text-white',
  },
}

// ── Status Badge ──

function StatusBadge({ status }: { status: PieceStatus }) {
  const labels: Record<PieceStatus, string> = {
    active: 'Attivo',
    ready: 'Configura',
    locked: 'Bloccato',
    warning: 'Attenzione',
  }
  const colors: Record<PieceStatus, string> = {
    active: 'bg-green-100 text-green-700 border-green-300',
    ready: 'bg-blue-100 text-blue-700 border-blue-300',
    locked: 'bg-slate-100 text-slate-500 border-slate-300',
    warning: 'bg-amber-100 text-amber-700 border-amber-300',
  }
  const icons: Record<PieceStatus, React.ReactNode> = {
    active: <CheckCircle2 className="h-3 w-3" />,
    ready: <ArrowRight className="h-3 w-3" />,
    locked: <Lock className="h-3 w-3" />,
    warning: <AlertTriangle className="h-3 w-3" />,
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide',
        colors[status],
      )}
    >
      {icons[status]}
      {labels[status]}
    </span>
  )
}

// ── Confetti Particle ──

function ConfettiParticle({ delay, x }: { delay: number; x: number }) {
  const colors = ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']
  const color = colors[Math.floor(Math.random() * colors.length)]
  const size = 6 + Math.random() * 6

  return (
    <motion.div
      className="absolute rounded-sm"
      style={{
        width: size,
        height: size,
        backgroundColor: color,
        left: `${x}%`,
        top: -10,
      }}
      initial={{ y: -20, opacity: 1, rotate: 0 }}
      animate={{
        y: [0, 400 + Math.random() * 200],
        opacity: [1, 1, 0],
        rotate: [0, 360 + Math.random() * 720],
        x: [0, (Math.random() - 0.5) * 100],
      }}
      transition={{
        duration: 2 + Math.random(),
        delay,
        ease: 'easeOut',
      }}
    />
  )
}

// ── SVG Puzzle Grid ──

const SVG_W = CW * 3
const SVG_H = CH * 2
const SVG_PAD = 4

interface PuzzleGridProps {
  pieces: PuzzlePieceConfig[]
  statuses: PieceStatus[]
  sources: SourceData[]
  onPieceClick: (piece: PuzzlePieceConfig, status: PieceStatus) => void
}

function PuzzleGrid({ pieces, statuses, sources, onPieceClick }: PuzzleGridProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  return (
    <div className="relative mx-auto w-full" style={{ maxWidth: 720 }}>
      {/* SVG Puzzle Shapes */}
      <svg
        viewBox={`${-SVG_PAD} ${-SVG_PAD} ${SVG_W + SVG_PAD * 2} ${SVG_H + SVG_PAD * 2}`}
        className="block w-full h-auto"
        style={{ filter: 'drop-shadow(0 4px 12px rgba(0,0,0,0.08))' }}
      >
        <defs>
          {/* Gradients per status */}
          <linearGradient id="grad-active" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#dcfce7" />
            <stop offset="100%" stopColor="#bbf7d0" />
          </linearGradient>
          <linearGradient id="grad-ready" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#dbeafe" />
            <stop offset="100%" stopColor="#bfdbfe" />
          </linearGradient>
          <linearGradient id="grad-locked" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#f8fafc" />
            <stop offset="100%" stopColor="#f1f5f9" />
          </linearGradient>
          <linearGradient id="grad-warning" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#fef3c7" />
            <stop offset="100%" stopColor="#fde68a" />
          </linearGradient>
          {/* Glow filter for hover */}
          <filter id="glow-active">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feFlood floodColor="#4ade80" floodOpacity="0.4" />
            <feComposite in2="blur" operator="in" />
            <feMerge>
              <feMergeNode />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="glow-ready">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feFlood floodColor="#60a5fa" floodOpacity="0.4" />
            <feComposite in2="blur" operator="in" />
            <feMerge>
              <feMergeNode />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="glow-warning">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feFlood floodColor="#fbbf24" floodOpacity="0.4" />
            <feComposite in2="blur" operator="in" />
            <feMerge>
              <feMergeNode />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {pieces.map((piece, index) => {
          const col = index % 3
          const row = Math.floor(index / 3)
          const path = generatePiecePath(col, row)
          const status = statuses[index]
          const style = STATUS_STYLE[status]
          const isClickable = status !== 'locked'
          const isHovered = hoveredIndex === index

          return (
            <g key={piece.id}>
              {/* Piece shape */}
              <path
                d={path}
                fill={`url(#grad-${status})`}
                stroke={style.stroke}
                strokeWidth={2}
                strokeLinejoin="round"
                className={cn(
                  'transition-all duration-200',
                  isClickable && 'cursor-pointer',
                )}
                style={{
                  filter: isHovered && isClickable ? `url(#glow-${status})` : undefined,
                  opacity: status === 'locked' ? 0.7 : 1,
                }}
                onClick={() => isClickable && onPieceClick(piece, status)}
                onMouseEnter={() => setHoveredIndex(index)}
                onMouseLeave={() => setHoveredIndex(null)}
              />

              {/* Active pulse ring */}
              {status === 'active' && (
                <path
                  d={path}
                  fill="none"
                  stroke="#4ade80"
                  strokeWidth={1}
                  opacity={0.4}
                >
                  <animate
                    attributeName="stroke-width"
                    values="1;4;1"
                    dur="2.5s"
                    repeatCount="indefinite"
                  />
                  <animate
                    attributeName="opacity"
                    values="0.4;0.1;0.4"
                    dur="2.5s"
                    repeatCount="indefinite"
                  />
                </path>
              )}
            </g>
          )
        })}
      </svg>

      {/* Content Overlays */}
      <div
        className="absolute inset-0"
        style={{ padding: `${(SVG_PAD / (SVG_H + SVG_PAD * 2)) * 100}%` }}
      >
        <div className="relative h-full w-full">
          {pieces.map((piece, index) => {
            const col = index % 3
            const row = Math.floor(index / 3)
            const status = statuses[index]
            const style = STATUS_STYLE[status]
            const source = sources.find((s) => s.source_type === piece.sourceType)
            const subtitle = getSubtitle(piece, source, status)
            const Icon = piece.icon
            const isClickable = status !== 'locked'

            return (
              <div
                key={`overlay-${piece.id}`}
                className={cn(
                  'absolute flex flex-col items-center justify-center gap-1.5 p-4',
                  isClickable ? 'cursor-pointer' : 'cursor-not-allowed',
                )}
                style={{
                  left: `${(col / 3) * 100}%`,
                  top: `${(row / 2) * 100}%`,
                  width: `${(1 / 3) * 100}%`,
                  height: `${(1 / 2) * 100}%`,
                }}
                onClick={() => isClickable && onPieceClick(piece, status)}
              >
                {/* Icon circle */}
                <div
                  className={cn(
                    'flex h-11 w-11 items-center justify-center rounded-full shadow-sm',
                    style.iconBg,
                    style.iconColor,
                  )}
                >
                  <Icon className="h-5 w-5" />
                </div>

                {/* Label */}
                <h3
                  className={cn(
                    'text-sm font-bold leading-tight',
                    status === 'locked' ? 'text-slate-400' : 'text-slate-800',
                  )}
                >
                  {piece.label}
                  {piece.required && (
                    <span className="ml-1 text-[9px] font-medium uppercase text-slate-400">
                      req
                    </span>
                  )}
                </h3>

                {/* Subtitle */}
                <p className="text-center text-[11px] leading-tight text-slate-500 max-w-[140px]">
                  {subtitle}
                </p>

                {/* Status badge */}
                <StatusBadge status={status} />
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// ── Main Component ──

export default function PuzzleDashboard() {
  const navigate = useNavigate()
  const { data: completenessData, isLoading: loadingCompleteness } = useCompletenessScore()
  const currentYear = new Date().getFullYear()
  const currentMonth = new Date().getMonth() + 1
  const { data: budgetData, isLoading: loadingBudget } = useBudgetVsActual(
    currentYear,
    currentMonth,
  )

  const [showCelebration, setShowCelebration] = useState(false)
  const [confettiParticles, setConfettiParticles] = useState<
    Array<{ id: number; delay: number; x: number }>
  >([])

  const completeness = completenessData as CompletenessData | undefined
  const sources = completeness?.sources ?? []

  // Build a set of active source IDs
  const activeIds = new Set<string>()
  for (const src of sources) {
    if (src.status === 'connected' || src.status === 'active') {
      activeIds.add(src.source_type)
    }
  }

  const hasBudget =
    budgetData != null && typeof budgetData === 'object' && !('detail' in budgetData)
  if (hasBudget) {
    activeIds.add('budget')
  }

  // Resolve statuses
  const pieceStatuses: PieceStatus[] = PUZZLE_PIECES.map((piece) => {
    const source = sources.find((s) => s.source_type === piece.sourceType)
    if (piece.id === 'budget') {
      if (piece.dependsOn?.some((dep) => !activeIds.has(dep))) return 'locked'
      return hasBudget ? 'active' : 'ready'
    }
    return resolveStatus(piece, source, activeIds)
  })

  const activeCount = pieceStatuses.filter((s) => s === 'active').length
  const totalCount = PUZZLE_PIECES.length
  const progressPct = Math.round((activeCount / totalCount) * 100)

  const allRequiredActive = REQUIRED_PIECES.every((id) => {
    const idx = PUZZLE_PIECES.findIndex((p) => p.id === id)
    return idx >= 0 && pieceStatuses[idx] === 'active'
  })

  // Celebration
  const triggerCelebration = useCallback(() => {
    setShowCelebration(true)
    const particles: Array<{ id: number; delay: number; x: number }> = []
    for (let i = 0; i < 40; i++) {
      particles.push({ id: i, delay: Math.random() * 0.8, x: Math.random() * 100 })
    }
    setConfettiParticles(particles)
  }, [])

  useEffect(() => {
    if (allRequiredActive && !showCelebration) {
      triggerCelebration()
    }
  }, [allRequiredActive, showCelebration, triggerCelebration])

  function handlePieceClick(piece: PuzzlePieceConfig, status: PieceStatus) {
    if (status === 'locked') return
    if (status === 'active' || status === 'warning') {
      navigate(piece.route)
    } else if (piece.lockedRoute) {
      navigate(piece.lockedRoute)
    } else {
      navigate(piece.route)
    }
  }

  // Loading
  if (loadingCompleteness || loadingBudget) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <LoadingSpinner size="lg" />
          <p className="mt-4 text-gray-500">Caricamento del puzzle...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl px-4 pb-12">
      {/* Confetti */}
      <AnimatePresence>
        {showCelebration && (
          <div className="pointer-events-none fixed inset-0 z-50 overflow-hidden">
            {confettiParticles.map((p) => (
              <ConfettiParticle key={p.id} delay={p.delay} x={p.x} />
            ))}
          </div>
        )}
      </AnimatePresence>

      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8 text-center"
      >
        <div className="mb-2 flex items-center justify-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-sm font-bold text-white">
            AF
          </div>
          <h1 className="text-2xl font-bold text-gray-900">AgentFlow</h1>
          <span className="text-gray-400">&mdash;</span>
          <span className="text-lg text-gray-600">Setup Azienda</span>
        </div>
        <p className="mx-auto max-w-lg text-gray-500">
          Completa il puzzle per avere il controllo completo della tua azienda
        </p>
      </motion.div>

      {/* Progress bar */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className={cn(
          'mb-8 rounded-2xl border-2 bg-white p-5 shadow-sm transition-all duration-500',
          allRequiredActive ? 'border-green-400 shadow-green-100' : 'border-gray-200',
        )}
      >
        <div className="mb-3 flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">Progresso configurazione</span>
          <span className="text-sm font-bold text-gray-900">
            {activeCount}/{totalCount} pezzi attivi
          </span>
        </div>
        <div className="h-3 overflow-hidden rounded-full bg-gray-100">
          <motion.div
            className={cn(
              'h-full rounded-full transition-colors duration-500',
              allRequiredActive ? 'bg-green-500' : 'bg-blue-500',
            )}
            initial={{ width: 0 }}
            animate={{ width: `${progressPct}%` }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
          />
        </div>
        {!allRequiredActive && (
          <p className="mt-2 text-xs text-gray-400">
            I pezzi obbligatori sono:{' '}
            {PUZZLE_PIECES.filter((p) => p.required)
              .map((p) => p.label)
              .join(', ')}
          </p>
        )}
      </motion.div>

      {/* Puzzle Grid */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        <PuzzleGrid
          pieces={PUZZLE_PIECES}
          statuses={pieceStatuses}
          sources={sources}
          onPieceClick={handlePieceClick}
        />
      </motion.div>

      {/* Completion Banner */}
      <AnimatePresence>
        {allRequiredActive && (
          <motion.div
            initial={{ opacity: 0, y: 30, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 30 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="mt-10 overflow-hidden rounded-2xl border-2 border-green-400 bg-gradient-to-br from-green-50 to-emerald-50 p-8 shadow-lg shadow-green-100/50"
          >
            <div className="flex flex-col items-center gap-4 text-center">
              <motion.div
                animate={{ rotate: [0, 10, -10, 0] }}
                transition={{ duration: 0.6, delay: 0.5 }}
              >
                <Sparkles className="h-12 w-12 text-green-500" />
              </motion.div>
              <h2 className="text-2xl font-bold text-green-800">
                La tua azienda e&apos; sotto controllo!
              </h2>
              <p className="max-w-md text-green-700">
                Tutti i pezzi obbligatori del puzzle sono attivi.
                {activeCount < totalCount && (
                  <span>
                    {' '}
                    Puoi comunque collegare i {totalCount - activeCount} pezzi rimanenti per un
                    controllo ancora piu completo.
                  </span>
                )}
              </p>
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => navigate('/dashboard')}
                className="mt-2 inline-flex items-center gap-2 rounded-xl bg-green-600 px-6 py-3 text-base font-semibold text-white shadow-md transition-colors hover:bg-green-700"
              >
                Vai alla Dashboard Gestionale
                <ArrowRight className="h-5 w-5" />
              </motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Not complete hint */}
      {!allRequiredActive && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="mt-8 text-center"
        >
          <p className="text-sm text-gray-400">
            Completa i pezzi obbligatori (Fatture, Banca, Budget) per sbloccare la Dashboard
            Gestionale
          </p>
        </motion.div>
      )}
    </div>
  )
}
