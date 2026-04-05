import { useState, useRef, useOptimistic } from 'react'
import type { DragEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  useCrmPipeline, useCrmDeals, useCrmStages, useCrmAnalytics, useUpdateCrmDeal,
  useActivityTypes, useCreateCrmActivity,
} from '../../api/hooks'
import { formatCurrency } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'
import { Briefcase, Plus, Eye, LayoutGrid, List } from 'lucide-react'

const DEAL_TYPE_SHORT: Record<string, string> = {
  'T&M': 'T&M',
  'fixed': 'Fixed',
  'spot': 'Spot',
  'hardware': 'HW',
}

export default function CrmPipelinePage() {
  const navigate = useNavigate()
  const [view, setView] = useState<'kanban' | 'table'>('kanban')
  const [typeFilter, setTypeFilter] = useState('')
  const dragDealId = useRef<string | null>(null)

  const { data: _pipeline } = useCrmPipeline()
  const { data: deals, isLoading } = useCrmDeals('', typeFilter)
  const { data: stages } = useCrmStages()
  const { data: analytics } = useCrmAnalytics()
  const updateDeal = useUpdateCrmDeal()
  const { data: activityTypes } = useActivityTypes(true)
  const createActivity = useCreateCrmActivity()

  // Stage move dialog
  const [moveDialog, setMoveDialog] = useState<{ dealId: string; dealName: string; contactId?: string; fromStage: string; toStageId: string; toStageName: string } | null>(null)
  const [moveForm, setMoveForm] = useState({ type: 'call', activity_type_id: '', subject: '', description: '' })
  const [showMoveActivity, setShowMoveActivity] = useState(false)

  // React 19 useOptimistic for instant drag feedback
  const [optimisticMoves, setOptimisticMove] = useOptimistic(
    {} as Record<string, string>, // dealId → new stageId
    (prev, move: { dealId: string; stageId: string }) => ({
      ...prev,
      [move.dealId]: move.stageId,
    })
  )

  // Group deals by stage_id (with optimistic overrides)
  const dealsByStage: Record<string, any[]> = {}
  if (deals?.deals && stages) {
    for (const stage of stages) {
      dealsByStage[stage.id] = []
    }
    for (const deal of deals.deals) {
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

  const handleDrop = (e: DragEvent, targetStageId: string) => {
    e.preventDefault()
    const dealId = dragDealId.current
    if (!dealId) return

    const deal = deals?.deals?.find((d: any) => d.id === dealId)
    if (!deal || deal.stage_id === targetStageId) return

    const toStage = stages?.find((s: any) => s.id === targetStageId)

    // Open dialog to log activity for this stage move
    setMoveDialog({
      dealId,
      dealName: deal.name,
      contactId: deal.contact_id,
      fromStage: deal.stage || '',
      toStageId: targetStageId,
      toStageName: toStage?.name || '',
    })
    setMoveForm({
      type: 'call',
      activity_type_id: '',
      subject: `Spostamento: ${deal.stage || '?'} → ${toStage?.name || '?'}`,
      description: '',
    })
  }

  const handleConfirmMove = async () => {
    if (!moveDialog) return

    // Optimistic move
    setOptimisticMove({ dealId: moveDialog.dealId, stageId: moveDialog.toStageId })

    // Move the deal
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
  }

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

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
        {/* AC-90.6: Toggle Kanban/Table */}
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

        {/* AC-90.8: Filters */}
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
        >
          <option value="">Tutti i tipi</option>
          <option value="T&M">Time & Material</option>
          <option value="fixed">Progetto fisso</option>
          <option value="spot">Spot</option>
          <option value="hardware">Hardware</option>
        </select>
      </div>

      {isLoading ? <LoadingSpinner /> : view === 'kanban' ? (
        /* ============ KANBAN VIEW ============ */
        <div className="flex gap-3 overflow-x-auto pb-4" style={{ minHeight: 400 }}>
          {stages?.filter((s: any) => !s.is_lost).map((stage: any) => {
            const stageDeals = dealsByStage[stage.id] || []
            const stageTotal = stageDeals.reduce((sum: number, d: any) => sum + (d.expected_revenue || 0), 0)

            return (
              <div
                key={stage.id}
                className="flex w-72 flex-none flex-col rounded-xl bg-gray-50"
                onDragOver={handleDragOver}
                onDrop={(e) => handleDrop(e, stage.id)}
              >
                {/* AC-90.3: Column header */}
                <div className="flex items-center justify-between rounded-t-xl px-3 py-2.5" style={{ borderTop: `3px solid ${stage.color}` }}>
                  <div>
                    <p className="text-sm font-semibold text-gray-800">{stage.name}</p>
                    <p className="text-xs text-gray-400">{stageDeals.length} deal &middot; {formatCurrency(stageTotal)}</p>
                  </div>
                  <span
                    className="flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold text-white"
                    style={{ backgroundColor: stage.color }}
                  >
                    {stageDeals.length}
                  </span>
                </div>

                {/* Cards */}
                <div className="flex-1 space-y-2 overflow-y-auto px-2 py-2" style={{ maxHeight: 500 }}>
                  {stageDeals.map((deal: any) => (
                    <div
                      key={deal.id}
                      draggable
                      onDragStart={(e) => handleDragStart(e, deal.id)}
                      onDragEnd={handleDragEnd}
                      className="cursor-grab rounded-lg border border-gray-200 bg-white p-3 shadow-sm transition-shadow hover:shadow-md active:cursor-grabbing"
                    >
                      {/* Card content — click name to open detail */}
                      <div className="flex items-start justify-between">
                        <button onClick={() => navigate(`/crm/deals/${deal.id}`)}
                          className="text-left text-sm font-medium text-gray-900 hover:text-blue-600 line-clamp-2">
                          {deal.name}
                        </button>
                      </div>
                      {deal.client_name && (
                        <p className="mt-0.5 text-xs text-gray-500">{deal.client_name}</p>
                      )}
                      <div className="mt-2 flex items-center justify-between">
                        <span className="text-sm font-semibold text-gray-800">
                          {formatCurrency(deal.expected_revenue)}
                        </span>
                        {deal.deal_type && (
                          <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-600">
                            {DEAL_TYPE_SHORT[deal.deal_type] || deal.deal_type}
                          </span>
                        )}
                      </div>
                      {deal.daily_rate > 0 && (
                        <p className="mt-1 text-[10px] text-gray-400">
                          {formatCurrency(deal.daily_rate)}/gg x {deal.estimated_days}gg
                        </p>
                      )}
                      {/* Action buttons */}
                      <div className="mt-2 flex items-center justify-between">
                        <button onClick={() => navigate(`/crm/deals/${deal.id}`)}
                          className="inline-flex items-center gap-1 rounded bg-blue-50 px-2 py-1 text-[10px] font-medium text-blue-700 hover:bg-blue-100">
                          <Eye className="h-3 w-3" /> Apri
                        </button>
                        {/* Mobile dropdown */}
                        <select
                          className="rounded border border-gray-200 px-1 py-0.5 text-[10px] text-gray-500 sm:hidden"
                          value={deal.stage_id}
                          onChange={(e) => updateDeal.mutate({ dealId: deal.id, stage_id: e.target.value })}
                        >
                          {stages?.map((s: any) => (
                            <option key={s.id} value={s.id}>{s.name}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                  ))}
                  {stageDeals.length === 0 && (
                    <div className="py-8 text-center text-xs text-gray-300">
                      Trascina qui un deal
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        /* ============ TABLE VIEW ============ */
        !deals?.deals?.length ? (
          <EmptyState icon={<Briefcase className="h-12 w-12" />} title="Nessun deal" description="La pipeline e vuota." />
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
                {deals.deals.map((deal: any) => (
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
