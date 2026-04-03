# Analisi Frontend AgentFlow PMI — Roadmap PWA Responsive

> Data: 2026-04-03
> Obiettivo: portare il frontend a una Progressive Web App responsive, con design system moderno

---

## 1. STATO ATTUALE

### Stack Tecnologico

| Componente | Versione | Status |
|-----------|---------|--------|
| React | **19.2.4** | Ultimo — StrictMode attivo |
| TypeScript | **5.9.3** | Strict mode, noUnusedLocals |
| Vite | **8.0.1** | Fast HMR, ES modules |
| Tailwind CSS | **4.2.2** | Zero-config via @tailwindcss/vite |
| React Router | **7.13.2** | Client-side, nested routes |
| React Query | **5.95.1** | Data fetching, staleTime 30s |
| Framer Motion | **12.38.0** | Animazioni Toast e Chat |
| Zustand | **5.0.12** | Auth store, AI blocks store |
| Recharts | **3.8.0** | Grafici dashboard |
| React Hook Form | **7.72.0** | + Zod 4.3.6 validazione |
| Lucide React | **1.0.1** | 1200+ icone SVG |

### Numeri del Progetto

| Metrica | Valore |
|---------|--------|
| Pagine | **48+** |
| Routes | **42** |
| API hooks | **100+** |
| UI components | **13** |
| Bundle size (build) | **~1.27 MB** (uncompressed), ~348 KB gzipped |
| Sezioni sidebar | **5** (Principale, Operativo, Commerciale, Gestione, Sistema) |

---

## 2. AUDIT RESPONSIVE

### Cosa funziona

| Area | Status | Note |
|------|--------|------|
| Sidebar | OK | Overlay mobile con z-50, chiude su click |
| Header | OK | Menu hamburger su mobile |
| Grid layout | Parziale | Tailwind grid-cols responsive |
| Tabelle | Parziale | overflow-x-auto ma colonne non ottimizzate |
| Form | Parziale | Stacking verticale su mobile |
| Kanban CRM | OK | Scroll orizzontale + dropdown mobile |
| Dashboard widgets | Parziale | react-grid-layout non ottimale su mobile |

### Problemi critici

| Problema | Impatto | Priorita |
|----------|---------|----------|
| **Tabelle non responsive** | Colonne tagliate su < 768px | Alta |
| **Dashboard widget grid fissa** | Non riadatta su mobile, richiede scroll | Alta |
| **Form CreateInvoice troppo largo** | Campi non stacking corretto | Media |
| **Nessun bottom navigation mobile** | Sidebar overlay non e il pattern mobile standard | Alta |
| **Font system-ui generico** | Nessuna identita tipografica | Media |
| **Nessun safe area per notch/gesture** | iPhone X+ taglia contenuto | Media |
| **Toast posizionato male su mobile** | Copre contenuto in basso | Bassa |

---

## 3. AUDIT PWA

### Stato attuale: NON PWA

| Requisito PWA | Status | Azione |
|---------------|--------|--------|
| **manifest.json** | Mancante | Creare con name, icons, theme_color, start_url |
| **Service Worker** | Mancante | Implementare con Workbox (vite-plugin-pwa) |
| **Icons (192x192, 512x512)** | Mancante | Generare da logo AF |
| **theme-color meta** | Mancante | Aggiungere in index.html |
| **apple-touch-icon** | Mancante | Aggiungere 180x180 |
| **HTTPS** | OK | Railway serve su HTTPS |
| **Offline support** | Mancante | Cache API responses + shell |
| **Install prompt** | Mancante | beforeinstallprompt handler |
| **Push notifications** | Mancante | Web Push API + backend |
| **Background sync** | Mancante | Per offline form submission |

### Lighthouse Score stimato attuale

| Metrica | Score stimato | Target |
|---------|--------------|--------|
| Performance | ~65 | 90+ |
| Accessibility | ~70 | 95+ |
| Best Practices | ~80 | 95+ |
| SEO | ~60 | 90+ |
| PWA | ~20 | 100 |

---

## 4. AUDIT REACT 19 FEATURES

### Feature React 19 utilizzabili

| Feature | Status | Beneficio |
|---------|--------|-----------|
| **React Compiler** | Non attivo | Auto-memoizzazione, elimina useMemo/useCallback manuali |
| **use() hook** | Non usato | Leggere Promise/Context direttamente nel render |
| **Server Components** | N/A (SPA) | Non applicabile con Vite SPA |
| **Actions (useActionState)** | Non usato | Form submission con pending state nativo |
| **useOptimistic** | Non usato | Ottimistic UI per Kanban drag-drop |
| **useTransition** | Non usato | Navigazione smooth senza blocking |
| **Suspense boundaries** | Non usato | Skeleton loading per pagine |
| **Lazy loading (React.lazy)** | Non usato | Code splitting per route |
| **ref as prop** | Non usato | Semplifica forwardRef |
| **Metadata (title, meta)** | Non usato | `<title>` dinamico per pagina |

---

## 5. ROADMAP IMPLEMENTAZIONE

