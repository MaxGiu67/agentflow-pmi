import { useState } from 'react'
import { RotateCcw, Check, X, Pencil } from 'lucide-react'
import { useAgentConfigs, useUpdateAgentConfig, useResetAgentConfigs } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import LoadingSpinner from '../../components/ui/LoadingSpinner'

interface AgentConfig {
  id: string
  agent_type: string
  display_name: string | null
  personality: string | null
  icon: string | null
  enabled: boolean
  visible: boolean
  created_at: string
  updated_at: string
}

export default function AgentConfigPage() {
  const { data, isLoading } = useAgentConfigs()
  const updateConfig = useUpdateAgentConfig()
  const resetConfigs = useResetAgentConfigs()

  const [editingType, setEditingType] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [resetConfirm, setResetConfirm] = useState(false)

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const configs: AgentConfig[] = data?.items ?? []
  const visibleConfigs = configs.filter((c) => c.visible)

  const handleStartEdit = (config: AgentConfig) => {
    setEditingType(config.agent_type)
    setEditName(config.display_name ?? '')
  }

  const handleSaveEdit = async (agentType: string) => {
    if (!editName.trim()) return
    await updateConfig.mutateAsync({ agentType, data: { display_name: editName.trim() } })
    setEditingType(null)
    setEditName('')
  }

  const handleCancelEdit = () => {
    setEditingType(null)
    setEditName('')
  }

  const handleToggleEnabled = async (config: AgentConfig) => {
    await updateConfig.mutateAsync({
      agentType: config.agent_type,
      data: { enabled: !config.enabled },
    })
  }

  const handleReset = async () => {
    await resetConfigs.mutateAsync()
    setResetConfirm(false)
  }

  return (
    <div>
      <PageHeader
        title="Configurazione Agenti"
        subtitle="Personalizza i nomi e le impostazioni degli agenti AI"
        actions={
          resetConfirm ? (
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600">Ripristinare i default?</span>
              <button
                onClick={handleReset}
                disabled={resetConfigs.isPending}
                className="inline-flex items-center gap-1 rounded-lg bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
              >
                <Check className="h-4 w-4" />
                Conferma
              </button>
              <button
                onClick={() => setResetConfirm(false)}
                className="inline-flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                <X className="h-4 w-4" />
                Annulla
              </button>
            </div>
          ) : (
            <button
              onClick={() => setResetConfirm(true)}
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              <RotateCcw className="h-4 w-4" />
              Ripristina nomi default
            </button>
          )
        }
      />

      <Card>
        <div className="divide-y divide-gray-100">
          {visibleConfigs.map((config) => (
            <div
              key={config.agent_type}
              className="flex items-center justify-between py-4 first:pt-0 last:pb-0"
            >
              {/* Left: icon + name */}
              <div className="flex items-center gap-3">
                <span className="text-2xl">{config.icon ?? '\u{1f916}'}</span>

                {editingType === config.agent_type ? (
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleSaveEdit(config.agent_type)
                        if (e.key === 'Escape') handleCancelEdit()
                      }}
                      autoFocus
                      className="rounded-lg border border-blue-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                    <button
                      onClick={() => handleSaveEdit(config.agent_type)}
                      disabled={updateConfig.isPending}
                      className="rounded p-1 text-green-600 hover:bg-green-50"
                    >
                      <Check className="h-4 w-4" />
                    </button>
                    <button
                      onClick={handleCancelEdit}
                      className="rounded p-1 text-gray-400 hover:bg-gray-100"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {config.display_name ?? config.agent_type}
                      </p>
                      <p className="text-xs text-gray-400">{config.agent_type}</p>
                    </div>
                    <button
                      onClick={() => handleStartEdit(config)}
                      className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                  </div>
                )}
              </div>

              {/* Right: toggle */}
              <button
                onClick={() => handleToggleEnabled(config)}
                disabled={updateConfig.isPending}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  config.enabled ? 'bg-blue-600' : 'bg-gray-300'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    config.enabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
