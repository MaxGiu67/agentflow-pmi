import { useEffect, useRef, useCallback } from 'react'

/* ── Types ──────────────────────────────────────────────────────────── */

export type OrbState = 'sleep' | 'idle' | 'thinking' | 'responding' | 'error'
export type JarvisVariant = 'hud-rings' | 'arc-reactor' | 'particle-sphere'

interface JarvisCanvasOrbProps {
  state: OrbState
  size?: number
  variant?: JarvisVariant
  className?: string
  onClick?: () => void
}

/* ── Color & speed configs ──────────────────────────────────────────── */

const COLORS: Record<OrbState, [number, number, number]> = {
  sleep:      [59, 130, 246],   // blue-400 attenuato
  idle:       [59, 130, 246],   // blue-400
  thinking:   [99, 102, 241],   // indigo-400
  responding: [56, 189, 248],   // sky-400
  error:      [248, 113, 113],  // red-400
}

const SPEED: Record<OrbState, number> = {
  sleep: 0.4, idle: 1, thinking: 2.5, responding: 1.4, error: 1.8,
}

const ALPHA_MULT: Record<OrbState, number> = {
  sleep: 0.4, idle: 1, thinking: 1, responding: 1, error: 1,
}

/* ── Drawing functions ──────────────────────────────────────────────── */

function drawHudRings(
  ctx: CanvasRenderingContext2D, w: number, h: number, t: number, state: OrbState,
) {
  const cx = w / 2, cy = h / 2
  const c = COLORS[state]
  const sp = SPEED[state]
  const am = ALPHA_MULT[state]

  ctx.clearRect(0, 0, w, h)

  // Scale rings to canvas size (designed for 100px base)
  const scale = w / 100

  // Center dot
  const cg = ctx.createRadialGradient(cx, cy, 0, cx, cy, 10 * scale)
  cg.addColorStop(0, `rgba(255,255,255,${0.9 * am})`)
  cg.addColorStop(0.5, `rgba(${c},${0.8 * am})`)
  cg.addColorStop(1, `rgba(${c},0)`)
  ctx.beginPath(); ctx.arc(cx, cy, 10 * scale, 0, Math.PI * 2); ctx.fillStyle = cg; ctx.fill()

  // Rotating dashed rings
  const rings = [
    { r: 22, w: 2,   dash: [14, 8],       speed: 1,    opacity: 0.7  },
    { r: 30, w: 1.5, dash: [6, 12],       speed: -1.5, opacity: 0.5  },
    { r: 38, w: 1,   dash: [3, 9],        speed: 0.8,  opacity: 0.35 },
    { r: 44, w: 0.8, dash: [20, 6, 4, 6], speed: -0.5, opacity: 0.2  },
  ]

  for (const ring of rings) {
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(t * ring.speed * sp)
    ctx.beginPath(); ctx.arc(0, 0, ring.r * scale, 0, Math.PI * 2)
    ctx.strokeStyle = `rgba(${c},${ring.opacity * am})`
    ctx.lineWidth = ring.w * scale
    ctx.setLineDash(ring.dash.map(d => d * scale))
    ctx.stroke()
    ctx.restore()
  }

  // Extra fast arc during thinking
  if (state === 'thinking') {
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(t * 3)
    ctx.beginPath(); ctx.arc(0, 0, 26 * scale, 0, 0.8)
    ctx.strokeStyle = `rgba(255,255,255,0.6)`; ctx.lineWidth = 2.5 * scale
    ctx.setLineDash([]); ctx.stroke()
    ctx.restore()
  }
}

function drawArcReactor(
  ctx: CanvasRenderingContext2D, w: number, h: number, t: number, state: OrbState,
) {
  const cx = w / 2, cy = h / 2
  const c = COLORS[state]
  const sp = SPEED[state]
  const am = ALPHA_MULT[state]
  const scale = w / 100

  ctx.clearRect(0, 0, w, h)

  // Outer glow
  const og = ctx.createRadialGradient(cx, cy, 20 * scale, cx, cy, 50 * scale)
  og.addColorStop(0, `rgba(${c},${0.1 * am})`); og.addColorStop(1, `rgba(${c},0)`)
  ctx.beginPath(); ctx.arc(cx, cy, 50 * scale, 0, Math.PI * 2); ctx.fillStyle = og; ctx.fill()

  // Rotating segments
  const segs = 8
  ctx.save(); ctx.translate(cx, cy); ctx.rotate(t * 0.3 * sp)
  for (let i = 0; i < segs; i++) {
    const a = (i / segs) * Math.PI * 2
    const flash = (state === 'thinking' && Math.sin(t * 6 + i * 1.5) > 0.5) ? 1 : 0
    ctx.save(); ctx.rotate(a)
    ctx.beginPath()
    ctx.moveTo(18 * scale, 0)
    ctx.lineTo(28 * scale, -4 * scale)
    ctx.lineTo(28 * scale, 4 * scale)
    ctx.closePath()
    ctx.fillStyle = `rgba(${c},${(0.5 + flash * 0.4) * am})`; ctx.fill()
    ctx.restore()
  }
  ctx.restore()

  // Inner ring
  ctx.beginPath(); ctx.arc(cx, cy, 15 * scale, 0, Math.PI * 2)
  ctx.strokeStyle = `rgba(${c},${0.6 * am})`; ctx.lineWidth = 1.5 * scale; ctx.setLineDash([]); ctx.stroke()

  // Outer dashed ring
  ctx.save(); ctx.translate(cx, cy); ctx.rotate(-t * 0.5 * sp)
  ctx.beginPath(); ctx.arc(0, 0, 32 * scale, 0, Math.PI * 2)
  ctx.strokeStyle = `rgba(${c},${0.3 * am})`; ctx.lineWidth = 1 * scale; ctx.setLineDash([4 * scale, 4 * scale]); ctx.stroke()
  ctx.restore()

  // Core
  const cg = ctx.createRadialGradient(cx, cy, 0, cx, cy, 12 * scale)
  cg.addColorStop(0, `rgba(255,255,255,${0.95 * am})`)
  cg.addColorStop(0.5, `rgba(${c},${0.6 * am})`)
  cg.addColorStop(1, `rgba(${c},0)`)
  ctx.beginPath(); ctx.arc(cx, cy, 12 * scale, 0, Math.PI * 2); ctx.fillStyle = cg; ctx.fill()
}

