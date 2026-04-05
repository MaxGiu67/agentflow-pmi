import { useState } from 'react'
import { useAuditLog } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import { Download } from 'lucide-react'
import api from '../../api/client'

const ACTION_COLORS: Record<string, string> = {
  create_contact: 'text-green-600', update_deal: 'text-blue-600', login: 'text-gray-500',
  permission_denied: 'text-red-600', export_csv: 'text-purple-600', delete_contact: 'text-red-500',
}

export default function AuditLogPage() {
  const [filter, setFilter] = useState('')
  const [page, setPage] = useState(0)
  const { data, isLoading } = useAuditLog({ action: filter || undefined, limit: 30, offset: page * 30 })

  const handleExport = async () => {
    const resp = await api.get('/social/audit-log/export', { responseType: 'blob' })
    const url = URL.createObjectURL(resp.data)
    const a = document.createElement('a')
    a.href = url
    a.download = 'audit_log.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Audit Log" subtitle="Log immutabile di tutte le azioni utente"
        actions={<button onClick={handleExport}
          className="inline-flex items-center gap-2 rounded-lg bg-gray-800 px-4 py-2 text-sm font-medium text-white hover:bg-gray-700">
          <Download className="h-4 w-4" /> Esporta CSV</button>} />

      <div className="flex items-center gap-3">
        <select value={filter} onChange={(e) => { setFilter(e.target.value); setPage(0) }}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
          <option value="">Tutte le azioni</option>
          <option value="create_contact">Crea contatto</option>
          <option value="update_deal">Modifica deal</option>
          <option value="login">Login</option>
          <option value="permission_denied">Accesso negato</option>
          <option value="export_csv">Export</option>
        </select>
        {data?.meta && <span className="text-xs text-gray-400">{data.meta.total} eventi totali</span>}
      </div>

      {isLoading ? <LoadingSpinner /> : (
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs font-semibold uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3">Timestamp</th>
                <th className="px-4 py-3">Azione</th>
                <th className="px-4 py-3">Entita</th>
                <th className="px-4 py-3">Dettaglio</th>
                <th className="px-4 py-3">Stato</th>
                <th className="px-4 py-3">IP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data?.data?.map((log: any) => (
                <tr key={log.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">{log.created_at?.split('T')[0]} {log.created_at?.split('T')[1]?.slice(0, 5)}</td>
                  <td className={`px-4 py-3 font-medium ${ACTION_COLORS[log.action] || 'text-gray-700'}`}>{log.action}</td>
                  <td className="px-4 py-3 text-gray-600">{log.entity_type}</td>
                  <td className="px-4 py-3 text-gray-500 truncate max-w-[200px]">{log.entity_name || '-'}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                      log.status === 'success' ? 'bg-green-50 text-green-600' :
                      log.status === 'denied' ? 'bg-red-50 text-red-600' : 'bg-gray-100 text-gray-600'
                    }`}>{log.status}</span>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-400">{log.ip_address || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data?.meta && data.meta.total > 30 && (
        <div className="flex justify-center gap-2">
          <button disabled={page === 0} onClick={() => setPage(page - 1)}
            className="rounded-lg border px-3 py-1 text-sm disabled:opacity-30">Precedente</button>
          <span className="px-3 py-1 text-sm text-gray-500">Pagina {page + 1}</span>
          <button onClick={() => setPage(page + 1)}
            className="rounded-lg border px-3 py-1 text-sm">Successiva</button>
        </div>
      )}
    </div>
  )
}
