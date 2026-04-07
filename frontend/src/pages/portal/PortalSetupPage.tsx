import { useState } from 'react'
import { usePortalStatus, usePortalAccountManagers, useMyPortalAccountManager } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import { Link2, CheckCircle, XCircle, RefreshCw, Users, FileText, Briefcase, Clock, UserCheck } from 'lucide-react'
import api from '../../api/client'

export default function PortalSetupPage() {
  const { data: portalStatus, isLoading, refetch } = usePortalStatus()
  const { data: accountManagers } = usePortalAccountManagers()
  const { data: myAccountManager } = useMyPortalAccountManager()
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string; customers?: number } | null>(null)
  const [testing, setTesting] = useState(false)

  const handleTestConnection = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const res = await api.get('/portal/customers?search=&page=1&page_size=1')
      const count = res.data?.pagination?.total || res.data?.total || res.data?.data?.length || 0
      setTestResult({ ok: true, message: `Connessione riuscita! ${count} clienti trovati.`, customers: count })
    } catch (e: any) {
      setTestResult({ ok: false, message: `Errore: ${e?.response?.data?.detail || e?.message || 'Connessione fallita'}` })
    }
    setTesting(false)
  }

  if (isLoading) return <LoadingSpinner />

  const isConnected = portalStatus?.enabled === true

  const features = [
    { icon: Users, name: 'Clienti Portal', desc: 'Cerca e collega clienti Portal ai deal CRM', endpoint: '/portal/customers' },
    { icon: UserCheck, name: 'Persone / Risorse', desc: 'Consulta dipendenti, skill, contratti, disponibilita', endpoint: '/portal/persons' },
    { icon: FileText, name: 'Crea Offerta', desc: 'Crea offerta su Portal direttamente dal deal CRM', endpoint: '/portal/offers/create' },
    { icon: Briefcase, name: 'Commesse', desc: 'Collega deal a progetto Portal, visualizza attivita e risorse', endpoint: '/portal/deal-project' },
    { icon: Clock, name: 'Avanzamento', desc: 'Calcolo margine, costo stimato, KPI operativi', endpoint: '/portal/deal-progress' },
    { icon: Users, name: 'Account Manager', desc: 'Mapping automatico account manager per email', endpoint: '/portal/my-account-manager' },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="Collegamento Portal"
        subtitle="Configurazione connessione a PortalJS.be per gestione operativa"
      />

      {/* Connection status card */}
      <div className={`rounded-2xl border-2 p-6 ${isConnected ? 'border-green-200 bg-green-50/30' : 'border-red-200 bg-red-50/30'}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={`flex h-14 w-14 items-center justify-center rounded-xl ${isConnected ? 'bg-green-100' : 'bg-red-100'}`}>
              {isConnected ? <CheckCircle className="h-7 w-7 text-green-600" /> : <XCircle className="h-7 w-7 text-red-600" />}
            </div>
            <div>
              <h2 className={`text-lg font-bold ${isConnected ? 'text-green-800' : 'text-red-800'}`}>
                {isConnected ? 'Portal Connesso' : 'Portal Non Connesso'}
              </h2>
              <p className="text-sm text-gray-500">
                {isConnected
                  ? 'La connessione a PortalJS.be e attiva. Tutte le funzionalita operative sono disponibili.'
                  : 'Configurare le variabili PORTAL_API_URL, PORTAL_JWT_SECRET e PORTAL_TENANT nelle impostazioni del server.'}
              </p>
            </div>
          </div>
          <button onClick={() => { handleTestConnection(); refetch() }} disabled={testing}
            className={`inline-flex items-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium text-white ${
              isConnected ? 'bg-green-600 hover:bg-green-700' : 'bg-gray-600 hover:bg-gray-700'
            } disabled:opacity-50`}>
            <RefreshCw className={`h-4 w-4 ${testing ? 'animate-spin' : ''}`} />
            {testing ? 'Test in corso...' : 'Testa Connessione'}
          </button>
        </div>

        {/* Connection details */}
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg bg-white/60 border border-gray-200 px-4 py-3">
            <p className="text-[10px] uppercase text-gray-400 font-medium">API URL</p>
            <p className="text-sm font-mono text-gray-700 truncate">{portalStatus?.url || 'Non configurato'}</p>
          </div>
          <div className="rounded-lg bg-white/60 border border-gray-200 px-4 py-3">
            <p className="text-[10px] uppercase text-gray-400 font-medium">Tenant</p>
            <p className="text-sm font-mono text-gray-700">{portalStatus?.tenant || 'Non configurato'}</p>
          </div>
          <div className="rounded-lg bg-white/60 border border-gray-200 px-4 py-3">
            <p className="text-[10px] uppercase text-gray-400 font-medium">JWT Token</p>
            <p className="text-sm text-gray-700">{isConnected ? 'Configurato (HS256)' : 'Non configurato'}</p>
          </div>
        </div>

        {/* Test result */}
        {testResult && (
          <div className={`mt-3 rounded-lg px-4 py-2.5 text-sm ${testResult.ok ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
            {testResult.ok ? <CheckCircle className="inline h-4 w-4 mr-1" /> : <XCircle className="inline h-4 w-4 mr-1" />}
            {testResult.message}
          </div>
        )}
      </div>

      {/* Account Manager mapping */}
      {isConnected && myAccountManager && (
        <div className="rounded-2xl border border-blue-200 bg-blue-50/30 p-6">
          <h3 className="text-sm font-semibold uppercase text-blue-600 mb-3">Il tuo Account Manager Portal</h3>
          {myAccountManager.id ? (
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100 text-sm font-bold text-blue-600">
                {(myAccountManager.name || '?').charAt(0)}
              </div>
              <div>
                <p className="font-medium text-gray-900">{myAccountManager.name}</p>
                <p className="text-xs text-gray-500">{myAccountManager.email} — Portal ID: {myAccountManager.id}</p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-amber-600">Nessun account manager trovato per {myAccountManager.email}. Verifica che l'email corrisponda a un utente Portal.</p>
          )}
          {accountManagers?.length > 0 && (
            <div className="mt-3">
              <p className="text-xs text-gray-400 mb-1">Tutti gli account manager Portal ({accountManagers.length}):</p>
              <div className="flex flex-wrap gap-1">
                {accountManagers.map((am: any) => (
                  <span key={am.id} className="rounded-full bg-white border border-blue-100 px-2 py-0.5 text-[10px] text-gray-600">
                    {am.name} ({am.email})
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Features grid */}
      {isConnected && (
        <div>
          <h3 className="text-sm font-semibold uppercase text-gray-400 mb-3">Funzionalita Disponibili</h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((f) => (
              <div key={f.name} className="rounded-xl border border-gray-200 bg-white p-4 flex items-start gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-100 shrink-0">
                  <f.icon className="h-4 w-4 text-indigo-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900">{f.name}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Help when not connected */}
      {!isConnected && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50/30 p-6">
          <h3 className="font-medium text-amber-800 mb-2">Come configurare</h3>
          <ol className="list-decimal list-inside space-y-1 text-sm text-amber-700">
            <li>Impostare <code className="bg-amber-100 px-1 rounded">PORTAL_API_URL</code> con l'URL dell'API PortalJS.be (es. https://portaaljsbe-staging.up.railway.app/api/v1)</li>
            <li>Impostare <code className="bg-amber-100 px-1 rounded">PORTAL_JWT_SECRET</code> con il secret condiviso (stesso di Portal, senza apici)</li>
            <li>Impostare <code className="bg-amber-100 px-1 rounded">PORTAL_TENANT</code> con il codice tenant (es. NEXA)</li>
            <li>Riavviare il server e tornare su questa pagina per testare la connessione</li>
          </ol>
        </div>
      )}
    </div>
  )
}
