import { useIsDark } from "@/lib/hooks";
import { cn } from "@/lib/utils";

/**
 * Theme-aware chart tokens, mirroring the dataviz skill's surface/ink/grid values.
 * Recessive grid + muted axis ink; text never wears a series color.
 * Matches the design system's dark/light border + muted-foreground tokens
 * (frontend/src/index.css) so charts sit flush with the surrounding cards.
 */
export function useChartTokens() {
  const isDark = useIsDark();
  return {
    isDark,
    grid: isDark ? "#212838" : "#e4e7ef",
    axis: isDark ? "#212838" : "#e4e7ef",
    tick: isDark ? "#8b93a7" : "#6b7280",
    surface: isDark ? "#12161f" : "#ffffff",
  };
}

/** Shared legend row — nests inside a chart card's panel-inset strip, image-2 style. */
export function ChartLegend({ items, className }) {
  return (
    <ul className={cn("flex flex-wrap gap-x-4 gap-y-1.5", className)}>
      {items.map((it) => (
        <li key={it.label} className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <span className="inline-block h-2.5 w-2.5 rounded-[3px]" style={{ backgroundColor: it.color }} />
          {it.label}
          {it.value !== undefined && <span className="font-semibold text-foreground">· {it.value}</span>}
        </li>
      ))}
    </ul>
  );
}

/** Shared tooltip card — text tokens only, a colored swatch carries identity. */
export function ChartTooltip({ active, payload, label, valueLabel }) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="rounded-xl border border-border bg-card px-3.5 py-2.5 text-xs shadow-card">
      {label !== undefined && (
        <p className="mb-1.5 font-semibold text-foreground">{label}</p>
      )}
      <div className="flex flex-col gap-1.5">
        {payload.map((entry, i) => (
          <div key={i} className="flex items-center gap-2">
            <span
              className="inline-block h-2.5 w-2.5 rounded-[3px]"
              style={{ backgroundColor: entry.color || entry.payload?.fill }}
            />
            <span className="text-muted-foreground">{entry.name}</span>
            <span className="ml-auto font-semibold tabular-nums text-foreground">
              {entry.value}
              {valueLabel ? ` ${valueLabel}` : ""}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
