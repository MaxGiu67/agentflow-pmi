import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { ArrowLeft, Plus, Trash2, Save } from 'lucide-react'
import api from '../../api/client'
import PageHeader from '../../components/ui/PageHeader'

// ── Types ──

interface LineItem {
  descrizione: string
  quantita: string
  unita_misura: string
  prezzo_unitario: string
  aliquota_iva: string
  natura: string
}

interface ClientData {
  denominazione: string
  piva: string
  codice_fiscale: string
  codice_sdi: string
  pec: string
  indirizzo: string
  cap: string
  comune: string
  provincia: string
}

const EMPTY_LINE: LineItem = {
  descrizione: '',
  quantita: '1',
  unita_misura: '',
  prezzo_unitario: '',
  aliquota_iva: '22',
  natura: '',
}

const ALIQUOTE_IVA = [
  { value: '22', label: '22%' },
  { value: '10', label: '10%' },
  { value: '5', label: '5%' },
  { value: '4', label: '4%' },
  { value: '0', label: 'Esente (0%)' },
]

const NATURE_IVA = [
  { value: 'N1', label: 'N1 — Escluse art. 15' },
  { value: 'N2', label: 'N2 — Non soggette' },
  { value: 'N2.1', label: 'N2.1 — Non soggette art. 7' },
  { value: 'N2.2', label: 'N2.2 — Non soggette altri' },
  { value: 'N3', label: 'N3 — Non imponibili' },
  { value: 'N4', label: 'N4 — Esenti' },
  { value: 'N5', label: 'N5 — Regime margine' },
  { value: 'N6', label: 'N6 — Inversione contabile' },
  { value: 'N7', label: 'N7 — Altro' },
]

const MODALITA_PAGAMENTO = [
  { value: 'MP01', label: 'Contanti' },
  { value: 'MP02', label: 'Assegno' },
  { value: 'MP05', label: 'Bonifico bancario' },
  { value: 'MP08', label: 'Carta di credito' },
  { value: 'MP12', label: 'RIBA' },
  { value: 'MP15', label: 'Giroconto' },
  { value: 'MP19', label: 'SEPA Direct Debit' },
  { value: 'MP23', label: 'PagoPA' },
]

const DOC_TYPES = [
  { value: 'TD01', label: 'TD01 — Fattura' },
  { value: 'TD04', label: 'TD04 — Nota di credito' },
]

// ── Helpers ──

function fmtCur(n: number): string {
  return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' }).format(n)
}

function calcLineTotal(line: LineItem): number {
  return (Number(line.quantita) || 0) * (Number(line.prezzo_unitario) || 0)
}

function calcLineIva(line: LineItem): number {
  return calcLineTotal(line) * (Number(line.aliquota_iva) || 0) / 100
}

// ── Component ──

