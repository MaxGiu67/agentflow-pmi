import { useState } from 'react'
import { ChevronRight, ChevronDown, FolderTree } from 'lucide-react'
import { usePianoConti } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'

interface Account {
  code: string
  name: string
  type: string
  children?: Account[]
}

function AccountNode({ account, level = 0 }: { account: Account; level?: number }) {
  const [expanded, setExpanded] = useState(level < 2)
  const hasChildren = account.children && account.children.length > 0

  return (
    <div>
      <div
        className="flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2 hover:bg-gray-50"
        style={{ paddingLeft: `${level * 24 + 12}px` }}
        onClick={() => setExpanded(!expanded)}
      >
        {hasChildren ? (
          expanded ? (
            <ChevronDown className="h-4 w-4 text-gray-400" />
          ) : (
            <ChevronRight className="h-4 w-4 text-gray-400" />
          )
        ) : (
          <div className="w-4" />
        )}
        <span className="font-mono text-xs text-gray-500">{account.code}</span>
        <span className="text-sm text-gray-700">{account.name}</span>
        <span className="ml-auto text-xs text-gray-400">{account.type}</span>
      </div>
      {expanded && hasChildren && (
        <div>
          {account.children!.map((child) => (
            <AccountNode key={child.code} account={child} level={level + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

export default function PianoContiPage() {
  const { data, isLoading, error } = usePianoConti()

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  if (error) {
    return (
      <div>
        <PageHeader title="Piano dei Conti" />
        <EmptyState
          title="Piano dei conti non disponibile"
          description="Il piano dei conti non e stato ancora configurato."
          icon={<FolderTree className="h-12 w-12" />}
        />
      </div>
    )
  }

  const accounts: Account[] = data?.accounts ?? []

  return (
    <div>
      <PageHeader
        title="Piano dei Conti"
        subtitle="Struttura gerarchica dei conti"
      />

      <Card>
        {accounts.length === 0 ? (
          <EmptyState
            title="Nessun conto configurato"
            description="Il piano dei conti verra creato durante l'onboarding."
          />
        ) : (
          <div className="divide-y divide-gray-100">
            {accounts.map((account) => (
              <AccountNode key={account.code} account={account} />
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
