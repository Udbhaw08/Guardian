import { useCallback, useEffect, useState } from "react";

/**
 * Fetch-on-mount hook with loading/error/reload.
 * fn should be a stable function returning a promise (wrap in useCallback).
 *
 * Pass intervalMs to silently re-fetch in the background on a timer (no
 * loading-skeleton flicker) — used to keep dashboard screens in sync with
 * scans coming in from other clients (MCP tools, other browser tabs, etc).
 */
export function useApi(fn, deps = [], intervalMs = 0) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback((opts) => {
    const silent = !!(opts && opts.silent);
    let alive = true;
    if (!silent) setLoading(true);
    setError(null);
    fn()
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e.message || String(e)))
      .finally(() => alive && !silent && setLoading(false));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => load(), [load]);

  useEffect(() => {
    if (!intervalMs) return undefined;
    const id = setInterval(() => load({ silent: true }), intervalMs);
    return () => clearInterval(id);
  }, [load, intervalMs]);

  return { data, loading, error, reload: load };
}

/** Track whether the `dark` class is present on <html>, for chart theming. */
export function useIsDark() {
  const [isDark, setIsDark] = useState(
    () => typeof document !== "undefined" && document.documentElement.classList.contains("dark")
  );
  useEffect(() => {
    const el = document.documentElement;
    const obs = new MutationObserver(() => setIsDark(el.classList.contains("dark")));
    obs.observe(el, { attributes: true, attributeFilter: ["class"] });
    return () => obs.disconnect();
  }, []);
  return isDark;
}
