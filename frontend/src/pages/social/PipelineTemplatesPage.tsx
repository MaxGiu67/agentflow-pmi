import { usePipelineTemplates } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import { GitBranch, CheckCircle, XCircle, Clock, SkipForward } from 'lucide-react'

const TYPE_COLORS: Record<string, string> = {
  services: 'bg-blue-100 text-blue-700',
  product: 'bg-purple-100 text-purple-700',
  custom: 'bg-gray-100 text-gray-700',
}

export default function PipelineTemplatesPage() {
  const { data: templates, isLoading } = usePipelineTemplates()

  if (isLoading) return <LoadingSpinner />

  return (
    <div className="space-y-6">
      <PageHeader
        title="Pipeline Templates"
        subtitle="Template di processo vendita — il prodotto scelto attiva la pipeline corretta"
      />

      <div className="space-y-6">
        {templates?.map((tmpl: any) => (
          <div key={tmpl.id} className="rounded-xl border border-gray-200 bg-white p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-100">
                  <GitBranch className="h-5 w-5 text-indigo-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">{tmpl.name}</h3>
                  <p className="text-xs text-gray-500">{tmpl.description}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`rounded-full px-3 py-1 text-xs font-medium ${TYPE_COLORS[tmpl.pipeline_type] || TYPE_COLORS.custom}`}>
                  {tmpl.pipeline_type}
                </span>
                <span className="text-xs text-gray-400">{tmpl.stage_count} stati</span>
              </div>
            </div>

            {/* Pipeline stages visual */}
            <div className="flex items-center gap-1 overflow-x-auto pb-2">
              {tmpl.stages?.map((stage: any, i: number) => (
                <div key={stage.id} className="flex items-center">
                  <div className={`flex-shrink-0 rounded-lg border px-3 py-2 text-center min-w-[100px] ${
                    stage.is_won ? 'border-green-300 bg-green-50' :
                    stage.is_lost ? 'border-red-300 bg-red-50' :
                    stage.is_optional ? 'border-dashed border-gray-300 bg-gray-50' :
                    'border-gray-200 bg-white'
                  }`}>
                    <p className="text-xs font-medium text-gray-900">{stage.name}</p>
                    <div className="flex items-center justify-center gap-1 mt-1">
                      {stage.is_won && <CheckCircle className="h-3 w-3 text-green-500" />}
                      {stage.is_lost && <XCircle className="h-3 w-3 text-red-500" />}
                      {stage.is_optional && <SkipForward className="h-3 w-3 text-gray-400" />}
                      {!stage.is_won && !stage.is_lost && stage.sla_days > 0 && (
                        <span className="text-[10px] text-gray-400 flex items-center gap-0.5">
                          <Clock className="h-2.5 w-2.5" />{stage.sla_days}gg
                        </span>
                      )}
                    </div>
                    {stage.required_fields?.length > 0 && (
                      <p className="text-[10px] text-gray-400 mt-0.5 truncate max-w-[90px]">
                        {stage.required_fields.join(', ')}
                      </p>
                    )}
                  </div>
                  {i < tmpl.stages.length - 1 && !tmpl.stages[i + 1]?.is_lost && (
                    <span className="mx-1 text-gray-300">→</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
