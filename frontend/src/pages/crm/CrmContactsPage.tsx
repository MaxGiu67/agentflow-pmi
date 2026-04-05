import { useState } from 'react'
import { useCrmContacts, useCreateCrmContact, useOrigins } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'
import { Users, Plus, Search, Building, Mail } from 'lucide-react'
import SendEmailModal from '../../components/email/SendEmailModal'

export default function CrmContactsPage() {
  const [search, setSearch] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', phone: '', vat: '', sector: '', city: '', type: 'lead', website: '', notes: '' })
  const [emailTarget, setEmailTarget] = useState<{ email: string; name: string; id: string } | null>(null)

  const { data, isLoading } = useCrmContacts(search)
  const createContact = useCreateCrmContact()
  const { data: origins } = useOrigins(true)

  const handleCreate = async () => {
    if (!form.name.trim()) return
    await createContact.mutateAsync(form)
    setForm({ name: '', email: '', phone: '', vat: '', sector: '', city: '', type: 'lead', website: '', notes: '' })
    setShowForm(false)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Contatti CRM"
        subtitle="Gestione contatti e aziende"
        actions={
          <button
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            Nuovo Contatto
          </button>
        }
      />

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Cerca per nome azienda..."
          className="w-full rounded-lg border border-gray-300 pl-10 pr-4 py-2 text-sm"
        />
      </div>

      {/* New Contact Form */}
      {showForm && (
        <div className="rounded-xl border border-blue-200 bg-blue-50/30 p-6 space-y-3">
          <h3 className="font-medium text-gray-900">Nuovo contatto aziendale</h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Ragione sociale *" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <input type="text" value={form.vat} onChange={(e) => setForm({ ...form, vat: e.target.value })}
              placeholder="P.IVA" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              <option value="lead">Lead</option>
              <option value="prospect">Prospect</option>
              <option value="cliente">Cliente</option>
              <option value="ex_cliente">Ex Cliente</option>
            </select>
            <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
              placeholder="Email" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <input type="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })}
              placeholder="Telefono" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <input type="text" value={form.sector} onChange={(e) => setForm({ ...form, sector: e.target.value })}
              placeholder="Settore (es. Manifatturiero, IT, Servizi)" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <input type="text" value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })}
              placeholder="Citta" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <input type="url" value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })}
              placeholder="Sito web" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <input type="text" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })}
              placeholder="Note" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <select value={(form as any).source || ''} onChange={(e) => setForm({ ...form, source: e.target.value } as any)}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              <option value="">-- Origine (opzionale) --</option>
              {origins?.map((o: any) => <option key={o.id} value={o.label}>{o.label}</option>)}
            </select>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleCreate}
              disabled={createContact.isPending || !form.name.trim()}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {createContact.isPending ? 'Creazione...' : 'Crea contatto'}
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50"
            >
              Annulla
            </button>
          </div>
        </div>
      )}

      {/* Contacts List */}
      {isLoading ? (
        <LoadingSpinner />
      ) : !data?.contacts?.length ? (
        <EmptyState
          icon={<Users className="h-12 w-12" />}
          title="Nessun contatto"
          description="Non ci sono contatti in Odoo CRM. Crea il primo contatto aziendale."
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.contacts.map((c: any) => (
            <div key={c.id} className="rounded-xl border border-gray-200 bg-white p-4 hover:shadow-md transition-shadow">
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-600">
                  <Building className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-gray-900 truncate">{c.name}</p>
                  {c.vat && <p className="text-xs text-gray-400">P.IVA: {c.vat}</p>}
                  {c.email && <p className="mt-1 text-sm text-gray-600 truncate">{c.email}</p>}
                  {c.phone && <p className="text-sm text-gray-500">{c.phone}</p>}
                  {c.city && (
                    <p className="mt-1 text-xs text-gray-400">
                      {c.city}{c.country ? `, ${c.country}` : ''}
                    </p>
                  )}
                  {c.email && (
                    <button onClick={() => setEmailTarget({ email: c.email, name: c.name, id: c.id })}
                      className="mt-2 inline-flex items-center gap-1 rounded-lg bg-purple-50 px-2.5 py-1 text-xs font-medium text-purple-700 hover:bg-purple-100">
                      <Mail className="h-3 w-3" /> Invia email
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      {emailTarget && (
        <SendEmailModal
          open={!!emailTarget}
          onClose={() => setEmailTarget(null)}
          toEmail={emailTarget.email}
          toName={emailTarget.name}
          contactId={emailTarget.id}
        />
      )}
    </div>
  )
}
