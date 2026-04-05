import { useRoles, useCreateRole, useDeleteRole } from '../../api/hooks'
import { useState } from 'react'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import { Plus, Shield, Trash2, Lock } from 'lucide-react'

const ENTITIES = ['contacts', 'deals', 'activities', 'pipelines', 'sequences', 'reports', 'audit_log', 'settings']
const PERMISSIONS = ['create', 'read', 'update', 'delete', 'export', 'view_all']

export default function RolesPage() {
  const { data: roles, isLoading } = useRoles()
  const createRole = useCreateRole()
  const deleteRole = useDeleteRole()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', description: '' })
  const [matrix, setMatrix] = useState<Record<string, string[]>>({})

  const togglePerm = (entity: string, perm: string) => {
    setMatrix((prev) => {
      const current = prev[entity] || []
      const has = current.includes(perm)
      return { ...prev, [entity]: has ? current.filter((p) => p !== perm) : [...current, perm] }
    })
  }

  const handleCreate = async () => {
    if (!form.name.trim()) return
    await createRole.mutateAsync({ name: form.name, description: form.description, permissions: matrix })
    setForm({ name: '', description: '' })
    setMatrix({})
    setShowForm(false)
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Ruoli RBAC" subtitle="Configura i permessi per ogni ruolo del team"
        actions={<button onClick={() => setShowForm(true)}
          className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          <Plus className="h-4 w-4" /> Nuovo Ruolo</button>} />

      {showForm && (
        <div className="rounded-xl border border-blue-200 bg-blue-50/30 p-6 space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Nome ruolo *" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <input type="text" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Descrizione" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </div>
          <div className="overflow-x-auto">
            <table className="text-xs">
              <thead>
                <tr>
                  <th className="px-2 py-1 text-left text-gray-500">Entita</th>
                  {PERMISSIONS.map((p) => <th key={p} className="px-2 py-1 text-center text-gray-500">{p}</th>)}
                </tr>
              </thead>
              <tbody>
                {ENTITIES.map((entity) => (
                  <tr key={entity} className="border-t border-gray-100">
                    <td className="px-2 py-1 font-medium text-gray-700">{entity}</td>
                    {PERMISSIONS.map((perm) => (
                      <td key={perm} className="px-2 py-1 text-center">
                        <input type="checkbox" checked={(matrix[entity] || []).includes(perm)}
                          onChange={() => togglePerm(entity, perm)} className="rounded border-gray-300" />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex gap-2">
            <button onClick={handleCreate} disabled={createRole.isPending || !form.name.trim()}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">Crea Ruolo</button>
            <button onClick={() => setShowForm(false)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600">Annulla</button>
          </div>
        </div>
      )}

      {isLoading ? <LoadingSpinner /> : (
        <div className="space-y-3">
          {roles?.map((role: any) => (
            <div key={role.id} className="rounded-xl border border-gray-200 bg-white p-5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Shield className={`h-5 w-5 ${role.is_system_role ? 'text-amber-500' : 'text-blue-500'}`} />
                  <div>
                    <h3 className="font-medium text-gray-900">{role.name}
                      {role.is_system_role && <Lock className="ml-1 inline h-3 w-3 text-amber-400" />}
                    </h3>
                    <p className="text-xs text-gray-500">{role.description}</p>
                  </div>
                </div>
                {!role.is_system_role && (
                  <button onClick={() => deleteRole.mutate(role.id)}
                    className="text-red-400 hover:text-red-600"><Trash2 className="h-4 w-4" /></button>
                )}
              </div>
              {role.permissions && Object.keys(role.permissions).length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1">
                  {Object.entries(role.permissions).map(([entity, perms]) => (
                    <span key={entity} className="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] text-gray-600">
                      {entity}: {(perms as string[]).join(', ')}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
