# 17 — BotOrb Component Specification

> Specifica per il componente BotOrb di AgentFlow: orb animato con tema Siri (CSS) e Jarvis (Canvas), selezionabile da impostazioni.

## 1. Overview

Il chatbot AgentFlow utilizza un avatar animato (orb) che comunica visivamente lo stato del bot. L'utente puo scegliere tra due temi:

- **Siri Orb** — Pure CSS con `conic-gradient`, `@property`, blur/contrast. Zero JS per il rendering. Ispirato a SmoothUI (MIT license).
- **Jarvis HUD** — Canvas 2D con anelli rotanti tratteggiati, segmenti arc-reactor, sfera particelle. Zero dipendenze.

Entrambi i temi condividono la stessa API React e gli stessi stati.

## 2. UX Flow

### 2.1 Stato Riposo (FAB)

```
+------------------------------------------------------+
|                    Pagina app                         |
|                                                       |
|                                                       |
|                                          [Orb 58px]  |  <-- FAB fixed bottom-right
+------------------------------------------------------+
```

- Orb fluttuante `position: fixed; bottom: 28px; right: 28px`
- Colori attenuati (sleep state), animazione lenta (35s)
- Hover: `scale(1.1)` con `cubic-bezier(0.34, 1.56, 0.64, 1)`
- Glow sottile dietro l'orb con `filter: blur(14px); opacity: 0.3`
- Breathing animation: pulsazione 3s opacity 0.2 → 0.35

### 2.2 Transizione FAB → Chatbar

1. Click su FAB
2. FAB si nasconde con `opacity: 0; transform: scale(0.5)` (0.3s)
3. Overlay appare `background: rgba(0,0,0,0.4); backdrop-filter: blur(4px)` (0.35s)
4. Chatbar appare dal basso `translateY(100px) → translateY(0)` con spring bezier (0.4s)
5. Auto-focus su input field dopo 350ms

### 2.3 Stato Attivo (Chatbar)

```
+------------------------------------------------------+
|                    Pagina app (overlay blur)           |
|                                                       |
|     +-------- RESPONSE PANEL (opzionale) ---------+   |
|     |  [Orb 20px] AgentFlow AI    [X]             |   |
|     |  Testo risposta...                           |   |
|     +---------------------------------------------+   |
|                                                       |
|     +===== CHATBAR con bordo Siri animato ========+   |
|     | [Orb 38px]  [    Input field    ]  [Send]   |   |
|     +==============================================+   |
|     |  [chip1]  [chip2]  [chip3]                  |   |
+------------------------------------------------------+
```

- Chatbar centered: `left: 50%; transform: translateX(-50%); bottom: 24px`
- Width: `min(600px, calc(100vw - 32px))`
- Bordo animato (solo tema Siri): `conic-gradient` rotante con `mask-composite: exclude`
- Orb mini (38px) a sinistra dell'input
- Suggestion chips sotto la chatbar

### 2.4 Chiusura

- Click su overlay → chiude chatbar, torna FAB
- Escape key → chiude chatbar
- Transizione inversa: chatbar slide-down, overlay fade-out, FAB scale-up (0.2s delay)

## 3. Stati del Bot

| Stato | Trigger | Orb | Border (Siri) | Durata animazione |
|---|---|---|---|---|
| **sleep** | Chat chiusa (FAB) | Colori attenuati, rotazione 35s | N/A | Lenta |
| **idle** | Chat aperta, in attesa | Colori normali, rotazione 20s | Azzurro tenue, rotazione 8s, opacity 0.5 | Media |
| **thinking** | Dopo invio messaggio | Colori intensi viola, rotazione 4s | Viola brillante, rotazione 2s, opacity 0.9 | Veloce |
| **responding** | Risposta in arrivo | Colori verde-acqua, rotazione 10s | Verde, rotazione 5s, opacity 0.7 | Calma |
| **error** | Errore API | Rosso-arancio, pulse 1s | Rosso, pulse rapido | Urgente |

## 4. Tema Siri — Implementazione CSS

### 4.1 Tecnica Core

