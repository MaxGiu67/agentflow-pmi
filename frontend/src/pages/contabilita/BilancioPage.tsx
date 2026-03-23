import { useState } from 'react'
import { useBalanceSheet } from '../../api/hooks'
import { formatCurrency } from '../../lib/utils'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'

interface BalanceSection {
  code: string
  name: string
  amount: number
  children?: BalanceSection[]
}

function SectionRow({ section, level = 0 }: { section: BalanceSection; level?: number }) {
  const isBold = level === 0
  return (
    <>
      <tr className={isBold ? 'bg-gray-50' : ''}>
        <td
          className="px-4 py-2 text-sm text-gray-700"
          style={{ paddingLeft: `${level * 24 + 16}px` }}
        >
          <span className={isBold ? 'font-semibold' : ''}>
            {section.code} - {section.name}
          </span>
        </td>
        <td className={`px-4 py-2 text-right text-sm ${isBold ? 'font-semibold' : ''} text-gray-900`}>
          {formatCurrency(section.amount)}
        </td>
      </tr>
      {section.children?.map((child) => (
        <SectionRow key={child.code} section={child} level={level + 1} />
      ))}
    </>
  )
}

export default function BilancioPage() {
  const currentYear = new Date().getFullYear()
  const [year, setYear] = useState(currentYear)
  const { data, isLoading, error } = useBalanceSheet(year)

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  return (
    <div>
      <PageHeader
        title="Bilancio CEE"
        subtitle="Stato patrimoniale e conto economico"
        actions={
          <select
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          >
            {Array.from({ length: 5 }, (_, i) => currentYear - i).map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        }
      />

      {error ? (
        <EmptyState
          title="Bilancio non disponibile"
          description="Non ci sono dati sufficienti per generare il bilancio."
        />
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Stato Patrimoniale - Attivo */}
          <Card>
            <h2 className="mb-4 text-lg font-semibold text-gray-900">Attivo</h2>
            <table className="w-full">
              <tbody>
                {(data?.attivo as BalanceSection[] ?? []).map((section: BalanceSection) => (
                  <SectionRow key={section.code} section={section} />
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t-2 border-gray-300">
                  <td className="px-4 py-2 text-sm font-bold text-gray-900">Totale Attivo</td>
                  <td className="px-4 py-2 text-right text-sm font-bold text-gray-900">
                    {formatCurrency(data?.total_attivo ?? 0)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </Card>

          {/* Stato Patrimoniale - Passivo */}
          <Card>
            <h2 className="mb-4 text-lg font-semibold text-gray-900">Passivo</h2>
            <table className="w-full">
              <tbody>
                {(data?.passivo as BalanceSection[] ?? []).map((section: BalanceSection) => (
                  <SectionRow key={section.code} section={section} />
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t-2 border-gray-300">
                  <td className="px-4 py-2 text-sm font-bold text-gray-900">Totale Passivo</td>
                  <td className="px-4 py-2 text-right text-sm font-bold text-gray-900">
                    {formatCurrency(data?.total_passivo ?? 0)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </Card>

          {/* Conto Economico */}
          <Card className="lg:col-span-2">
            <h2 className="mb-4 text-lg font-semibold text-gray-900">Conto Economico</h2>
            <table className="w-full">
              <tbody>
                {(data?.conto_economico as BalanceSection[] ?? []).map((section: BalanceSection) => (
                  <SectionRow key={section.code} section={section} />
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t-2 border-gray-300">
                  <td className="px-4 py-2 text-sm font-bold text-gray-900">Risultato d'esercizio</td>
                  <td className="px-4 py-2 text-right text-sm font-bold text-gray-900">
                    {formatCurrency(data?.risultato_esercizio ?? 0)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </Card>
        </div>
      )}
    </div>
  )
}
