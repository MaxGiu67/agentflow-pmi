import { motion } from 'framer-motion'

export type OrbState = 'idle' | 'thinking' | 'responding' | 'error'

interface JarvisOrbProps {
  state: OrbState
  size?: number
  className?: string
}

/* ── Gradient & glow configs per state ───────────────────────────── */

const STATE_CONFIG = {
  idle: {
    innerStop: 'var(--orb-idle-inner, #60a5fa)',     // blue-400
    outerStop: 'var(--orb-idle-outer, #22d3ee)',      // cyan-400
    glow: 'var(--orb-idle-glow, rgba(96,165,250,0.4))',
    glowOuter: 'var(--orb-idle-glow-outer, rgba(34,211,238,0.15))',
  },
  thinking: {
    innerStop: 'var(--orb-thinking-inner, #a78bfa)',  // violet-400
    outerStop: 'var(--orb-thinking-outer, #9333ea)',   // purple-600
    glow: 'var(--orb-thinking-glow, rgba(167,139,250,0.5))',
    glowOuter: 'var(--orb-thinking-glow-outer, rgba(147,51,234,0.2))',
  },
  responding: {
    innerStop: 'var(--orb-responding-inner, #34d399)', // emerald-400
    outerStop: 'var(--orb-responding-outer, #22c55e)', // green-500
    glow: 'var(--orb-responding-glow, rgba(52,211,153,0.45))',
    glowOuter: 'var(--orb-responding-glow-outer, rgba(34,197,94,0.15))',
  },
  error: {
    innerStop: 'var(--orb-error-inner, #f87171)',      // red-400
    outerStop: 'var(--orb-error-outer, #fb923c)',      // orange-400
    glow: 'var(--orb-error-glow, rgba(248,113,113,0.5))',
    glowOuter: 'var(--orb-error-glow-outer, rgba(251,146,60,0.2))',
  },
} as const

/* ── Animation variants ──────────────────────────────────────────── */

const orbVariants = {
  idle: {
    scale: [1, 1.08, 1],
    opacity: [0.7, 1, 0.7],
    transition: {
      duration: 3,
      repeat: Infinity,
      ease: 'easeInOut' as const,
    },
  },
  thinking: {
    scale: [1, 1.15, 0.95, 1],
    opacity: [0.8, 1, 0.85, 1],
    transition: {
      duration: 0.8,
      repeat: Infinity,
      ease: 'easeInOut' as const,
    },
  },
  responding: {
    scale: [1, 1.06, 1],
    opacity: [0.85, 1, 0.85],
    transition: {
      duration: 1.8,
      repeat: Infinity,
      ease: 'easeInOut' as const,
    },
  },
  error: {
    scale: [1, 1.1, 1],
    opacity: [0.7, 1, 0.7],
    transition: {
      duration: 1,
      repeat: Infinity,
      ease: 'easeInOut' as const,
    },
  },
}

const ringVariants = {
  idle: {
    scale: [1, 1.3, 1],
    opacity: [0.3, 0, 0.3],
    transition: {
      duration: 3,
      repeat: Infinity,
      ease: 'easeInOut' as const,
    },
  },
  thinking: {
    scale: [1, 1.5, 1],
    opacity: [0.4, 0, 0.4],
    transition: {
      duration: 0.8,
      repeat: Infinity,
      ease: 'easeInOut' as const,
    },
  },
  responding: {
    scale: [1, 1.6],
    opacity: [0.35, 0],
    transition: {
      duration: 1.5,
      repeat: Infinity,
      ease: 'easeOut' as const,
    },
  },
  error: {
    scale: [1, 1.4, 1],
    opacity: [0.3, 0, 0.3],
    transition: {
      duration: 1,
      repeat: Infinity,
      ease: 'easeInOut' as const,
    },
  },
}

/* ── Orbiting dots config ────────────────────────────────────────── */

const DOT_OFFSETS = [0, 120, 240] // degrees apart

