import { useState, useCallback } from 'react'
import { Play, CheckCircle, XCircle, Clock, BarChart3 } from 'lucide-react'
import api from '../api/client'
import PageHeader from '../components/ui/PageHeader'

interface TestPrompt {
  id: string
  category: string
  prompt: string
  context: { page: string; year: number }
  checks: { type: string; value: string }[]
}

interface TestResult {
  id: string
  category: string
  prompt: string
  verdict: 'PASS' | 'FAIL' | 'ERROR' | 'PENDING'
  timeMs: number
  tools: string[]
  hasBlocks: boolean
  content: string
  failedChecks: string[]
}

const TEST_PROMPTS: TestPrompt[] = [
  // KPI (20)
  { id: 'A01', category: 'KPI', prompt: 'qual è il fatturato 2024?', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'contains', value: '4' }, { type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'A02', category: 'KPI', prompt: 'ebitda primo trimestre 2024', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'A03', category: 'KPI', prompt: 'costi 2024', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'contains', value: '106' }] },
  { id: 'A04', category: 'KPI', prompt: 'fatturato 2025', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'A05', category: 'KPI', prompt: 'ricavi di ottobre', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'A06', category: 'KPI', prompt: 'kpi annuali', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'A07', category: 'KPI', prompt: 'quanto ho guadagnato?', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'A08', category: 'KPI', prompt: 'utile netto 2024', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'A09', category: 'KPI', prompt: 'ebitda q2 2024', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'A10', category: 'KPI', prompt: 'entrate e uscite 2024', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'A11', category: 'KPI', prompt: 'margine lordo 2024', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'A12', category: 'KPI', prompt: 'fatturato q3 2024', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'A13', category: 'KPI', prompt: 'costi primo trimestre', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'A14', category: 'KPI', prompt: 'profitto 2024', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'A15', category: 'KPI', prompt: 'guadagno di marzo', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'A16', category: 'KPI', prompt: 'ebitda annuale', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'A17', category: 'KPI', prompt: 'fatturato dicembre 2024', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'A18', category: 'KPI', prompt: 'ricavi febbraio 2024', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'A19', category: 'KPI', prompt: 'costi secondo trimestre 2024', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'A20', category: 'KPI', prompt: 'fatturato q4 2024', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },

  // Top Clienti (15)
  { id: 'B01', category: 'Top', prompt: 'top 5 clienti', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'contains', value: 'NTT' }] },
  { id: 'B02', category: 'Top', prompt: 'classifica fornitori 2024', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'B03', category: 'Top', prompt: 'chi è il mio miglior cliente?', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'B04', category: 'Top', prompt: 'top fornitori', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'B05', category: 'Top', prompt: 'top 3 clienti 2024', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'B06', category: 'Top', prompt: 'top 10 clienti', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'B07', category: 'Top', prompt: 'migliore cliente', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'B08', category: 'Top', prompt: 'principale fornitore', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'B09', category: 'Top', prompt: 'classifica clienti per fatturato', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'B10', category: 'Top', prompt: 'top clienti 2023', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'B11', category: 'Top', prompt: 'miglior cliente 2024', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'B12', category: 'Top', prompt: 'top 5 fornitori 2024', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'B13', category: 'Top', prompt: 'principali clienti', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'B14', category: 'Top', prompt: 'migliori fornitori', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'B15', category: 'Top', prompt: 'top clienti', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },

  // Fatture (15)
  { id: 'C01', category: 'Fatture', prompt: 'fatture NTT Data', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'contains', value: 'NTT' }] },
  { id: 'C02', category: 'Fatture', prompt: 'fattura numero 1/7', context: { page: 'fatture', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'C03', category: 'Fatture', prompt: 'quante fatture ricevute?', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'C04', category: 'Fatture', prompt: 'elenco fatture emesse', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'C05', category: 'Fatture', prompt: 'fatture di gennaio 2024', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: '0 fatture' }] },
  { id: 'C06', category: 'Fatture', prompt: 'quante fatture emesse nel 2024?', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'C07', category: 'Fatture', prompt: 'fatture Engineering', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'contains', value: 'ENGINEERING' }] },
  { id: 'C08', category: 'Fatture', prompt: 'fatture Deloitte', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'contains', value: 'DELOITTE' }] },
  { id: 'C09', category: 'Fatture', prompt: 'fatture Nexa Data', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'contains', value: 'NEXA' }] },
  { id: 'C10', category: 'Fatture', prompt: 'lista fatture marzo 2024', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'C11', category: 'Fatture', prompt: 'quante fatture ho?', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'C12', category: 'Fatture', prompt: 'fatture ricevute febbraio', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'C13', category: 'Fatture', prompt: 'mostra fatture attive', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'C14', category: 'Fatture', prompt: 'conta fatture passive', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'C15', category: 'Fatture', prompt: 'cerca fatture settembre 2024', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },

  // Panoramica (10)
  { id: 'E01', category: 'Panoramica', prompt: 'situazione 2024', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'E02', category: 'Panoramica', prompt: 'come stanno le finanze?', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'E03', category: 'Panoramica', prompt: 'panoramica', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'E04', category: 'Panoramica', prompt: "come va l'azienda?", context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'E05', category: 'Panoramica', prompt: 'riepilogo', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'E06', category: 'Panoramica', prompt: 'come stiamo?', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'E07', category: 'Panoramica', prompt: "stato dell'azienda", context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'E08', category: 'Panoramica', prompt: 'situazione finanziaria', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'E09', category: 'Panoramica', prompt: 'dammi un riepilogo del 2024', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'E10', category: 'Panoramica', prompt: "com'è la situazione?", context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },

  // Edge (10)
  { id: 'H01', category: 'Edge', prompt: 'ciao', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'contains', value: 'iao' }] },
  { id: 'H02', category: 'Edge', prompt: 'grazie', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'contains', value: 'rego' }] },
  { id: 'H03', category: 'Edge', prompt: 'cosa sai fare?', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'H04', category: 'Edge', prompt: 'help', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'H05', category: 'Edge', prompt: "cash flow", context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'H06', category: 'Edge', prompt: 'stato patrimoniale', context: { page: 'contabilita', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'H07', category: 'Edge', prompt: 'scadenze in ritardo', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'H08', category: 'Edge', prompt: 'prossime scadenze', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'H09', category: 'Edge', prompt: 'stato cassetto fiscale', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
  { id: 'H10', category: 'Edge', prompt: 'fatture da verificare', context: { page: 'dashboard', year: 2024 }, checks: [{ type: 'not_contains', value: 'Non ho capito' }] },
]

function runCheck(content: string, check: { type: string; value: string }): boolean {
  if (check.type === 'contains') return content.toLowerCase().includes(check.value.toLowerCase())
  if (check.type === 'not_contains') return !content.includes(check.value)
  return true
}

const CATEGORIES = [...new Set(TEST_PROMPTS.map((t) => t.category))]
const CATEGORY_COLORS: Record<string, string> = {
  KPI: 'bg-blue-100 text-blue-800',
  Top: 'bg-purple-100 text-purple-800',
  Fatture: 'bg-green-100 text-green-800',
  Panoramica: 'bg-amber-100 text-amber-800',
  Edge: 'bg-gray-100 text-gray-800',
}

export default function ChatTestPage() {
  const [results, setResults] = useState<TestResult[]>([])
  const [running, setRunning] = useState(false)
  const [progress, setProgress] = useState(0)

  const runTests = useCallback(async () => {
    setRunning(true)
    setResults([])
    setProgress(0)

    const newResults: TestResult[] = []

    for (let i = 0; i < TEST_PROMPTS.length; i++) {
      const test = TEST_PROMPTS[i]
      setProgress(i + 1)

      const t0 = Date.now()
      try {
        const resp = await api.post('/chat/send', {
          message: test.prompt,
          conversation_id: null,
          context: test.context,
        })
        const elapsed = Date.now() - t0
        const data = resp.data
        const content = data.content ?? ''
        const tools = (data.tool_calls ?? []).map((tc: Record<string, string>) => tc.tool)
        const hasBlocks = !!(data.response_meta?.content_blocks?.length)

        const failedChecks: string[] = []
        for (const check of test.checks) {
          if (!runCheck(content, check)) {
            failedChecks.push(`${check.type}: "${check.value}"`)
          }
        }

        newResults.push({
          id: test.id,
          category: test.category,
          prompt: test.prompt,
          verdict: failedChecks.length === 0 ? 'PASS' : 'FAIL',
          timeMs: elapsed,
          tools,
          hasBlocks,
          content: content.slice(0, 200),
          failedChecks,
        })
      } catch (err) {
        newResults.push({
          id: test.id,
          category: test.category,
          prompt: test.prompt,
          verdict: 'ERROR',
          timeMs: Date.now() - t0,
          tools: [],
          hasBlocks: false,
          content: String(err),
          failedChecks: ['HTTP error'],
        })
      }

      setResults([...newResults])
    }

    setRunning(false)
  }, [])

  const totalPass = results.filter((r) => r.verdict === 'PASS').length
  const totalFail = results.filter((r) => r.verdict !== 'PASS').length
  const avgMs = results.length > 0 ? Math.round(results.reduce((s, r) => s + r.timeMs, 0) / results.length) : 0
  const score = results.length > 0 ? Math.round((totalPass / results.length) * 100) : 0

  // Category stats
  const catStats = CATEGORIES.map((cat) => {
    const catResults = results.filter((r) => r.category === cat)
    const pass = catResults.filter((r) => r.verdict === 'PASS').length
    return { cat, total: TEST_PROMPTS.filter((t) => t.category === cat).length, pass, tested: catResults.length }
  })

  return (
    <div>
      <PageHeader
        title="Chatbot Test Suite"
        subtitle={`${TEST_PROMPTS.length} prompt — verifica qualità ed efficienza`}
        actions={
          <button
            onClick={() => void runTests()}
            disabled={running}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            <Play className="h-4 w-4" />
            {running ? `Test in corso... ${progress}/${TEST_PROMPTS.length}` : 'Esegui Test'}
          </button>
        }
      />

      {/* Score Summary */}
      {results.length > 0 && (
        <div className="mb-6 grid grid-cols-4 gap-4">
          <div className="rounded-lg border bg-white p-4 text-center">
            <p className="text-3xl font-bold text-blue-600">{score}%</p>
            <p className="text-xs text-gray-500">Score</p>
          </div>
          <div className="rounded-lg border bg-white p-4 text-center">
            <p className="text-3xl font-bold text-green-600">{totalPass}</p>
            <p className="text-xs text-gray-500">Pass</p>
          </div>
          <div className="rounded-lg border bg-white p-4 text-center">
            <p className="text-3xl font-bold text-red-600">{totalFail}</p>
            <p className="text-xs text-gray-500">Fail</p>
          </div>
          <div className="rounded-lg border bg-white p-4 text-center">
            <p className="text-3xl font-bold text-gray-700">{avgMs}ms</p>
            <p className="text-xs text-gray-500">Avg Time</p>
          </div>
        </div>
      )}

      {/* Category Progress */}
      {results.length > 0 && (
        <div className="mb-6 flex flex-wrap gap-3">
          {catStats.map(({ cat, total, pass, tested }) => (
            <div key={cat} className="flex items-center gap-2 rounded-lg border bg-white px-3 py-2">
              <BarChart3 className="h-4 w-4 text-gray-400" />
              <span className="text-sm font-medium">{cat}</span>
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                tested === total && pass === total ? 'bg-green-100 text-green-700' :
                tested === total ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600'
              }`}>
                {pass}/{total}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Results Table */}
      {results.length > 0 && (
        <div className="overflow-x-auto rounded-lg border bg-white">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">ID</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Cat</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Prompt</th>
                <th className="px-3 py-2 text-center text-xs font-medium text-gray-500">Verdict</th>
                <th className="px-3 py-2 text-right text-xs font-medium text-gray-500">ms</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Tools</th>
                <th className="px-3 py-2 text-center text-xs font-medium text-gray-500">Blocks</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500">Response</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {results.map((r) => (
                <tr key={r.id} className={r.verdict !== 'PASS' ? 'bg-red-50' : 'hover:bg-gray-50'}>
                  <td className="whitespace-nowrap px-3 py-2 font-mono text-xs">{r.id}</td>
                  <td className="px-3 py-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${CATEGORY_COLORS[r.category] ?? 'bg-gray-100'}`}>
                      {r.category}
                    </span>
                  </td>
                  <td className="px-3 py-2 font-medium text-gray-900">{r.prompt}</td>
                  <td className="px-3 py-2 text-center">
                    {r.verdict === 'PASS' ? (
                      <CheckCircle className="mx-auto h-4 w-4 text-green-500" />
                    ) : (
                      <XCircle className="mx-auto h-4 w-4 text-red-500" />
                    )}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-right font-mono text-xs">
                    <span className={r.timeMs > 2000 ? 'text-amber-600' : 'text-gray-500'}>
                      {r.timeMs}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-xs text-gray-500">{r.tools.join(', ')}</td>
                  <td className="px-3 py-2 text-center text-xs">{r.hasBlocks ? 'Y' : '-'}</td>
                  <td className="max-w-xs truncate px-3 py-2 text-xs text-gray-500" title={r.content}>
                    {r.verdict !== 'PASS' && r.failedChecks.length > 0 ? (
                      <span className="text-red-600">{r.failedChecks.join('; ')}</span>
                    ) : (
                      r.content.slice(0, 80)
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Progress bar while running */}
      {running && (
        <div className="mt-4 flex items-center gap-3">
          <Clock className="h-4 w-4 animate-spin text-blue-500" />
          <div className="flex-1 rounded-full bg-gray-200">
            <div
              className="h-2 rounded-full bg-blue-500 transition-all"
              style={{ width: `${(progress / TEST_PROMPTS.length) * 100}%` }}
            />
          </div>
          <span className="text-sm text-gray-500">{progress}/{TEST_PROMPTS.length}</span>
        </div>
      )}
    </div>
  )
}