Il Siri Orb usa 6 `conic-gradient` sovrapposti su pseudo-elementi `::before` e `::after` con `@property --angle` per animare la rotazione GPU-accelerated.

```css
@property --angle {
  syntax: "<angle>";
  inherits: false;
  initial-value: 0deg;
}

.siri-orb::before {
  background:
    conic-gradient(from calc(var(--angle) * 2) at 25% 70%, var(--c3), transparent 20% 80%, var(--c3)),
    conic-gradient(from calc(var(--angle) * 2) at 45% 75%, var(--c2), transparent 30% 60%, var(--c2)),
    conic-gradient(from calc(var(--angle) * -3) at 80% 20%, var(--c1), transparent 40% 60%, var(--c1)),
    conic-gradient(from calc(var(--angle) * 2) at 15% 5%, var(--c2), transparent 10% 90%, var(--c2)),
    conic-gradient(from calc(var(--angle) * 1) at 20% 80%, var(--c1), transparent 10% 90%, var(--c1)),
    conic-gradient(from calc(var(--angle) * -2) at 85% 10%, var(--c3), transparent 20% 80%, var(--c3));
  filter: blur(var(--blur)) contrast(var(--contrast));
  animation: orb-spin var(--orb-speed) linear infinite;
}

.siri-orb::after {
  backdrop-filter: blur(calc(var(--blur) * 2)) contrast(calc(var(--contrast) * 2));
  mix-blend-mode: overlay;
  mask-image: radial-gradient(black 15%, transparent 75%);
}

@keyframes orb-spin { to { --angle: 360deg; } }
```

### 4.2 Bordo Animato Chatbar

Il bordo usa la tecnica `mask-composite: exclude` per rendere visibile solo il bordo di un conic-gradient:

```css
@property --border-angle {
  syntax: "<angle>";
  inherits: false;
  initial-value: 0deg;
}

.chatbar-border::before {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: 22px;
  padding: 2px;
  background: conic-gradient(
    from var(--border-angle),
    var(--bc1) 0%, var(--bc2) 25%, var(--bc3) 50%, var(--bc1) 75%, var(--bc2) 100%
  );
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  animation: border-spin var(--border-speed) linear infinite;
}

.chatbar-border::after {
  /* Outer glow: stesso gradient, blur 20px, opacity bassa */
  filter: blur(20px);
  opacity: var(--glow-opacity);
  z-index: -1;
}

@keyframes border-spin { to { --border-angle: 360deg; } }
```

### 4.3 Palette Colori per Stato (oklch, bassa saturazione)

```typescript
const SIRI_COLORS = {
  sleep: {
    bg: 'oklch(14% 0.005 220)', c1: 'oklch(40% 0.04 220)',
    c2: 'oklch(35% 0.04 210)',  c3: 'oklch(38% 0.03 230)',
    blur: '1.5px', contrast: 1.2, speed: '35s'
  },
  idle: {
    bg: 'oklch(22% 0.01 220)',  c1: 'oklch(65% 0.08 220)',
    c2: 'oklch(60% 0.10 210)',  c3: 'oklch(58% 0.07 230)',
    blur: '2px', contrast: 1.4, speed: '20s'
  },
  thinking: {
    bg: 'oklch(18% 0.02 240)',  c1: 'oklch(60% 0.12 250)',
    c2: 'oklch(55% 0.14 270)',  c3: 'oklch(62% 0.10 230)',
    blur: '2px', contrast: 1.5, speed: '4s'
  },
  responding: {
    bg: 'oklch(20% 0.01 180)',  c1: 'oklch(65% 0.09 180)',
    c2: 'oklch(60% 0.08 195)',  c3: 'oklch(68% 0.07 165)',
    blur: '2px', contrast: 1.4, speed: '10s'
  },
  error: {
    bg: 'oklch(18% 0.02 25)',   c1: 'oklch(60% 0.15 25)',
    c2: 'oklch(55% 0.12 35)',   c3: 'oklch(58% 0.10 15)',
    blur: '2px', contrast: 1.5, speed: '2s'
  }
}
```

