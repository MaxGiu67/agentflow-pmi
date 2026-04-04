import { Link } from 'react-router-dom'
import {
  FileText, CalendarClock, TrendingUp, Briefcase, Target,
  CheckCircle, Shield, Globe, ChevronRight,
} from 'lucide-react'

const PROBLEMS = [
  {
    icon: FileText,
    problem: 'Perdi ore a scaricare fatture dal cassetto fiscale',
    solution: 'Le fatture arrivano da sole. Tu le trovi gia categorizzate.',
    color: 'from-blue-500 to-blue-600',
  },
  {
    icon: CalendarClock,
    problem: 'Le scadenze te le scordi sempre',
    solution: 'Lo scadenzario ti avvisa. Rosso se urgente, verde se tranquillo.',
    color: 'from-amber-500 to-orange-500',
  },
  {
    icon: TrendingUp,
    problem: 'Non sai quanto incasserai il mese prossimo',
    solution: 'Vedi il cash flow a 30, 60, 90 giorni. Con un click.',
    color: 'from-emerald-500 to-green-600',
  },
  {
    icon: Briefcase,
    problem: 'I commerciali usano Excel per i clienti',
    solution: 'Pipeline visuale. Trascini i deal, mandi email, tutto tracciato.',
    color: 'from-purple-500 to-violet-600',
  },
]

