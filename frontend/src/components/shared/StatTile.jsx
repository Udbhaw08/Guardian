import { AreaChart, Area, ResponsiveContainer } from "recharts";
import { ArrowUp, ArrowDown } from "lucide-react";
import { cn } from "@/lib/utils";

const ACCENT = {
  primary: { icon: "text-emerald-400", chip: "bg-emerald-500/10 border-emerald-500/20 text-emerald-400", stroke: "#10b981" },
  allow: { icon: "text-emerald-400", chip: "bg-emerald-500/10 border-emerald-500/20 text-emerald-400", stroke: "#10b981" },
  warn: { icon: "text-amber-400", chip: "bg-amber-500/10 border-amber-500/20 text-amber-400", stroke: "#f59e0b" },
  block: { icon: "text-rose-400", chip: "bg-rose-500/10 border-rose-500/20 text-rose-400", stroke: "#f43f5e" },
  muted: { icon: "text-muted-foreground", chip: "bg-secondary border-border text-muted-foreground", stroke: "#71717a" },
};

/**
 * Stat tile: icon chip + micro-label, big numerical value with an optional trend delta,
 * and an inline sparkline.
 */
export function StatTile({ label, value, sub, icon: Icon, accent = "primary", series, delta, inset = false, className }) {
  const tone = ACCENT[accent] || ACCENT.primary;
  const points = Array.isArray(series) ? series.map((v, i) => ({ i, v })) : null;
  const hasDelta = typeof delta === "number" && Number.isFinite(delta);
  const deltaUp = hasDelta && delta >= 0;
  const gradientId = `spark-${String(label).toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;

  return (
    <div className={cn(
      "relative overflow-hidden rounded-xl border border-border/80 bg-card/70 p-4 transition-all hover:border-border hover:shadow-xs",
      className
    )}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
          {label}
        </span>
        {Icon && (
          <span className={cn("flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border", tone.chip)}>
            <Icon className="h-3.5 w-3.5" />
          </span>
        )}
      </div>

      <div className="mt-3 flex items-baseline justify-between gap-2">
        <p className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground tabular-nums">
          {value}
        </p>
        {hasDelta && (
          <span
            className={cn(
              "inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[11px] font-semibold tabular-nums border",
              deltaUp
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                : "bg-rose-500/10 text-rose-400 border-rose-500/20"
            )}
          >
            {deltaUp ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />}
            {Math.abs(delta).toFixed(1)}%
          </span>
        )}
      </div>

      <div className="mt-2 flex items-center justify-between gap-3">
        {sub && <p className="text-xs text-muted-foreground truncate">{sub}</p>}
        {points && points.length > 1 && (
          <div className="h-6 w-20 shrink-0 ml-auto">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={points} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={tone.stroke} stopOpacity={0.4} />
                    <stop offset="100%" stopColor={tone.stroke} stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <Area
                  type="monotone"
                  dataKey="v"
                  stroke={tone.stroke}
                  strokeWidth={1.5}
                  fill={`url(#${gradientId})`}
                  isAnimationActive={false}
                  dot={false}
                  activeDot={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}
