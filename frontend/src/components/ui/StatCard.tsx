import { TrendingUp, TrendingDown } from 'lucide-react'
import Card from './Card'
import { cn } from '../../lib/utils'

interface StatCardProps {
  title: string
  value: string | number
  subtitle?: string
  trend?: number
  icon?: React.ReactNode
  className?: string
}

export default function StatCard({ title, value, subtitle, trend, icon, className }: StatCardProps) {
  return (
    <Card className={cn('flex items-start gap-4', className)}>
      {icon && (
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
          {icon}
        </div>
      )}
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-gray-500">{title}</p>
        <p className="mt-1 text-2xl font-semibold text-gray-900">{value}</p>
        {(subtitle || trend !== undefined) && (
          <div className="mt-1 flex items-center gap-1">
            {trend !== undefined && (
              <>
                {trend >= 0 ? (
                  <TrendingUp className="h-4 w-4 text-green-500" />
                ) : (
                  <TrendingDown className="h-4 w-4 text-red-500" />
                )}
                <span
                  className={cn(
                    'text-sm font-medium',
                    trend >= 0 ? 'text-green-600' : 'text-red-600'
                  )}
                >
                  {trend > 0 ? '+' : ''}
                  {trend}%
                </span>
              </>
            )}
            {subtitle && <span className="text-sm text-gray-500">{subtitle}</span>}
          </div>
        )}
      </div>
    </Card>
  )
}