export default function LandingPage() {
  return (
    <div className="min-h-[100dvh] bg-white" style={{ fontFamily: 'var(--font-display, system-ui)' }}>

      {/* ── Header ── */}
      <header className="fixed top-0 left-0 right-0 z-50 border-b border-gray-100 bg-white/90 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-purple-600 text-sm font-bold text-white">AF</div>
            <span className="text-lg font-bold text-gray-900">AgentFlow</span>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/login" className="text-sm font-medium text-gray-600 hover:text-gray-900">Accedi</Link>
            <Link to="/register" className="rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 transition-colors">
              Provalo gratis
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero ── */}
      <section className="relative overflow-hidden pt-32 pb-20 sm:pt-40 sm:pb-28">
        <div className="absolute inset-0 bg-gradient-to-br from-purple-50 via-white to-blue-50" />
        <div className="absolute top-20 right-0 h-96 w-96 rounded-full bg-purple-200/30 blur-3xl" />
        <div className="absolute bottom-0 left-0 h-72 w-72 rounded-full bg-blue-200/30 blur-3xl" />

        <div className="relative mx-auto max-w-4xl px-4 text-center sm:px-6">
          <div className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border border-purple-200 bg-purple-50 px-4 py-1.5 text-sm text-purple-700">
            <span className="h-2 w-2 rounded-full bg-purple-500 animate-pulse" />
            Controller aziendale AI per PMI italiane
          </div>

          <h1 className="text-4xl font-extrabold tracking-tight text-gray-900 sm:text-5xl lg:text-6xl" style={{ letterSpacing: '-0.03em' }}>
            Sai sempre come sta<br />
            <span className="bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">la tua azienda.</span>
          </h1>

          <p className="mx-auto mt-6 max-w-2xl text-lg text-gray-500 sm:text-xl">
            Fatture, incassi, scadenze, banca, clienti — tutto in un'app che lavora per te.
            Tu chiedi, l'AI risponde.
          </p>

          <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link to="/register" className="inline-flex items-center gap-2 rounded-xl bg-purple-600 px-8 py-3.5 text-base font-semibold text-white shadow-lg shadow-purple-200 hover:bg-purple-700 transition-all hover:shadow-xl">
              Provalo gratis <ChevronRight className="h-5 w-5" />
            </Link>
            <a href="#come-funziona" className="inline-flex items-center gap-2 rounded-xl border border-gray-200 px-8 py-3.5 text-base font-semibold text-gray-700 hover:bg-gray-50 transition-colors">
              Guarda come funziona
            </a>
          </div>

          <p className="mt-4 text-sm text-gray-400">Nessuna carta di credito. Setup in 2 minuti.</p>
        </div>
      </section>

      {/* ── Problemi → Soluzioni ── */}
      <section id="come-funziona" className="py-20 sm:py-28">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="text-center">
            <h2 className="text-3xl font-bold text-gray-900 sm:text-4xl">I tuoi problemi, risolti.</h2>
            <p className="mt-3 text-lg text-gray-500">Ogni giorno perdi tempo in attivita che l'AI puo fare per te.</p>
          </div>

          <div className="mt-16 grid gap-6 sm:grid-cols-2">
            {PROBLEMS.map((item, i) => (
              <div key={i} className="group relative rounded-2xl border border-gray-200 bg-white p-6 transition-all hover:border-gray-300 hover:shadow-lg">
                <div className={`inline-flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br ${item.color} text-white`}>
                  <item.icon className="h-6 w-6" />
                </div>
                <p className="mt-4 text-sm font-medium text-gray-400 uppercase tracking-wide">Il problema</p>
                <p className="mt-1 text-lg font-semibold text-gray-900">{item.problem}</p>
                <p className="mt-3 text-sm font-medium text-purple-600 uppercase tracking-wide">La soluzione</p>
                <p className="mt-1 text-gray-600">{item.solution}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Numeri/Trust ── */}
      <section className="border-y border-gray-100 bg-gray-50 py-16">
        <div className="mx-auto grid max-w-4xl grid-cols-3 gap-8 px-4 text-center">
          <div>
            <div className="flex items-center justify-center gap-2 text-purple-600"><CheckCircle className="h-6 w-6" /></div>
            <p className="mt-2 text-2xl font-bold text-gray-900">Automatico</p>
            <p className="mt-1 text-sm text-gray-500">Le fatture arrivano da sole dal cassetto fiscale</p>
          </div>
          <div>
            <div className="flex items-center justify-center gap-2 text-purple-600"><Shield className="h-6 w-6" /></div>
            <p className="mt-2 text-2xl font-bold text-gray-900">Sicuro</p>
            <p className="mt-1 text-sm text-gray-500">Dati criptati, GDPR compliant, server in Europa</p>
          </div>
          <div>
            <div className="flex items-center justify-center gap-2 text-purple-600"><Globe className="h-6 w-6" /></div>
            <p className="mt-2 text-2xl font-bold text-gray-900">Italiano</p>
            <p className="mt-1 text-sm text-gray-500">Pensato per la fiscalita italiana: IVA, F24, CU, SDI</p>
          </div>
        </div>
      </section>

      {/* ── Budget ── */}
      <section className="py-20 sm:py-28">
        <div className="mx-auto max-w-6xl px-4 text-center sm:px-6">
          <div className="inline-flex items-center gap-2 text-purple-600 mb-4"><Target className="h-5 w-5" /> <span className="text-sm font-semibold uppercase tracking-wide">Budget vs Consuntivo</span></div>
          <h2 className="text-3xl font-bold text-gray-900 sm:text-4xl">Il commercialista ti manda il bilancio in ritardo?</h2>
          <p className="mt-4 mx-auto max-w-2xl text-lg text-gray-500">
            Con AgentFlow vedi il budget in tempo reale. Mese per mese, voce per voce. Sai sempre se stai spendendo troppo o se puoi investire.
          </p>
        </div>
      </section>



      {/* ── CTA Finale ── */}
      <section className="py-20 sm:py-28">
        <div className="mx-auto max-w-3xl px-4 text-center">
          <h2 className="text-3xl font-bold text-gray-900 sm:text-4xl">Pronto a sapere sempre come sta la tua azienda?</h2>
          <p className="mt-4 text-lg text-gray-500">Setup in 2 minuti. Nessuna carta di credito.</p>
          <Link to="/register" className="mt-8 inline-flex items-center gap-2 rounded-xl bg-purple-600 px-8 py-3.5 text-base font-semibold text-white shadow-lg shadow-purple-200 hover:bg-purple-700">
            Provalo gratis <ChevronRight className="h-5 w-5" />
          </Link>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-gray-200 bg-gray-50 py-10">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-purple-600 text-xs font-bold text-white">AF</div>
              <span className="text-sm font-semibold text-gray-700">AgentFlow PMI</span>
            </div>
            <p className="text-xs text-gray-400">
              Nexa Data srl — P.IVA 12345678901 — Made in Italy
            </p>
            <div className="flex gap-4 text-xs text-gray-400">
              <a href="#" className="hover:text-gray-600">Privacy</a>
              <a href="#" className="hover:text-gray-600">Termini</a>
              <a href="#" className="hover:text-gray-600">Contatti</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
