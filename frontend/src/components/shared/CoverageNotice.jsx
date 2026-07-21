import { Info } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Honest caveat about what this dashboard can and can't see: enforcement
 * depends on the connected AI assistant voluntarily calling the scan tools.
 * A skipped call leaves no record anywhere, so an empty/quiet feed means
 * "nothing we saw," not "nothing happened."
 *
 * Icon + hover tooltip (not a full banner) so it doesn't eat page height —
 * hover/focus the info icon to read the caveat.
 */
export function CoverageNotice({ className }) {
  return (
    <div className={cn("group/coverage relative inline-flex", className)}>
      <button
        type="button"
        aria-label="Scan coverage caveat"
        className="flex h-8 w-8 items-center justify-center rounded-full text-warn transition-colors hover:bg-warn/10 focus-visible:bg-warn/10 focus-visible:outline-none"
      >
        <Info className="h-4 w-4" />
      </button>
      <div
        role="tooltip"
        className={cn(
          "panel invisible absolute right-0 top-full z-30 mt-2 w-[300px] p-3.5 text-sm opacity-0",
          "transition-opacity duration-150 group-hover/coverage:visible group-hover/coverage:opacity-100",
          "group-focus-within/coverage:visible group-focus-within/coverage:opacity-100"
        )}
      >
        <p className="text-muted-foreground">
          <span className="font-medium text-foreground">This shows only scans that were actually triggered.</span>{" "}
          Enforcement relies on the connected AI assistant choosing to call the security tool before
          responding — a skipped call leaves no record here. Treat a quiet feed as "nothing we saw,"
          not a guarantee that nothing risky happened.
        </p>
      </div>
    </div>
  );
}
