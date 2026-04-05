import { useState } from 'react'
import { useTeamUsers, useInviteUser, useUpdateUserRole, useUpdateUserCrmRole, useToggleUserActive, useMyPermissions, useOrigins, useProducts, useRoles } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import PageMeta from '../../components/ui/PageMeta'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import Badge from '../../components/ui/Badge'
import { Plus, UserX, UserCheck, Copy, ExternalLink, Clock } from 'lucide-react'

const ROLES = [
  { value: 'owner', label: 'Owner', color: 'error' as const },
  { value: 'admin', label: 'Admin', color: 'warning' as const },
  { value: 'commerciale', label: 'Commerciale', color: 'info' as const },
  { value: 'viewer', label: 'Viewer', color: 'default' as const },
]

export default function UsersPage() {
  const { data: users, isLoading } = useTeamUsers()
  const { data: perms } = useMyPermissions()
  const { data: origins } = useOrigins(true)
  const { data: products } = useProducts(true)
  const { data: crmRoles } = useRoles()
  const inviteUser = useInviteUser()
  const updateRole = useUpdateUserRole()
  const updateCrmRole = useUpdateUserCrmRole()
  const toggleActive = useToggleUserActive()

  const [showInvite, setShowInvite] = useState(false)
  const [form, setForm] = useState({
    email: '', name: '', role: 'commerciale',
    user_type: 'internal', access_expires_at: '',
    default_origin_id: '', default_product_id: '', crm_role_id: '',
  })
  const [inviteResult, setInviteResult] = useState<any>(null)

  const canManage = perms?.can_manage_users

  const handleInvite = async () => {
    const payload: any = { email: form.email, name: form.name, role: form.role, user_type: form.user_type }
    if (form.user_type === 'external') {
      if (form.access_expires_at) payload.access_expires_at = form.access_expires_at + 'T23:59:59Z'
      if (form.default_origin_id) payload.default_origin_id = form.default_origin_id
      if (form.default_product_id) payload.default_product_id = form.default_product_id
      if (form.crm_role_id) payload.crm_role_id = form.crm_role_id
    }
    const result = await inviteUser.mutateAsync(payload)
    setInviteResult(result)
    setForm({ email: '', name: '', role: 'commerciale', user_type: 'internal', access_expires_at: '', default_origin_id: '', default_product_id: '', crm_role_id: '' })
  }

  return (
    <div className="space-y-4">
      <PageMeta title="Gestione Utenti" />
      <PageHeader
        title="Gestione Utenti"
        subtitle="Team e permessi"
        actions={canManage ? (
          <button onClick={() => setShowInvite(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
            <Plus className="h-4 w-4" /> Invita utente
          </button>
        ) : undefined}
      />

      {/* Invite form */}
      {showInvite && (
        <div className="rounded-xl border border-blue-200 bg-blue-50/30 p-4 space-y-3">
          <h3 className="font-medium text-gray-900">Invita nuovo utente</h3>
          <div className="grid gap-3 sm:grid-cols-3">
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Nome *" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="Email *" type="email" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
          </div>

          {/* User type toggle */}
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input type="radio" name="user_type" value="internal" checked={form.user_type === 'internal'}
                onChange={() => setForm({ ...form, user_type: 'internal' })} />
              Interno
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="radio" name="user_type" value="external" checked={form.user_type === 'external'}
                onChange={() => setForm({ ...form, user_type: 'external' })} />
              Esterno (freelancer/partner)
            </label>
          </div>

          {/* External user fields */}
          {form.user_type === 'external' && (
            <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-3 space-y-3">
              <p className="text-xs font-medium text-amber-700">Configurazione utente esterno</p>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Scadenza accesso *</label>
                  <input type="date" value={form.access_expires_at}
                    onChange={(e) => setForm({ ...form, access_expires_at: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Ruolo CRM</label>
                  <select value={form.crm_role_id} onChange={(e) => setForm({ ...form, crm_role_id: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
                    <option value="">-- Nessun ruolo CRM --</option>
                    {crmRoles?.map((r: any) => <option key={r.id} value={r.id}>{r.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Canale default (origine)</label>
                  <select value={form.default_origin_id} onChange={(e) => setForm({ ...form, default_origin_id: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
                    <option value="">-- Nessun canale --</option>
                    {origins?.map((o: any) => <option key={o.id} value={o.id}>{o.label}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Prodotto default</label>
                  <select value={form.default_product_id} onChange={(e) => setForm({ ...form, default_product_id: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
                    <option value="">-- Nessun prodotto --</option>
                    {products?.map((p: any) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </div>
              </div>
            </div>
          )}

          <div className="flex gap-2">
            <button onClick={handleInvite} disabled={inviteUser.isPending || !form.email || !form.name}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">Invita</button>
            <button onClick={() => { setShowInvite(false); setInviteResult(null) }}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600">Annulla</button>
          </div>
        </div>
      )}

      {/* Invite success with temp password */}
      {inviteResult && !inviteResult.error && (
        <div className="rounded-xl border border-green-200 bg-green-50 p-4">
          <p className="font-medium text-green-800">Utente invitato: {inviteResult.name} ({inviteResult.email})</p>
          <div className="mt-2 flex items-center gap-2">
            <span className="text-sm text-green-600">Password temporanea:</span>
            <code className="rounded bg-white px-2 py-1 text-sm font-mono font-bold text-green-800 border border-green-200">{inviteResult.temp_password}</code>
            <button onClick={() => navigator.clipboard.writeText(inviteResult.temp_password)} className="text-green-500 hover:text-green-700"><Copy className="h-4 w-4" /></button>
          </div>
          <p className="mt-1 text-xs text-green-500">Comunica questa password all'utente. Non verra piu mostrata.</p>
        </div>
      )}

      {/* Users list */}
      {isLoading ? <LoadingSpinner /> : (
        <div className="space-y-2">
          {users?.map((u: any) => {
            const roleInfo = ROLES.find((r) => r.value === u.role) || ROLES[3]
            const isExternal = u.user_type === 'external'
            const isExpired = u.access_expires_at && new Date(u.access_expires_at) < new Date()
            return (
              <div key={u.id} className={`rounded-xl border bg-white p-4 ${u.active === false ? 'border-gray-300 opacity-60' : 'border-gray-200'}`}>
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div className={`flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold shrink-0 ${isExternal ? 'bg-amber-100 text-amber-600' : 'bg-purple-100 text-purple-600'}`}>
                      {(u.name || u.email).charAt(0).toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="font-medium text-gray-900 truncate">{u.name || u.email}</p>
                        <Badge variant={roleInfo.color}>{roleInfo.label}</Badge>
                        {isExternal && <Badge variant="warning"><ExternalLink className="mr-1 inline h-3 w-3" />Esterno</Badge>}
                        {u.active === false && <Badge variant="error">Disattivato</Badge>}
                        {isExpired && <Badge variant="error"><Clock className="mr-1 inline h-3 w-3" />Scaduto</Badge>}
                      </div>
                      <p className="text-xs text-gray-400 truncate">{u.email}</p>
                      {u.access_expires_at && (
                        <p className="text-[10px] text-amber-500">Accesso fino al {u.access_expires_at.split('T')[0]}</p>
                      )}
                      {u.sender_email && <p className="text-[10px] text-gray-300">Sender: {u.sender_email}</p>}
                    </div>
                  </div>

                  {canManage && (
                    <div className="flex items-center gap-2 shrink-0">
                      <select
                        value={u.role}
                        onChange={(e) => updateRole.mutate({ userId: u.id, role: e.target.value })}
                        className="rounded border border-gray-200 px-2 py-1 text-xs"
                        title="Ruolo sistema"
                      >
                        {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                      </select>
                      <select
                        value={u.crm_role_id || ''}
                        onChange={(e) => updateCrmRole.mutate({ userId: u.id, crm_role_id: e.target.value || null })}
                        className="rounded border border-gray-200 px-2 py-1 text-xs max-w-[140px]"
                        title="Ruolo CRM"
                      >
                        <option value="">-- Ruolo CRM --</option>
                        {crmRoles?.map((r: any) => <option key={r.id} value={r.id}>{r.name}</option>)}
                      </select>
                      <button
                        onClick={() => toggleActive.mutate(u.id)}
                        className={`rounded-lg p-1.5 ${u.active !== false ? 'text-red-400 hover:bg-red-50' : 'text-green-400 hover:bg-green-50'}`}
                        title={u.active !== false ? 'Disattiva' : 'Riattiva'}
                      >
                        {u.active !== false ? <UserX className="h-4 w-4" /> : <UserCheck className="h-4 w-4" />}
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
