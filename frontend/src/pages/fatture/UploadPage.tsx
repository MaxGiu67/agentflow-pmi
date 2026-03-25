import { useState, useRef } from 'react'
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
  const folderInputRef = useRef<HTMLInputElement>(null)
  const [folderFiles, setFolderFiles] = useState<File[]>([])
  const [folderLoading, setFolderLoading] = useState(false)
  const [folderProgress, setFolderProgress] = useState({ current: 0, total: 0 })
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
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Errore durante il caricamento'
      )
    }
  }

  const handleFolderSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files
    if (!fileList) return

    // Filter only XML files, exclude metaDato
    const xmlFiles = Array.from(fileList).filter(
      f => f.name.endsWith('.xml') && !f.name.includes('metaDato')
    )

    setFolderFiles(xmlFiles)
    setFolderResult(null)
    setErrorMessage('')
  }

  const handleFolderImport = async () => {
    if (folderFiles.length === 0) return
    setFolderLoading(true)
    setFolderResult(null)
    setErrorMessage('')

    let imported = 0
    let duplicates = 0
    let errors = 0
    const total = folderFiles.length

    for (let i = 0; i < folderFiles.length; i++) {
      const file = folderFiles[i]
      setFolderProgress({ current: i + 1, total })

      try {
        const formData = new FormData()
        formData.append('file', file)
        const { data } = await api.post('/invoices/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })

        if (data.message?.toLowerCase().includes('duplicata')) {
          duplicates++
        } else {
          imported++
        }
      } catch {
        errors++
      }
    }

    setFolderResult({ total_files: total, imported, duplicates, errors })
    setFolderLoading(false)
  }

  return (
    <div>
      <PageHeader
        title="Carica Fatture"
        subtitle="Carica fatture singole o importa un'intera cartella"
      />

      <div className="grid gap-6 lg:grid-cols-2 max-w-4xl">
        {/* Upload singolo file */}
        <Card>
          <h2 className="mb-4 text-lg font-semibold text-gray-900">
            <Upload className="inline h-5 w-5 mr-2" />
            Carica file
          </h2>
          <p className="mb-4 text-sm text-gray-500">Trascina o seleziona file XML, PDF, P7M</p>

          {uploadStatus === 'success' && !folderResult ? (
            <div className="flex flex-col items-center py-8 text-center">
              <CheckCircle className="mb-4 h-16 w-16 text-green-500" />
              <h3 className="text-lg font-semibold text-gray-900">Caricamento completato!</h3>
              <button onClick={() => navigate('/fatture')} className="mt-4 text-sm text-blue-600 hover:underline">
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
            Seleziona una cartella contenente fatture XML (es. scaricate dal cassetto fiscale)
          </p>

          {/* Hidden directory input */}
          <input
            ref={folderInputRef}
            type="file"
            /* @ts-expect-error webkitdirectory is non-standard but widely supported */
            webkitdirectory=""
            directory=""
            multiple
            className="hidden"
            onChange={handleFolderSelect}
          />

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
                onClick={() => { setFolderResult(null); setFolderFiles([]); setUploadStatus('idle') }}
                className="w-full text-sm text-gray-500 hover:underline"
              >
                Importa un'altra cartella
              </button>
            </div>
          ) : folderLoading ? (
            <div className="space-y-3 py-4">
              <div className="flex items-center justify-center gap-2 text-sm text-blue-600">
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
                Importazione in corso...
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-gray-200">
                <div
                  className="h-full rounded-full bg-blue-600 transition-all"
                  style={{ width: `${folderProgress.total > 0 ? (folderProgress.current / folderProgress.total) * 100 : 0}%` }}
                />
              </div>
              <p className="text-center text-xs text-gray-500">
                {folderProgress.current} / {folderProgress.total} file
              </p>
            </div>
          ) : folderFiles.length > 0 ? (
            <div className="space-y-3">
              <div className="rounded-lg border border-blue-200 bg-blue-50 p-3">
                <p className="text-sm font-medium text-blue-800">
                  {folderFiles.length} file XML trovati nella cartella
                </p>
                <p className="mt-1 text-xs text-blue-600">
                  File metadati esclusi automaticamente
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleFolderImport}
                  className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                >
                  <Upload className="h-4 w-4" />
                  Importa {folderFiles.length} fatture
                </button>
                <button
                  onClick={() => { setFolderFiles([]); if (folderInputRef.current) folderInputRef.current.value = '' }}
                  className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Annulla
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => folderInputRef.current?.click()}
              className="w-full rounded-xl border-2 border-dashed border-gray-300 p-8 text-center hover:border-blue-400 hover:bg-blue-50 transition-colors"
            >
              <FolderOpen className="mx-auto mb-3 h-12 w-12 text-gray-400" />
              <p className="text-sm font-medium text-gray-700">Seleziona cartella</p>
              <p className="mt-1 text-xs text-gray-500">Clicca per aprire il file picker</p>
            </button>
          )}
        </Card>
      </div>
    </div>
  )
}
