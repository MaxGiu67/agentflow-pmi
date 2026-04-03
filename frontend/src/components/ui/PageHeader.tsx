import type { ReactNode } from 'react'

interface PageHeaderProps {
  title: string
  subtitle?: string
  actions?: ReactNode
}

export default function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <div className="mb-4 flex flex-col gap-3 sm:mb-6 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <h1 className="truncate text-xl font-bold text-gray-900 sm:text-2xl">{title}</h1>
        {subtitle && <p className="mt-0.5 truncate text-xs text-gray-500 sm:text-sm">{subtitle}</p>}
      </div>
      {actions && (
        <div className="flex shrink-0 items-center gap-2 overflow-x-auto sm:gap-3">
          {actions}
        </div>
      )}
    </div>
  )
}
