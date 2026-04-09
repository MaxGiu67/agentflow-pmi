import { useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  useCrmDeal, usePortalStatus, usePipelineTemplates,
  usePortalAccountManagers,
} from '../../api/hooks'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import SendEmailModal from '../../components/email/SendEmailModal'

import DealHeader from './deal-detail/DealHeader'
import DealClientCard from './deal-detail/DealClientCard'
import DealDetailsCard from './deal-detail/DealDetailsCard'
import DealOrderCard from './deal-detail/DealOrderCard'
import DealDocuments from './deal-detail/DealDocuments'
import DealResources from './deal-detail/DealResources'
import DealPortalWorkflow from './deal-detail/DealPortalWorkflow'
import DealActivities from './deal-detail/DealActivities'
import DealProgress from './deal-detail/DealProgress'

export default function CrmDealDetailPage() {
  const { dealId } = useParams()
  const id = dealId || ''

  const { data: deal, isLoading } = useCrmDeal(id)
  const { data: portalStatus } = usePortalStatus()
  const { data: pipelineTemplates } = usePipelineTemplates()
  const { data: accountManagers } = usePortalAccountManagers()

  const [showEmailModal, setShowEmailModal] = useState(false)
  const [editMode, setEditMode] = useState(false)

  if (isLoading) return <LoadingSpinner />
  if (!deal) return <div className="p-8 text-center text-gray-500">Deal non trovato</div>

  return (
    <div className="space-y-6">
      <DealHeader
        deal={deal}
        pipelineTemplates={pipelineTemplates}
        editMode={editMode}
        onToggleEdit={() => setEditMode(!editMode)}
        onOpenEmail={() => setShowEmailModal(true)}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        {/* ── Cliente + Dettagli ── */}
        <div className="rounded-2xl border border-gray-200 bg-white p-6 space-y-4">
          <DealClientCard deal={deal} />
          <DealDetailsCard deal={deal} dealId={id} editMode={editMode} setEditMode={setEditMode} />
        </div>

        {/* ── Ordine ── */}
        <DealOrderCard deal={deal} dealId={id} />
      </div>

      {/* ── Risorse ── */}
      <DealResources deal={deal} dealId={id} portalEnabled={!!portalStatus?.enabled} />

      {/* ── Documenti ── */}
      <DealDocuments deal={deal} dealId={id} />

      {/* ── Operativo Portal ── */}
      <DealPortalWorkflow
        deal={deal}
        dealId={id}
        portalEnabled={!!portalStatus?.enabled}
        accountManagers={accountManagers}
      />

      {/* ── Avanzamento Operativo ── */}
      <DealProgress deal={deal} dealId={id} portalEnabled={!!portalStatus?.enabled} />

      {/* ── Attivita + Email History ── */}
      <DealActivities deal={deal} />

      <SendEmailModal open={showEmailModal} onClose={() => setShowEmailModal(false)}
        toEmail="" toName={deal.client_name} contactId={deal.client_id}
        defaultParams={{ deal_name: deal.name, deal_value: String(deal.expected_revenue) }} />
    </div>
  )
}
