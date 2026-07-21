import { cn } from "@/lib/utils";
import { SEVERITY_META } from "@/lib/constants";

const styles = {
  critical: "bg-rose-50 text-rose-700 border-rose-200/80",
  high: "bg-orange-50 text-orange-700 border-orange-200/80",
  medium: "bg-amber-50 text-amber-700 border-amber-200/80",
  low: "bg-emerald-50 text-emerald-700 border-emerald-200/80",
  none: "bg-secondary text-muted-foreground border-border",
};

export function SeverityBadge({ severity, className }) {
  const key = (severity || "none").toLowerCase();
  const meta = SEVERITY_META[key] || SEVERITY_META.none;
  return (
    <span
      className={cn(
        "mono inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider shadow-2xs",
        styles[key] || styles.none,
        className
      )}
    >
      <span className="h-1 w-1 rounded-full bg-current opacity-80" />
      {meta.label}
    </span>
  );
}
