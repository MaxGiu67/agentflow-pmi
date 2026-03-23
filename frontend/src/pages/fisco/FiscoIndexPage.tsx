import { useNavigate } from 'react-router-dom'
import {
  FileText,
  Calculator,
  Receipt,
  UserCheck,
  Shield,
  Stamp,
} from 'lucide-react'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'

const sections = [
  {
    to: '/fisco/f24',
    icon: FileText,
    title: 'Modelli F24',
    description: 'Genera ed esporta modelli F24',
  },
  {
    to: '/fisco/liquidazione',
    icon: Calculator,
    title: 'Liquidazione IVA',
    description: 'Calcolo IVA trimestrale',
  },
  {
    to: '/fisco/ritenute',
    icon: Receipt,
    title: 'Ritenute d\'acconto',
    description: 'Gestione ritenute sui professionisti',
  },
  {
    to: '/fisco/cu',
    icon: UserCheck,
    title: 'Certificazione Unica',
    description: 'Generazione CU annuali',
  },
  {
    to: '/fisco/conservazione',
    icon: Shield,
    title: 'Conservazione digitale',
    description: 'Stato conservazione a norma',
  },
  {
    to: '/fisco/bollo',
    icon: Stamp,
    title: 'Imposta di Bollo',
    description: 'Riepilogo bollo trimestrale',
  },
]

export default function FiscoIndexPage() {
  const navigate = useNavigate()

  return (
    <div>
      <PageHeader title="Fisco" subtitle="Adempimenti e obblighi fiscali" />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {sections.map((section) => (
          <Card
            key={section.to}
            className="cursor-pointer transition-shadow hover:shadow-md"
          >
            <button
              onClick={() => navigate(section.to)}
              className="flex w-full items-start gap-4 text-left"
            >
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
                <section.icon className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-900">{section.title}</h3>
                <p className="mt-1 text-xs text-gray-500">{section.description}</p>
              </div>
            </button>
          </Card>
        ))}
      </div>
    </div>
  )
}
