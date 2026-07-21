import { useCallback } from "react";
import { Layers, Info, ShieldAlert, Sliders } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { detectorMeta, SEVERITY_META } from "@/lib/constants";
import { DetectorIcon } from "@/components/shared/DetectorIcon";
import { cn } from "@/lib/utils";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { ErrorState } from "@/components/shared/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";

const ACTION_STYLES = {
  ALLOW: "bg-emerald-500/10 text-emerald-400 border-emerald-500/25",
  WARN_CONFIRM: "bg-amber-500/10 text-amber-400 border-amber-500/25",
  BLOCK: "bg-rose-500/10 text-rose-400 border-rose-500/25",
};

const ACTION_LABEL = {
  ALLOW: "Allow",
  WARN_CONFIRM: "Warn / Confirm",
  BLOCK: "Block",
};

function ActionCell({ action }) {
  if (!action) return <span className="text-xs text-muted-foreground">—</span>;
  return (
    <span
      className={cn(
        "inline-flex items-center rounded border px-2 py-0.5 text-[11px] font-semibold tracking-tight",
        ACTION_STYLES[action] || "bg-muted text-muted-foreground border-border"
      )}
    >
      {ACTION_LABEL[action] || action}
    </span>
  );
}

export default function Policy() {
  const { data, loading, error } = useApi(useCallback(() => api.policy(), []));

  if (error) return <ErrorState message={`Couldn't load policy matrix: ${error}`} />;
  if (loading || !data) return <Skeleton className="h-96 rounded-xl" />;

  const severities = data.severities || ["critical", "high", "medium", "low"];
  const detectors = data.detectors || {};

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="border-b border-border/60 pb-5">
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
          Policy Engine Matrix
        </h1>
        <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
          Configured rules mapping detected threat severities to automated enforcement decisions
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader className="flex-row items-center gap-3 space-y-0 pb-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-500/10 border border-emerald-500/25 text-emerald-400">
              <Layers className="h-4 w-4" />
            </div>
            <div>
              <CardTitle>Aggregation Strategy</CardTitle>
              <CardDescription className="mono text-xs text-primary font-semibold">
                {data.aggregation_rule || "highest_severity"}
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent className="text-xs text-muted-foreground leading-relaxed">
            When multiple detectors trigger during a single scan, the single finding with the highest-ranked policy action (<code className="mono text-foreground font-semibold">BLOCK</code> &gt; <code className="mono text-foreground font-semibold">WARN_CONFIRM</code> &gt; <code className="mono text-foreground font-semibold">ALLOW</code>) determines the overall decision.
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center gap-3 space-y-0 pb-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-secondary text-muted-foreground border border-border">
              <Info className="h-4 w-4" />
            </div>
            <div>
              <CardTitle>Default Policy Fallback</CardTitle>
              <CardDescription>Applied to unlisted detectors or custom severities</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-x-4 gap-y-2">
              {severities.map((s) => (
                <div key={s} className="flex items-center gap-2">
                  <span className="text-xs capitalize font-medium text-muted-foreground">
                    {SEVERITY_META[s]?.label || s}:
                  </span>
                  <ActionCell action={data.defaults?.[s]} />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="border-b border-border/60 pb-3">
          <CardTitle>Detector × Severity Enforcement Grid</CardTitle>
          <CardDescription>
            Active decision matrix enforced across all incoming LLM prompt and payload requests
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="border-b border-border/80 bg-muted/40">
                <TableHead className="min-w-[220px] text-[11px] font-semibold uppercase tracking-wider">Detector Module</TableHead>
                {severities.map((s) => (
                  <TableHead key={s} className="text-center text-[11px] font-semibold uppercase tracking-wider">
                    {SEVERITY_META[s]?.label || s}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {Object.entries(detectors).map(([name, mapping]) => {
                const meta = detectorMeta(name);
                return (
                  <TableRow key={name} className="border-b border-border/40 hover:bg-secondary/30 transition-colors">
                    <TableCell>
                      <div className="flex items-center gap-2.5">
                        <div className="flex h-7 w-7 items-center justify-center rounded bg-secondary/80 border border-border/60 text-muted-foreground">
                          <DetectorIcon name={name} className="h-3.5 w-3.5" />
                        </div>
                        <div className="leading-tight">
                          <p className="text-xs font-semibold text-foreground">{meta.label}</p>
                          <code className="mono text-[10px] text-muted-foreground">{name}</code>
                        </div>
                      </div>
                    </TableCell>
                    {severities.map((s) => (
                      <TableCell key={s} className="text-center">
                        <ActionCell action={mapping[s]} />
                      </TableCell>
                    ))}
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
