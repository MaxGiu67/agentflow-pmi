import { useState } from 'react'
import {
  useDealResources, useAddDealResource, useUpdateDealResource, useRemoveDealResource,
  useDealRequiresResources, usePortalPersons,
} from '../../../api/hooks'
import { useUIHighlights, AIHighlightTooltip } from '../../../context/UIHighlightContext'
import { formatCurrency } from '../../../lib/utils'
import { Users, Plus, X, Pencil, ChevronUp, Save, Trash2 } from 'lucide-react'

interface DealResourcesProps {
  deal: any
  dealId: string
  portalEnabled: boolean
}

export default function DealResources({ deal: _deal, dealId, portalEnabled }: DealResourcesProps) {
  void _deal
  const { data: dealResources } = useDealResources(dealId)
  const { data: requiresResourcesData } = useDealRequiresResources(dealId)
  const addDealResource = useAddDealResource()
  const updateDealResource = useUpdateDealResource()
  const removeDealResource = useRemoveDealResource()

  const [personSearch, setPersonSearch] = useState('')
  const { data: searchedPersons } = usePortalPersons(personSearch)

  const [showResourceForm, setShowResourceForm] = useState(false)
  const [resourceForm, setResourceForm] = useState({ portal_person_id: '', person_name: '', role: '', start_date: '', end_date: '' })
  const [editingResourceId, setEditingResourceId] = useState<string | null>(null)
  const [editResForm, setEditResForm] = useState({ role: '', start_date: '', end_date: '', status: '' })

  const { getHighlight, clearHighlights } = useUIHighlights()
  const resourcesSectionHL = getHighlight('section', 'resources')

  if (!portalEnabled) return null
  if (!requiresResourcesData?.requires_resources && !(dealResources && dealResources.length > 0)) return null

  return (
    <div className="rounded-2xl border border-teal-200 bg-teal-50/20 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Users className="h-4 w-4 text-teal-600" />
          <h3 className={`text-sm font-semibold uppercase text-teal-600 ${resourcesSectionHL ? 'ai-highlight-badge' : ''}`}
            style={resourcesSectionHL ? { '--ai-color': resourcesSectionHL.color } as React.CSSProperties : undefined}>Risorse</h3>
          {resourcesSectionHL && <AIHighlightTooltip highlight={resourcesSectionHL} onDismiss={clearHighlights} />}
        </div>
        <button onClick={() => { setShowResourceForm(!showResourceForm); setPersonSearch('') }}
          className="inline-flex items-center gap-1 rounded-lg bg-teal-50 px-3 py-1.5 text-xs font-medium text-teal-700 hover:bg-teal-100">
          <Plus className="h-3 w-3" /> Aggiungi Risorsa
        </button>
      </div>

      {/* Add resource form */}
      {showResourceForm && (
        <div className="mb-4 rounded-lg border border-teal-200 bg-white p-4 space-y-3">
          <div>
            <input type="text" value={personSearch} onChange={(e) => setPersonSearch(e.target.value)}
              placeholder="Cerca persona per nome..." className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            {personSearch.length >= 2 && searchedPersons?.persons && searchedPersons.persons.length > 0 && (
              <div className="mt-1 max-h-40 overflow-y-auto rounded-lg border border-gray-200 bg-white">
                {searchedPersons.persons.map((p: any) => (
                  <button key={p.portal_id} onClick={() => {
                    setResourceForm({
                      ...resourceForm,
                      portal_person_id: String(p.portal_id),
                      person_name: p.full_name || `${p.firstName || ''} ${p.lastName || ''}`.trim(),
                    })
                    setPersonSearch('')
                  }}
                    className="w-full text-left px-3 py-2 text-sm hover:bg-teal-50 border-b border-gray-100 last:border-0">
                    <span className="font-medium">{p.full_name || `${p.firstName || ''} ${p.lastName || ''}`.trim()}</span>
                    {p.seniority && <span className="text-xs text-gray-400 ml-2">{typeof p.seniority === 'object' ? p.seniority.description : p.seniority}</span>}
                    {p.skills?.length > 0 && <span className="text-xs text-gray-400 ml-2">({p.skills.map((s: any) => s.name).join(', ')})</span>}
                  </button>
                ))}
              </div>
            )}
          </div>
          {resourceForm.portal_person_id && (
            <div className="flex items-center gap-2 rounded-lg bg-teal-50 px-3 py-2">
              <span className="text-sm font-medium text-teal-800">{resourceForm.person_name}</span>
              <button onClick={() => setResourceForm({ ...resourceForm, portal_person_id: '', person_name: '' })}
                className="text-teal-400 hover:text-red-500"><X className="h-3.5 w-3.5" /></button>
            </div>
          )}
          <input type="text" value={resourceForm.role} onChange={(e) => setResourceForm({ ...resourceForm, role: e.target.value })}
            placeholder="Ruolo (es. Frontend Developer, PM, ...)" className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          <div className="grid gap-2 sm:grid-cols-2">
            <div>
              <label className="block text-[10px] text-gray-400 mb-0.5">Data inizio</label>
              <input type="date" value={resourceForm.start_date} onChange={(e) => setResourceForm({ ...resourceForm, start_date: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="block text-[10px] text-gray-400 mb-0.5">Data fine</label>
              <input type="date" value={resourceForm.end_date} onChange={(e) => setResourceForm({ ...resourceForm, end_date: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={async () => {
              if (!resourceForm.portal_person_id) return
              await addDealResource.mutateAsync({
                dealId,
                portal_person_id: parseInt(resourceForm.portal_person_id),
                person_name: resourceForm.person_name,
                role: resourceForm.role || undefined,
                start_date: resourceForm.start_date || undefined,
                end_date: resourceForm.end_date || undefined,
              })
              setResourceForm({ portal_person_id: '', person_name: '', role: '', start_date: '', end_date: '' })
              setShowResourceForm(false)
            }} disabled={!resourceForm.portal_person_id || addDealResource.isPending}
              className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
              {addDealResource.isPending ? 'Aggiunta...' : 'Aggiungi'}
            </button>
            <button onClick={() => setShowResourceForm(false)}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600">Annulla</button>
          </div>
        </div>
      )}

      {/* Resource list */}
      {dealResources && dealResources.length > 0 ? (
        <div className="space-y-2">
          {dealResources.map((res: any) => {
            const isEditingRes = editingResourceId === res.id
            const statusColors: Record<string, string> = {
              assigned: 'bg-blue-100 text-blue-700',
              active: 'bg-green-100 text-green-700',
              released: 'bg-gray-100 text-gray-500',
            }
            return (
              <div key={res.id} className="rounded-lg border border-teal-100 bg-white px-4 py-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-teal-100 text-teal-600 text-xs font-bold shrink-0">
                      {(res.person_name || '?').charAt(0).toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-gray-900">{res.person_name || `Person #${res.portal_person_id}`}</p>
                        <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${statusColors[res.status] || statusColors.assigned}`}>
                          {res.status === 'assigned' ? 'Assegnato' : res.status === 'active' ? 'Attivo' : 'Rilasciato'}
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-gray-500 mt-0.5">
                        {res.role && <span>{res.role}</span>}
                        {res.seniority && <span>{res.seniority}</span>}
                        {res.daily_cost != null && <span>{formatCurrency(res.daily_cost)}/gg</span>}
                        {res.start_date && <span>dal {new Date(res.start_date).toLocaleDateString('it-IT')}</span>}
                        {res.end_date && <span>al {new Date(res.end_date).toLocaleDateString('it-IT')}</span>}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <button onClick={() => {
                      if (isEditingRes) {
                        setEditingResourceId(null)
                      } else {
                        setEditingResourceId(res.id)
                        setEditResForm({
                          role: res.role || '',
                          start_date: res.start_date || '',
                          end_date: res.end_date || '',
                          status: res.status || 'assigned',
                        })
                      }
                    }}
                      className={`rounded px-2 py-1 text-[10px] font-medium ${isEditingRes ? 'bg-teal-100 text-teal-700' : 'bg-gray-50 text-gray-500 hover:bg-gray-100'}`}>
                      {isEditingRes ? <ChevronUp className="h-3 w-3" /> : <Pencil className="h-3 w-3" />}
                    </button>
                    <button onClick={() => {
                      if (confirm(`Rimuovere ${res.person_name || 'questa risorsa'}?`))
                        removeDealResource.mutate({ dealId, resourceId: res.id })
                    }}
                      className="text-gray-300 hover:text-red-500"><Trash2 className="h-3.5 w-3.5" /></button>
                  </div>
                </div>

                {/* Inline edit for resource */}
                {isEditingRes && (
                  <div className="mt-3 space-y-2 border-t border-gray-100 pt-3">
                    <input type="text" value={editResForm.role} onChange={(e) => setEditResForm({ ...editResForm, role: e.target.value })}
                      placeholder="Ruolo" className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
                    <div className="grid gap-2 sm:grid-cols-3">
                      <div>
                        <label className="block text-[10px] text-gray-400 mb-0.5">Data inizio</label>
                        <input type="date" value={editResForm.start_date} onChange={(e) => setEditResForm({ ...editResForm, start_date: e.target.value })}
                          className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
                      </div>
                      <div>
                        <label className="block text-[10px] text-gray-400 mb-0.5">Data fine</label>
                        <input type="date" value={editResForm.end_date} onChange={(e) => setEditResForm({ ...editResForm, end_date: e.target.value })}
                          className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
                      </div>
                      <div>
                        <label className="block text-[10px] text-gray-400 mb-0.5">Stato</label>
                        <select value={editResForm.status} onChange={(e) => setEditResForm({ ...editResForm, status: e.target.value })}
                          className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm">
                          <option value="assigned">Assegnato</option>
                          <option value="active">Attivo</option>
                          <option value="released">Rilasciato</option>
                        </select>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={async () => {
                        await updateDealResource.mutateAsync({
                          dealId,
                          resourceId: res.id,
                          role: editResForm.role || undefined,
                          start_date: editResForm.start_date || undefined,
                          end_date: editResForm.end_date || undefined,
                          status: editResForm.status,
                        })
                        setEditingResourceId(null)
                      }} disabled={updateDealResource.isPending}
                        className="inline-flex items-center gap-1 rounded-lg bg-teal-600 px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50">
                        <Save className="h-3 w-3" /> {updateDealResource.isPending ? 'Salvataggio...' : 'Salva'}
                      </button>
                      <button onClick={() => setEditingResourceId(null)}
                        className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-600">Annulla</button>
                    </div>
                  </div>
                )}
              </div>
            )
          })}

          {/* Total daily cost */}
          {(() => {
            const totalCost = dealResources.reduce((sum: number, r: any) => sum + (r.daily_cost || 0), 0)
            if (totalCost > 0) {
              return (
                <div className="flex items-center justify-end gap-2 pt-2 border-t border-teal-100">
                  <span className="text-xs text-gray-400">Costo giornaliero totale:</span>
                  <span className="text-sm font-bold text-teal-700">{formatCurrency(totalCost)}/gg</span>
                </div>
              )
            }
            return null
          })()}
        </div>
      ) : (
        <p className="text-sm text-gray-400 text-center py-4">Nessuna risorsa assegnata</p>
      )}
    </div>
  )
}
