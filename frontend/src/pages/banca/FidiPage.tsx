import { useState } from 'react'
import { useFidi, useCreateFido, useBankAccounts } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import PageMeta from '../../components/ui/PageMeta'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'
import { formatCurrency } from '../../lib/utils'
import { Shield, Plus } from 'lucide-react'

export default function FidiPage() {
  const { data: fidi, isLoading } = useFidi()
  const { data: bankAccounts } = useBankAccounts()
  const createFido = useCreateFido()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ bank_account_id: '', plafond: '', percentuale_anticipo: '80', tasso_interesse_annuo: '0', commissione_presentazione_pct: '0', commissione_incasso: '0', commissione_insoluto: '0' })

  const handleCreate = async () => {
    await createFido.mutateAsync({
      bank_account_id: form.bank_account_id,
      plafond: parseFloat(form.plafond),
      percentuale_anticipo: parseFloat(form.percentuale_anticipo),
      tasso_interesse_annuo: parseFloat(form.tasso_interesse_annuo),
      commissione_presentazione_pct: parseFloat(form.commissione_presentazione_pct),
      commissione_incasso: parseFloat(form.commissione_incasso),
      commissione_insoluto: parseFloat(form.commissione_insoluto),
    })
    setShowForm(false)
  }

  return (
    <div className="space-y-4">
      <PageMeta title="Fidi Bancari" />
      <PageHeader title="Fidi Bancari" subtitle="Configurazione anticipo fatture per banca"
        actions={<button onClick={() => setShowForm(true)} className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"><Plus className="h-4 w-4" /> Nuovo fido</button>}
      />

      {showForm && (
        <div className="rounded-xl border border-blue-200 bg-blue-50/30 p-4 space-y-3">
          <select value={form.bank_account_id} onChange={(e) => setForm({ ...form, bank_account_id: e.target.value })} className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm">
            <option value="">Seleziona banca *</option>
            {bankAccounts?.map((b: any) => <option key={b.id} value={b.id}>{b.bank_name} — {b.iban}</option>)}
          </select>
          <div className="grid gap-3 sm:grid-cols-3">
            <div><label className="text-xs text-gray-500">Plafond EUR</label><input type="number" value={form.plafond} onChange={(e) => setForm({ ...form, plafond: e.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" /></div>
            <div><label className="text-xs text-gray-500">% Anticipo</label><input type="number" value={form.percentuale_anticipo} onChange={(e) => setForm({ ...form, percentuale_anticipo: e.target.value })} className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" /></div>
            <div><label className="text-xs text-gray-500">Tasso % annuo</label><input type="number" value={form.tasso_interesse_annuo} onChange={(e) => setForm({ ...form, tasso_interesse_annuo: e.target.value })} step="0.01" className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm" /></div>
          </div>
          <div className="flex gap-2">
            <button onClick={handleCreate} disabled={!form.bank_account_id || !form.plafond} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">Crea</button>
            <button onClick={() => setShowForm(false)} className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-600">Annulla</button>
          </div>
        </div>
      )}

      {isLoading ? <LoadingSpinner /> : !fidi?.length ? (
        <EmptyState icon={Shield} title="Nessun fido" description="Configura il primo fido bancario per gli anticipi fatture." />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {fidi.map((f: any) => {
            const usedPct = f.plafond > 0 ? (f.utilizzato / f.plafond * 100) : 0
            return (
              <div key={f.id} className="rounded-xl border border-gray-200 bg-white p-4">
                <p className="font-medium text-gray-900">{f.bank_name}</p>
                <div className="mt-2 text-sm text-gray-500">Plafond: {formatCurrency(f.plafond)} | Tasso: {f.tasso_interesse_annuo}% | Anticipo: {f.percentuale_anticipo}%</div>
                <div className="mt-3">
                  <div className="flex justify-between text-xs text-gray-400 mb-1">
                    <span>Utilizzato: {formatCurrency(f.utilizzato)}</span>
                    <span>Disponibile: {formatCurrency(f.disponibile)}</span>
                  </div>
                  <div className="h-2 rounded-full bg-gray-200">
                    <div className="h-2 rounded-full bg-blue-600 transition-all" style={{ width: `${Math.min(usedPct, 100)}%` }} />
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