### Fase 1: PWA Foundation (1 sprint)

**Obiettivo:** Installabile come app, offline shell, Lighthouse PWA 100

```
1.1 Installare vite-plugin-pwa
    npm install -D vite-plugin-pwa

1.2 Creare manifest.json
    - name: "AgentFlow PMI"
    - short_name: "AgentFlow"
    - start_url: "/"
    - display: "standalone"
    - theme_color: "#2563EB" (blue-600)
    - background_color: "#F9FAFB"
    - icons: 192x192, 512x512, maskable

1.3 Configurare Service Worker (Workbox)
    - Strategie:
      - NetworkFirst per API /api/v1/*
      - StaleWhileRevalidate per assets (JS, CSS, fonts)
      - CacheFirst per immagini/icone
    - Precache: app shell (index.html, main JS, main CSS)
    - Offline fallback page

1.4 Aggiornare index.html
    - <meta name="theme-color" content="#2563EB">
    - <meta name="apple-mobile-web-app-capable" content="yes">
    - <link rel="apple-touch-icon" href="/icons/icon-180.png">
    - <link rel="manifest" href="/manifest.json">

1.5 Install prompt UX
    - Banner "Installa AgentFlow" con beforeinstallprompt
    - Dismissabile, non intrusivo
```

### Fase 2: Responsive Excellence (2 sprint)

**Obiettivo:** Mobile-first perfetto su tutti i breakpoint

```
2.1 Bottom Navigation Mobile
    - Su viewport < lg: bottom tab bar (5 icone)
    - Dashboard, Fatture, CRM, Chat, Menu (...)
    - Sidebar resta per desktop
    - Pattern: YouTube/Instagram mobile nav

2.2 Tabelle Responsive
    - Pattern "card on mobile": su < md trasforma tabella in card stack
    - Componente ResponsiveTable che wrappa DataTable
    - Priority columns: solo 2-3 colonne su mobile, espandi con tap

2.3 Dashboard Mobile
    - Su mobile: layout verticale singola colonna
    - Widget impilati, non griglia
    - Swipe tra widget (carousel)
    - Pull-to-refresh nativo

2.4 Form Mobile
    - Full-width inputs
    - Floating labels
    - Keyboard-aware scroll
    - Step wizard per form complessi (CreateInvoice → 4 step)

2.5 Safe Areas
    - env(safe-area-inset-top/bottom) per iPhone notch
    - Padding bottom per bottom nav
    - Touch targets: minimo 44x44px

2.6 Kanban Mobile
    - Swipe orizzontale tra stage (snap scroll)
    - Long-press per spostare card (no drag)
    - Full-screen card detail
```

### Fase 3: React 19 Optimization (1 sprint)

**Obiettivo:** Performance top, code splitting, smooth transitions

```
3.1 React.lazy + Suspense per route
    - Ogni pagina caricata on-demand
    - Skeleton loading durante il caricamento
    - Riduzione bundle iniziale del ~60%

    const DashboardPage = lazy(() => import('./pages/DashboardPage'))
    <Suspense fallback={<PageSkeleton />}>
      <Route path="/dashboard" element={<DashboardPage />} />
    </Suspense>

3.2 useTransition per navigazione
    - Navigazione non blocca UI
    - Loading indicator subtile (progress bar top)
    - isPending → NProgress-like bar

3.3 useOptimistic per Kanban
    - Drag-drop mostra stato ottimistico immediato
    - Rollback automatico se API fallisce
    - No spinner, feedback istantaneo

3.4 React Compiler (se stabile)
    - Abilitare babel-plugin-react-compiler
    - Rimuovere useMemo/useCallback manuali
    - Build-time optimization

3.5 Metadata per pagina
    - <title> dinamico: "Dashboard — AgentFlow PMI"
    - <meta description> per SEO internal

3.6 Error Boundaries globali
    - ErrorBoundary component con retry
    - Sentry/LogRocket integration (opzionale)
```

### Fase 4: Design System (1 sprint)

**Obiettivo:** Identita visiva forte, non "generic Tailwind"

```
4.1 Typography
    - Display font: "DM Sans" o "Plus Jakarta Sans" (Google Fonts, gratuito)
    - Body font: "Inter" per leggibilita (gia nel sistema)
    - Monospace: "JetBrains Mono" per codici/numeri
    - Scale tipografico: xs(11), sm(13), base(15), lg(17), xl(20), 2xl(24), 3xl(30)

4.2 Color System
    - CSS variables in :root per theming
    - Primary: Blue-600 (#2563EB) — gia in uso
    - Success: Emerald-500 (#10B981)
    - Warning: Amber-500 (#F59E0B)
    - Error: Rose-500 (#F43F5E)
    - Neutral: Slate scale (non gray)
    - Dark mode ready: prefers-color-scheme media query

4.3 Component Library Upgrade
    - Card → con varianti (default, outlined, elevated, glass)
    - Button → sizes (xs, sm, md, lg), variants (primary, secondary, ghost, danger)
    - Input → con floating label, error state, helper text
    - Select → custom dropdown con search
    - Modal → con animazione slide-up su mobile
    - Drawer → slide-in da destra per dettagli
    - Skeleton → loading placeholder per ogni componente
    - Avatar → iniziali o immagine, sizes
    - Tooltip → hover/touch info
    - Progress → bar e circular per upload/loading

4.4 Motion System
    - Transizioni pagina: fade + slide (Framer Motion + AnimatePresence)
    - Micro-interazioni: button press scale, hover lift
    - Loading: skeleton shimmer, non spinner
    - Success: confetti o checkmark animato
    - Page transitions: staggered content reveal

4.5 Iconografia
    - Lucide gia OK, aggiungere custom SVG per brand
    - Logo animato per splash screen
    - Empty state illustrations (SVG custom o Undraw)

4.6 Dark Mode
    - CSS custom properties per tutti i colori
    - Toggle in header (sole/luna)
    - Persistenza in localStorage
    - Auto-detect sistema (prefers-color-scheme)
```

