import { useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import {
  Menu,
  X,
  Search,
  ScrollText,
  BarChart3,
  Radar,
  ShieldCheck,
  Shield,
  BookOpen,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { ThemeToggle } from "@/components/shared/ThemeToggle";

const NAV_ITEMS = [
  { to: "/", label: "Scan Feed", icon: ScrollText, end: true },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/detectors", label: "Detectors", icon: Radar },
  { to: "/policy", label: "Policy Matrix", icon: ShieldCheck },
  { href: "/docs", label: "Docs", icon: BookOpen, hardNav: true },
];

function StatusPill() {
  const [online, setOnline] = useState(null);

  useEffect(() => {
    let alive = true;
    const ping = () =>
      api.health().then(() => alive && setOnline(true)).catch(() => alive && setOnline(false));
    ping();
    const id = setInterval(ping, 15000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  const state = online === false ? "block" : online ? "allow" : "muted";

  return (
    <div className="flex items-center gap-2 rounded-full border border-border bg-background px-3 py-1.5 text-xs font-medium">
      <span className="relative flex h-2 w-2">
        {state === "allow" && (
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
        )}
        <span
          className={cn(
            "relative inline-flex h-2 w-2 rounded-full",
            state === "allow" && "bg-emerald-500",
            state === "block" && "bg-rose-500",
            state === "muted" && "bg-zinc-400"
          )}
        />
      </span>
      <span className="text-[11.5px] text-muted-foreground font-medium">
        {online === false ? (
          <span className="text-rose-600 font-semibold">Offline</span>
        ) : online ? (
          <span className="text-foreground font-medium">Operational</span>
        ) : (
          "Connecting…"
        )}
      </span>
    </div>
  );
}

export function TopNav() {
  const [open, setOpen] = useState(false);

  return (
    <div className="flex items-center justify-between gap-4 px-4 sm:px-6 lg:px-8 py-3.5 bg-card border-b border-border">
      {/* Brand & Left Navigation */}
      <div className="flex items-center gap-8">
        <button
          type="button"
          aria-label="Open menu"
          onClick={() => setOpen((o) => !o)}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border text-foreground transition-colors hover:bg-secondary lg:hidden"
        >
          {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
        </button>

        {/* Logo */}
        <NavLink to="/" className="flex items-center gap-2.5 group">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-xs">
            <Shield className="h-4 w-4" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-[17px] font-extrabold tracking-tight text-foreground">Guardian</span>
            <span className="text-[11px] font-medium text-muted-foreground hidden sm:inline">
              AI Security Gateway
            </span>
          </div>
        </NavLink>

        {/* Desktop Nav Items */}
        <nav className="hidden items-center gap-1 lg:flex">
          {NAV_ITEMS.map(({ to, href, label, icon: Icon, end, hardNav }) =>
            hardNav ? (
              <a
                key={href}
                href={href}
                className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
              >
                <Icon className="h-3.5 w-3.5 opacity-60" />
                {label}
              </a>
            ) : (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-all",
                    isActive
                      ? "bg-secondary text-foreground font-semibold shadow-2xs"
                      : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground"
                  )
                }
              >
                <Icon className="h-3.5 w-3.5 opacity-60" />
                {label}
              </NavLink>
            )
          )}
        </nav>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        <StatusPill />
        <ThemeToggle />
      </div>

      {/* Mobile Drawer Menu */}
      {open && (
        <>
          <button
            aria-label="Close menu"
            className="fixed inset-0 z-30 bg-black/30 backdrop-blur-xs cursor-default lg:hidden"
            onClick={() => setOpen(false)}
          />
          <div className="panel absolute left-4 right-4 top-[calc(100%+0.5rem)] z-40 flex flex-col gap-2 p-4 lg:hidden shadow-lg bg-card">
            {NAV_ITEMS.map(({ to, href, label, icon: Icon, end, hardNav }) =>
              hardNav ? (
                <a
                  key={href}
                  href={href}
                  className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                >
                  <Icon className="h-4 w-4 shrink-0 opacity-70" />
                  {label}
                </a>
              ) : (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                      isActive
                        ? "bg-secondary text-foreground font-semibold"
                        : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                    )
                  }
                >
                  <Icon className="h-4 w-4 shrink-0 opacity-70" />
                  {label}
                </NavLink>
              )
            )}
          </div>
        </>
      )}
    </div>
  );
}
