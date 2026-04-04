import { useEmailAnalytics } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import PageMeta from '../../components/ui/PageMeta'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import { BarChart3, Mail, MousePointer, AlertTriangle, Users } from 'lucide-react'

export default function EmailAnalyticsPage() {
  const { data, isLoading } = useEmailAnalytics()

  if (isLoading) return <LoadingSpinner />

  return (
    <div className="space-y-6">
      <PageMeta title="Email Analytics" />
      <PageHeader title="Email Analytics" subtitle="Statistiche email marketing" />

      {data && (
        <>
          {/* KPI Cards */}
          <div className="grid gap-3 grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-gray-200 bg-white p-4">
              <div className="flex items-center gap-2 text-gray-400"><Mail className="h-4 w-4" /><span className="text-[10px] font-semibold uppercase">Inviate</span></div>
              <p className="mt-2 text-3xl font-bold text-gray-900">{data.total_sent}</p>
            </div>
            <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
              <div className="flex items-center gap-2 text-blue-400"><BarChart3 className="h-4 w-4" /><span className="text-[10px] font-semibold uppercase">Open rate</span></div>
              <p className="mt-2 text-3xl font-bold text-blue-700">{data.open_rate}%</p>
              <p className="text-xs text-blue-400">{data.total_opened} aperte</p>
            </div>
            <div className="rounded-xl border border-green-200 bg-green-50 p-4">
              <div className="flex items-center gap-2 text-green-400"><MousePointer className="h-4 w-4" /><span className="text-[10px] font-semibold uppercase">Click rate</span></div>
              <p className="mt-2 text-3xl font-bold text-green-700">{data.click_rate}%</p>
              <p className="text-xs text-green-400">{data.total_clicked} click</p>
            </div>
            <div className="rounded-xl border border-red-200 bg-red-50 p-4">
              <div className="flex items-center gap-2 text-red-400"><AlertTriangle className="h-4 w-4" /><span className="text-[10px] font-semibold uppercase">Bounce</span></div>
              <p className="mt-2 text-3xl font-bold text-red-700">{data.bounce_rate}%</p>
              <p className="text-xs text-red-400">{data.total_bounced} bounce</p>
            </div>
          </div>

          {/* Breakdown per template */}
          {data.by_template?.length > 0 && (
            <div>
              <h3 className="mb-3 text-sm font-semibold text-gray-500 uppercase">Per template</h3>
              <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500">Template</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500">Inviate</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold text-blue-500">Aperte</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold text-green-500">Click</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500">Open %</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {data.by_template.map((t: any) => (
                      <tr key={t.template_id}>
                        <td className="px-4 py-2 text-sm font-medium text-gray-900">{t.template_name}</td>
                        <td className="px-4 py-2 text-right text-sm text-gray-600">{t.sent}</td>
                        <td className="px-4 py-2 text-right text-sm text-blue-600">{t.opened}</td>
                        <td className="px-4 py-2 text-right text-sm text-green-600">{t.clicked}</td>
                        <td className="px-4 py-2 text-right text-sm font-medium text-gray-900">{t.open_rate}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Top contacts */}
          {data.top_contacts?.length > 0 && (
            <div>
              <h3 className="mb-3 text-sm font-semibold text-gray-500 uppercase flex items-center gap-2"><Users className="h-4 w-4" /> Top contatti</h3>
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {data.top_contacts.map((c: any) => (
                  <div key={c.contact_id} className="rounded-xl border border-gray-200 bg-white p-3">
                    <p className="font-medium text-gray-900 text-sm truncate">{c.name || c.email}</p>
                    <p className="text-xs text-gray-400 truncate">{c.email}</p>
                    <div className="mt-1 flex gap-3 text-xs">
                      <span className="text-gray-500">{c.total_sent} inviate</span>
                      <span className="text-blue-500">{c.total_opens} aperte</span>
                      <span className="text-green-500">{c.total_clicks} click</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Bounced */}
          {data.bounced_contacts?.length > 0 && (
            <div>
              <h3 className="mb-3 text-sm font-semibold text-red-500 uppercase">Email invalide</h3>
              <div className="flex flex-wrap gap-2">
                {data.bounced_contacts.map((c: any, i: number) => (
                  <span key={i} className="rounded-lg border border-red-200 bg-red-50 px-3 py-1 text-xs text-red-600">{c.email}</span>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
