import { DECISIONS, DECISION_META } from "@/lib/constants";
import { cn } from "@/lib/utils";

const BAR_COLOR = {
  ALLOW: "bg-emerald-500",
  WARN_CONFIRM: "bg-amber-500",
  BLOCK: "bg-rose-500",
};

const TEXT_COLOR = {
  ALLOW: "text-emerald-400",
  WARN_CONFIRM: "text-amber-400",
  BLOCK: "text-rose-400",
};

/** Single segmented bar + a per-decision breakdown list. `counts` = { ALLOW, WARN_CONFIRM, BLOCK }. */
export function DecisionBar({ counts, className }) {
  const total = DECISIONS.reduce((sum, d) => sum + (counts[d] || 0), 0);

  return (
    <div className={cn("flex flex-col gap-3.5", className)}>
      <div className="flex h-2.5 overflow-hidden rounded-full bg-secondary gap-0.5 p-0.5 border border-border/60">
        {DECISIONS.map((d) => {
          const pct = total > 0 ? ((counts[d] || 0) / total) * 100 : 0;
          if (pct === 0) return null;
          return (
            <span
              key={d}
              className={cn("h-full rounded-full transition-all duration-300", BAR_COLOR[d])}
              style={{ width: `${pct}%` }}
            />
          );
        })}
      </div>

      <div className="flex flex-col gap-2">
        {DECISIONS.map((d) => {
          const count = counts[d] || 0;
          const pct = total > 0 ? (count / total) * 100 : 0;
          return (
            <div key={d} className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span className={cn("h-2 w-2 rounded-full", BAR_COLOR[d])} />
                <span className="font-medium text-foreground">{DECISION_META[d].label}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="mono text-muted-foreground tabular-nums">{count}</span>
                <span className={cn("mono w-12 text-right font-semibold tabular-nums", TEXT_COLOR[d])}>
                  {pct.toFixed(1)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
