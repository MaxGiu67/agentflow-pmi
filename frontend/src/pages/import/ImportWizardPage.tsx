import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Landmark, FileText, Calculator, Receipt, Users, CheckCircle2 } from 'lucide-react'
import {
  useBankAccounts,
  useImportBankStatement,
  useImportBankCsv,
  useImportCorrispettivo,
  useImportBilancio,
  useConfirmBilancio,
  useImportF24Pdf,
} from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import FileUpload from '../../components/ui/FileUpload'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import { formatCurrency } from '../../lib/utils'

type TabId = 'banca' | 'corrispettivi' | 'bilancio' | 'f24' | 'paghe'

interface TabDef {
  id: TabId
  label: string
  icon: React.ReactNode
  accept: string
  description: string
}

const tabs: TabDef[] = [
  { id: 'banca', label: 'Banca', icon: <Landmark className="h-4 w-4" />, accept: '.pdf,.csv', description: 'Importa estratto conto PDF o CSV' },
  { id: 'corrispettivi', label: 'Corrispettivi', icon: <Receipt className="h-4 w-4" />, accept: '.xml', description: 'Importa file XML corrispettivi' },
  { id: 'bilancio', label: 'Bilancio', icon: <FileText className="h-4 w-4" />, accept: '.csv,.pdf,.xbrl', description: 'Importa bilancio CSV, PDF o XBRL' },
  { id: 'f24', label: 'F24', icon: <Calculator className="h-4 w-4" />, accept: '.pdf', description: 'Importa modello F24 da PDF' },
  { id: 'paghe', label: 'Paghe', icon: <Users className="h-4 w-4" />, accept: '', description: 'Gestione import paghe e personale' },
]

