import { useState } from 'react'
import { useTeamUsers, useInviteUser, useUpdateUserRole, useToggleUserActive, useMyPermissions } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import PageMeta from '../../components/ui/PageMeta'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import Badge from '../../components/ui/Badge'
import { Users, Plus, Shield, UserX, UserCheck, Copy } from 'lucide-react'

const ROLES = [
  { value: 'owner', label: 'Owner', color: 'error' as const },
  { value: 'admin', label: 'Admin', color: 'warning' as const },
  { value: 'commerciale', label: 'Commerciale', color: 'info' as const },
  { value: 'viewer', label: 'Viewer', color: 'default' as const },
]

export default function UsersPage() {
  const { data: users, isLoading } = useTeamUsers()
  const { data: perms } = useMyPermissions()
  const inviteUser = useInviteUser()
  const updateRole = useUpdateUserRole()
  const toggleActive = useToggleUserActive()

  const [showInvite, setShowInvite] = useState(false)
  const [form, setForm] = useState({ email: '', name: '', role: 'commerciale' })
  const [inviteResult, setInviteResult] = useState<any>(null)

  const canManage = perms?.can_manage_users

  const handleInvite = async () => {
    const result = await inviteUser.mutateAsync(form)
    setInviteResult(result)
    setForm({ email: '', name: '', role: 'commerciale' })
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
            return (
              <div key={u.id} className={`rounded-xl border bg-white p-4 ${u.active === false ? 'border-gray-300 opacity-60' : 'border-gray-200'}`}>
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-purple-100 text-purple-600 text-sm font-bold shrink-0">
                      {(u.name || u.email).charAt(0).toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-gray-900 truncate">{u.name || u.email}</p>
                        <Badge variant={roleInfo.color}>{roleInfo.label}</Badge>
                        {u.active === false && <Badge variant="error">Disattivato</Badge>}
                      </div>
                      <p className="text-xs text-gray-400 truncate">{u.email}</p>
                      {u.sender_email && <p className="text-[10px] text-gray-300">Sender: {u.sender_email}</p>}
                    </div>
                  </div>

                  {canManage && (
                    <div className="flex items-center gap-2 shrink-0">
                      <select
                        value={u.role}
                        onChange={(e) => updateRole.mutate({ userId: u.id, role: e.target.value })}
                        className="rounded border border-gray-200 px-2 py-1 text-xs"
                      >
                        {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
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
