import { useState, useRef } from 'react'
import { Upload, Plus, X, Receipt } from 'lucide-react'
import { useCorrispettivi, useImportCorrispettivo } from '../../api/hooks'
import api from '../../api/client'
import { useQueryClient } from '@tanstack/react-query'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'
import { formatCurrency, formatDate } from '../../lib/utils'

interface CorrispettivoRow {
  id: string
  data: string
  imponibile: number
  imposta: number
  contanti: number
  elettronico: number
  documenti: number
  source: string
}

const currentYear = new Date().getFullYear()
const currentMonth = new Date().getMonth() + 1

export default function CorrispettiviPage() {
  const [year, setYear] = useState(currentYear)
  const [month, setMonth] = useState(currentMonth)
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    data: '',
    imponibile: '',
    imposta: '',
    contanti: '',
    elettronico: '',
    documenti: '',
  })
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { data, isLoading } = useCorrispettivi(year, month)
  const importXml = useImportCorrispettivo()
  const qc = useQueryClient()

  const rows = (data as CorrispettivoRow[]) ?? (data as { items?: CorrispettivoRow[] })?.items ?? []

  const months = [
    'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
    'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre',
  ]

  const handleImport = () => {
    fileInputRef.current?.click()
  }

  const handleFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    await importXml.mutateAsync(file)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleAddManual = async () => {
    try {
      await api.post('/corrispettivi', {
        data: formData.data,
        imponibile: parseFloat(formData.imponibile) || 0,
        imposta: parseFloat(formData.imposta) || 0,
        contanti: parseFloat(formData.contanti) || 0,
        elettronico: parseFloat(formData.elettronico) || 0,
        documenti: parseInt(formData.documenti) || 0,
      })
      qc.invalidateQueries({ queryKey: ['corrispettivi'] })
      setShowForm(false)
      setFormData({ data: '', imponibile: '', imposta: '', contanti: '', elettronico: '', documenti: '' })
    } catch {
      // Error handling
    }
  }

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader
        title="Corrispettivi"
        subtitle="Registro dei corrispettivi giornalieri"
        actions={
          <div className="flex items-center gap-3">
            <button
              onClick={handleImport}
              disabled={importXml.isPending}
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              <Upload className="h-4 w-4" />
              {importXml.isPending ? 'Importazione...' : 'Importa XML'}
            </button>
            <button
              onClick={() => setShowForm(!showForm)}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              {showForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
              {showForm ? 'Chiudi' : 'Aggiungi manuale'}
            </button>
          </div>
        }
      />

      <input
        ref={fileInputRef}
        type="file"
        accept=".xml"
        className="hidden"
        onChange={handleFileSelected}
      />

      {/* Filters */}
      <div className="mb-4 flex gap-3">
        <select
          value={month}
          onChange={(e) => setMonth(Number(e.target.value))}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          {months.map((m, i) => (
            <option key={i} value={i + 1}>{m}</option>
          ))}
        </select>
        <select
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          {[currentYear - 1, currentYear, currentYear + 1].map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>

      {/* Inline form */}
      {showForm && (
        <Card className="mb-4">
          <h3 className="mb-3 font-medium text-gray-900">Nuovo corrispettivo</h3>
          <div className="grid gap-3 sm:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Data</label>
              <input
                type="date"
                value={formData.data}
                onChange={(e) => setFormData({ ...formData, data: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Imponibile</label>
              <input
                type="number"
                step="0.01"
                value={formData.imponibile}
                onChange={(e) => setFormData({ ...formData, imponibile: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                placeholder="0.00"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Imposta</label>
              <input
                type="number"
                step="0.01"
                value={formData.imposta}
                onChange={(e) => setFormData({ ...formData, imposta: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                placeholder="0.00"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Contanti</label>
              <input
                type="number"
                step="0.01"
                value={formData.contanti}
                onChange={(e) => setFormData({ ...formData, contanti: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                placeholder="0.00"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Elettronico</label>
              <input
                type="number"
                step="0.01"
                value={formData.elettronico}
                onChange={(e) => setFormData({ ...formData, elettronico: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                placeholder="0.00"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">N. documenti</label>
              <input
                type="number"
                value={formData.documenti}
                onChange={(e) => setFormData({ ...formData, documenti: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                placeholder="0"
              />
            </div>
          </div>
          <div className="mt-4 flex gap-3">
            <button
              onClick={handleAddManual}
              className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
            >
              Salva
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Annulla
            </button>
          </div>
        </Card>
      )}

      {/* Table */}
      {isLoading ? (
        <LoadingSpinner className="py-12" />
      ) : rows.length > 0 ? (
        <Card className="!p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-200 bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Data</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Imponibile</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Imposta</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Contanti</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Elettronico</th>
                  <th className="px-4 py-3 text-right font-medium text-gray-600">Documenti</th>
                  <th className="px-4 py-3 text-left font-medium text-gray-600">Fonte</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {rows.map((row) => (
                  <tr key={row.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-900">{formatDate(row.data)}</td>
                    <td className="px-4 py-3 text-right text-gray-700">{formatCurrency(row.imponibile)}</td>
                    <td className="px-4 py-3 text-right text-gray-700">{formatCurrency(row.imposta)}</td>
                    <td className="px-4 py-3 text-right text-gray-700">{formatCurrency(row.contanti)}</td>
                    <td className="px-4 py-3 text-right text-gray-700">{formatCurrency(row.elettronico)}</td>
                    <td className="px-4 py-3 text-right text-gray-700">{row.documenti}</td>
                    <td className="px-4 py-3">
                      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                        {row.source}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        <EmptyState
          icon={<Receipt className="h-12 w-12" />}
          title="Nessun corrispettivo trovato"
          description={`Nessun corrispettivo per ${months[month - 1]} ${year}. Importa un file XML o aggiungine uno manualmente.`}
        />
      )}
    </div>
  )
}