### Fase 5: Offline & Advanced PWA (1 sprint)

**Obiettivo:** Funzionalita offline reale, push notifications

```
5.1 Offline Data
    - IndexedDB per cache dati critici (fatture, contatti, scadenze)
    - Background sync per form submission offline
    - Queue operazioni offline → sync quando online
    - Indicator online/offline nella UI

5.2 Push Notifications
    - Web Push API (VAPID keys)
    - Backend: endpoint /push/subscribe, /push/send
    - Notifiche per: scadenze in arrivo, deal cambiato stage, email aperta
    - Permission request non intrusivo (dopo 3 sessioni)

5.3 Share API
    - Condivisione report/fatture via Web Share API
    - Share button su fatture, report, deal

5.4 Badging API
    - Badge su icona app per notifiche non lette
    - Contatore scadenze in scadenza

5.5 Splash Screen
    - Animated logo durante caricamento
    - Skeleton dell'app shell
    - Transizione fluida a contenuto reale
```

---

## 6. DIPENDENZE DA AGGIUNGERE

| Pacchetto | Versione | Motivo |
|-----------|---------|--------|
| `vite-plugin-pwa` | ^0.21 | Service worker + manifest generation |
| `workbox-precaching` | ^7 | Strategie cache avanzate |
| `@fontsource/dm-sans` | latest | Typography display |
| `@fontsource/jetbrains-mono` | latest | Typography monospace |
| `idb-keyval` | ^6 | IndexedDB wrapper per offline |

### Dipendenze da rimuovere (pulizia)

| Pacchetto | Motivo |
|-----------|--------|
| `react-grid-layout` | Sostituire con CSS Grid + drag nativo (piu leggero) |

---

## 7. STIMA EFFORT

| Fase | Sprint | SP | Note |
|------|--------|-----|------|
| 1. PWA Foundation | 1 | 8 | manifest, SW, icons, install prompt |
| 2. Responsive Excellence | 2 | 21 | bottom nav, tabelle, form wizard, safe areas |
| 3. React 19 Optimization | 1 | 13 | lazy loading, transitions, optimistic |
| 4. Design System | 1 | 13 | typography, colors, components, dark mode |
| 5. Offline & Push | 1 | 13 | IndexedDB, push, share, badge |
| **TOTALE** | **6 sprint** | **68 SP** | |

---

## 8. PRIORITA IMPLEMENTAZIONE

### Must Have (Sprint 1-2)

1. **PWA manifest + service worker** — l'app deve essere installabile
2. **Bottom navigation mobile** — pattern standard per app mobile
3. **Tabelle responsive** — dati leggibili su ogni viewport
4. **React.lazy + Suspense** — riduzione bundle 60%
5. **Safe areas iOS** — contenuto non tagliato

### Should Have (Sprint 3-4)

6. **Design system con CSS variables** — dark mode ready
7. **Typography personalizzata** — identita visiva
8. **Form wizard mobile** — step-by-step per form complessi
9. **Skeleton loading** — al posto degli spinner
10. **useOptimistic per Kanban** — feedback istantaneo

### Could Have (Sprint 5-6)

11. **Offline data con IndexedDB** — funzionalita offline reale
12. **Push notifications** — scadenze e deal
13. **Dark mode** — toggle manuale + auto
14. **Page transitions animate** — polish UX
15. **Share API** — condivisione nativa

---

## 9. METRICHE DI SUCCESSO

| Metrica | Attuale | Target |
|---------|---------|--------|
| Lighthouse Performance | ~65 | **90+** |
| Lighthouse Accessibility | ~70 | **95+** |
| Lighthouse PWA | ~20 | **100** |
| First Contentful Paint | ~2.5s | **< 1.0s** |
| Largest Contentful Paint | ~4.0s | **< 2.0s** |
| Cumulative Layout Shift | ~0.15 | **< 0.05** |
| Time to Interactive | ~3.5s | **< 2.0s** |
| Bundle size (initial) | 1.27 MB | **< 200 KB** (con lazy) |
| Mobile usability score | N/A | **100** |

---

_Documento generato: 2026-04-03_
_Prossimo step: implementare Fase 1 (PWA Foundation)_
