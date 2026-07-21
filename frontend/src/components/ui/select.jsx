import { cn } from "@/lib/utils";
import { ChevronDown } from "lucide-react";

/**
 * Lightweight native <select> styled to match the shadcn look.
 * options: [{ value, label }]
 */
export function Select({ className, options = [], placeholder, ...props }) {
  return (
    <div className={cn("relative", className)}>
      <select
        className={cn(
          "h-9 w-full appearance-none rounded-full border border-input bg-background pl-4 pr-8 text-sm shadow-sm",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          "disabled:cursor-not-allowed disabled:opacity-50"
        )}
        {...props}
      >
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
    </div>
  );
}