export default function CreateInvoicePage() {
  const navigate = useNavigate()

  // Document
  const [docType, setDocType] = useState('TD01')
  const [dataFattura, setDataFattura] = useState(new Date().toISOString().slice(0, 10))
  const [causale, setCausale] = useState('')

  // Credit note reference
  const [origNumero, setOrigNumero] = useState('')
  const [origDate, setOrigDate] = useState('')

  // Client
  const [cliente, setCliente] = useState<ClientData>({
    denominazione: '', piva: '', codice_fiscale: '', codice_sdi: '0000000',
    pec: '', indirizzo: '', cap: '', comune: '', provincia: '',
  })

  // Line items
  const [linee, setLinee] = useState<LineItem[]>([{ ...EMPTY_LINE }])

  // Payment
  const [modalitaPag, setModalitaPag] = useState('MP05')
  const [giorniPag, setGiorniPag] = useState('30')
  const [iban, setIban] = useState('')

  // Calculated totals
  const totals = useMemo(() => {
    const imponibile = linee.reduce((s, l) => s + calcLineTotal(l), 0)
    const iva = linee.reduce((s, l) => s + calcLineIva(l), 0)

    // Riepilogo IVA per aliquota
    const riepilogoMap: Record<string, { imponibile: number; imposta: number }> = {}
    for (const line of linee) {
      const key = `${line.aliquota_iva}%`
      if (!riepilogoMap[key]) riepilogoMap[key] = { imponibile: 0, imposta: 0 }
      riepilogoMap[key].imponibile += calcLineTotal(line)
      riepilogoMap[key].imposta += calcLineIva(line)
    }

    return {
      imponibile: Math.round(imponibile * 100) / 100,
      iva: Math.round(iva * 100) / 100,
      totale: Math.round((imponibile + iva) * 100) / 100,
      riepilogo: Object.entries(riepilogoMap).map(([aliquota, vals]) => ({
        aliquota,
        imponibile: Math.round(vals.imponibile * 100) / 100,
        imposta: Math.round(vals.imposta * 100) / 100,
      })),
    }
  }, [linee])

  // API
  const createMutation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      (await api.post('/invoices/active', payload)).data,
    onSuccess: () => navigate('/fatture'),
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    createMutation.mutate({
      cliente: {
        denominazione: cliente.denominazione,
        piva: cliente.piva || null,
        codice_fiscale: cliente.codice_fiscale || null,
        codice_sdi: cliente.codice_sdi || '0000000',
        pec: cliente.pec || null,
        indirizzo: cliente.indirizzo || null,
        cap: cliente.cap || null,
        comune: cliente.comune || null,
        provincia: cliente.provincia || null,
      },
      data_fattura: dataFattura,
      document_type: docType,
      causale: causale || null,
      linee: linee.map((l) => ({
        descrizione: l.descrizione,
        quantita: Number(l.quantita) || 1,
        unita_misura: l.unita_misura || null,
        prezzo_unitario: Number(l.prezzo_unitario) || 0,
        aliquota_iva: Number(l.aliquota_iva) ?? 22,
        natura: Number(l.aliquota_iva) === 0 ? (l.natura || null) : null,
      })),
      modalita_pagamento: modalitaPag,
      giorni_pagamento: Number(giorniPag) || 30,
      iban: iban || null,
      original_invoice_numero: docType === 'TD04' ? origNumero || null : null,
      original_invoice_date: docType === 'TD04' && origDate ? origDate : null,
    })
  }

  function addLine() {
    setLinee([...linee, { ...EMPTY_LINE }])
  }

  function removeLine(index: number) {
    if (linee.length > 1) setLinee(linee.filter((_, i) => i !== index))
  }

  function updateLine(index: number, field: keyof LineItem, value: string) {
    const updated = [...linee]
    updated[index] = { ...updated[index], [field]: value }
    setLinee(updated)
  }

  function updateCliente(field: keyof ClientData, value: string) {
    setCliente({ ...cliente, [field]: value })
  }

  const isCredit = docType === 'TD04'

  return (
    <div className="mx-auto max-w-4xl px-4 pb-12">
      <PageHeader
        title={isCredit ? 'Nuova Nota di Credito' : 'Nuova Fattura'}
        subtitle="Compila i dati per generare la fattura elettronica"
        actions={
          <button onClick={() => navigate('/fatture')} className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50">
            <ArrowLeft className="h-4 w-4" /> Indietro
          </button>
        }
      />

      <form onSubmit={handleSubmit} className="space-y-6">

        {/* Document type + date */}
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h3 className="mb-4 text-sm font-semibold text-slate-800">Documento</h3>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Tipo documento</label>
              <select value={docType} onChange={(e) => setDocType(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm">
                {DOC_TYPES.map((dt) => <option key={dt.value} value={dt.value}>{dt.label}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Data fattura</label>
              <input type="date" required value={dataFattura} onChange={(e) => setDataFattura(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </div>
            <div className="col-span-2">
              <label className="mb-1 block text-xs font-medium text-slate-600">Causale (opzionale)</label>
              <input type="text" value={causale} onChange={(e) => setCausale(e.target.value)} placeholder="Descrizione o riferimento..." className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </div>
          </div>
          {isCredit && (
            <div className="mt-4 grid grid-cols-2 gap-4 rounded-lg border border-amber-200 bg-amber-50 p-4">
              <div>
                <label className="mb-1 block text-xs font-medium text-amber-700">Numero fattura originale</label>
                <input type="text" value={origNumero} onChange={(e) => setOrigNumero(e.target.value)} placeholder="FTA-2026-0001" className="w-full rounded-lg border border-amber-300 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-amber-700">Data fattura originale</label>
                <input type="date" value={origDate} onChange={(e) => setOrigDate(e.target.value)} className="w-full rounded-lg border border-amber-300 px-3 py-2 text-sm" />
              </div>
            </div>
          )}
        </div>

        {/* Client */}
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h3 className="mb-4 text-sm font-semibold text-slate-800">Cliente / Destinatario</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className="col-span-2 sm:col-span-1">
              <label className="mb-1 block text-xs font-medium text-slate-600">Denominazione *</label>
              <input type="text" required value={cliente.denominazione} onChange={(e) => updateCliente('denominazione', e.target.value)} placeholder="Ragione sociale" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">P.IVA</label>
              <input type="text" value={cliente.piva} onChange={(e) => updateCliente('piva', e.target.value)} placeholder="IT01234567890" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Codice Fiscale</label>
              <input type="text" value={cliente.codice_fiscale} onChange={(e) => updateCliente('codice_fiscale', e.target.value)} placeholder="RSSMRA80A01H501U" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Codice SDI</label>
              <input type="text" value={cliente.codice_sdi} onChange={(e) => updateCliente('codice_sdi', e.target.value)} placeholder="0000000" maxLength={7} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">PEC</label>
              <input type="email" value={cliente.pec} onChange={(e) => updateCliente('pec', e.target.value)} placeholder="pec@azienda.it" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </div>
          </div>
          <div className="mt-3 grid grid-cols-4 gap-3">
            <div className="col-span-2">
              <label className="mb-1 block text-xs font-medium text-slate-600">Indirizzo</label>
              <input type="text" value={cliente.indirizzo} onChange={(e) => updateCliente('indirizzo', e.target.value)} placeholder="Via Roma 10" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">CAP</label>
              <input type="text" value={cliente.cap} onChange={(e) => updateCliente('cap', e.target.value)} placeholder="00100" maxLength={5} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Comune</label>
              <input type="text" value={cliente.comune} onChange={(e) => updateCliente('comune', e.target.value)} placeholder="Roma" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </div>
          </div>
        </div>

        {/* Line items */}
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-800">Righe dettaglio</h3>
            <button type="button" onClick={addLine} className="inline-flex items-center gap-1 rounded-lg border border-blue-300 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-50">
              <Plus className="h-3.5 w-3.5" /> Aggiungi riga
            </button>
          </div>

          <div className="space-y-3">
            {linee.map((line, i) => (
              <div key={i} className="rounded-lg border border-slate-100 bg-slate-50/50 p-3">
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-xs font-medium text-slate-500">Riga {i + 1}</span>
                  {linee.length > 1 && (
                    <button type="button" onClick={() => removeLine(i)} className="rounded p-1 text-slate-400 hover:bg-red-50 hover:text-red-500">
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
                <div className="grid grid-cols-12 gap-2">
                  <div className="col-span-5">
                    <input type="text" required value={line.descrizione} onChange={(e) => updateLine(i, 'descrizione', e.target.value)} placeholder="Descrizione servizio/prodotto" className="w-full rounded border border-slate-200 px-2.5 py-1.5 text-sm" />
                  </div>
                  <div className="col-span-1">
                    <input type="number" value={line.quantita} onChange={(e) => updateLine(i, 'quantita', e.target.value)} placeholder="Qta" min={0.01} step={0.01} className="w-full rounded border border-slate-200 px-2 py-1.5 text-right text-sm" />
                  </div>
                  <div className="col-span-1">
                    <input type="text" value={line.unita_misura} onChange={(e) => updateLine(i, 'unita_misura', e.target.value)} placeholder="UM" className="w-full rounded border border-slate-200 px-2 py-1.5 text-sm" />
                  </div>
                  <div className="col-span-2">
                    <input type="number" required value={line.prezzo_unitario} onChange={(e) => updateLine(i, 'prezzo_unitario', e.target.value)} placeholder="Prezzo unit." min={0} step={0.01} className="w-full rounded border border-slate-200 px-2 py-1.5 text-right text-sm" />
                  </div>
                  <div className="col-span-1">
                    <select value={line.aliquota_iva} onChange={(e) => updateLine(i, 'aliquota_iva', e.target.value)} className="w-full rounded border border-slate-200 px-1 py-1.5 text-sm">
                      {ALIQUOTE_IVA.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
                    </select>
                  </div>
                  <div className="col-span-2 flex items-center justify-end">
                    <span className="text-sm font-semibold text-slate-700">{fmtCur(calcLineTotal(line))}</span>
                  </div>
                </div>
                {line.aliquota_iva === '0' && (
                  <div className="mt-2">
                    <select value={line.natura} onChange={(e) => updateLine(i, 'natura', e.target.value)} required className="w-full rounded border border-amber-200 bg-amber-50 px-2.5 py-1.5 text-sm text-amber-800">
                      <option value="">— Seleziona natura IVA esente —</option>
                      {NATURE_IVA.map((n) => <option key={n.value} value={n.value}>{n.label}</option>)}
                    </select>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Payment */}
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <h3 className="mb-4 text-sm font-semibold text-slate-800">Pagamento</h3>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Modalita</label>
              <select value={modalitaPag} onChange={(e) => setModalitaPag(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm">
                {MODALITA_PAGAMENTO.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">Giorni pagamento</label>
              <input type="number" value={giorniPag} onChange={(e) => setGiorniPag(e.target.value)} min={0} className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-slate-600">IBAN (opzionale)</label>
              <input type="text" value={iban} onChange={(e) => setIban(e.target.value)} placeholder="IT60X0542811101000000123456" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </div>
          </div>
        </div>

        {/* Totals */}
        <div className="rounded-xl border-2 border-slate-300 bg-white p-5">
          <h3 className="mb-4 text-sm font-semibold text-slate-800">Riepilogo</h3>

          {/* IVA breakdown */}
          {totals.riepilogo.length > 0 && (
            <div className="mb-4 overflow-hidden rounded-lg border border-slate-100">
              <table className="w-full text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium text-slate-500">Aliquota</th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-slate-500">Imponibile</th>
                    <th className="px-3 py-2 text-right text-xs font-medium text-slate-500">Imposta</th>
                  </tr>
                </thead>
                <tbody>
                  {totals.riepilogo.map((r) => (
                    <tr key={r.aliquota} className="border-t border-slate-100">
                      <td className="px-3 py-1.5">{r.aliquota}</td>
                      <td className="px-3 py-1.5 text-right">{fmtCur(r.imponibile)}</td>
                      <td className="px-3 py-1.5 text-right">{fmtCur(r.imposta)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-600">Imponibile</span>
              <span className="font-medium">{fmtCur(totals.imponibile)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-600">IVA</span>
              <span className="font-medium">{fmtCur(totals.iva)}</span>
            </div>
            <div className="flex justify-between border-t border-slate-200 pt-2">
              <span className="text-base font-bold text-slate-800">Totale</span>
              <span className="text-base font-bold text-slate-800">{fmtCur(totals.totale)}</span>
            </div>
          </div>
        </div>

        {/* Error */}
        {createMutation.isError && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            Errore nella creazione: {(createMutation.error as Error)?.message || 'Riprova'}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <button type="button" onClick={() => navigate('/fatture')} className="rounded-lg border border-slate-300 px-5 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50">
            Annulla
          </button>
          <button type="submit" disabled={createMutation.isPending || !cliente.denominazione || linee.every((l) => !l.descrizione)} className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">
            <Save className="h-4 w-4" />
            {createMutation.isPending ? 'Creazione...' : 'Crea fattura'}
          </button>
        </div>
      </form>
    </div>
  )
}