export default function ImportWizardPage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<TabId>('banca')
  const [selectedAccountId, setSelectedAccountId] = useState<string>('')
  const [previewData, setPreviewData] = useState<Record<string, unknown>[] | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const { data: bankAccounts } = useBankAccounts()
  const importStatement = useImportBankStatement()
  const importCsv = useImportBankCsv()
  const importCorrispettivi = useImportCorrispettivo()
  const importBilancio = useImportBilancio()
  const confirmBilancio = useConfirmBilancio()
  const importF24 = useImportF24Pdf()

  const accountsRaw = bankAccounts as { items?: { id: string; bank_name: string; iban: string }[] } | { id: string; bank_name: string; iban: string }[] | undefined
  const accounts = Array.isArray(accountsRaw) ? accountsRaw : (accountsRaw?.items ?? [])

  const resetState = () => {
    setPreviewData(null)
    setSuccessMessage(null)
  }

  const handleTabChange = (tab: TabId) => {
    setActiveTab(tab)
    resetState()
  }

  const handleBancaUpload = async (files: File[]) => {
    if (!files[0] || !selectedAccountId) return
    resetState()
    const file = files[0]
    const isCsv = file.name.toLowerCase().endsWith('.csv')
    try {
      const result = isCsv
        ? await importCsv.mutateAsync({ accountId: selectedAccountId, file })
        : await importStatement.mutateAsync({ accountId: selectedAccountId, file })
      const r = result as Record<string, unknown>
      const items = (r.movements ?? r.transactions ?? r.preview ?? []) as Record<string, unknown>[]
      if (Array.isArray(items) && items.length > 0) {
        setPreviewData(items)
      } else {
        setSuccessMessage(`Importazione completata! ${r.movements_count ?? r.count ?? 0} movimenti estratti.`)
      }
    } catch {
      // Error handled by React Query
    }
  }

  const handleCorrispettiviUpload = async (files: File[]) => {
    if (!files[0]) return
    resetState()
    try {
      const result = await importCorrispettivi.mutateAsync(files[0])
      setSuccessMessage(`Importazione completata! ${(result as { count?: number })?.count ?? 0} corrispettivi importati.`)
    } catch {
      // Error handled by React Query
    }
  }

  const handleBilancioUpload = async (files: File[]) => {
    if (!files[0]) return
    resetState()
    try {
      const result = await importBilancio.mutateAsync(files[0])
      const lines = (result as { lines?: Record<string, unknown>[] })?.lines ?? []
      if (lines.length > 0) {
        setPreviewData(lines)
      } else {
        setSuccessMessage('Bilancio importato correttamente.')
      }
    } catch {
      // Error handled by React Query
    }
  }

  const handleConfirmBilancio = async () => {
    if (!previewData) return
    try {
      await confirmBilancio.mutateAsync({ lines: previewData })
      setPreviewData(null)
      setSuccessMessage('Bilancio confermato e registrato correttamente.')
    } catch {
      // Error handled by React Query
    }
  }

  const handleF24Upload = async (files: File[]) => {
    if (!files[0]) return
    resetState()
    try {
      const result = await importF24.mutateAsync(files[0])
      setSuccessMessage(`F24 importato correttamente! Importo totale: ${formatCurrency((result as { total?: number })?.total ?? 0)}`)
    } catch {
      // Error handled by React Query
    }
  }

  const isPending =
    importStatement.isPending ||
    importCsv.isPending ||
    importCorrispettivi.isPending ||
    importBilancio.isPending ||
    confirmBilancio.isPending ||
    importF24.isPending

  const currentError =
    importStatement.error || importCsv.error || importCorrispettivi.error || importBilancio.error || importF24.error

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader
        title="Importa dati"
        subtitle="Carica i tuoi documenti e li elaboriamo noi"
      />

      {/* Tabs */}
      <div className="mb-6 flex gap-1 overflow-x-auto rounded-xl border border-gray-200 bg-gray-50 p-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => {
              if (tab.id === 'paghe') {
                navigate('/personale/gestione-import')
              } else {
                handleTabChange(tab.id)
              }
            }}
            className={`flex items-center gap-2 whitespace-nowrap rounded-lg px-4 py-2 text-sm font-medium transition ${
              activeTab === tab.id
                ? 'bg-white text-blue-700 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <Card>
        <p className="mb-4 text-sm text-gray-600">
          {tabs.find((t) => t.id === activeTab)?.description}
        </p>

        {/* Bank account selector for Banca tab */}
        {activeTab === 'banca' && (
          <div className="mb-4">
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Seleziona conto bancario
            </label>
            <select
              value={selectedAccountId}
              onChange={(e) => setSelectedAccountId(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">-- Seleziona --</option>
              {accounts.map((acc) => (
                <option key={acc.id} value={acc.id}>
                  {acc.bank_name} - {acc.iban}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* File upload area */}
        {activeTab !== 'paghe' && (
          <FileUpload
            accept={tabs.find((t) => t.id === activeTab)?.accept ?? ''}
            onFileSelect={(files) => {
              if (activeTab === 'banca') handleBancaUpload(files)
              else if (activeTab === 'corrispettivi') handleCorrispettiviUpload(files)
              else if (activeTab === 'bilancio') handleBilancioUpload(files)
              else if (activeTab === 'f24') handleF24Upload(files)
            }}
          />
        )}

        {/* Loading */}
        {isPending && (
          <div className="mt-6 flex items-center gap-3">
            <LoadingSpinner size="sm" />
            <p className="text-sm text-gray-600">Elaborazione in corso...</p>
          </div>
        )}

        {/* Error */}
        {currentError && (
          <div className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">
            Si e verificato un errore durante l&apos;importazione. Verifica il file e riprova.
          </div>
        )}

        {/* Success */}
        {successMessage && (
          <div className="mt-4 flex items-center gap-2 rounded-lg bg-green-50 p-3 text-sm text-green-700">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            {successMessage}
          </div>
        )}

        {/* Preview table */}
        {previewData && previewData.length > 0 && (
          <div className="mt-6">
            <h3 className="mb-2 font-medium text-gray-900">Anteprima dati</h3>
            <div className="overflow-x-auto rounded-lg border border-gray-200">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    {Object.keys(previewData[0]).map((key) => (
                      <th key={key} className="px-3 py-2 text-left font-medium text-gray-600">
                        {key}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {previewData.slice(0, 10).map((row, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      {Object.values(row).map((val, j) => (
                        <td key={j} className="px-3 py-2 text-gray-700">
                          {String(val ?? '')}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {previewData.length > 10 && (
              <p className="mt-1 text-xs text-gray-400">
                Mostrate 10 di {previewData.length} righe
              </p>
            )}
            <div className="mt-4 flex gap-3">
              <button
                onClick={activeTab === 'bilancio' ? handleConfirmBilancio : () => setPreviewData(null)}
                className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
              >
                Conferma importazione
              </button>
              <button
                onClick={() => setPreviewData(null)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Annulla
              </button>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
