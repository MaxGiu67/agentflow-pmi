import { useState } from 'react'
import { useCrmContacts, useCreateCrmContact, useUpdateCrmContact, useDeleteCrmContact, useCrmCompanies, useCreateCrmCompany } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'
import { Users, Plus, Search, Building, Mail, PlusCircle, Pencil, Trash2, X, Check } from 'lucide-react'
import SendEmailModal from '../../components/email/SendEmailModal'

export default function CrmContactsPage() {
  const [search, setSearch] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [emailTarget, setEmailTarget] = useState<{ email: string; name: string; id: string } | null>(null)
  const [editingId, setEditingId] = useState('')
  const [editForm, setEditForm] = useState({ contact_name: '', contact_role: '', email: '', phone: '' })

  // Company autocomplete
  const [companySearch, setCompanySearch] = useState('')
  const [selectedCompanyId, setSelectedCompanyId] = useState('')
  const [selectedCompanyName, setSelectedCompanyName] = useState('')
  const [showCompanyDropdown, setShowCompanyDropdown] = useState(false)
  const [showNewCompany, setShowNewCompany] = useState(false)
  const [newCompany, setNewCompany] = useState({ name: '', vat: '', sector: '', city: '', website: '' })

  // Contact form
  const [form, setForm] = useState({ name: '', email: '', phone: '', contact_role: '' })

  const { data, isLoading } = useCrmContacts(search)
  const { data: companiesData } = useCrmCompanies('')
  const createContact = useCreateCrmContact()
  const updateContact = useUpdateCrmContact()
  const deleteContact = useDeleteCrmContact()
  const createCompany = useCreateCrmCompany()

  const allCompanies = (companiesData?.companies || []).sort((a: any, b: any) => a.name.localeCompare(b.name))
  const filteredCompanies = companySearch.length >= 3
    ? allCompanies.filter((c: any) => c.name.toLowerCase().includes(companySearch.toLowerCase()))
    : allCompanies
  const showAutocomplete = showCompanyDropdown && !selectedCompanyId

  const handleCreateCompany = async () => {
    if (!newCompany.name) return
    const result = await createCompany.mutateAsync(newCompany)
    setSelectedCompanyId(result.id)
    setSelectedCompanyName(result.name)
    setCompanySearch(result.name)
    setShowNewCompany(false)
    setShowCompanyDropdown(false)
    setNewCompany({ name: '', vat: '', sector: '', city: '', website: '' })
  }

  const handleCreate = async () => {
    if (!form.name.trim()) return
    await createContact.mutateAsync({
      ...form,
      company_id: selectedCompanyId || undefined,
      contact_name: form.name,
      contact_role: form.contact_role,
    })
    setForm({ name: '', email: '', phone: '', contact_role: '' })
    setSelectedCompanyId('')
    setSelectedCompanyName('')
    setCompanySearch('')
    setShowForm(false)
  }

  const handleStartEdit = (c: any) => {
    setEditingId(c.id)
    setEditForm({
      contact_name: c.contact_name || '',
      contact_role: c.contact_role || '',
      email: c.email || '',
      phone: c.phone || '',
    })
  }

  const handleSaveEdit = async () => {
    await updateContact.mutateAsync({ id: editingId, ...editForm })
    setEditingId('')
  }

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Eliminare il contatto "${name}"?`)) return
    await deleteContact.mutateAsync(id)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Contatti CRM"
        subtitle="Gestione contatti e aziende"
        actions={
          <button onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
            <Plus className="h-4 w-4" /> Nuovo Contatto
          </button>
        }
      />

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input type="text" value={search} onChange={(e) => setSearch(e.target.value)}
          placeholder="Cerca per nome, azienda, email..."
          className="w-full rounded-lg border border-gray-300 pl-10 pr-4 py-2 text-sm" />
      </div>

      {/* New Contact Form */}
      {showForm && (
        <div className="rounded-xl border border-blue-200 bg-blue-50/30 p-6 space-y-4">

          {/* Step 1: Company autocomplete */}
          <div>
            <h3 className="font-medium text-gray-900 mb-2">1. Azienda</h3>
            {selectedCompanyId ? (
              <div className="flex items-center justify-between rounded-lg bg-blue-50 border border-blue-200 p-3">
                <div className="flex items-center gap-2">
                  <Building className="h-4 w-4 text-blue-600" />
                  <span className="font-medium text-blue-900">{selectedCompanyName}</span>
                </div>
                <button onClick={() => { setSelectedCompanyId(''); setSelectedCompanyName(''); setCompanySearch('') }}
                  className="text-xs text-blue-600 hover:underline">Cambia</button>
              </div>
            ) : showNewCompany ? (
              <div className="rounded-lg border border-gray-200 bg-white p-3 space-y-2">
                <p className="text-xs font-medium text-gray-500">Nuova azienda</p>
                <div className="grid gap-2 sm:grid-cols-3">
                  <input type="text" value={newCompany.name} onChange={(e) => setNewCompany({ ...newCompany, name: e.target.value })}
                    placeholder="Ragione sociale *" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                  <input type="text" value={newCompany.vat} onChange={(e) => setNewCompany({ ...newCompany, vat: e.target.value })}
                    placeholder="P.IVA" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                  <input type="text" value={newCompany.sector} onChange={(e) => setNewCompany({ ...newCompany, sector: e.target.value })}
                    placeholder="Settore" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                  <input type="text" value={newCompany.city} onChange={(e) => setNewCompany({ ...newCompany, city: e.target.value })}
                    placeholder="Citta" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                  <input type="url" value={newCompany.website} onChange={(e) => setNewCompany({ ...newCompany, website: e.target.value })}
                    placeholder="Sito web" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                </div>
                <div className="flex gap-2">
                  <button onClick={handleCreateCompany} disabled={!newCompany.name}
                    className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50">Crea azienda</button>
                  <button onClick={() => setShowNewCompany(false)}
                    className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-600">Annulla</button>
                </div>
              </div>
            ) : (
              <div className="relative">
                <input type="text" value={companySearch}
                  onChange={(e) => { setCompanySearch(e.target.value); setShowCompanyDropdown(true) }}
                  onFocus={() => setShowCompanyDropdown(true)}
                  placeholder="Clicca per vedere tutte — o digita 3+ caratteri per cercare..."
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />

                {/* Autocomplete dropdown */}
                {showAutocomplete && (
                  <div className="absolute z-10 mt-1 w-full rounded-lg border border-gray-200 bg-white shadow-lg max-h-48 overflow-y-auto">
                    {filteredCompanies.map((c: any) => (
                      <button key={c.id}
                        onClick={() => {
                          setSelectedCompanyId(c.id)
                          setSelectedCompanyName(c.name)
                          setCompanySearch(c.name)
                          setShowCompanyDropdown(false)
                        }}
                        className="w-full flex items-center gap-2 px-3 py-2.5 text-left text-sm hover:bg-blue-50 border-b border-gray-100 last:border-0">
                        <Building className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
                        <div>
                          <span className="font-medium">{c.name}</span>
                          {c.city && <span className="text-xs text-gray-400 ml-2">— {c.city}</span>}
                          {c.vat && <span className="text-xs text-gray-400 ml-2">P.IVA: {c.vat}</span>}
                        </div>
                      </button>
                    ))}
                  </div>
                )}

                {companySearch.length >= 3 && filteredCompanies.length === 0 && showCompanyDropdown && (
                  <div className="absolute z-10 mt-1 w-full rounded-lg border border-gray-200 bg-white shadow-lg p-3">
                    <p className="text-xs text-gray-500 mb-2">Nessuna azienda trovata per "{companySearch}"</p>
                    <button onClick={() => { setShowNewCompany(true); setShowCompanyDropdown(false); setNewCompany({ ...newCompany, name: companySearch }) }}
                      className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700">
                      <PlusCircle className="h-3.5 w-3.5" /> Crea "{companySearch}"
                    </button>
                  </div>
                )}

                <button onClick={() => setShowNewCompany(true)}
                  className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:text-blue-700">
                  <PlusCircle className="h-3.5 w-3.5" /> Crea nuova azienda
                </button>
              </div>
            )}
          </div>

          {/* Step 2: Contact info */}
          <div>
            <h3 className="font-medium text-gray-900 mb-2">2. Referente</h3>
            <div className="grid gap-3 sm:grid-cols-2">
              <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="Nome e cognome *" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              <input type="text" value={form.contact_role} onChange={(e) => setForm({ ...form, contact_role: e.target.value })}
                placeholder="Ruolo (es. CEO, CTO, Buyer)" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="Email" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
              <input type="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })}
                placeholder="Telefono" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
          </div>

          <div className="flex gap-2">
            <button onClick={handleCreate} disabled={createContact.isPending || !form.name.trim()}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
              {createContact.isPending ? 'Creazione...' : 'Crea contatto'}
            </button>
            <button onClick={() => setShowForm(false)}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50">Annulla</button>
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
          description="Crea il primo contatto per iniziare a tracciare le relazioni commerciali."
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data.contacts.map((c: any) => (
            <div key={c.id} className="rounded-xl border border-gray-200 bg-white p-4 hover:shadow-md transition-shadow">
              {editingId === c.id ? (
                /* Inline edit mode */
                <div className="space-y-2">
                  <input type="text" value={editForm.contact_name} onChange={(e) => setEditForm({ ...editForm, contact_name: e.target.value })}
                    placeholder="Nome referente" className="w-full rounded border border-gray-300 px-2 py-1 text-sm" />
                  <input type="text" value={editForm.contact_role} onChange={(e) => setEditForm({ ...editForm, contact_role: e.target.value })}
                    placeholder="Ruolo" className="w-full rounded border border-gray-300 px-2 py-1 text-sm" />
                  <input type="email" value={editForm.email} onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                    placeholder="Email" className="w-full rounded border border-gray-300 px-2 py-1 text-sm" />
                  <input type="tel" value={editForm.phone} onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })}
                    placeholder="Telefono" className="w-full rounded border border-gray-300 px-2 py-1 text-sm" />
                  <div className="flex gap-1">
                    <button onClick={handleSaveEdit}
                      className="inline-flex items-center gap-1 rounded bg-green-600 px-2 py-1 text-xs text-white">
                      <Check className="h-3 w-3" /> Salva
                    </button>
                    <button onClick={() => setEditingId('')}
                      className="inline-flex items-center gap-1 rounded border border-gray-300 px-2 py-1 text-xs text-gray-600">
                      <X className="h-3 w-3" /> Annulla
                    </button>
                  </div>
                </div>
              ) : (
                /* Normal view */
                <div className="flex items-start gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-600 flex-shrink-0">
                    <Building className="h-5 w-5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-gray-900 truncate">{c.name}</p>
                    {c.contact_name && (
                      <p className="text-xs text-gray-600">{c.contact_name}{c.contact_role ? ` — ${c.contact_role}` : ''}</p>
                    )}
                    {c.vat && <p className="text-xs text-gray-400">P.IVA: {c.vat}</p>}
                    {c.email && <p className="mt-1 text-sm text-gray-600 truncate">{c.email}</p>}
                    {c.phone && <p className="text-sm text-gray-500">{c.phone}</p>}
                    {c.city && <p className="mt-1 text-xs text-gray-400">{c.city}</p>}

                    <div className="mt-2 flex flex-wrap gap-1">
                      {c.email && (
                        <button onClick={() => setEmailTarget({ email: c.email, name: c.name, id: c.id })}
                          className="inline-flex items-center gap-1 rounded-lg bg-purple-50 px-2.5 py-1 text-xs font-medium text-purple-700 hover:bg-purple-100">
                          <Mail className="h-3 w-3" /> Email
                        </button>
                      )}
                      <button onClick={() => handleStartEdit(c)}
                        className="inline-flex items-center gap-1 rounded-lg bg-gray-50 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-100">
                        <Pencil className="h-3 w-3" /> Modifica
                      </button>
                      <button onClick={() => handleDelete(c.id, c.contact_name || c.name)}
                        className="inline-flex items-center gap-1 rounded-lg bg-red-50 px-2.5 py-1 text-xs font-medium text-red-600 hover:bg-red-100">
                        <Trash2 className="h-3 w-3" /> Elimina
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {emailTarget && (
        <SendEmailModal open={!!emailTarget} onClose={() => setEmailTarget(null)}
          toEmail={emailTarget.email} toName={emailTarget.name} contactId={emailTarget.id} />
      )}
    </div>
  )
}
