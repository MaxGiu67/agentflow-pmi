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
  Unlock,
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
    required: true,
  },
  {
    id: 'banca',
    sourceType: 'banca',
    label: 'Banca',
    icon: Landmark,
    route: '/banca',
    lockedRoute: '/import',
    required: true,
  },
  {
    id: 'paghe',
    sourceType: 'paghe',
    label: 'Paghe',
    icon: Users,
    route: '/personale',
    required: false,
  },
  {
    id: 'corrispettivi',
    sourceType: 'corrispettivi',
    label: 'Corrispettivi',
    icon: Receipt,
    route: '/corrispettivi',
    required: false,
  },
  {
    id: 'bilancio',
    sourceType: 'bilancio',
    label: 'Bilancio',
    icon: FileSpreadsheet,
    route: '/import',
    required: false,
  },
  {
    id: 'budget',
    sourceType: 'budget',
    label: 'Budget',
    icon: Target,
    route: '/controller',
    dependsOn: ['fatture'],
    required: true,
  },
]

const REQUIRED_PIECES = PUZZLE_PIECES.filter((p) => p.required).map((p) => p.id)

// ── Helpers ──

function getSubtitle(piece: PuzzlePieceConfig, source: SourceData | undefined, status: PieceStatus): string {
  if (status === 'locked') {
    const deps = piece.dependsOn ?? []
    const depLabels = deps.map((d) => PUZZLE_PIECES.find((p) => p.id === d)?.label ?? d)
    return `Richiede ${depLabels.join(', ')}`
  }
  if (status === 'ready') return 'Da configurare'
  if (status === 'warning') return source?.summary ?? 'Dati non aggiornati'
  // active
  return source?.summary ?? 'Collegato'
}

function resolveStatus(
  piece: PuzzlePieceConfig,
  source: SourceData | undefined,
  activeIds: Set<string>
): PieceStatus {
  // Check dependencies
  if (piece.dependsOn) {
    const unmet = piece.dependsOn.some((dep) => !activeIds.has(dep))
    if (unmet) return 'locked'
  }

  if (!source) return 'ready'

  const s = source.status
  if (s === 'connected' || s === 'active') {
    // Check for staleness
    if (source.last_sync) {
      const daysSinceSync = (Date.now() - new Date(source.last_sync).getTime()) / (1000 * 60 * 60 * 24)
      if (daysSinceSync > 30) return 'warning'
    }
    return 'active'
  }
  if (s === 'warning' || s === 'stale' || s === 'error') return 'warning'
  return 'ready'
}

// ── SVG Puzzle Clip Paths ──

const PUZZLE_PATHS: Record<string, string> = {
  // Top-left: tab right, tab bottom
  'piece-0': `
    M 0,0
    L 60,0 L 60,15 C 60,15 65,10 70,15 C 75,20 75,30 70,35 C 65,40 60,35 60,35 L 60,50
    L 15,50 C 15,50 20,55 15,60 C 10,65 0,65 0,60 C -5,55 0,50 0,50
    L 0,0 Z
  `,
  // Top-center: notch left, tab right, tab bottom
  'piece-1': `
    M 0,0
    L 60,0 L 60,15 C 60,15 65,10 70,15 C 75,20 75,30 70,35 C 65,40 60,35 60,35 L 60,50
    L 15,50 C 15,50 20,55 15,60 C 10,65 0,65 0,60 C -5,55 0,50 0,50
    L 0,35 C 0,35 5,40 10,35 C 15,30 15,20 10,15 C 5,10 0,15 0,15
    L 0,0 Z
  `,
  // Top-right: notch left, tab bottom
  'piece-2': `
    M 0,0
    L 70,0 L 70,50
    L 15,50 C 15,50 20,55 15,60 C 10,65 0,65 0,60 C -5,55 0,50 0,50
    L 0,35 C 0,35 5,40 10,35 C 15,30 15,20 10,15 C 5,10 0,15 0,15
    L 0,0 Z
  `,
  // Bottom-left: tab right, notch top
  'piece-3': `
    M 0,0
    L 15,0 C 15,0 20,-5 15,-10 C 10,-15 0,-15 0,-10 C -5,-5 0,0 0,0
    L 60,0 L 60,15 C 60,15 65,10 70,15 C 75,20 75,30 70,35 C 65,40 60,35 60,35 L 60,50
    L 0,50 L 0,0 Z
  `,
  // Bottom-center: notch left, tab right, notch top
  'piece-4': `
    M 0,0
    L 15,0 C 15,0 20,-5 15,-10 C 10,-15 0,-15 0,-10 C -5,-5 0,0 0,0
    L 60,0 L 60,15 C 60,15 65,10 70,15 C 75,20 75,30 70,35 C 65,40 60,35 60,35 L 60,50
    L 0,50
    L 0,35 C 0,35 5,40 10,35 C 15,30 15,20 10,15 C 5,10 0,15 0,15
    L 0,0 Z
  `,
  // Bottom-right: notch left, notch top
  'piece-5': `
    M 0,0
    L 15,0 C 15,0 20,-5 15,-10 C 10,-15 0,-15 0,-10 C -5,-5 0,0 0,0
    L 70,0 L 70,50
    L 0,50
    L 0,35 C 0,35 5,40 10,35 C 15,30 15,20 10,15 C 5,10 0,15 0,15
    L 0,0 Z
  `,
}

