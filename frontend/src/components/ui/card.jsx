import { cn } from "@/lib/utils";

export function Card({ className, ...props }) {
  return <div className={cn("panel overflow-hidden", className)} {...props} />;
}

// Header = title block at the top of a card's padding, no divider rule.
export function CardHeader({ className, ...props }) {
  return <div className={cn("panel-header", className)} {...props} />;
}

export function CardTitle({ className, ...props }) {
  return (
    <h3
      className={cn("text-[14.5px] font-bold leading-none tracking-tight", className)}
      {...props}
    />
  );
}

export function CardDescription({ className, ...props }) {
  return <p className={cn("mt-1 text-[11.5px] text-muted-foreground", className)} {...props} />;
}

export function CardContent({ className, ...props }) {
  return <div className={cn("p-4", className)} {...props} />;
}

export function CardFooter({ className, ...props }) {
  return <div className={cn("flex items-center px-4 pb-4", className)} {...props} />;
}
