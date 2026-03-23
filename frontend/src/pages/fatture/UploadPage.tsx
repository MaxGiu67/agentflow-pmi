import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, CheckCircle, AlertTriangle } from 'lucide-react'
import { useUploadInvoice } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import FileUpload from '../../components/ui/FileUpload'
import Card from '../../components/ui/Card'

export default function UploadPage() {
  const navigate = useNavigate()
  const uploadMutation = useUploadInvoice()
  const [files, setFiles] = useState<File[]>([])
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState('')

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

  return (
    <div>
      <PageHeader
        title="Carica Fatture"
        subtitle="Carica fatture in formato XML, PDF o P7M"
      />

      <Card className="max-w-2xl">
        {uploadStatus === 'success' ? (
          <div className="flex flex-col items-center py-8 text-center">
            <CheckCircle className="mb-4 h-16 w-16 text-green-500" />
            <h2 className="text-lg font-semibold text-gray-900">Caricamento completato!</h2>
            <p className="mt-2 text-sm text-gray-500">Le fatture sono state caricate e verranno elaborate.</p>
            <button
              onClick={() => navigate('/fatture')}
              className="mt-4 text-sm text-blue-600 hover:underline"
            >
              Vai alle fatture
            </button>
          </div>
        ) : (
          <>
            {uploadStatus === 'error' && (
              <div className="mb-4 flex items-center gap-2 rounded-lg bg-red-50 p-3">
                <AlertTriangle className="h-5 w-5 text-red-500" />
                <span className="text-sm text-red-700">{errorMessage}</span>
              </div>
            )}

            <FileUpload
              onFileSelect={setFiles}
              multiple
              accept=".xml,.pdf,.p7m"
            />

            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => navigate('/fatture')}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Annulla
              </button>
              <button
                onClick={handleUpload}
                disabled={files.length === 0 || uploadMutation.isPending}
                className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Upload className="h-4 w-4" />
                {uploadMutation.isPending ? 'Caricamento...' : `Carica (${files.length} file)`}
              </button>
            </div>
          </>
        )}
      </Card>
    </div>
  )
}
