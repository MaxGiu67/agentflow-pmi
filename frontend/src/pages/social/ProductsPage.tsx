import { useState } from 'react'
import { useProducts, useCreateProduct, useUpdateProduct } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import { Plus, Package, ToggleLeft, ToggleRight, Pencil, Trash2, X, Check } from 'lucide-react'
import { formatCurrency } from '../../lib/utils'

export default function ProductsPage() {
  const { data: products, isLoading } = useProducts()
  const createProduct = useCreateProduct()
  const updateProduct = useUpdateProduct()
  const [showForm, setShowForm] = useState(false)
  const [editId, setEditId] = useState<string | null>(null)
  const [form, setForm] = useState({ name: '', code: '', pricing_model: 'fixed', base_price: '', hourly_rate: '', description: '' })
  const [editForm, setEditForm] = useState({ name: '', base_price: '', hourly_rate: '', description: '' })

  const handleCreate = async () => {
    if (!form.code.trim() || !form.name.trim()) return
    await createProduct.mutateAsync({
      ...form,
      base_price: form.base_price ? Number(form.base_price) : undefined,
      hourly_rate: form.hourly_rate ? Number(form.hourly_rate) : undefined,
    })
    setForm({ name: '', code: '', pricing_model: 'fixed', base_price: '', hourly_rate: '', description: '' })
    setShowForm(false)
  }

  const startEdit = (p: any) => {
    setEditId(p.id)
    setEditForm({
      name: p.name || '',
      base_price: p.base_price ? String(p.base_price) : '',
      hourly_rate: p.hourly_rate ? String(p.hourly_rate) : '',
      description: p.description || '',
    })
  }

  const handleSaveEdit = async (id: string) => {
    await updateProduct.mutateAsync({
      id,
      name: editForm.name || undefined,
      base_price: editForm.base_price ? Number(editForm.base_price) : undefined,
      hourly_rate: editForm.hourly_rate ? Number(editForm.hourly_rate) : undefined,
      description: editForm.description || undefined,
    })
    setEditId(null)
  }

  const handleDelete = async (id: string) => {
    // Products use soft-delete (deactivate), hard delete returns 409
    // So we deactivate instead
    await updateProduct.mutateAsync({ id, is_active: false })
  }

  const pricingBadge = (model: string) => {
    const map: Record<string, string> = { fixed: 'bg-blue-100 text-blue-700', hourly: 'bg-amber-100 text-amber-700', custom: 'bg-gray-100 text-gray-600' }
    return <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${map[model] || map.custom}`}>{model}</span>
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Catalogo Prodotti" subtitle="Prodotti e servizi offerti ai clienti"
        actions={
          <button onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
            <Plus className="h-4 w-4" /> Nuovo Prodotto
          </button>
        } />

      {showForm && (
        <div className="rounded-xl border border-blue-200 bg-blue-50/30 p-6 space-y-3">
          <h3 className="font-medium text-gray-900">Nuovo prodotto</h3>
          <div className="grid gap-3 sm:grid-cols-3">
            <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Nome prodotto *" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <input type="text" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })}
              placeholder="Codice (es. custom_dev) *" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            <select value={form.pricing_model} onChange={(e) => setForm({ ...form, pricing_model: e.target.value })}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm">
              <option value="fixed">Prezzo Fisso</option>
              <option value="hourly">A Ore</option>
              <option value="custom">Custom</option>
            </select>
            <input type="number" value={form.base_price} onChange={(e) => setForm({ ...form, base_price: e.target.value })}
              placeholder="Prezzo base (EUR)" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            {form.pricing_model === 'hourly' && (
              <input type="number" value={form.hourly_rate} onChange={(e) => setForm({ ...form, hourly_rate: e.target.value })}
                placeholder="Tariffa oraria (EUR/h)" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
            )}
            <input type="text" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Descrizione" className="rounded-lg border border-gray-300 px-3 py-2 text-sm" />
          </div>
          <div className="flex gap-2">
            <button onClick={handleCreate} disabled={createProduct.isPending || !form.code.trim() || !form.name.trim()}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">Crea</button>
            <button onClick={() => setShowForm(false)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600">Annulla</button>
          </div>
        </div>
      )}

      {isLoading ? <LoadingSpinner /> : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {products?.map((p: any) => (
            <div key={p.id} className={`rounded-xl border bg-white p-4 transition-shadow hover:shadow-md ${!p.is_active ? 'opacity-50' : ''}`}>
              {editId === p.id ? (
                /* ── Edit mode ── */
                <div className="space-y-2">
                  <input type="text" value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                    placeholder="Nome" className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
                  <div className="grid grid-cols-2 gap-2">
                    <input type="number" value={editForm.base_price} onChange={(e) => setEditForm({ ...editForm, base_price: e.target.value })}
                      placeholder="Prezzo base" className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
                    <input type="number" value={editForm.hourly_rate} onChange={(e) => setEditForm({ ...editForm, hourly_rate: e.target.value })}
                      placeholder="Tariffa oraria" className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
                  </div>
                  <input type="text" value={editForm.description} onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                    placeholder="Descrizione" className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm" />
                  <div className="flex gap-2">
                    <button onClick={() => handleSaveEdit(p.id)}
                      className="inline-flex items-center gap-1 rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700">
                      <Check className="h-3 w-3" /> Salva
                    </button>
                    <button onClick={() => setEditId(null)}
                      className="inline-flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-1.5 text-xs text-gray-600">
                      <X className="h-3 w-3" /> Annulla
                    </button>
                  </div>
                </div>
              ) : (
                /* ── View mode ── */
                <>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <Package className="h-5 w-5 text-blue-500" />
                      <h3 className="font-medium text-gray-900">{p.name}</h3>
                    </div>
                    {pricingBadge(p.pricing_model)}
                  </div>
                  <p className="mt-1 font-mono text-xs text-gray-400">{p.code}</p>
                  {p.base_price != null && p.base_price > 0 && <p className="mt-2 text-lg font-semibold text-gray-900">{formatCurrency(p.base_price)}</p>}
                  {p.hourly_rate != null && p.hourly_rate > 0 && <p className="text-sm text-amber-600">{formatCurrency(p.hourly_rate)}/h</p>}
                  {p.description && <p className="mt-1 text-xs text-gray-500 line-clamp-2">{p.description}</p>}
                  <div className="mt-3 flex items-center justify-between">
                    <button onClick={() => updateProduct.mutate({ id: p.id, is_active: !p.is_active })}
                      className={`inline-flex items-center gap-1 text-xs font-medium ${p.is_active ? 'text-green-600' : 'text-gray-400'}`}>
                      {p.is_active ? <ToggleRight className="h-4 w-4" /> : <ToggleLeft className="h-4 w-4" />}
                      {p.is_active ? 'Attivo' : 'Disattivato'}
                    </button>
                    <div className="flex items-center gap-1">
                      <button onClick={() => startEdit(p)} title="Modifica"
                        className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-blue-600">
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                      <button onClick={() => handleDelete(p.id)} title="Disattiva"
                        className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600">
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
