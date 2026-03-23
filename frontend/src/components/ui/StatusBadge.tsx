import Badge from './Badge'

type BadgeVariant = 'default' | 'success' | 'warning' | 'error' | 'info'

interface StatusBadgeProps {
  status: string
  className?: string
}

const statusMap: Record<string, { label: string; variant: BadgeVariant }> = {
  verified: { label: 'Verificata', variant: 'success' },
  pending_review: { label: 'Da verificare', variant: 'warning' },
  pending: { label: 'In attesa', variant: 'warning' },
  error: { label: 'Errore', variant: 'error' },
  synced: { label: 'Sincronizzata', variant: 'success' },
  draft: { label: 'Bozza', variant: 'default' },
  posted: { label: 'Registrata', variant: 'success' },
  paid: { label: 'Pagato', variant: 'success' },
  unpaid: { label: 'Non pagato', variant: 'error' },
  overdue: { label: 'Scaduto', variant: 'error' },
  approved: { label: 'Approvata', variant: 'success' },
  rejected: { label: 'Rifiutata', variant: 'error' },
  active: { label: 'Attivo', variant: 'success' },
  idle: { label: 'Inattivo', variant: 'default' },
  running: { label: 'In esecuzione', variant: 'info' },
  preserved: { label: 'Conservato', variant: 'success' },
  sent: { label: 'Inviato', variant: 'info' },
  reconciled: { label: 'Riconciliato', variant: 'success' },
  partial: { label: 'Parziale', variant: 'warning' },
}

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  const mapped = statusMap[status] ?? { label: status, variant: 'default' as BadgeVariant }
  return (
    <Badge variant={mapped.variant} className={className}>
      {mapped.label}
    </Badge>
  )
}
