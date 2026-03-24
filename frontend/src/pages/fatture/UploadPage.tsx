import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, CheckCircle, AlertTriangle, FolderOpen } from 'lucide-react'
import { useUploadInvoice } from '../../api/hooks'
import api from '../../api/client'
import PageHeader from '../../components/ui/PageHeader'
import FileUpload from '../../components/ui/FileUpload'
import Card from '../../components/ui/Card'

export default function UploadPage() {
  const navigate = useNavigate()
  const uploadMutation = useUploadInvoice()
  const [files, setFiles] = useState<File[]>([])
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState('')

  // Folder import state
  const [folderPath, setFolderPath] = useState('')
  const [folderLoading, setFolderLoading] = useState(false)
  const [folderResult, setFolderResult] = useState<{
    total_files: number; imported: number; duplicates: number; errors: number
  } | null>(null)

  const handleUpload = async () => {
    if (files.length === 0) return

    setUploadStatus('idle')
    setErrorMessage('')

    try {
      for (const file of files) {
        const formData = new FormData()
        formData.append('file', file)
        await uploadMutation.mutateAsync(formData)
      }
      setUploadStatus('success')
      setTimeout(() => navigate('/fatture'), 2000)
    } catch (err: unknown) {
      setUploadStatus('error')
      setErrorMessage(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          'Errore durante il caricamento'
      )
    }
  }

  const handleFolderImport = async () => {
    if (!folderPath.trim()) return
    setFolderLoading(true)
    setFolderResult(null)
    setErrorMessage('')

    try {
      const { data } = await api.post('/invoices/import-folder', { folder_path: folderPath.trim() })
      setFolderResult(data)
      if (data.imported > 0) {
        setUploadStatus('success')
      }
    } catch (err: unknown) {
      setErrorMessage(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          'Errore importazione cartella'
      )
      setUploadStatus('error')
    } finally {
      setFolderLoading(false)
    }
  }

  return (
    <div>
      <PageHeader
        title="Carica Fatture"
        subtitle="Carica fatture singole o importa da una cartella"
      />

      <div className="grid gap-6 lg:grid-cols-2 max-w-4xl">
        {/* Upload singolo file */}
        <Card>
          <h2 className="mb-4 text-lg font-semibold text-gray-900">Carica file</h2>
          <p className="mb-4 text-sm text-gray-500">Trascina o seleziona file XML, PDF o P7M</p>

          {uploadStatus === 'success' && !folderResult ? (
            <div className="flex flex-col items-center py-8 text-center">
              <CheckCircle className="mb-4 h-16 w-16 text-green-500" />
              <h3 className="text-lg font-semibold text-gray-900">Caricamento completato!</h3>
              <button
                onClick={() => navigate('/fatture')}
                className="mt-4 text-sm text-blue-600 hover:underline"
              >
                Vai alle fatture
              </button>
            </div>
          ) : (
            <>
              {uploadStatus === 'error' && !folderResult && (
                <div className="mb-4 flex items-center gap-2 rounded-lg bg-red-50 p-3">
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                  <span className="text-sm text-red-700">{errorMessage}</span>
                </div>
              )}

              <FileUpload onFileSelect={setFiles} multiple accept=".xml,.pdf,.p7m" />

              <div className="mt-4 flex justify-end">
                <button
                  onClick={handleUpload}
                  disabled={files.length === 0 || uploadMutation.isPending}
                  className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  <Upload className="h-4 w-4" />
                  {uploadMutation.isPending ? 'Caricamento...' : `Carica (${files.length} file)`}
                </button>
              </div>
            </>
          )}
        </Card>

        {/* Import da cartella */}
        <Card>
          <h2 className="mb-4 text-lg font-semibold text-gray-900">
            <FolderOpen className="inline h-5 w-5 mr-2" />
            Importa da cartella
          </h2>
          <p className="mb-4 text-sm text-gray-500">
            Inserisci il percorso di una cartella contenente fatture XML scaricate dal cassetto fiscale
          </p>

          {folderResult ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-500" />
                <span className="text-sm font-semibold text-gray-900">Importazione completata</span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg bg-blue-50 p-3 text-center">
                  <p className="text-2xl font-bold text-blue-700">{folderResult.total_files}</p>
                  <p className="text-xs text-blue-600">File trovati</p>
                </div>
                <div className="rounded-lg bg-green-50 p-3 text-center">
                  <p className="text-2xl font-bold text-green-700">{folderResult.imported}</p>
                  <p className="text-xs text-green-600">Importati</p>
                </div>
                <div className="rounded-lg bg-amber-50 p-3 text-center">
                  <p className="text-2xl font-bold text-amber-700">{folderResult.duplicates}</p>
                  <p className="text-xs text-amber-600">Duplicati</p>
                </div>
                <div className="rounded-lg bg-red-50 p-3 text-center">
                  <p className="text-2xl font-bold text-red-700">{folderResult.errors}</p>
                  <p className="text-xs text-red-600">Errori</p>
                </div>
              </div>
              <button
                onClick={() => navigate('/fatture')}
                className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Vai alle fatture
              </button>
              <button
                onClick={() => { setFolderResult(null); setUploadStatus('idle') }}
                className="w-full text-sm text-gray-500 hover:underline"
              >
                Importa un'altra cartella
              </button>
            </div>
          ) : (
            <>
              {uploadStatus === 'error' && !files.length && (
                <div className="mb-4 flex items-center gap-2 rounded-lg bg-red-50 p-3">
                  <AlertTriangle className="h-5 w-5 text-red-500" />
                  <span className="text-sm text-red-700">{errorMessage}</span>
                </div>
              )}

              <input
                type="text"
                value={folderPath}
                onChange={(e) => setFolderPath(e.target.value)}
                placeholder="/percorso/cartella/fatture"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
              <p className="mt-1 text-xs text-gray-400">
                Verranno importati tutti i file .xml (esclusi i metadati)
              </p>

              <div className="mt-4 flex justify-end">
                <button
                  onClick={handleFolderImport}
                  disabled={!folderPath.trim() || folderLoading}
                  className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  <FolderOpen className="h-4 w-4" />
                  {folderLoading ? 'Importazione...' : 'Importa cartella'}
                </button>
              </div>
            </>
          )}
        </Card>
      </div>
    </div>
  )
}