function drawParticleSphere(
  ctx: CanvasRenderingContext2D, w: number, h: number, t: number, state: OrbState,
) {
  const cx = w / 2, cy = h / 2
  const c = COLORS[state]
  const sp = SPEED[state]
  const am = ALPHA_MULT[state]
  const scale = w / 100

  ctx.clearRect(0, 0, w, h)

  const N = 120
  const R = (32 + Math.sin(t * 1.5 * sp) * 3) * scale
  const golden = (1 + Math.sqrt(5)) / 2
  const pts: { x: number; y: number; z: number; s: number }[] = []

  for (let i = 0; i < N; i++) {
    const theta = Math.acos(1 - 2 * (i + 0.5) / N)
    const phi = 2 * Math.PI * i / golden + t * 0.4 * sp
    const x = R * Math.sin(theta) * Math.cos(phi)
    const z = R * Math.sin(theta) * Math.sin(phi)
    const y = R * Math.cos(theta)
    const s = (z + 60 * scale) / (120 * scale)
    pts.push({ x: cx + x, y: cy + y, z, s })
  }
  pts.sort((a, b) => a.z - b.z)

  // Glow behind
  const bg = ctx.createRadialGradient(cx, cy, 0, cx, cy, R + 10 * scale)
  bg.addColorStop(0, `rgba(${c},${0.06 * am})`); bg.addColorStop(1, `rgba(${c},0)`)
  ctx.beginPath(); ctx.arc(cx, cy, R + 10 * scale, 0, Math.PI * 2); ctx.fillStyle = bg; ctx.fill()

  // Dots
  for (const p of pts) {
    const alpha = (0.15 + p.s * 0.75) * am
    const sz = (0.8 + p.s * 2) * scale
    ctx.beginPath(); ctx.arc(p.x, p.y, sz, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(${c},${alpha.toFixed(2)})`; ctx.fill()
  }
}

const DRAW_FNS: Record<JarvisVariant, typeof drawHudRings> = {
  'hud-rings': drawHudRings,
  'arc-reactor': drawArcReactor,
  'particle-sphere': drawParticleSphere,
}

/* ── Component ──────────────────────────────────────────────────────── */

/**
 * JarvisCanvasOrb — Canvas 2D animated orb with multiple HUD-style variants.
 *
 * Uses requestAnimationFrame for smooth animation. Pauses when document is hidden.
 * Zero dependencies beyond React.
 */
export default function JarvisCanvasOrb({
  state,
  size = 40,
  variant = 'hud-rings',
  className = '',
  onClick,
}: JarvisCanvasOrbProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const stateRef = useRef(state)
  const rafRef = useRef<number>(0)
  const timeRef = useRef(0)

  // Keep state ref in sync for the animation loop
  stateRef.current = state

  const drawFn = DRAW_FNS[variant]

  const startLoop = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // HiDPI support
    const dpr = window.devicePixelRatio || 1
    canvas.width = size * dpr
    canvas.height = size * dpr
    ctx.scale(dpr, dpr)

    let lastTime = performance.now()

    function loop(now: number) {
      const dt = (now - lastTime) / 1000
      lastTime = now
      timeRef.current += dt

      drawFn(ctx!, size, size, timeRef.current, stateRef.current)
      rafRef.current = requestAnimationFrame(loop)
    }

    rafRef.current = requestAnimationFrame(loop)
  }, [size, drawFn])

  useEffect(() => {
    startLoop()

    // Pause when tab hidden
    function onVisChange() {
      if (document.hidden) {
        cancelAnimationFrame(rafRef.current)
      } else {
        startLoop()
      }
    }
    document.addEventListener('visibilitychange', onVisChange)

    return () => {
      cancelAnimationFrame(rafRef.current)
      document.removeEventListener('visibilitychange', onVisChange)
    }
  }, [startLoop])

  return (
    <div
      className={className}
      style={{ width: size, height: size, flexShrink: 0, position: 'relative' }}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      aria-label={onClick ? 'Apri chat AgentFlow' : 'AgentFlow AI'}
      onKeyDown={onClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') onClick() } : undefined}
    >
      <canvas
        ref={canvasRef}
        style={{ width: size, height: size, borderRadius: '50%' }}
      />
    </div>
  )
}
