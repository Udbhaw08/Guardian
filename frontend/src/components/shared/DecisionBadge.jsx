import { cn } from "@/lib/utils";
import { ShieldCheck, ShieldAlert, ShieldX } from "lucide-react";

const styles = {
  ALLOW: "bg-emerald-50 text-emerald-700 border-emerald-200/80",
  WARN_CONFIRM: "bg-amber-50 text-amber-700 border-amber-200/80",
  BLOCK: "bg-rose-50 text-rose-700 border-rose-200/80",
};

const icons = {
  ALLOW: ShieldCheck,
  WARN_CONFIRM: ShieldAlert,
  BLOCK: ShieldX,
};

const labels = {
  ALLOW: "Allowed",
  WARN_CONFIRM: "Warn / Confirm",
  BLOCK: "Blocked",
};

export function DecisionBadge({ decision, className, showIcon = true }) {
  const Icon = icons[decision] || ShieldAlert;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-semibold tracking-tight shadow-2xs",
        styles[decision] || "bg-secondary text-muted-foreground border-border",
        className
      )}
    >
      {showIcon && <Icon className="h-3 w-3 shrink-0" />}
      {labels[decision] || decision}
    </span>
  );
}
