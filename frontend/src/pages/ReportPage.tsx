import { useState } from 'react'
import { Download, FileText } from 'lucide-react'
import api from '../api/client'
import PageHeader from '../components/ui/PageHeader'
import Card from '../components/ui/Card'

export default function ReportPage() {
  const currentYear = new Date().getFullYear()
  const [period, setPeriod] = useState(`Q1-${currentYear}`)
  const [format, setFormat] = useState('pdf')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState('')

  const periods = [
    `Q1-${currentYear}`,
    `Q2-${currentYear}`,
    `Q3-${currentYear}`,
    `Q4-${currentYear}`,
    `H1-${currentYear}`,
    `H2-${currentYear}`,
    `FY-${currentYear}`,
    `FY-${currentYear - 1}`,
  ]

  const handleGenerate = async () => {
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const { data } = await api.get('/reports/commercialista', { params: { period, format } })
      setResult(data)
    } catch (err: unknown) {
      setError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          'Errore nella generazione del report'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Report"
        subtitle="Generazione report per il commercialista"
      />

      <Card className="mb-6 max-w-xl">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Genera report</h2>

        <div className="flex flex-wrap gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-500">Periodo</label>
            <select
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="mt-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            >
              {periods.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-500">Formato</label>
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value)}
              className="mt-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="pdf">PDF</option>
              <option value="csv">CSV</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={handleGenerate}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              <FileText className="h-4 w-4" />
              {loading ? 'Generazione...' : 'Genera'}
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>
        )}
      </Card>

      {result && (
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Report generato</h3>
              <p className="mt-1 text-sm text-gray-500">
                Periodo: {String(result.period ?? '')} - Formato: {String(result.format ?? '').toUpperCase()}
              </p>
            </div>
            {result.download_url != null && (
              <a
                href={result.download_url as string}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
              >
                <Download className="h-4 w-4" />
                Scarica
              </a>
            )}
          </div>

          {result.summary != null && (
            <div className="mt-4 rounded-lg bg-gray-50 p-4">
              <h4 className="mb-2 text-sm font-medium text-gray-700">Riepilogo</h4>
              <pre className="text-xs text-gray-600">
                {typeof result.summary === 'string'
                  ? result.summary
                  : JSON.stringify(result.summary, null, 2)}
              </pre>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
