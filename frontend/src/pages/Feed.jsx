import { useCallback, useState } from "react";
import { ChevronDown, ChevronRight, RotateCw, Search, Shield, Filter, CheckCircle2, AlertTriangle, Ban } from "lucide-react";
import { api } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { formatTime, cn } from "@/lib/utils";
import { DECISIONS, DECISION_META, SEVERITIES, SEVERITY_META, detectorMeta } from "@/lib/constants";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { DecisionBadge } from "@/components/shared/DecisionBadge";
import { SeverityBadge } from "@/components/shared/SeverityBadge";
import { DetectorChip } from "@/components/shared/DetectorChip";
import { EmptyState, ErrorState } from "@/components/shared/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";

function pct(n) {
  return `${Math.round((n || 0) * 100)}%`;
}

const PAGE_SIZE = 25;

function MaskedMatches({ matches }) {
  if (!matches || matches.length === 0) {
    return <p className="text-xs text-muted-foreground py-2">No specific patterns recorded for this scan.</p>;
  }
  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-card">
      <Table>
        <TableHeader>
          <TableRow className="border-b border-border bg-secondary/40">
            <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Detector</TableHead>
            <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Severity</TableHead>
            <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Type</TableHead>
            <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Masked Finding</TableHead>
            <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Span</TableHead>
            <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Confidence</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {matches.map((m, i) => (
            <TableRow key={i} className="border-b border-border/50 last:border-0 hover:bg-secondary/20">
              <TableCell><DetectorChip name={m.detector} /></TableCell>
              <TableCell>{m.severity ? <SeverityBadge severity={m.severity} /> : "—"}</TableCell>
              <TableCell className="text-xs font-mono text-muted-foreground">{m.match_type || "—"}</TableCell>
              <TableCell>
                <code className="mono rounded bg-secondary px-2 py-0.5 text-xs text-foreground font-semibold border border-border/60">
                  {m.masked_value || "—"}
                </code>
              </TableCell>
              <TableCell className="mono text-xs text-muted-foreground">
                {Array.isArray(m.span) ? `${m.span[0]}–${m.span[1]}` : "—"}
              </TableCell>
              <TableCell className="mono text-xs tabular-nums text-muted-foreground">
                {typeof m.confidence === "number" ? `${Math.round(m.confidence * 100)}%` : "—"}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function Row({ row }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <TableRow
        className="cursor-pointer transition-colors hover:bg-secondary/40 border-b border-border"
        data-state={open ? "open" : undefined}
        onClick={() => setOpen((o) => !o)}
      >
        <TableCell className="w-8 text-muted-foreground">
          {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </TableCell>
        <TableCell className="mono whitespace-nowrap text-xs text-muted-foreground tabular-nums">
          {formatTime(row.scanned_at)}
        </TableCell>
        <TableCell><DecisionBadge decision={row.decision} /></TableCell>
        <TableCell>
          {row.highest_severity ? <SeverityBadge severity={row.highest_severity} /> : <span className="text-xs text-muted-foreground">—</span>}
        </TableCell>
        <TableCell>
          <div className="flex flex-wrap gap-1">
            {row.matched_detectors.length === 0 ? (
              <span className="text-xs text-muted-foreground">Clean request</span>
            ) : (
              row.matched_detectors.map((d) => <DetectorChip key={d} name={d} showLabel={false} />)
            )}
          </div>
        </TableCell>
        <TableCell className="mono text-xs tabular-nums font-semibold">{row.match_count}</TableCell>
        <TableCell className="hidden text-xs text-muted-foreground uppercase font-medium tracking-wider sm:table-cell">
          {row.client_name || "—"}
        </TableCell>
      </TableRow>
      {open && (
        <TableRow className="bg-secondary/20 hover:bg-secondary/20 border-b border-border">
          <TableCell colSpan={7} className="p-4">
            <div className="mb-3 rounded-lg border border-border bg-card p-3 text-xs leading-relaxed shadow-2xs">
              <span className="font-semibold text-foreground">Rule Decision Reason: </span>
              <span className="text-muted-foreground">{row.reason}</span>
            </div>
            <MaskedMatches matches={row.matches_json} />
            <div className="mt-3 flex items-center justify-between text-[11px] text-muted-foreground">
              <span>Payload Size: <strong className="font-mono text-foreground">{row.text_length}</strong> characters</span>
              <span>🔒 Zero-Leak Invariant: Raw sensitive tokens are never written to disk or logs.</span>
            </div>
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

export default function Feed() {
  const [decision, setDecision] = useState("");
  const [severity, setSeverity] = useState("");
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [page, setPage] = useState(0);

  const stats = useApi(useCallback(() => api.stats(), []), [], 15000);

  const fetcher = useCallback(
    () =>
      api.scans({
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
        decision,
        severity,
        search,
      }),
    [decision, severity, search, page]
  );
  const { data, loading, error, reload } = useApi(fetcher, [decision, severity, search, page], 15000);

  const total = data?.total || 0;
  const maxPage = Math.max(0, Math.ceil(total / PAGE_SIZE) - 1);

  const resetPageThen = (setter) => (v) => {
    setPage(0);
    setter(v);
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Security Scan Feed
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground mt-0.5">
            Real-time audit log of prompts, files, and payloads intercepted by Guardian
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => reload()}
            className="text-xs h-8 gap-1.5 bg-card border-border shadow-2xs"
          >
            <RotateCw className="h-3.5 w-3.5 text-muted-foreground" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Clean Minimalist KPI Summary Strip (Replacing the bulky rainbow bar) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.loading || !stats.data ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)
        ) : (
          <>
            <div className="panel p-4 flex items-center justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Total Scans</p>
                <p className="text-2xl font-extrabold text-foreground tabular-nums mt-0.5">{stats.data.total_scans}</p>
                <p className="text-[11px] text-muted-foreground mt-0.5">All incoming requests</p>
              </div>
              <div className="h-9 w-9 rounded-lg bg-secondary flex items-center justify-center text-muted-foreground border border-border">
                <Shield className="h-4 w-4" />
              </div>
            </div>

            <div className="panel p-4 flex items-center justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Blocked Threats</p>
                <p className="text-2xl font-extrabold text-rose-600 tabular-nums mt-0.5">{stats.data.decisions.BLOCK || 0}</p>
                <p className="text-[11px] text-muted-foreground mt-0.5">{pct(stats.data.block_rate)} block rate</p>
              </div>
              <div className="h-9 w-9 rounded-lg bg-rose-50 flex items-center justify-center text-rose-600 border border-rose-200">
                <Ban className="h-4 w-4" />
              </div>
            </div>

            <div className="panel p-4 flex items-center justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Under Review</p>
                <p className="text-2xl font-extrabold text-amber-600 tabular-nums mt-0.5">{stats.data.decisions.WARN_CONFIRM || 0}</p>
                <p className="text-[11px] text-muted-foreground mt-0.5">Required confirmation</p>
              </div>
              <div className="h-9 w-9 rounded-lg bg-amber-50 flex items-center justify-center text-amber-600 border border-amber-200">
                <AlertTriangle className="h-4 w-4" />
              </div>
            </div>

            <div className="panel p-4 flex items-center justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Allowed Safely</p>
                <p className="text-2xl font-extrabold text-emerald-600 tabular-nums mt-0.5">{stats.data.decisions.ALLOW || 0}</p>
                <p className="text-[11px] text-muted-foreground mt-0.5">Clean prompts</p>
              </div>
              <div className="h-9 w-9 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-600 border border-emerald-200">
                <CheckCircle2 className="h-4 w-4" />
              </div>
            </div>
          </>
        )}
      </div>

      {/* Filter and Audit Log Table */}
      <Card className="panel">
        <CardHeader className="border-b border-border pb-4 bg-card rounded-t-xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <CardTitle>Interception Events</CardTitle>
              <CardDescription>{total} event{total === 1 ? "" : "s"} match active filters</CardDescription>
            </div>

            {/* Filter controls */}
            <div className="flex flex-wrap items-center gap-2">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  resetPageThen(setSearch)(searchInput);
                }}
                className="relative"
              >
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                <Input
                  type="search"
                  placeholder="Search reason, detectors..."
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  className="pl-8 h-8 text-xs w-[180px] sm:w-[220px] bg-background border-border"
                />
              </form>

              <Select
                value={decision}
                onChange={(e) => resetPageThen(setDecision)(e.target.value)}
                className="h-8 text-xs w-[120px] bg-background border-border"
              >
                <option value="">All Decisions</option>
                {DECISIONS.map((d) => (
                  <option key={d} value={d}>{DECISION_META[d].label}</option>
                ))}
              </Select>

              <Select
                value={severity}
                onChange={(e) => resetPageThen(setSeverity)(e.target.value)}
                className="h-8 text-xs w-[120px] bg-background border-border"
              >
                <option value="">All Severities</option>
                {SEVERITIES.map((s) => (
                  <option key={s} value={s}>{SEVERITY_META[s].label}</option>
                ))}
              </Select>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-0 bg-card rounded-b-xl">
          {error ? (
            <div className="p-6"><ErrorState message={`Couldn't load feed: ${error}`} /></div>
          ) : loading && !data ? (
            <div className="p-4 flex flex-col gap-2">
              {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-10" />)}
            </div>
          ) : data.items.length === 0 ? (
            <div className="p-8">
              <EmptyState
                title="No events match criteria"
                description="Try clearing search filters or trigger a new prompt scan."
              />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-b border-border bg-secondary/30">
                  <TableHead className="w-8"></TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Timestamp</TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Decision</TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Max Severity</TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Threat Detectors</TableHead>
                  <TableHead className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">Hits</TableHead>
                  <TableHead className="hidden text-[11px] font-semibold uppercase tracking-wider text-muted-foreground sm:table-cell">Client</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.items.map((row) => (
                  <Row key={row.id} row={row} />
                ))}
              </TableBody>
            </Table>
          )}

          {/* Pagination */}
          {total > PAGE_SIZE && (
            <div className="flex items-center justify-between border-t border-border p-4 bg-card rounded-b-xl">
              <p className="text-xs text-muted-foreground">
                Showing <span className="font-semibold text-foreground">{page * PAGE_SIZE + 1}</span>–
                <span className="font-semibold text-foreground">{Math.min((page + 1) * PAGE_SIZE, total)}</span> of{" "}
                <span className="font-semibold text-foreground">{total}</span> events
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page === 0}
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  className="h-8 text-xs bg-background"
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= maxPage}
                  onClick={() => setPage((p) => Math.min(maxPage, p + 1))}
                  className="h-8 text-xs bg-background"
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
