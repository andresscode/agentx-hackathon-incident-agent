import { ApiIncidentService } from '@/lib/services'
import type { IncidentDetail } from '@/lib/types'

import {
  CategoryBarChart,
  type CategoryDatum,
  IncidentsOverTimeChart,
  PriorityBarChart,
  type PriorityDatum,
  type SeverityDatum,
  SeverityHistogram,
  StatCard,
  type StatusDatum,
  StatusPieChart,
  type TimeSeriesDatum,
} from './charts'

export const dynamic = 'force-dynamic'

/* ─── Aggregation helpers ─── */

function countBy<K extends string>(
  items: IncidentDetail[],
  key: (item: IncidentDetail) => K | null,
  order: K[],
): { key: K; count: number }[] {
  const map = new Map<K, number>()
  for (const k of order) map.set(k, 0)
  for (const item of items) {
    const k = key(item)
    if (k !== null) map.set(k, (map.get(k) ?? 0) + 1)
  }
  return order.map((k) => ({ key: k, count: map.get(k) ?? 0 }))
}

function computeTimeSeries(incidents: IncidentDetail[]): TimeSeriesDatum[] {
  const now = new Date()
  const buckets = new Map<string, number>()

  for (let i = 29; i >= 0; i--) {
    const d = new Date(now)
    d.setDate(d.getDate() - i)
    buckets.set(d.toISOString().slice(0, 10), 0)
  }

  for (const inc of incidents) {
    const day = inc.created_at.slice(0, 10)
    if (buckets.has(day)) {
      buckets.set(day, (buckets.get(day) ?? 0) + 1)
    }
  }

  return [...buckets.entries()].map(([date, count]) => ({ date, count }))
}

/* ─── Page ─── */

export default async function MetricsPage() {
  const service = new ApiIncidentService()
  const incidents = await service.listIncidents()

  if (incidents.length === 0) {
    return (
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-12">
        <div className="text-center max-w-lg">
          <h1 className="text-3xl font-bold tracking-tight font-mono">
            Incident Metrics
          </h1>
          <p className="mt-3 text-muted-foreground text-balance">
            No incidents have been reported yet. Submit an incident to see
            metrics here.
          </p>
        </div>
      </main>
    )
  }

  /* ── Stats ── */
  const total = incidents.length
  const withSeverity = incidents.filter((i) => i.severity_score !== null)
  const avgSeverity =
    withSeverity.length > 0
      ? (
          withSeverity.reduce((s, i) => s + (i.severity_score ?? 0), 0) /
          withSeverity.length
        ).toFixed(1)
      : '—'

  const resolved = incidents.filter(
    (i) => i.status === 'triaged' || i.status === 'resolved',
  ).length
  const resolutionRate =
    total > 0 ? `${Math.round((resolved / total) * 100)}%` : '—'

  /* ── Chart data ── */
  const statusOrder = ['pending', 'triaging', 'triaged', 'resolved'] as const
  const statusData: StatusDatum[] = countBy(
    incidents,
    (i) => i.status as (typeof statusOrder)[number],
    [...statusOrder],
  ).map((d) => ({
    status: d.key,
    count: d.count,
    fill: `var(--color-${d.key})`,
  }))

  const priorityOrder = ['critical', 'high', 'medium', 'low'] as const
  const priorityData: PriorityDatum[] = countBy(
    incidents,
    (i) => i.priority as (typeof priorityOrder)[number] | null,
    [...priorityOrder],
  ).map((d) => ({
    priority: d.key,
    count: d.count,
    fill: `var(--color-${d.key})`,
  }))

  const categoryOrder = [
    'bug',
    'security',
    'outage',
    'performance',
    'data_issue',
    'other',
  ] as const
  const categoryData: CategoryDatum[] = countBy(
    incidents,
    (i) => i.category as (typeof categoryOrder)[number] | null,
    [...categoryOrder],
  ).map((d) => ({
    category: d.key,
    count: d.count,
    fill: `var(--color-${d.key})`,
  }))

  const severityData: SeverityDatum[] = Array.from({ length: 10 }, (_, i) => ({
    score: String(i + 1),
    count: incidents.filter((inc) => inc.severity_score === i + 1).length,
  }))

  const timeSeriesData = computeTimeSeries(incidents)

  return (
    <main className="flex-1 flex flex-col items-center px-4 py-12">
      <div className="mb-8 text-center max-w-lg">
        <h1 className="text-3xl font-bold tracking-tight font-mono">
          Incident Metrics
        </h1>
        <p className="mt-3 text-muted-foreground text-balance">
          Real-time overview of incident triage and resolution.
        </p>
      </div>

      <div className="w-full max-w-5xl space-y-6">
        {/* ── Summary stats ── */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatCard
            title="Total Incidents"
            value={String(total)}
            description="All time reported incidents"
            icon="alert-triangle"
          />
          <StatCard
            title="Avg Severity"
            value={avgSeverity}
            description="Mean severity score (1-10)"
            icon="gauge"
          />
          <StatCard
            title="Resolution Rate"
            value={resolutionRate}
            description="Triaged or resolved incidents"
            icon="check-circle"
          />
        </div>

        {/* ── Timeline ── */}
        <IncidentsOverTimeChart data={timeSeriesData} />

        {/* ── Charts 2x2 ── */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <StatusPieChart data={statusData} total={total} />
          <PriorityBarChart data={priorityData} />
          <CategoryBarChart data={categoryData} />
          <SeverityHistogram data={severityData} />
        </div>
      </div>
    </main>
  )
}