### 4.4 Palette Bordo per Stato

```typescript
const SIRI_BORDER = {
  idle: {
    bc1: 'rgba(125,211,252,0.35)', bc2: 'rgba(165,180,252,0.25)',
    bc3: 'rgba(110,231,183,0.2)',  speed: '8s', opacity: 0.5, glow: 0.06
  },
  thinking: {
    bc1: 'rgba(165,180,252,0.75)', bc2: 'rgba(192,132,252,0.65)',
    bc3: 'rgba(125,211,252,0.55)', speed: '2s', opacity: 0.9, glow: 0.15
  },
  responding: {
    bc1: 'rgba(110,231,183,0.55)', bc2: 'rgba(125,211,252,0.45)',
    bc3: 'rgba(165,180,252,0.35)', speed: '5s', opacity: 0.7, glow: 0.1
  },
  error: {
    bc1: 'rgba(248,113,113,0.7)',  bc2: 'rgba(251,146,60,0.6)',
    bc3: 'rgba(248,113,113,0.5)',  speed: '1.5s', opacity: 0.85, glow: 0.12
  }
}
```

## 5. Tema Jarvis — Implementazione Canvas 2D

### 5.1 Varianti Disponibili

Sono state testate 8 varianti. Le raccomandate per AgentFlow:

1. **HUD Rings** (default) — Anelli concentrici rotanti con tratteggio, center dot luminoso
2. **Arc Reactor** — Segmenti triangolari attorno a core, stile Iron Man
3. **Particle Sphere** — 120 punti distribuiti su sfera 3D (Fibonacci), rotazione lenta

### 5.2 Colori per Stato

```typescript
const JARVIS_COLORS = {
  idle:       [59, 130, 246],   // blue-400
  thinking:   [99, 102, 241],   // indigo-400
  responding: [56, 189, 248],   // sky-400
  error:      [248, 113, 113],  // red-400
}

const JARVIS_SPEED = {
  idle: 1, thinking: 2.5, responding: 1.4, error: 1.8
}
```

### 5.3 Rendering HUD Rings (Principale)

```typescript
function drawHudRings(ctx: CanvasRenderingContext2D, w: number, h: number, t: number, state: OrbState) {
  const cx = w/2, cy = h/2
  const c = JARVIS_COLORS[state]
  const sp = JARVIS_SPEED[state]

  ctx.clearRect(0, 0, w, h)

  // Center dot con radial gradient
  const cg = ctx.createRadialGradient(cx, cy, 0, cx, cy, 10)
  cg.addColorStop(0, `rgba(255,255,255,0.9)`)
  cg.addColorStop(0.5, `rgba(${c},0.8)`)
  cg.addColorStop(1, `rgba(${c},0)`)
  ctx.beginPath(); ctx.arc(cx, cy, 10, 0, Math.PI*2); ctx.fillStyle = cg; ctx.fill()

  // 4 anelli rotanti con dash pattern diversi
  const rings = [
    { r: 22, w: 2,   dash: [14, 8],        speed: 1,    opacity: 0.7  },
    { r: 30, w: 1.5, dash: [6, 12],        speed: -1.5, opacity: 0.5  },
    { r: 38, w: 1,   dash: [3, 9],         speed: 0.8,  opacity: 0.35 },
    { r: 44, w: 0.8, dash: [20, 6, 4, 6],  speed: -0.5, opacity: 0.2  },
  ]

  rings.forEach(ring => {
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(t * ring.speed * sp)
    ctx.beginPath(); ctx.arc(0, 0, ring.r, 0, Math.PI*2)
    ctx.strokeStyle = `rgba(${c},${ring.opacity})`
    ctx.lineWidth = ring.w
    ctx.setLineDash(ring.dash)
    ctx.stroke()
    ctx.restore()
  })

  // Extra: arco bianco rapido durante thinking
  if (state === 'thinking') {
    ctx.save(); ctx.translate(cx, cy); ctx.rotate(t * 3)
    ctx.beginPath(); ctx.arc(0, 0, 26, 0, 0.8)
    ctx.strokeStyle = 'rgba(255,255,255,0.6)'; ctx.lineWidth = 2.5
    ctx.setLineDash([]); ctx.stroke()
    ctx.restore()
  }
}
```

