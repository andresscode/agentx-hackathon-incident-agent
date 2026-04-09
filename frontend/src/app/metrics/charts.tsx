'use client'

import { AlertTriangle, CheckCircle2, Gauge } from 'lucide-react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Label,
  LabelList,
  Pie,
  PieChart,
  XAxis,
  YAxis,
} from 'recharts'

import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  type ChartConfig,
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from '@/components/ui/chart'

/* ─── Stat Cards ─── */

const iconEntries = {
  'alert-triangle': {
    icon: AlertTriangle,
    bg: 'bg-amber-100',
    fg: 'text-amber-600',
  },
  gauge: {
    icon: Gauge,
    bg: 'bg-blue-100',
    fg: 'text-blue-600',
  },
  'check-circle': {
    icon: CheckCircle2,
    bg: 'bg-emerald-100',
    fg: 'text-emerald-600',
  },
} as const

export type StatCardProps = {
  title: string
  value: string
  description: string
  icon: keyof typeof iconEntries
}

export function StatCard({ title, value, description, icon }: StatCardProps) {
  const entry = iconEntries[icon]
  const Icon = entry.icon
  return (
    <Card size="sm" className="shadow-sm">
      <CardHeader>
        <CardDescription>{title}</CardDescription>
        <CardTitle>
          <p className="text-3xl font-semibold">{value}</p>
        </CardTitle>
        <CardAction>
          <div
            className={`flex size-8 items-center justify-center rounded-lg ${entry.bg}`}
          >
            <Icon className={`size-4 ${entry.fg}`} />
          </div>
        </CardAction>
      </CardHeader>
      <CardContent>
        <p className="text-xs text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  )
}

/* ─── Status Pie Chart ─── */

export type StatusDatum = { status: string; count: number; fill: string }

const statusConfig = {
  count: { label: 'Incidents' },
  pending: { label: 'Pending', color: 'var(--chart-1)' },
  triaging: { label: 'Triaging', color: 'var(--chart-2)' },
  triaged: { label: 'Triaged', color: 'var(--chart-3)' },
  resolved: { label: 'Resolved', color: 'var(--chart-4)' },
} satisfies ChartConfig

export function StatusPieChart({
  data,
  total,
}: {
  data: StatusDatum[]
  total: number
}) {
  return (
    <Card className="shadow-sm">
      <CardHeader>
        <CardTitle>By Status</CardTitle>
        <CardDescription>Pipeline distribution</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer
          config={statusConfig}
          className="mx-auto aspect-square max-h-62.5"
        >
          <PieChart>
            <ChartTooltip
              cursor={false}
              content={<ChartTooltipContent hideLabel />}
            />
            <Pie
              data={data}
              dataKey="count"
              nameKey="status"
              innerRadius={60}
              strokeWidth={5}
            >
              {data.map((entry) => (
                <Cell
                  key={entry.status}
                  fill={`var(--color-${entry.status})`}
                />
              ))}
              <Label
                content={({ viewBox }) => {
                  if (viewBox && 'cx' in viewBox && 'cy' in viewBox) {
                    return (
                      <text x={viewBox.cx} y={viewBox.cy} textAnchor="middle">
                        <tspan
                          x={viewBox.cx}
                          y={(viewBox.cy ?? 0) - 20}
                          className="fill-foreground text-3xl font-bold"
                        >
                          {total}
                        </tspan>
                        <tspan
                          x={viewBox.cx}
                          y={(viewBox.cy ?? 0) + 4}
                          className="fill-muted-foreground text-xs"
                        >
                          Incidents
                        </tspan>
                      </text>
                    )
                  }
                }}
              />
            </Pie>
            <ChartLegend
              content={<ChartLegendContent nameKey="status" />}
              className="-translate-y-2 flex-wrap gap-2 *:basis-1/4 *:justify-center"
            />
          </PieChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}

/* ─── Priority Bar Chart (Horizontal) ─── */

export type PriorityDatum = { priority: string; count: number; fill: string }

const priorityConfig = {
  count: { label: 'Incidents' },
  critical: { label: 'Critical', color: 'var(--chart-1)' },
  high: { label: 'High', color: 'var(--chart-2)' },
  medium: { label: 'Medium', color: 'var(--chart-3)' },
  low: { label: 'Low', color: 'var(--chart-5)' },
} satisfies ChartConfig

export function PriorityBarChart({ data }: { data: PriorityDatum[] }) {
  return (
    <Card className="shadow-sm">
      <CardHeader>
        <CardTitle>By Priority</CardTitle>
        <CardDescription>Urgency breakdown</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={priorityConfig}>
          <BarChart data={data} layout="vertical" margin={{ left: 8 }}>
            <YAxis
              dataKey="priority"
              type="category"
              tickLine={false}
              tickMargin={10}
              axisLine={false}
              tickFormatter={(v: string) =>
                priorityConfig[v as keyof typeof priorityConfig]?.label ?? v
              }
            />
            <XAxis dataKey="count" type="number" hide />
            <ChartTooltip
              cursor={false}
              content={<ChartTooltipContent hideLabel />}
            />
            <Bar dataKey="count" radius={5}>
              {data.map((entry) => (
                <Cell
                  key={entry.priority}
                  fill={`var(--color-${entry.priority})`}
                />
              ))}
              <LabelList
                dataKey="count"
                position="right"
                offset={8}
                className="fill-foreground"
                fontSize={12}
              />
            </Bar>
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}

/* ─── Category Bar Chart (Vertical) ─── */

export type CategoryDatum = { category: string; count: number; fill: string }

const categoryConfig = {
  count: { label: 'Incidents' },
  bug: { label: 'Bug', color: 'var(--chart-1)' },
  security: { label: 'Security', color: 'var(--chart-2)' },
  outage: { label: 'Outage', color: 'var(--chart-3)' },
  performance: { label: 'Performance', color: 'var(--chart-4)' },
  data_issue: { label: 'Data Issue', color: 'var(--chart-5)' },
  other: { label: 'Other', color: 'var(--chart-2)' },
} satisfies ChartConfig

export function CategoryBarChart({ data }: { data: CategoryDatum[] }) {
  return (
    <Card className="shadow-sm">
      <CardHeader>
        <CardTitle>By Category</CardTitle>
        <CardDescription>Incident types</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={categoryConfig}>
          <BarChart data={data} margin={{ top: 20 }}>
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="category"
              tickLine={false}
              tickMargin={10}
              axisLine={false}
              tickFormatter={(v: string) =>
                categoryConfig[v as keyof typeof categoryConfig]?.label ?? v
              }
            />
            <ChartTooltip
              cursor={false}
              content={<ChartTooltipContent hideLabel />}
            />
            <Bar dataKey="count" radius={[4, 4, 0, 0]}>
              {data.map((entry) => (
                <Cell
                  key={entry.category}
                  fill={`var(--color-${entry.category})`}
                />
              ))}
              <LabelList
                dataKey="count"
                position="top"
                offset={4}
                className="fill-foreground"
                fontSize={12}
              />
            </Bar>
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}

/* ─── Severity Distribution ─── */

export type SeverityDatum = { score: string; count: number }

const severityConfig = {
  count: { label: 'Incidents', color: 'var(--chart-3)' },
} satisfies ChartConfig

export function SeverityHistogram({ data }: { data: SeverityDatum[] }) {
  return (
    <Card className="shadow-sm">
      <CardHeader>
        <CardTitle>Severity Distribution</CardTitle>
        <CardDescription>Score frequency (1-10)</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={severityConfig}>
          <BarChart data={data} margin={{ top: 20 }}>
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="score"
              tickLine={false}
              tickMargin={10}
              axisLine={false}
            />
            <ChartTooltip
              cursor={false}
              content={<ChartTooltipContent hideLabel />}
            />
            <Bar
              dataKey="count"
              fill="var(--color-count)"
              radius={[4, 4, 0, 0]}
            >
              <LabelList
                dataKey="count"
                position="top"
                offset={4}
                className="fill-foreground"
                fontSize={12}
              />
            </Bar>
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}

/* ─── Incidents Over Time (Area) ─── */

export type TimeSeriesDatum = { date: string; count: number }

const timeSeriesConfig = {
  count: { label: 'Incidents', color: 'var(--chart-2)' },
} satisfies ChartConfig

export function IncidentsOverTimeChart({ data }: { data: TimeSeriesDatum[] }) {
  return (
    <Card className="shadow-sm">
      <CardHeader>
        <CardTitle>Incidents Over Time</CardTitle>
        <CardDescription>Daily volume — last 30 days</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={timeSeriesConfig} className="h-64 w-full">
          <AreaChart
            data={data}
            margin={{ top: 8, left: 12, right: 12, bottom: 0 }}
          >
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="date"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              tickFormatter={(v: string) => {
                const d = new Date(v)
                return d.toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric',
                })
              }}
            />
            <ChartTooltip
              cursor={false}
              content={<ChartTooltipContent indicator="line" />}
            />
            <Area
              dataKey="count"
              type="natural"
              fill="var(--color-count)"
              fillOpacity={0.2}
              stroke="var(--color-count)"
              strokeWidth={2}
            />
          </AreaChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
