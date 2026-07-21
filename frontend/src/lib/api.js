// Thin fetch wrapper for the Guardian dashboard REST layer.
// All requests go through Vite's /api proxy -> uvicorn api.app on :8001.

async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) {
    const message = (data && data.error) || `Request failed (${res.status})`;
    throw new Error(message);
  }
  return data;
}

export const api = {
  health: () => request("/api/health"),

  stats: () => request("/api/stats"),

  scans: (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") qs.append(k, v);
    });
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request(`/api/scans${suffix}`);
  },

  detectors: () => request("/api/detectors"),

  policy: () => request("/api/policy"),
};
