import { useNavigate } from 'react-router-dom'
import PageHeader from '../../../components/ui/PageHeader'
import { ArrowLeft, Mail, Pencil } from 'lucide-react'

interface DealHeaderProps {
  deal: any
  pipelineTemplates: any[] | undefined
  editMode: boolean
  onToggleEdit: () => void
  onOpenEmail: () => void
}

export default function DealHeader({ deal, pipelineTemplates, editMode, onToggleEdit, onOpenEmail }: DealHeaderProps) {
  const navigate = useNavigate()

  return (
    <>
      <PageHeader
        title={deal.name}
        subtitle={`${deal.client_name} · ${deal.stage}`}
        actions={
          <div className="flex items-center gap-2">
            <button onClick={onOpenEmail}
              className="inline-flex items-center gap-2 rounded-lg bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700">
              <Mail className="h-4 w-4" /> Invia email
            </button>
            <button onClick={onToggleEdit}
              className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm ${editMode ? 'border-purple-300 bg-purple-50 text-purple-700' : 'border-gray-300 text-gray-600 hover:bg-gray-50'}`}>
              <Pencil className="h-4 w-4" /> {editMode ? 'Annulla' : 'Modifica'}
            </button>
            <button onClick={() => navigate('/crm')}
              className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900">
              <ArrowLeft className="h-4 w-4" /> Pipeline
            </button>
          </div>
        }
      />

      {/* Badge tipo vendita + pipeline + commerciale */}
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded-full px-3 py-1 text-xs font-medium ${
          deal.deal_type === 'T&M' ? 'bg-purple-100 text-purple-700' :
          deal.deal_type === 'fixed' ? 'bg-blue-100 text-blue-700' :
          deal.deal_type === 'spot' ? 'bg-green-100 text-green-700' :
          'bg-gray-100 text-gray-700'
        }`}>
          {deal.deal_type === 'T&M' ? '\u{1F91D} Consulenza' : deal.deal_type === 'fixed' ? '\u{1F4CB} Progetto a corpo' : deal.deal_type === 'spot' ? '\u{1F916} Elevia / Prodotto' : '\u{1F4E6} ' + (deal.deal_type || 'Altro')}
        </span>
        <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600">
          Fase: {deal.stage}
        </span>
        <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600">
          Probabilita: {deal.probability}%
        </span>
        {deal.assigned_to_name && (
          <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-700">
            {deal.assigned_to_name}
          </span>
        )}
        {deal.pipeline_template_id && (() => {
          const tmpl = pipelineTemplates?.find((t: any) => t.id === deal.pipeline_template_id)
          return tmpl ? (
            <span className="rounded-full bg-indigo-100 px-3 py-1 text-xs font-medium text-indigo-700">
              Pipeline: {tmpl.name}
            </span>
          ) : null
        })()}
      </div>
    </>
  )
}