function getRotationDuration(state: OrbState): number {
  switch (state) {
    case 'idle': return 6
    case 'thinking': return 1.5
    case 'responding': return 3
    case 'error': return 2
  }
}

/**
 * JarvisOrb — animated SVG orb with state-driven visual feedback.
 *
 * States: idle (blue breathing), thinking (purple rapid pulse),
 * responding (green wave), error (red pulse).
 *
 * Lightweight: SVG + Framer Motion only, no canvas/webgl.
 */
export default function JarvisOrb({ state, size = 40, className }: JarvisOrbProps) {
  const cfg = STATE_CONFIG[state]
  const half = size / 2
  const coreR = size * 0.28
  const midR = size * 0.38
  const outerR = size * 0.46
  const dotOrbitR = size * 0.35
  const dotR = size * 0.04

  const rotDuration = getRotationDuration(state)

  // Unique ID prefix per instance (stable enough for SVG defs)
  const id = `orb-${state}`

  return (
    <motion.div
      className={className}
      style={{
        width: size,
        height: size,
        position: 'relative',
        flexShrink: 0,
      }}
      animate={orbVariants[state]}
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
        style={{ overflow: 'visible' }}
      >
        <defs>
          {/* Core radial gradient */}
          <radialGradient id={`${id}-core`} cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={cfg.innerStop} stopOpacity="1" />
            <stop offset="70%" stopColor={cfg.outerStop} stopOpacity="0.7" />
            <stop offset="100%" stopColor={cfg.outerStop} stopOpacity="0" />
          </radialGradient>
          {/* Middle ring gradient */}
          <radialGradient id={`${id}-mid`} cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={cfg.innerStop} stopOpacity="0.35" />
            <stop offset="100%" stopColor={cfg.outerStop} stopOpacity="0" />
          </radialGradient>
          {/* Outer glow gradient */}
          <radialGradient id={`${id}-outer`} cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={cfg.glow} stopOpacity="0.25" />
            <stop offset="100%" stopColor={cfg.glowOuter} stopOpacity="0" />
          </radialGradient>
          {/* Drop-shadow filter for the core */}
          <filter id={`${id}-shadow`} x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur in="SourceGraphic" stdDeviation={size * 0.08} />
          </filter>
        </defs>

        {/* Outer glow circle */}
        <circle cx={half} cy={half} r={outerR} fill={`url(#${id}-outer)`} />

        {/* Middle ring */}
        <circle cx={half} cy={half} r={midR} fill={`url(#${id}-mid)`} />

        {/* Core bright center */}
        <circle cx={half} cy={half} r={coreR} fill={`url(#${id}-core)`} />

        {/* Shadow layer under core for depth */}
        <circle
          cx={half}
          cy={half}
          r={coreR * 0.6}
          fill={cfg.innerStop}
          opacity="0.5"
          filter={`url(#${id}-shadow)`}
        />
      </svg>

      {/* Expanding ring animation */}
      <motion.div
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: '50%',
          border: `1.5px solid ${cfg.innerStop}`,
        }}
        animate={ringVariants[state]}
      />

      {/* Orbiting dots */}
      <motion.div
        style={{
          position: 'absolute',
          inset: 0,
        }}
        animate={{ rotate: 360 }}
        transition={{
          duration: rotDuration,
          repeat: Infinity,
          ease: 'linear' as const,
        }}
      >
        {DOT_OFFSETS.map((deg) => {
          const rad = (deg * Math.PI) / 180
          const x = half + dotOrbitR * Math.cos(rad) - dotR
          const y = half + dotOrbitR * Math.sin(rad) - dotR
          return (
            <div
              key={deg}
              style={{
                position: 'absolute',
                left: x,
                top: y,
                width: dotR * 2,
                height: dotR * 2,
                borderRadius: '50%',
                backgroundColor: cfg.innerStop,
                opacity: 0.7,
              }}
            />
          )
        })}
      </motion.div>
    </motion.div>
  )
}
