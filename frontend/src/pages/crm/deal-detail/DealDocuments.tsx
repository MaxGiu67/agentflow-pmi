import { useState, useRef } from 'react'
import { useDealDocuments, useDeleteDealDocument, useUploadDealDocument } from '../../../api/hooks'
import api from '../../../api/client'
import { Plus, FileText, Trash2, Upload, Download } from 'lucide-react'

interface DealDocumentsProps {
  deal: any
  dealId: string
}

export default function DealDocuments({ deal, dealId }: DealDocumentsProps) {
  const { data: documents } = useDealDocuments(dealId)
  const deleteDocument = useDeleteDealDocument()
  const uploadDocument = useUploadDealDocument()

  const [showDocForm, setShowDocForm] = useState(false)
  const [docForm, setDocForm] = useState({ doc_type: 'offerta', name: '', notes: '' })
  const [docFile, setDocFile] = useState<File | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold uppercase text-gray-400">Documenti</h3>
        <button onClick={() => setShowDocForm(!showDocForm)}
          className="inline-flex items-center gap-1 rounded-lg bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-100">
          <Plus className="h-3 w-3" /> Aggiungi documento
        </button>
      </div>

      {showDocForm && (
        <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50/30 p-4 space-y-3">
          <div className="grid gap-2 sm:grid-cols-2">
            <select value={docForm.doc_type} onChange={(e) => setDocForm({ ...docForm, doc_type: e.target.value })}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              <option value="offerta">Offerta</option>
              <option value="ordine">Ordine cliente</option>
              <option value="contratto">Contratto</option>
              <option value="specifica">Specifica tecnica</option>
              <option value="altro">Altro</option>
            </select>
            <input type="text" value={docForm.name} onChange={(e) => setDocForm({ ...docForm, name: e.target.value })}
              placeholder="Nome documento (opzionale)" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </div>
          {/* File upload */}
          <div>
            <input ref={fileInputRef} type="file" className="hidden" onChange={(e) => {
              const f = e.target.files?.[0] || null
              setDocFile(f)
              if (f && !docForm.name.trim()) setDocForm({ ...docForm, name: f.name })
            }} />
            <button type="button" onClick={() => fileInputRef.current?.click()}
              className={`w-full flex items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-3 text-sm transition-colors ${
                docFile ? 'border-green-300 bg-green-50 text-green-700' : 'border-gray-300 text-gray-500 hover:border-blue-400 hover:text-blue-600'
              }`}>
              <Upload className="h-4 w-4" />
              {docFile ? docFile.name : 'Seleziona file da caricare'}
            </button>
            {docFile && (
              <div className="flex items-center gap-2 mt-1.5">
                <span className="text-xs text-gray-400">{(docFile.size / 1024).toFixed(1)} KB</span>
                <button onClick={() => { setDocFile(null); if (fileInputRef.current) fileInputRef.current.value = '' }}
                  className="text-xs text-red-500 hover:text-red-700">Rimuovi</button>
              </div>
            )}
          </div>
          <input type="text" value={docForm.notes} onChange={(e) => setDocForm({ ...docForm, notes: e.target.value })}
            placeholder="Note (opzionale)" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          <div className="flex gap-2">
            <button onClick={async () => {
              if (!docFile) return
              const formData = new FormData()
              formData.append('file', docFile)
              formData.append('doc_type', docForm.doc_type)
              formData.append('name', docForm.name || docFile.name)
              formData.append('notes', docForm.notes)
              try {
                await uploadDocument.mutateAsync({ dealId: deal.id, formData })
                setDocForm({ doc_type: 'offerta', name: '', notes: '' })
                setDocFile(null)
                if (fileInputRef.current) fileInputRef.current.value = ''
                setShowDocForm(false)
              } catch (err: any) {
                const detail = err?.response?.data?.detail || err?.response?.data?.message || (typeof err?.response?.data === 'string' ? err.response.data : null) || err?.message || 'Errore sconosciuto'
                alert(`Errore upload: ${detail}`)
              }
            }} disabled={!docFile || uploadDocument.isPending}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
              {uploadDocument.isPending ? 'Caricamento...' : 'Carica'}
            </button>
            <button onClick={() => { setShowDocForm(false); setDocFile(null) }}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600">Annulla</button>
          </div>
        </div>
      )}

      {documents && documents.length > 0 ? (
        <div className="space-y-2">
          {documents.map((doc: any) => {
            const typeLabels: Record<string, { label: string; color: string }> = {
              offerta: { label: 'Offerta', color: 'bg-green-100 text-green-700' },
              ordine: { label: 'Ordine', color: 'bg-blue-100 text-blue-700' },
              contratto: { label: 'Contratto', color: 'bg-purple-100 text-purple-700' },
              specifica: { label: 'Specifica', color: 'bg-yellow-100 text-yellow-700' },
              altro: { label: 'Altro', color: 'bg-gray-100 text-gray-700' },
            }
            const typeInfo = typeLabels[doc.doc_type] || typeLabels.altro
            return (
              <div key={doc.id} className="flex items-center justify-between rounded-lg border border-gray-100 px-4 py-3">
                <div className="flex items-center gap-3 min-w-0">
                  <FileText className="h-4 w-4 text-gray-400 shrink-0" />
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${typeInfo.color}`}>{typeInfo.label}</span>
                      <p className="text-sm font-medium text-gray-900 truncate">{doc.name}</p>
                    </div>
                    {doc.notes && <p className="text-xs text-gray-400 mt-0.5">{doc.notes}</p>}
                    {doc.created_at && <p className="text-[10px] text-gray-300 mt-0.5">{new Date(doc.created_at).toLocaleDateString('it-IT')}</p>}
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {doc.url && (
                    <button onClick={async () => {
                      try {
                        const res = await api.get(`/crm/documents/${doc.id}/download`, { responseType: 'blob' })
                        const blob = res.data as Blob
                        const url = window.URL.createObjectURL(blob)
                        const a = document.createElement('a')
                        a.href = url
                        a.download = doc.name || 'documento'
                        a.click()
                        window.URL.revokeObjectURL(url)
                      } catch {
                        alert('Errore download')
                      }
                    }}
                      className="inline-flex items-center gap-1 rounded bg-gray-50 px-2 py-1 text-xs text-blue-600 hover:bg-blue-50">
                      <Download className="h-3 w-3" /> Scarica
                    </button>
                  )}
                  <button onClick={() => { if (confirm(`Eliminare "${doc.name}"?`)) deleteDocument.mutate(doc.id) }}
                    className="text-gray-300 hover:text-red-500"><Trash2 className="h-3.5 w-3.5" /></button>
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <p className="text-sm text-gray-400 text-center py-4">Nessun documento allegato</p>
      )}
    </div>
  )
}