// ── Status Icon Component ──

function StatusIcon({ status }: { status: PieceStatus }) {
  switch (status) {
    case 'locked':
      return <Lock className="h-5 w-5" />
    case 'ready':
      return <Unlock className="h-5 w-5" />
    case 'active':
      return <CheckCircle2 className="h-5 w-5" />
    case 'warning':
      return <AlertTriangle className="h-5 w-5" />
  }
}

// ── Puzzle Piece SVG Background ──

function PuzzlePieceSvg({ index, status }: { index: number; status: PieceStatus }) {
  const path = PUZZLE_PATHS[`piece-${index}`] ?? PUZZLE_PATHS['piece-0']

  const fillColor = (() => {
    switch (status) {
      case 'active': return '#dcfce7'    // green-100
      case 'ready': return '#dbeafe'     // blue-100
      case 'warning': return '#fef3c7'   // amber-100
      case 'locked': return '#f3f4f6'    // gray-100
    }
  })()

  const strokeColor = (() => {
    switch (status) {
      case 'active': return '#4ade80'    // green-400
      case 'ready': return '#60a5fa'     // blue-400
      case 'warning': return '#fbbf24'   // amber-400
      case 'locked': return '#d1d5db'    // gray-300
    }
  })()

  return (
    <svg
      viewBox="-10 -20 90 80"
      className="absolute inset-0 h-full w-full opacity-20 pointer-events-none"
      preserveAspectRatio="none"
    >
      <path d={path} fill={fillColor} stroke={strokeColor} strokeWidth="1.5" />
    </svg>
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

// ── Puzzle Piece Card Component ──

interface PuzzlePieceCardProps {
  piece: PuzzlePieceConfig
  source: SourceData | undefined
  status: PieceStatus
  index: number
  onClick: () => void
}

function PuzzlePieceCard({ piece, source, status, index, onClick }: PuzzlePieceCardProps) {
  const Icon = piece.icon
  const subtitle = getSubtitle(piece, source, status)
  const isClickable = status === 'ready' || status === 'active' || status === 'warning'

  const baseClasses = 'relative overflow-hidden rounded-2xl border-2 p-6 shadow-lg transition-all duration-300'

  const statusClasses: Record<PieceStatus, string> = {
    active: 'bg-green-50 border-green-400 shadow-green-100/50',
    ready: 'bg-blue-50 border-blue-400 cursor-pointer hover:scale-105 hover:shadow-xl',
    locked: 'bg-gray-100 border-gray-300 opacity-60 cursor-not-allowed',
    warning: 'bg-amber-50 border-amber-400 cursor-pointer hover:scale-105 hover:shadow-xl',
  }

  const iconBgClasses: Record<PieceStatus, string> = {
    active: 'bg-green-100 text-green-600',
    ready: 'bg-blue-100 text-blue-600',
    locked: 'bg-gray-200 text-gray-400',
    warning: 'bg-amber-100 text-amber-600',
  }

  const statusIconClasses: Record<PieceStatus, string> = {
    active: 'text-green-500',
    ready: 'text-blue-500',
    locked: 'text-gray-400',
    warning: 'text-amber-500',
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.9 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.4, delay: index * 0.1 }}
      whileHover={isClickable ? { scale: 1.05 } : undefined}
      whileTap={isClickable ? { scale: 0.98 } : undefined}
      className={cn(baseClasses, statusClasses[status])}
      onClick={isClickable ? onClick : undefined}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={isClickable ? (e) => { if (e.key === 'Enter' || e.key === ' ') onClick() } : undefined}
    >
      {/* Puzzle shape background */}
      <PuzzlePieceSvg index={index} status={status} />

      {/* Active glow effect */}
      {status === 'active' && (
        <motion.div
          className="absolute inset-0 rounded-2xl"
          animate={{
            boxShadow: [
              '0 0 0 0 rgba(74, 222, 128, 0)',
              '0 0 20px 4px rgba(74, 222, 128, 0.3)',
              '0 0 0 0 rgba(74, 222, 128, 0)',
            ],
          }}
          transition={{ duration: 2, repeat: Infinity }}
        />
      )}

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center text-center gap-3">
        {/* Icon */}
        <div className={cn('flex h-12 w-12 items-center justify-center rounded-xl', iconBgClasses[status])}>
          <Icon className="h-6 w-6" />
        </div>

        {/* Title row */}
        <div className="flex items-center gap-2">
          <h3 className="text-lg font-bold text-gray-900">{piece.label}</h3>
          {piece.required && (
            <span className="rounded-full bg-gray-200 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-gray-500">
              req
            </span>
          )}
        </div>

        {/* Status icon */}
        <div className={cn('flex items-center gap-1.5', statusIconClasses[status])}>
          <StatusIcon status={status} />
          <span className="text-sm font-medium capitalize">{status === 'active' ? 'Attivo' : status === 'ready' ? 'Pronto' : status === 'locked' ? 'Bloccato' : 'Attenzione'}</span>
        </div>

        {/* Subtitle / summary */}
        <p className="text-sm text-gray-500 leading-tight min-h-[2.5rem]">
          {subtitle}
        </p>

        {/* Action hint on ready/warning */}
        {(status === 'ready' || status === 'warning') && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-1 text-sm font-medium text-blue-600"
          >
            {status === 'ready' ? 'Configura' : 'Verifica'} <ArrowRight className="h-3.5 w-3.5" />
          </motion.div>
        )}

        {status === 'active' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-1 text-sm font-medium text-green-600"
          >
            Vai <ArrowRight className="h-3.5 w-3.5" />
          </motion.div>
        )}
      </div>
    </motion.div>
  )
}