### 5.4 Rendering via requestAnimationFrame

```typescript
useEffect(() => {
  let time = 0
  let rafId: number

  function loop() {
    time += 0.016 // ~60fps
    drawHudRings(ctx, canvas.width, canvas.height, time, state)
    rafId = requestAnimationFrame(loop)
  }

  loop()
  return () => cancelAnimationFrame(rafId)
}, [state])
```

## 6. Component API

### 6.1 BotOrb (componente wrapper)

```typescript
// components/chat/BotOrb.tsx

export type OrbState = 'sleep' | 'idle' | 'thinking' | 'responding' | 'error'
export type OrbTheme = 'siri' | 'jarvis'

interface BotOrbProps {
  state: OrbState
  size?: number            // default: 40
  theme?: OrbTheme         // default: da settings store
  className?: string
  onClick?: () => void
}

export default function BotOrb({ state, size = 40, theme, className, onClick }: BotOrbProps) {
  const activeTheme = theme ?? useSettingsStore(s => s.orbTheme)

  if (activeTheme === 'siri') {
    return <SiriOrb state={state} size={size} className={className} onClick={onClick} />
  }
  return <JarvisOrb state={state} size={size} className={className} onClick={onClick} />
}
```

### 6.2 SiriOrb (nuovo)

```typescript
// components/chat/SiriOrb.tsx

interface SiriOrbProps {
  state: OrbState
  size?: number
  className?: string
  onClick?: () => void
}

// Rendering: div con CSS custom properties, ::before e ::after via styled/CSS module
// Cambio stato: aggiorna le CSS custom properties (--c1, --c2, --c3, --bg, --blur, etc.)
// Animazione: keyframe @property --angle gestita dal browser (GPU-accelerated)
```

### 6.3 JarvisCanvasOrb (nuovo, rinomina dell'attuale)

```typescript
// components/chat/JarvisCanvasOrb.tsx

interface JarvisCanvasOrbProps {
  state: OrbState
  size?: number
  variant?: 'hud-rings' | 'arc-reactor' | 'particle-sphere'
  className?: string
  onClick?: () => void
}

// Rendering: <canvas> con requestAnimationFrame
// Cambio stato: aggiorna colori e velocita nel loop
```

## 7. Struttura File

```
frontend/src/components/chat/
  BotOrb.tsx               # Wrapper che sceglie il tema
  SiriOrb.tsx              # Tema Siri (CSS conic-gradient)
  SiriOrb.module.css       # Stili CSS con @property e keyframes
  JarvisCanvasOrb.tsx      # Tema Jarvis (Canvas 2D)
  JarvisOrb.tsx            # [ESISTENTE] SVG orb — mantenuto come fallback/legacy
  ChatbotFloating.tsx       # [MODIFICA] Usa BotOrb al posto di JarvisOrb
```

## 8. Integrazione Settings

### 8.1 Store (Zustand)

```typescript
// store/settings.ts (o aggiungere al settings store esistente)

interface SettingsState {
  orbTheme: OrbTheme     // 'siri' | 'jarvis'
  setOrbTheme: (theme: OrbTheme) => void
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      orbTheme: 'siri',  // default
      setOrbTheme: (theme) => set({ orbTheme: theme }),
    }),
    { name: 'agentflow-settings' }
  )
)
```

### 8.2 UI Impostazioni

Nella pagina Impostazioni, sezione "Aspetto":

```
Tema Avatar Bot
  ○ Siri Orb — Sfere colorate fluide (CSS)     [preview orb]
  ● Jarvis HUD — Anelli rotanti stile HUD      [preview orb]
```

- Preview live dell'orb selezionato (stato idle, size 60px)
- Cambio immediato senza reload
- Persistenza in localStorage via Zustand persist

## 9. Integrazione in ChatbotFloating.tsx

### 9.1 Modifiche Necessarie

