import { useState } from 'react'
import PageHeader from '../../components/ui/PageHeader'
import PageMeta from '../../components/ui/PageMeta'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import Badge from '../../components/ui/Badge'
import { Settings, Save, Trash2, Eye, EyeOff } from 'lucide-react'
import api from '../../api/client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

function useIntegrationSettings() {
  return useQuery({
    queryKey: ['integration-settings'],
    queryFn: () => api.get('/settings/integrations').then((r) => r.data),
  })
}

function useEmailQuota() {
  return useQuery({
    queryKey: ['email-quota'],
    queryFn: () => api.get('/settings/email-quota').then((r) => r.data),
  })
}

function useLlmQuota() {
  return useQuery({
    queryKey: ['llm-quota'],
    queryFn: () => api.get('/metering/llm-quota').then((r) => r.data),
  })
}

function useMyUsage() {
  return useQuery({
    queryKey: ['my-usage'],
    queryFn: () => api.get('/metering/my-usage').then((r) => r.data),
  })
}

const SECTIONS: Record<string, { title: string; keys: string[] }> = {
  acube: { title: 'A-Cube (Fatturazione + Banca)', keys: ['acube_api_key', 'acube_company_id', 'acube_connection_id'] },
  brevo: { title: 'Brevo (Email Marketing)', keys: ['brevo_api_key'] },
  openai: { title: 'OpenAI (AI Chatbot)', keys: ['openai_api_key'] },
}

export default function IntegrazioniPage() {
  const { data: settings, isLoading } = useIntegrationSettings()
  const { data: emailQuota } = useEmailQuota()
  const { data: llmQuota } = useLlmQuota()
  const { data: usage } = useMyUsage()
  const qc = useQueryClient()

  const [editKey, setEditKey] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [showValue, setShowValue] = useState<Record<string, boolean>>({})

  const saveSetting = useMutation({
    mutationFn: (data: { key: string; value: string }) =>
      api.post('/settings/integrations', data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['integration-settings'] })
      setEditKey(null)
      setEditValue('')
    },
  })

  const deleteSetting = useMutation({
    mutationFn: (key: string) => api.delete(`/settings/integrations/${key}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['integration-settings'] }),
  })

  if (isLoading) return <LoadingSpinner />

  const settingsMap = new Map<string, { key: string; description?: string; value_masked?: string; source?: string }>((settings || []).map((s: any) => [s.key, s]))

  return (
    <div className="space-y-6">
      <PageMeta title="Integrazioni" />
      <PageHeader title="Integrazioni" subtitle="Configurazione servizi esterni per la tua azienda" />

      {/* Usage cards */}
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <p className="text-[10px] font-semibold text-gray-400 uppercase">Email questo mese</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">{emailQuota?.sent || 0} <span className="text-sm font-normal text-gray-400">/ {emailQuota?.quota || 5000}</span></p>
          <div className="mt-2 h-1.5 rounded-full bg-gray-200">
            <div className="h-1.5 rounded-full bg-blue-600" style={{ width: `${Math.min(((emailQuota?.sent || 0) / (emailQuota?.quota || 5000)) * 100, 100)}%` }} />
          </div>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <p className="text-[10px] font-semibold text-gray-400 uppercase">AI Token questo mese</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">{(llmQuota?.tokens_used || 0).toLocaleString()} <span className="text-sm font-normal text-gray-400">/ {(llmQuota?.quota || 100000).toLocaleString()}</span></p>
          <div className="mt-2 h-1.5 rounded-full bg-gray-200">
            <div className="h-1.5 rounded-full bg-purple-600" style={{ width: `${Math.min(((llmQuota?.tokens_used || 0) / (llmQuota?.quota || 100000)) * 100, 100)}%` }} />
          </div>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <p className="text-[10px] font-semibold text-gray-400 uppercase">API Calls questo mese</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">{usage?.api_calls || 0}</p>
          <p className="text-xs text-gray-400 mt-1">PDF: {usage?.pdf_pages || 0} pagine</p>
        </div>
      </div>

      {/* Settings by section */}
      {Object.entries(SECTIONS).map(([sectionKey, section]) => (
        <div key={sectionKey} className="rounded-xl border border-gray-200 bg-white">
          <div className="border-b border-gray-100 px-4 py-3">
            <h3 className="text-sm font-semibold text-gray-800">{section.title}</h3>
          </div>
          <div className="divide-y divide-gray-100">
            {section.keys.map((key) => {
              const setting = settingsMap.get(key)
              const isEditing = editKey === key
              return (
                <div key={key} className="flex items-center justify-between gap-3 px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-700">{key}</p>
                    <p className="text-xs text-gray-400">{setting?.description || ''}</p>
                    {!isEditing && (
                      <p className="mt-0.5 text-xs font-mono text-gray-500">
                        {showValue[key] ? setting?.value_masked : (setting?.source === 'none' ? 'Non configurato' : `${setting?.source || 'platform'}: ****`)}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    {isEditing ? (
                      <>
                        <input value={editValue} onChange={(e) => setEditValue(e.target.value)}
                          placeholder="Valore" className="rounded border border-gray-300 px-2 py-1 text-xs w-48" />
                        <button onClick={() => saveSetting.mutate({ key, value: editValue })}
                          className="rounded bg-blue-600 p-1.5 text-white hover:bg-blue-700"><Save className="h-3.5 w-3.5" /></button>
                        <button onClick={() => setEditKey(null)}
                          className="rounded border border-gray-300 p-1.5 text-gray-400"><Trash2 className="h-3.5 w-3.5" /></button>
                      </>
                    ) : (
                      <>
                        <button onClick={() => setShowValue({ ...showValue, [key]: !showValue[key] })}
                          className="rounded p-1.5 text-gray-400 hover:bg-gray-100">
                          {showValue[key] ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                        </button>
                        <button onClick={() => { setEditKey(key); setEditValue('') }}
                          className="rounded p-1.5 text-blue-500 hover:bg-blue-50"><Settings className="h-3.5 w-3.5" /></button>
                        {setting?.source === 'custom' && (
                          <button onClick={() => deleteSetting.mutate(key)}
                            className="rounded p-1.5 text-red-400 hover:bg-red-50"><Trash2 className="h-3.5 w-3.5" /></button>
                        )}
                      </>
                    )}
                    <Badge variant={setting?.source === 'custom' ? 'success' : setting?.source === 'platform' ? 'info' : 'default'}>
                      {setting?.source || 'none'}
                    </Badge>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
