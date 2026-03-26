import { useState, useCallback, useRef, useEffect } from 'react'
import {
  ResponsiveGridLayout,
  useContainerWidth,
} from 'react-grid-layout'
import type { LayoutItem } from 'react-grid-layout'
import 'react-grid-layout/css/styles.css'
import {
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  RotateCcw,
  RefreshCw,
  MessageSquare,
} from 'lucide-react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  useDashboardLayout,
  useSaveDashboardLayout,
  useResetDashboardLayout,
  useYearlyStats,
  useSyncCassetto,
} from '../api/hooks'
import WidgetRenderer from '../components/dashboard/WidgetRenderer'
import type { WidgetDef } from '../components/dashboard/WidgetRenderer'
import PageHeader from '../components/ui/PageHeader'
import LoadingSpinner from '../components/ui/LoadingSpinner'

export default function DashboardPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const currentYear = new Date().getFullYear()

  // Read year from URL params (set by chatbot action) or default to current year
  const urlYear = searchParams.get('year')
  const initialYear = urlYear ? parseInt(urlYear, 10) : currentYear
  const [selectedYear, setSelectedYear] = useState(isNaN(initialYear) ? currentYear : initialYear)

  // Sync year from URL when chatbot changes it
  useEffect(() => {
    const yp = searchParams.get('year')
    if (yp) {
      const parsed = parseInt(yp, 10)
      if (!isNaN(parsed) && parsed !== selectedYear) {
        setSelectedYear(parsed)
      }
    }
  }, [searchParams])

  // Container width for responsive grid
  const { width, containerRef } = useContainerWidth()

  // Layout data
  const { data: layoutData, isLoading: layoutLoading } = useDashboardLayout()
  const saveLayout = useSaveDashboardLayout()
  const resetLayout = useResetDashboardLayout()

  // Stats data
  const { data: yearlyData, isLoading: yearlyLoading, error: yearlyError } = useYearlyStats(selectedYear)
  const syncCassetto = useSyncCassetto()

  // Debounce save
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const widgets: WidgetDef[] = (layoutData?.widgets ?? []) as WidgetDef[]

  // Build grid layout from widgets
  const gridLayout: LayoutItem[] = widgets.map((w) => ({
    i: w.id,
    x: w.layout.x,
    y: w.layout.y,
    w: w.layout.w,
    h: w.layout.h,
    minW: 2,
    minH: 2,
  }))

  const handleLayoutChange = useCallback(
    (newLayout: readonly LayoutItem[]) => {
      if (!layoutData?.widgets || widgets.length === 0) return

      // Map new positions back to widgets
      const updatedWidgets = widgets.map((widget) => {
        const gridItem = newLayout.find((l) => l.i === widget.id)
        if (gridItem) {
          return {
            ...widget,
            layout: { x: gridItem.x, y: gridItem.y, w: gridItem.w, h: gridItem.h },
          }
        }
        return widget
      })

      // Debounce the save
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
      saveTimerRef.current = setTimeout(() => {
        saveLayout.mutate({
          widgets: updatedWidgets as unknown as Record<string, unknown>[],
          year: selectedYear,
        })
      }, 500)
    },
    [layoutData?.widgets, widgets, selectedYear, saveLayout],
  )

  const handleReset = useCallback(() => {
    resetLayout.mutate()
  }, [resetLayout])

  const isLoading = layoutLoading || yearlyLoading

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  if (yearlyError) {
    return (
      <div className="mt-20 text-center">
        <AlertTriangle className="mx-auto mb-4 h-12 w-12 text-amber-500" />
        <p className="text-gray-600">Errore nel caricamento della dashboard</p>
      </div>
    )
  }

  const availableYears: number[] = (yearlyData?.available_years as number[]) ?? []
  const yearOptions = availableYears.length > 0 ? availableYears : [currentYear]
  const canGoBack = selectedYear > (yearOptions[0] ?? currentYear - 5)
  const canGoForward = selectedYear < currentYear

  return (
    <div ref={containerRef}>
      <PageHeader
        title={`Dashboard ${selectedYear}`}
        subtitle="Panoramica annuale fatturazione"
        actions={
          <div className="flex items-center gap-3">
            {/* Year navigation */}
            <div className="flex items-center gap-1 rounded-lg border border-gray-300 px-1 py-1">
              <button
                onClick={() => setSelectedYear((y) => y - 1)}
                disabled={!canGoBack}
                className="rounded p-1 hover:bg-gray-100 disabled:opacity-30"
                aria-label="Anno precedente"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <select
                value={selectedYear}
                onChange={(e) => setSelectedYear(Number(e.target.value))}
                className="appearance-none border-none bg-transparent px-2 py-0.5 text-sm font-medium text-gray-700 focus:outline-none"
              >
                {Array.from(new Set([...yearOptions, currentYear, selectedYear]))
                  .sort((a, b) => b - a)
                  .map((y) => (
                    <option key={y} value={y}>
                      {y}
                    </option>
                  ))}
              </select>
              <button
                onClick={() => setSelectedYear((y) => y + 1)}
                disabled={!canGoForward}
                className="rounded p-1 hover:bg-gray-100 disabled:opacity-30"
                aria-label="Anno successivo"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>

            <button
              onClick={handleReset}
              disabled={resetLayout.isPending}
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              title="Reset layout"
            >
              <RotateCcw className={`h-4 w-4 ${resetLayout.isPending ? 'animate-spin' : ''}`} />
              Reset
            </button>

            <button
              onClick={() => navigate('/chat')}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              <MessageSquare className="h-4 w-4" />
              Apri Chat
            </button>

            <button
              onClick={() => syncCassetto.mutate({})}
              disabled={syncCassetto.isPending}
              className="inline-flex items-center gap-2 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${syncCassetto.isPending ? 'animate-spin' : ''}`} />
              Sincronizza
            </button>
          </div>
        }
      />

      {widgets.length > 0 && width > 0 ? (
        <ResponsiveGridLayout
          width={width}
          layouts={{ lg: gridLayout }}
          breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
          cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
          rowHeight={60}
          onLayoutChange={handleLayoutChange}
          dragConfig={{ handle: '.widget-drag-handle' }}
        >
          {widgets.map((widget) => (
            <div key={widget.id} className="group relative">
              {/* Drag handle overlay */}
              <div className="widget-drag-handle absolute inset-x-0 top-0 z-10 h-6 cursor-move rounded-t-lg opacity-0 transition-opacity group-hover:opacity-100">
                <div className="mx-auto mt-1 h-1 w-8 rounded-full bg-gray-300" />
              </div>
              <WidgetRenderer
                widget={widget}
                data={(yearlyData as Record<string, unknown>) ?? null}
              />
            </div>
          ))}
        </ResponsiveGridLayout>
      ) : widgets.length === 0 ? (
        <div className="mt-12 text-center">
          <p className="text-sm text-gray-500">Nessun widget configurato. Premi &quot;Reset&quot; per ripristinare il layout predefinito.</p>
        </div>
      ) : null}
    </div>
  )
}
