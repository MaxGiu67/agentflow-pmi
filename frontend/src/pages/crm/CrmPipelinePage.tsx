import { useState, useRef, useOptimistic } from 'react'
import type { DragEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  useCrmPipeline, useCrmDeals, useCrmStages, useCrmAnalytics, useUpdateCrmDeal,
  useActivityTypes, useCreateCrmActivity, usePipelineTemplates,
} from '../../api/hooks'
import { formatCurrency } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'
import { Briefcase, Plus, Eye, LayoutGrid, List, User, Clock, Search, X } from 'lucide-react'

const DEAL_TYPE_SHORT: Record<string, string> = {
  'T&M': 'T&M',
  'fixed': 'Fixed',
  'spot': 'Spot',
  'hardware': 'HW',
}

export default function CrmPipelinePage() {
  const navigate = useNavigate()
  const [view, setView] = useState<'kanban' | 'table'>('kanban')
  const [searchQuery, setSearchQuery] = useState('')
  const [pipelineTab, setPipelineTab] = useState('all')
  const [commercialeFilter, setCommercialeFilter] = useState('')
  const dragDealId = useRef<string | null>(null)

  const { data: _pipeline } = useCrmPipeline()
  const { data: deals, isLoading, refetch: refetchDeals } = useCrmDeals('', '')
  const { data: stages, refetch: refetchStages } = useCrmStages()
  const { data: analytics } = useCrmAnalytics()
  const updateDeal = useUpdateCrmDeal()
  const { data: activityTypes } = useActivityTypes(true)
  const createActivity = useCreateCrmActivity()
  const { data: pipelineTemplates } = usePipelineTemplates()

  // Stage move dialog
  const [moveDialog, setMoveDialog] = useState<{ dealId: string; dealName: string; contactId?: string; fromStage: string; toStageId: string; toStageName: string } | null>(null)
  const [moveForm, setMoveForm] = useState({ type: 'call', activity_type_id: '', subject: '', description: '' })
  const [showMoveActivity, setShowMoveActivity] = useState(false)

  // React 19 useOptimistic for instant drag feedback
  const [optimisticMoves, _setOptimisticMove] = useOptimistic(
    {} as Record<string, string>, // dealId → new stageId
    (prev, move: { dealId: string; stageId: string }) => ({
      ...prev,
      [move.dealId]: move.stageId,
    })
  )
  void _setOptimisticMove // suppress unused warning

  // Client-side search filter (cliente, nominativo, descrizione deal)
  const searchLower = searchQuery.toLowerCase().trim()
  const filteredDeals = (deals?.deals || []).filter((d: any) => {
    if (!searchLower) return true
    const fields = [
      d.name || '',             // descrizione offerta / deal name
      d.client_name || '',      // nominativo contatto
      d.company_name || '',     // ragione sociale (if available)
      d.deal_type || '',
      d.technology || '',
      d.assigned_to_name || '',
    ]
    return fields.some(f => f.toLowerCase().includes(searchLower))
  })

  // Group deals by stage_id (with optimistic overrides)
  const dealsByStage: Record<string, any[]> = {}
  if (filteredDeals.length > 0 && stages) {
    for (const stage of stages) {
      dealsByStage[stage.id] = []
    }
    for (const deal of filteredDeals) {
      const effectiveStageId = optimisticMoves[deal.id] || deal.stage_id
      if (effectiveStageId && dealsByStage[effectiveStageId]) {
        dealsByStage[effectiveStageId].push({ ...deal, stage_id: effectiveStageId })
      }
    }
  }

  // Drag handlers
  const handleDragStart = (e: DragEvent, dealId: string) => {
    dragDealId.current = dealId
    e.dataTransfer.effectAllowed = 'move'
    if (e.currentTarget instanceof HTMLElement) {
      e.currentTarget.style.opacity = '0.5'
    }
  }

  const handleDragEnd = (e: DragEvent) => {
    if (e.currentTarget instanceof HTMLElement) {
      e.currentTarget.style.opacity = '1'
    }
    dragDealId.current = null
  }

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }

  const handleDrop = (e: DragEvent, targetStageId: string, stageName?: string) => {
    e.preventDefault()
    const dealId = dragDealId.current
    if (!dealId) return

    const deal = deals?.deals?.find((d: any) => d.id === dealId)
    if (!deal) return

    // Resolve to a generic crm_pipeline_stages ID
    // First try direct match (generic stage ID), then match by name (template stage → generic)
    let toStage = stages?.find((s: any) => s.id === targetStageId)
    if (!toStage && stageName) {
      toStage = stages?.find((s: any) => s.name === stageName)
    }
    const resolvedStageId = toStage?.id || targetStageId
    const resolvedStageName = toStage?.name || stageName || targetStageId

    // Skip if same stage
    if (deal.stage_id === resolvedStageId) return

    // Open dialog to log activity for this stage move
    setMoveDialog({
      dealId,
      dealName: deal.name,
      contactId: deal.contact_id,
      fromStage: deal.stage || '',
      toStageId: resolvedStageId,
      toStageName: resolvedStageName,
    })
    setMoveForm({
      type: 'call',
      activity_type_id: '',
      subject: `Spostamento: ${deal.stage || '?'} → ${resolvedStageName}`,
      description: '',
    })
  }

  const handleConfirmMove = async () => {
    if (!moveDialog) return

    // Move the deal (wait for backend to resolve template→generic stage)
    await updateDeal.mutateAsync({ dealId: moveDialog.dealId, stage_id: moveDialog.toStageId })

    // Log the activity (if subject provided)
    if (moveForm.subject.trim()) {
      await createActivity.mutateAsync({
        deal_id: moveDialog.dealId,
        contact_id: moveDialog.contactId || undefined,
        type: moveForm.type,
        activity_type_id: moveForm.activity_type_id || undefined,
        subject: moveForm.subject,
        description: moveForm.description || undefined,
        status: 'completed',
      })
    }

    setMoveDialog(null)
    setShowMoveActivity(false)
    // Force refetch stages too (backend may have created new generic stages)
    await Promise.all([refetchDeals(), refetchStages()])
  }

  // ── Reusable Kanban column + card renderer ──
  const renderKanbanColumn = (stage: any, stageDeals: any[], stageTotal: number) => (
    <div
      key={stage.id}
      className="flex w-64 flex-none flex-col rounded-xl bg-gray-50"
      onDragOver={handleDragOver}
      onDrop={(e) => handleDrop(e, stage.id, stage.name)}
    >
      <div className="flex items-center justify-between rounded-t-xl px-3 py-2" style={{ borderTop: `3px solid ${stage.color || '#6B7280'}` }}>
        <div>
          <p className="text-xs font-semibold text-gray-800">{stage.name}</p>
          <p className="text-[10px] text-gray-400">{stageDeals.length} deal &middot; {formatCurrency(stageTotal)}</p>
        </div>
        <span className="flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold text-white" style={{ backgroundColor: stage.color || '#6B7280' }}>
          {stageDeals.length}
        </span>
      </div>
      <div className="flex-1 space-y-1.5 overflow-y-auto px-1.5 py-1.5" style={{ maxHeight: 400 }}>
        {stageDeals.map((deal: any) => (
          <div key={deal.id} draggable onDragStart={(e) => handleDragStart(e, deal.id)} onDragEnd={handleDragEnd}
            className="cursor-grab rounded-lg border border-gray-200 bg-white p-2.5 shadow-sm transition-shadow hover:shadow-md active:cursor-grabbing">
            <button onClick={() => navigate(`/crm/deals/${deal.id}`)}
              className="text-left text-xs font-medium text-gray-900 hover:text-blue-600 line-clamp-2">{deal.name}</button>
            {deal.client_name && <p className="mt-0.5 text-[10px] text-gray-500">{deal.client_name}</p>}
            <div className="mt-1.5 flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-800">{formatCurrency(deal.expected_revenue)}</span>
              {deal.deal_type && <span className="rounded bg-gray-100 px-1 py-0.5 text-[9px] font-medium text-gray-600">{DEAL_TYPE_SHORT[deal.deal_type] || deal.deal_type}</span>}
            </div>
            <div className="mt-1 flex items-center justify-between text-[9px] text-gray-400">
              {deal.assigned_to_name && <span className="flex items-center gap-0.5"><User className="h-2.5 w-2.5" /> {deal.assigned_to_name}</span>}
              {deal.days_in_stage != null && <span className="flex items-center gap-0.5"><Clock className="h-2.5 w-2.5" /> {deal.days_in_stage}gg</span>}
            </div>
            <div className="mt-1.5">
              <button onClick={() => navigate(`/crm/deals/${deal.id}`)}
                className="inline-flex items-center gap-1 rounded bg-blue-50 px-1.5 py-0.5 text-[9px] font-medium text-blue-700 hover:bg-blue-100">
                <Eye className="h-2.5 w-2.5" /> Apri
              </button>
            </div>
          </div>
        ))}
        {stageDeals.length === 0 && <div className="py-6 text-center text-[10px] text-gray-300">Trascina qui un deal</div>}
      </div>
    </div>
  )

  return (
    <div className="space-y-4">
      <PageHeader
        title="CRM Pipeline"
        subtitle="Gestione opportunita e ordini cliente"
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate('/crm/deals/nuovo')}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" />
              Nuovo Deal
            </button>
          </div>
        }
      />

      {/* Analytics Bar */}
      {analytics && (
        <div className="flex flex-wrap gap-3">
          <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-2">
            <p className="text-[10px] font-semibold uppercase text-blue-400">Pipeline pesata</p>
            <p className="text-lg font-bold text-blue-700">{formatCurrency(analytics.weighted_pipeline_value)}</p>
          </div>
          <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-2">
            <p className="text-[10px] font-semibold uppercase text-green-400">Vinti</p>
            <p className="text-lg font-bold text-green-700">{analytics.won_count}</p>
          </div>
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-2">
            <p className="text-[10px] font-semibold uppercase text-red-400">Persi</p>
            <p className="text-lg font-bold text-red-700">{analytics.lost_count}</p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-2">
            <p className="text-[10px] font-semibold uppercase text-gray-400">Win rate</p>
            <p className="text-lg font-bold text-gray-700">{analytics.won_lost_ratio}%</p>
          </div>
        </div>
      )}

      {/* Pipeline tabs (US-203) */}
      {pipelineTemplates && pipelineTemplates.length > 0 && (
        <div className="flex gap-1 rounded-lg border border-gray-200 bg-white p-1">
          <button
            onClick={() => setPipelineTab('all')}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              pipelineTab === 'all' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            Tutti ({filteredDeals.length})
          </button>
          {pipelineTemplates.map((tmpl: any) => {
            const count = filteredDeals.filter((d: any) => d.pipeline_template_id === tmpl.id).length || 0
            return (
              <button
                key={tmpl.id}
                onClick={() => setPipelineTab(tmpl.id)}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  pipelineTab === tmpl.id ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {tmpl.name} ({count})
              </button>
            )
          })}
        </div>
      )}

      {/* Filtro commerciale (solo admin) */}
      {(() => {
        const allDeals = deals?.deals || []
        const assigneeNames: string[] = [...new Set(allDeals.map((d: any) => d.assigned_to_name || '').filter(Boolean))] as string[]
        if (assigneeNames.length <= 1) return null
        return (
          <div className="flex flex-wrap gap-1">
            <button onClick={() => setCommercialeFilter('')}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${!commercialeFilter ? 'bg-purple-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
              Tutti
            </button>
            {assigneeNames.map((name: string) => (
              <button key={name} onClick={() => setCommercialeFilter(name)}
                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${commercialeFilter === name ? 'bg-purple-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                {name}
              </button>
            ))}
          </div>
        )
      })()}

      {/* Controls: View toggle + Search */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Toggle Kanban/Table */}
        <div className="inline-flex rounded-lg border border-gray-300 bg-white">
          <button
            onClick={() => setView('kanban')}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-l-lg ${
              view === 'kanban' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-50'
            }`}
          >
            <LayoutGrid className="h-4 w-4" /> Kanban
          </button>
          <button
            onClick={() => setView('table')}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-r-lg ${
              view === 'table' ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-50'
            }`}
          >
            <List className="h-4 w-4" /> Tabella
          </button>
        </div>

        {/* Search: cliente, nominativo, descrizione */}
        <div className="relative flex-1 min-w-[250px] max-w-md">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Cerca per cliente, nominativo o descrizione deal..."
            className="w-full rounded-lg border border-gray-300 py-1.5 pl-9 pr-8 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
          {searchQuery && (
            <button onClick={() => setSearchQuery('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {isLoading ? <LoadingSpinner /> : view === 'kanban' ? (
        /* ============ KANBAN VIEW ============ */
        <>
          {/* Render kanban sections */}
          {(() => {
            // Build list of pipeline sections to render
            const allDealsList = filteredDeals
            const filteredByComm = commercialeFilter
              ? allDealsList.filter((d: any) => d.assigned_to_name === commercialeFilter)
              : allDealsList

            // If specific tab selected, show template-specific stages
            if (pipelineTab !== 'all') {
              const tabDeals = filteredByComm.filter((d: any) => d.pipeline_template_id === pipelineTab)
              const tmpl = pipelineTemplates?.find((t: any) => t.id === pipelineTab)
              const tmplStages = tmpl?.stages?.length ? [...tmpl.stages].sort((a: any, b: any) => a.sequence - b.sequence) : stages || []

              // Build stage name map from both generic stages AND deal's own stage field
              const genericStageMap: Record<string, string> = {}
              for (const s of stages || []) { genericStageMap[s.id] = s.name }

              return (
                <div className="flex gap-3 overflow-x-auto pb-4" style={{ minHeight: 400 }}>
                  {tmplStages.map((tStage: any) => {
                    // Match deals by stage name — use deal.stage (name from backend) as primary, fallback to genericStageMap
                    const stageDeals = tabDeals.filter((d: any) => {
                      const dealStageName = d.stage || d.stage_name || genericStageMap[d.stage_id] || ''
                      return dealStageName === tStage.name
                    })
                    // Catch unmatched deals in first stage
                    const isFirstStage = tStage.sequence === tmplStages[0]?.sequence
                    const unmatchedDeals = isFirstStage ? tabDeals.filter((d: any) => {
                      const dealStageName = d.stage || d.stage_name || genericStageMap[d.stage_id] || ''
                      return !tmplStages.some((ts: any) => ts.name === dealStageName)
                    }) : []
                    const allDeals = [...stageDeals, ...unmatchedDeals]
                    const stageTotal = allDeals.reduce((sum: number, d: any) => sum + (d.expected_revenue || 0), 0)
                    // Use template stage with fallback color/probability
                    const columnStage = { ...tStage, color: tStage.is_won ? '#10B981' : tStage.is_lost ? '#EF4444' : '#6B7280', probability_default: tStage.is_won ? 100 : tStage.is_lost ? 0 : 50 }
                    return renderKanbanColumn(columnStage, allDeals, stageTotal)
                  })}
                </div>
              )
            }

            // Tab "Tutti" → stacked per pipeline, using TEMPLATE stages
            const sections: { title: string; templateId: string; color: string; deals: any[]; stagesForSection: any[] }[] = []
            const genericStageMap: Record<string, string> = {}
            for (const s of stages || []) { genericStageMap[s.id] = s.name }
            const genericStages = stages?.map((s: any) => ({ ...s, code: s.id, name: s.name })) || []

            // Pipeline templates — use template stages
            if (pipelineTemplates) {
              for (const tmpl of pipelineTemplates) {
                const tmplDeals = filteredByComm.filter((d: any) => d.pipeline_template_id === tmpl.id)
                if (tmplDeals.length > 0) {
                  const tmplStages = tmpl.stages?.length
                    ? [...tmpl.stages].sort((a: any, b: any) => a.sequence - b.sequence).map((s: any) => ({
                        ...s, color: s.is_won ? '#10B981' : s.is_lost ? '#EF4444' : '#6B7280', probability_default: s.is_won ? 100 : s.is_lost ? 0 : 50,
                      }))
                    : genericStages
                  sections.push({ title: tmpl.name, templateId: tmpl.id, color: '#6366f1', deals: tmplDeals, stagesForSection: tmplStages })
                }
              }
            }

            // Legacy deals (no pipeline_template_id)
            const legacyDeals = filteredByComm.filter((d: any) => !d.pipeline_template_id)
            if (legacyDeals.length > 0) {
              sections.push({
                title: 'Non classificati',
                templateId: 'legacy',
                color: '#6b7280',
                deals: legacyDeals,
                stagesForSection: genericStages,
              })
            }

            return (
              <div className="space-y-6">
                {sections.map((section) => {
                  const sectionTotal = section.deals.reduce((s: number, d: any) => s + (d.expected_revenue || 0), 0)
                  return (
                    <div key={section.templateId}>
                      {/* Section header */}
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm font-bold text-gray-800">{section.title}</h3>
                          <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">{section.deals.length} deal</span>
                        </div>
                        <span className="text-sm font-medium text-gray-500">{formatCurrency(sectionTotal)}</span>
                      </div>
                      {/* Full kanban for this pipeline — match by stage name */}
                      <div className="flex gap-3 overflow-x-auto pb-3">
                        {section.stagesForSection.map((stageInfo: any, idx: number) => {
                          const stageDeals = section.deals.filter((d: any) => {
                            const dealStageName = d.stage || d.stage_name || genericStageMap[d.stage_id] || ''
                            return dealStageName === stageInfo.name
                          })
                          // Catch unmatched in first stage
                          const unmatchedDeals = idx === 0 ? section.deals.filter((d: any) => {
                            const dealStageName = d.stage || d.stage_name || genericStageMap[d.stage_id] || ''
                            return !section.stagesForSection.some((ts: any) => ts.name === dealStageName)
                          }) : []
                          const allDeals = [...stageDeals, ...unmatchedDeals]
                          const stTotal = allDeals.reduce((s: number, d: any) => s + (d.expected_revenue || 0), 0)
                          const color = stageInfo.color || '#6B7280'
                          return renderKanbanColumn({ ...stageInfo, color }, allDeals, stTotal)
                        })}
                      </div>
                    </div>
                  )
                })}
              </div>
            )
          })()}
        </>
      ) : (
        /* ============ TABLE VIEW ============ */
        !filteredDeals.length ? (
          <EmptyState icon={<Briefcase className="h-12 w-12" />} title={searchQuery ? "Nessun risultato" : "Nessun deal"} description={searchQuery ? `Nessun deal trovato per "${searchQuery}"` : "La pipeline e vuota."} />
        ) : (
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Deal</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Cliente</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Fase</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-gray-500">Tipo</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold uppercase text-gray-500">Valore</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold uppercase text-gray-500">Prob.</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold uppercase text-gray-500">Azioni</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredDeals.map((deal: any) => (
                  <tr key={deal.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{deal.name}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{deal.client_name}</td>
                    <td className="px-4 py-3">
                      <span className="inline-flex rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700">
                        {deal.stage}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{deal.deal_type || '-'}</td>
                    <td className="px-4 py-3 text-right text-sm font-medium">{formatCurrency(deal.expected_revenue)}</td>
                    <td className="px-4 py-3 text-center text-sm">{deal.probability}%</td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => navigate(`/crm/deals/${deal.id}`)}
                        className="text-xs text-blue-600 hover:underline"
                      >
                        Dettaglio
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
      {/* ── Stage Move Dialog (Hybrid: optional activity) ── */}
      {moveDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl space-y-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900">Cambio fase</h3>
              <p className="text-sm text-gray-500 mt-1">
                <strong>{moveDialog.dealName}</strong>: {moveDialog.fromStage} → <span className="text-blue-600 font-medium">{moveDialog.toStageName}</span>
              </p>
            </div>

            {/* Quick move — no activity needed */}
            <button onClick={() => { handleConfirmMove(); }}
              className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700">
              Sposta senza registrare attivita
            </button>

            {/* Optional: expand to log activity */}
            {!showMoveActivity ? (
              <button onClick={() => setShowMoveActivity(true)}
                className="w-full text-center text-xs text-gray-400 hover:text-blue-600 py-1">
                + Registra anche un'attivita collegata
              </button>
            ) : (
              <div className="space-y-3 border-t border-gray-100 pt-3">
                <p className="text-xs font-medium text-gray-500">Attivita collegata (opzionale)</p>
                <div className="grid gap-2 sm:grid-cols-2">
                  <select value={moveForm.type} onChange={(e) => setMoveForm({ ...moveForm, type: e.target.value })}
                    className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                    <option value="call">Chiamata</option>
                    <option value="meeting">Incontro</option>
                    <option value="email">Email ricevuta</option>
                    <option value="note">Nota interna</option>
                    <option value="task">Task completato</option>
                  </select>
                  <select value={moveForm.activity_type_id} onChange={(e) => setMoveForm({ ...moveForm, activity_type_id: e.target.value })}
                    className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
                    <option value="">-- Tipo specifico --</option>
                    {activityTypes?.map((t: any) => (
                      <option key={t.id} value={t.id}>{t.label}</option>
                    ))}
                  </select>
                </div>
                <input type="text" value={moveForm.subject} onChange={(e) => setMoveForm({ ...moveForm, subject: e.target.value })}
                  placeholder="Oggetto (es. Chiamata qualifica — budget 80k)" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                <textarea value={moveForm.description} onChange={(e) => setMoveForm({ ...moveForm, description: e.target.value })}
                  placeholder="Dettagli (BANT, note...)" rows={2}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                <button onClick={handleConfirmMove}
                  className="w-full rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700">
                  Sposta e Registra Attivita
                </button>
              </div>
            )}

            <button onClick={() => { setMoveDialog(null); setShowMoveActivity(false) }}
              className="w-full text-center text-xs text-gray-400 hover:text-gray-600 py-1">
              Annulla
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
