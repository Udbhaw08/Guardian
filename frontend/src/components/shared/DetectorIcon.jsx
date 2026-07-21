import { detectorMeta } from "@/lib/constants";
import { cn } from "@/lib/utils";

/** Renders a detector's Lucide SVG icon (no emoji). */
export function DetectorIcon({ name, className }) {
  const { Icon } = detectorMeta(name);
  return <Icon className={cn("h-4 w-4", className)} aria-hidden />;
}