// ── Main Component ──

export default function PuzzleDashboard() {
  const navigate = useNavigate()
  const { data: completenessData, isLoading: loadingCompleteness } = useCompletenessScore()
  const currentYear = new Date().getFullYear()
  const currentMonth = new Date().getMonth() + 1
  const { data: budgetData, isLoading: loadingBudget } = useBudgetVsActual(currentYear, currentMonth)

  const [showCelebration, setShowCelebration] = useState(false)
  const [confettiParticles, setConfettiParticles] = useState<Array<{ id: number; delay: number; x: number }>>([])

  const completeness = completenessData as CompletenessData | undefined
  const sources = completeness?.sources ?? []

  // Build a set of active source IDs
  const activeIds = new Set<string>()
  for (const src of sources) {
    if (src.status === 'connected' || src.status === 'active') {
      activeIds.add(src.source_type)
    }
  }

  // Budget check: if budget data returned successfully, budget is active
  const hasBudget = budgetData != null && typeof budgetData === 'object' && !('detail' in budgetData)
  if (hasBudget) {
    activeIds.add('budget')
  }

  // Resolve statuses for all pieces
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

  // Check if all required pieces are active
  const allRequiredActive = REQUIRED_PIECES.every((id) => {
    const idx = PUZZLE_PIECES.findIndex((p) => p.id === id)
    return idx >= 0 && pieceStatuses[idx] === 'active'
  })

  // Celebration trigger
  const triggerCelebration = useCallback(() => {
    setShowCelebration(true)
    const particles: Array<{ id: number; delay: number; x: number }> = []
    for (let i = 0; i < 40; i++) {
      particles.push({
        id: i,
        delay: Math.random() * 0.8,
        x: Math.random() * 100,
      })
    }
    setConfettiParticles(particles)
  }, [])

  useEffect(() => {
    if (allRequiredActive && !showCelebration) {
      triggerCelebration()
    }
  }, [allRequiredActive, showCelebration, triggerCelebration])

  // Click handlers
  function handlePieceClick(piece: PuzzlePieceConfig, status: PieceStatus) {
    if (status === 'locked') return
    if (status === 'ready' && piece.lockedRoute) {
      navigate(piece.lockedRoute)
    } else {
      navigate(piece.route)
    }
  }

  // ── Loading state ──

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

  // ── Render ──

  return (
    <div className="mx-auto max-w-4xl pb-12">
      {/* Confetti layer */}
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
          <span className="text-gray-400">—</span>
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
          allRequiredActive ? 'border-green-400 shadow-green-100' : 'border-gray-200'
        )}
      >
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-gray-700">Progresso configurazione</span>
          <span className="text-sm font-bold text-gray-900">{activeCount}/{totalCount} pezzi attivi</span>
        </div>
        <div className="h-3 overflow-hidden rounded-full bg-gray-100">
          <motion.div
            className={cn(
              'h-full rounded-full transition-colors duration-500',
              allRequiredActive ? 'bg-green-500' : 'bg-blue-500'
            )}
            initial={{ width: 0 }}
            animate={{ width: `${progressPct}%` }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
          />
        </div>
        {!allRequiredActive && (
          <p className="mt-2 text-xs text-gray-400">
            I pezzi obbligatori sono: {PUZZLE_PIECES.filter((p) => p.required).map((p) => p.label).join(', ')}
          </p>
        )}
      </motion.div>

      {/* Puzzle Grid */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {PUZZLE_PIECES.map((piece, index) => {
          const source = sources.find((s) => s.source_type === piece.sourceType)
          const status = pieceStatuses[index]
          return (
            <PuzzlePieceCard
              key={piece.id}
              piece={piece}
              source={source}
              status={status}
              index={index}
              onClick={() => handlePieceClick(piece, status)}
            />
          )
        })}
      </div>

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
            <div className="flex flex-col items-center text-center gap-4">
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
                  <span> Puoi comunque collegare i {totalCount - activeCount} pezzi rimanenti per un controllo ancora piu completo.</span>
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
            Completa i pezzi obbligatori (Fatture, Banca, Budget) per sbloccare la Dashboard Gestionale
          </p>
        </motion.div>
      )}
    </div>
  )
}
