import { Building2 } from 'lucide-react'

interface DealClientCardProps {
  deal: any
}

export default function DealClientCard({ deal }: DealClientCardProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold uppercase text-gray-400">Cliente</h3>
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-600 shrink-0">
            <Building2 className="h-5 w-5" />
          </div>
          <div>
            <p className="font-semibold text-gray-900">{deal.client_name || 'Cliente non specificato'}</p>
            {deal.contact_name && (
              <p className="text-sm text-gray-600">{deal.contact_name}{deal.contact_role ? ` \u2014 ${deal.contact_role}` : ''}</p>
            )}
          </div>
        </div>
        {(deal.client_email || deal.client_phone) && (
          <div className="flex gap-4 text-sm text-gray-500 pl-[52px]">
            {deal.client_email && <span>{deal.client_email}</span>}
            {deal.client_phone && <span>{deal.client_phone}</span>}
          </div>
        )}
      </div>
    </div>
  )
}
