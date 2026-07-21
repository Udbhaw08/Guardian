import { useCallback } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  LabelList,
} from "recharts";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { formatDay, cn } from "@/lib/utils";
import {
  DECISION_META,
  SEVERITY_META,
  SEVERITIES,
  detectorMeta,
} from "@/lib/constants";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/shared/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { ShieldCheck, ShieldAlert, ShieldX, Terminal, Layers } from "lucide-react";

function pct(n) {
  return `${Math.round((n || 0) * 100)}%`;
}

export default function Analytics() {
  const { data, loading, error } = useApi(useCallback(() => api.stats(), []), [], 15000);

  if (error) return <ErrorState message={`Couldn't load analytics: ${error}`} />;
  if (loading || !data) {
    return (
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-72 rounded-xl" />)}
      </div>
    );
  }

  // Aggregate timeseries daily totals for a clean, non-artificial volume chart
  const timelineData = data.timeseries.map((d) => ({
    date: d.date,
    total: (d.ALLOW || 0) + (d.WARN_CONFIRM || 0) + (d.BLOCK || 0),
    blocked: d.BLOCK || 0,
    allowed: d.ALLOW || 0,
    warned: d.WARN_CONFIRM || 0,
  }));

  const detectorData = Object.entries(data.detectors)
    .sort((a, b) => b[1] - a[1])
    .map(([name, count]) => ({ name: detectorMeta(name).label, short: name, value: count }));

  const clientData = Object.entries(data.clients)
    .sort((a, b) => b[1] - a[1])
    .map(([name, count]) => ({ name, value: count }));

  const totalScans = data.total_scans || 1;

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="border-b border-border pb-5">
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          Security Analytics &amp; Metrics
        </h1>
        <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
          Quantified threat metrics, policy enforcement distributions, and detector hit rates
        </p>
      </div>

      {/* Top 3 High-Impact Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="panel p-5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Total Interceptions</span>
            <span className="h-8 w-8 rounded-lg bg-secondary flex items-center justify-center text-foreground border border-border">
              <Layers className="h-4 w-4" />
            </span>
          </div>
          <p className="text-3xl font-extrabold text-foreground tabular-nums mt-2">{data.total_scans}</p>
          <p className="text-xs text-muted-foreground mt-1">Prompt and file payloads scanned</p>
        </Card>

        <Card className="panel p-5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-rose-600">Threat Block Rate</span>
            <span className="h-8 w-8 rounded-lg bg-rose-50 flex items-center justify-center text-rose-600 border border-rose-200">
              <ShieldX className="h-4 w-4" />
            </span>
          </div>
          <p className="text-3xl font-extrabold text-foreground tabular-nums mt-2">
            {pct(data.block_rate)}
          </p>
          <p className="text-xs text-muted-foreground mt-1">{data.decisions.BLOCK} critical exfiltrations stopped</p>
        </Card>

        <Card className="panel p-5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-600">Clean Pass Rate</span>
            <span className="h-8 w-8 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-600 border border-emerald-200">
              <ShieldCheck className="h-4 w-4" />
            </span>
          </div>
          <p className="text-3xl font-extrabold text-foreground tabular-nums mt-2">
            {pct(data.decisions.ALLOW / totalScans)}
          </p>
          <p className="text-xs text-muted-foreground mt-1">{data.decisions.ALLOW} benign requests approved</p>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Daily Scan Volume (Replacing the wavy multi-color mountain chart) */}
        <Card className="panel lg:col-span-2">
          <CardHeader className="pb-3 border-b border-border">
            <CardTitle>Daily Interception Throughput</CardTitle>
            <CardDescription>Total volume of requests inspected per day</CardDescription>
          </CardHeader>
          <CardContent className="pt-4">
            {timelineData.length === 0 ? (
              <EmptyState title="No timeline data" description="Scans will chart here as they occur." />
            ) : (
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={timelineData} margin={{ left: -20, right: 12, top: 12 }}>
                  <CartesianGrid stroke="#E2E8F0" vertical={false} strokeDasharray="3 3" opacity={0.6} />
                  <XAxis dataKey="date" tickFormatter={formatDay} tick={{ fontSize: 11, fill: "#64748B" }} axisLine={{ stroke: "#E2E8F0" }} tickLine={false} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} width={36} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#FFFFFF", borderColor: "#E2E8F0", borderRadius: "0.5rem", boxShadow: "0 4px 6px -1px rgba(0,0,0,0.1)", fontSize: "12px" }}
                  />
                  <Bar dataKey="total" name="Total Scans" fill="#2563EB" radius={[4, 4, 0, 0]} maxBarSize={36} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Decision Breakdown (Clean Linear Metrics instead of Cartoonish Donut) */}
        <Card className="panel flex flex-col">
          <CardHeader className="pb-3 border-b border-border">
            <CardTitle>Decision Enforcement Distribution</CardTitle>
            <CardDescription>Posture breakdown across all evaluated interactions</CardDescription>
          </CardHeader>
          <CardContent className="pt-5 flex flex-col gap-4">
            {/* Blocked */}
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-rose-500" />
                  <span className="font-semibold text-foreground">Blocked (Threat Interceptions)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="mono text-muted-foreground">{data.decisions.BLOCK || 0}</span>
                  <span className="mono font-bold text-rose-600">{pct(data.decisions.BLOCK / totalScans)}</span>
                </div>
              </div>
              <div className="w-full bg-secondary h-2.5 rounded-full overflow-hidden">
                <div className="bg-rose-500 h-full rounded-full transition-all" style={{ width: pct(data.decisions.BLOCK / totalScans) }} />
              </div>
            </div>

            {/* Allowed */}
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
                  <span className="font-semibold text-foreground">Allowed (Clean &amp; Safe)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="mono text-muted-foreground">{data.decisions.ALLOW || 0}</span>
                  <span className="mono font-bold text-emerald-600">{pct(data.decisions.ALLOW / totalScans)}</span>
                </div>
              </div>
              <div className="w-full bg-secondary h-2.5 rounded-full overflow-hidden">
                <div className="bg-emerald-500 h-full rounded-full transition-all" style={{ width: pct(data.decisions.ALLOW / totalScans) }} />
              </div>
            </div>

            {/* Warn */}
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
                  <span className="font-semibold text-foreground">Warned (Human Confirmation Required)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="mono text-muted-foreground">{data.decisions.WARN_CONFIRM || 0}</span>
                  <span className="mono font-bold text-amber-600">{pct(data.decisions.WARN_CONFIRM / totalScans)}</span>
                </div>
              </div>
              <div className="w-full bg-secondary h-2.5 rounded-full overflow-hidden">
                <div className="bg-amber-500 h-full rounded-full transition-all" style={{ width: pct(data.decisions.WARN_CONFIRM / totalScans) }} />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Severity Breakdown */}
        <Card className="panel flex flex-col">
          <CardHeader className="pb-3 border-b border-border">
            <CardTitle>Risk Severity Breakdown</CardTitle>
            <CardDescription>Classification of detected threats by severity tier</CardDescription>
          </CardHeader>
          <CardContent className="pt-5 flex flex-col gap-3.5">
            {SEVERITIES.map((s) => {
              const count = data.severity[s] || 0;
              const ratio = count / totalScans;
              return (
                <div key={s} className="flex flex-col gap-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold capitalize text-foreground">{SEVERITY_META[s].label}</span>
                    <span className="mono text-muted-foreground">{count} ({pct(ratio)})</span>
                  </div>
                  <div className="w-full bg-secondary h-2 rounded-full overflow-hidden">
                    <div
                      className={cn(
                        "h-full rounded-full",
                        s === "critical" && "bg-rose-500",
                        s === "high" && "bg-orange-500",
                        s === "medium" && "bg-amber-500",
                        s === "low" && "bg-emerald-500"
                      )}
                      style={{ width: `${Math.max(ratio * 100, 2)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>

        {/* Detector Frequency */}
        <Card className="panel lg:col-span-2">
          <CardHeader className="pb-3 border-b border-border">
            <CardTitle>Threat Detections by Signature</CardTitle>
            <CardDescription>Most frequently triggered detector modules</CardDescription>
          </CardHeader>
          <CardContent className="pt-4">
            {detectorData.length === 0 ? (
              <EmptyState title="No detector hits" />
            ) : (
              <ResponsiveContainer width="100%" height={Math.max(220, detectorData.length * 36)}>
                <BarChart data={detectorData} layout="vertical" margin={{ left: 16, right: 32, top: 4 }}>
                  <CartesianGrid stroke="#E2E8F0" horizontal={false} strokeDasharray="3 3" opacity={0.6} />
                  <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11, fill: "#64748B" }} axisLine={false} tickLine={false} />
                  <YAxis type="category" dataKey="name" width={180} tick={{ fontSize: 11, fill: "#0F172A", fontWeight: 500 }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#FFFFFF", borderColor: "#E2E8F0", borderRadius: "0.5rem", boxShadow: "0 4px 6px -1px rgba(0,0,0,0.1)", fontSize: "12px" }}
                  />
                  <Bar dataKey="value" name="Threat Hits" fill="#0F172A" radius={[0, 4, 4, 0]} maxBarSize={20}>
                    <LabelList dataKey="value" position="right" className="font-mono text-xs fill-foreground" />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
