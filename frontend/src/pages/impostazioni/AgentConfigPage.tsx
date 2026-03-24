import { useState, useEffect } from 'react'
import { RotateCcw, Check, X, Pencil, Save } from 'lucide-react'
import {
  useAgentConfigs,
  useUpdateAgentConfig,
  useResetAgentConfigs,
  useLLMSettings,
  useUpdateLLMSettings,
} from '../../api/hooks'
import type { LLMProvider, LLMModel } from '../../api/hooks'
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
  const { data: llmData, isLoading: llmLoading } = useLLMSettings()
  const updateLLM = useUpdateLLMSettings()

  const [editingType, setEditingType] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [resetConfirm, setResetConfirm] = useState(false)

  // LLM state
  const [selectedProvider, setSelectedProvider] = useState('')
  const [selectedModel, setSelectedModel] = useState('')
  const [llmDirty, setLlmDirty] = useState(false)

  useEffect(() => {
    if (llmData) {
      setSelectedProvider(llmData.current_provider)
      setSelectedModel(llmData.current_model)
      setLlmDirty(false)
    }
  }, [llmData])

  if (isLoading || llmLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const configs: AgentConfig[] = data?.items ?? []
  const visibleConfigs = configs.filter((c) => c.visible)

  const providers: LLMProvider[] = llmData?.available_providers ?? []
  const currentProviderObj = providers.find((p) => p.id === selectedProvider)
  const models: LLMModel[] = currentProviderObj?.models ?? []

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

  const handleProviderChange = (newProvider: string) => {
    setSelectedProvider(newProvider)
    const provObj = providers.find((p) => p.id === newProvider)
    if (provObj) {
      setSelectedModel(provObj.default_model)
    }
    setLlmDirty(true)
  }

  const handleModelChange = (newModel: string) => {
    setSelectedModel(newModel)
    setLlmDirty(true)
  }

  const handleSaveLLM = async () => {
    await updateLLM.mutateAsync({ provider: selectedProvider, model: selectedModel })
    setLlmDirty(false)
  }

  const formatContext = (ctx: number): string => {
    if (ctx >= 1000000) return `${(ctx / 1000000).toFixed(ctx % 1000000 === 0 ? 0 : 1)}M`
    return `${(ctx / 1000).toFixed(0)}k`
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

      {/* LLM Settings Section */}
      <Card className="mb-6">
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Modello AI</h2>
          <p className="mt-1 text-sm text-gray-500">
            Scegli il provider e il modello AI per l&apos;assistente
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="llm-provider" className="mb-1 block text-sm font-medium text-gray-700">
              Provider
            </label>
            <select
              id="llm-provider"
              value={selectedProvider}
              onChange={(e) => handleProviderChange(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {providers.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                  {!p.configured ? ' (non configurato)' : ''}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="llm-model" className="mb-1 block text-sm font-medium text-gray-700">
              Modello
            </label>
            <select
              id="llm-model"
              value={selectedModel}
              onChange={(e) => handleModelChange(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} — {formatContext(m.context)} ctx, ${m.price_input}/${m.price_output} per 1M tok
                </option>
              ))}
            </select>
          </div>
        </div>

        {llmDirty && (
          <div className="mt-4 flex justify-end">
            <button
              onClick={handleSaveLLM}
              disabled={updateLLM.isPending}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              <Save className="h-4 w-4" />
              {updateLLM.isPending ? 'Salvataggio...' : 'Salva'}
            </button>
          </div>
        )}

        {updateLLM.isSuccess && !llmDirty && (
          <p className="mt-3 text-sm text-green-600">Impostazioni salvate con successo.</p>
        )}
      </Card>

      {/* Agent Config Section */}
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
