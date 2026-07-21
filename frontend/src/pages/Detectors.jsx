import { useCallback } from "react";
import { FileText, Type, Shield, Terminal, KeyRound } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { DetectorIcon } from "@/components/shared/DetectorIcon";
import { SeverityBadge } from "@/components/shared/SeverityBadge";
import { Badge } from "@/components/ui/badge";
import { ErrorState } from "@/components/shared/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";

function DetectorCard({ d }) {
  return (
    <Card className="flex flex-col hover:border-border transition-all hover:shadow-xs">
      <CardHeader className="flex-row items-center gap-3 pb-2">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-emerald-500/25 bg-emerald-500/10 text-emerald-400">
          <DetectorIcon name={d.name} className="h-4 w-4" />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-bold text-foreground leading-tight">{d.label}</p>
          <code className="mono text-[11px] text-muted-foreground">{d.name}</code>
        </div>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-3 pt-2">
        <p className="text-xs text-muted-foreground leading-relaxed">{d.description}</p>

        <div className="panel-inset flex flex-1 flex-col justify-between gap-3 p-3">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] font-medium text-muted-foreground">Severity:</span>
            {d.severities.map((s) => (
              <SeverityBadge key={s} severity={s} />
            ))}
          </div>

          <div className="mt-1">
            <p className="mb-1 text-[10px] uppercase font-semibold tracking-wider text-muted-foreground">
              Signatures / Match Types
            </p>
            <div className="flex flex-wrap gap-1">
              {d.match_types.map((t) => (
                <span
                  key={t}
                  className="mono inline-flex items-center rounded border border-border/80 bg-background/60 px-1.5 py-0.5 text-[10px] text-foreground font-medium"
                >
                  {t}
                </span>
              ))}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function Section({ icon: Icon, title, subtitle, items }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <div className="flex h-6 w-6 items-center justify-center rounded bg-secondary text-primary">
          <Icon className="h-3.5 w-3.5" />
        </div>
        <h2 className="text-sm font-bold text-foreground">{title}</h2>
        <span className="text-xs text-muted-foreground">· {subtitle} ({items.length})</span>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {items.map((d) => (
          <DetectorCard key={d.name} d={d} />
        ))}
      </div>
    </div>
  );
}

export default function Detectors() {
  const { data, loading, error } = useApi(useCallback(() => api.detectors(), []));

  if (error) return <ErrorState message={`Couldn't load detector catalog: ${error}`} />;
  if (loading || !data) {
    return (
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-48 rounded-xl" />
        ))}
      </div>
    );
  }

  const promptDetectors = data.detectors.filter((d) => d.target === "prompt");
  const docDetectors = data.detectors.filter((d) => d.target === "document");

  return (
    <div className="flex flex-col gap-8">
      {/* Header */}
      <div className="border-b border-border/60 pb-5">
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
          Detector Engine Catalog
        </h1>
        <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
          Active pattern matching signatures, ML models, and heuristic scanners protecting conversations
        </p>
      </div>

      <div className="flex flex-col gap-8">
        <Section
          icon={Type}
          title="Chat & Prompt Scanners"
          subtitle="Real-time text tokenization & heuristic DLP"
          items={promptDetectors}
        />
        <Section
          icon={FileText}
          title="Document & Image Scanners"
          subtitle="PDF hidden layers, OCR classifiers, and archive structure"
          items={docDetectors}
        />
      </div>
    </div>
  );
}