1. **Import**: Sostituire `JarvisOrb` con `BotOrb`
2. **FAB State**: Aggiungere gestione apertura/chiusura (overlay, FAB hidden, chatbar visible)
3. **Orb Instances**: 3 istanze di BotOrb
   - FAB orb: `size={58}` `state="sleep"` — nel bottone fluttuante
   - Chatbar orb: `size={38}` `state={orbState}` — nell'input bar
   - Response orb: `size={20}` `state={orbState}` — nell'header risposta
4. **Bordo Siri**: Wrappare chatbar in `<SiriBorder state={orbState} />` (solo se tema Siri)
5. **Overlay**: Aggiungere div overlay con click-to-close
6. **Keyboard**: Escape per chiudere, Ctrl+Space per aprire (gia presente)

### 9.2 Layout Nuovo

```tsx
return (
  <>
    {/* Overlay */}
    <AnimatePresence>
      {chatOpen && (
        <motion.div className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
          onClick={closeChat} />
      )}
    </AnimatePresence>

    {/* FAB (sleep) */}
    <AnimatePresence>
      {!chatOpen && (
        <motion.div className="fixed bottom-7 right-7 z-50 cursor-pointer"
          onClick={openChat}
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}>
          <BotOrb state="sleep" size={58} />
        </motion.div>
      )}
    </AnimatePresence>

    {/* Chatbar (active) */}
    <AnimatePresence>
      {chatOpen && (
        <motion.div className="fixed bottom-6 left-1/2 z-50 w-[min(600px,calc(100vw-32px))]"
          style={{ x: '-50%' }}
          initial={{ opacity: 0, y: 100 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 100 }}>

          {/* Response Panel */}
          {showResponse && <ResponsePanel ... />}

          {/* Input Bar con bordo animato */}
          <SiriBorder state={orbState} enabled={theme === 'siri'}>
            <div className="flex items-center gap-3 p-3 bg-slate-950/95 rounded-xl backdrop-blur-xl">
              <BotOrb state={orbState} size={38} />
              <input ref={inputRef} ... />
              <button onClick={handleSubmit}>
                <Send />
              </button>
            </div>
          </SiriBorder>

          {/* Chips */}
          <SuggestionChips ... />
        </motion.div>
      )}
    </AnimatePresence>
  </>
)
```

## 10. Performance

### 10.1 Siri Orb
- **Rendering**: Pure CSS, GPU-accelerated via `@property` e `will-change`
- **Costo**: ~0% CPU (tutto su compositor thread)
- **Size**: ~3KB CSS module
- **Compatibilita**: Chrome 85+, Safari 15.4+, Firefox 128+ (per `@property`)
- **Fallback**: Se `@property` non supportata, orb statico con colori corretti ma senza rotazione

### 10.2 Jarvis Canvas
- **Rendering**: `requestAnimationFrame` a 60fps, ma solo quando visibile
- **Costo**: ~1-2% CPU (un solo canvas piccolo)
- **Size**: ~4KB JS
- **Ottimizzazione**: `cancelAnimationFrame` su unmount, pause se `document.hidden`

### 10.3 Accessibilita
- `prefers-reduced-motion: reduce` → disabilita tutte le animazioni
- `aria-label` su FAB e orb
- Focus management: auto-focus input all'apertura, focus-trap nella chatbar

## 11. Riferimenti

- **SmoothUI Siri Orb** — https://github.com/educlopez/smoothui (MIT) — Tecnica conic-gradient
- **Demo SiriChatFAB.html** — `/Gestione_azienda/SiriChatFAB.html` — Prototipo completo FAB→Chatbar
- **Demo SiriChatBar.html** — `/Gestione_azienda/SiriChatBar.html` — Chatbar con bordo animato
- **Demo JarvisBot.html** — `/Gestione_azienda/JarvisBot.html` — 8 varianti Jarvis Canvas
- **JarvisOrb.tsx attuale** — Implementazione SVG+Framer Motion esistente (legacy)
- **Brainstorm UI** — `/brainstorm/16-chatbot-ui-brainstorm.md` — Analisi UX iniziale
