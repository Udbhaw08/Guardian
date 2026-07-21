import { cn } from "@/lib/utils";
import { detectorMeta } from "@/lib/constants";

export function DetectorChip({ name, className, showLabel = true }) {
  const { Icon, label } = detectorMeta(name);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border border-border/80 bg-secondary/60 px-2 py-0.5 text-xs font-medium text-foreground transition-colors hover:border-border",
        className
      )}
      title={label}
    >
      <Icon className="h-3 w-3 text-muted-foreground shrink-0" aria-hidden />
      {showLabel && <span>{label}</span>}
    </span>
  );
}
