# Guardian Dashboard (frontend)

A React dashboard for the AI Security Gateway. It surfaces everything the gateway
does today: live scanning, the scan feed, analytics, the detector catalog, and the
policy matrix.

- **Stack:** Vite + React (JavaScript) · Tailwind CSS · shadcn-style UI · Recharts · lucide-react
- **Data:** the thin REST layer in [`../ai-security-gateway/api/`](../ai-security-gateway/api/)
  (Starlette + CORS), which reuses the existing MCP tool handlers and reads/writes
  `audit/scans.db`.

## Running locally

Two processes. From `ai-security-gateway/` (with the repo venv active):

```bash
# 1) Dashboard REST API  (port 8001)
AUTH_ENABLED=false uvicorn api.app:app --host 0.0.0.0 --port 8001 --reload
```

From `frontend/`:

```bash
# 2) Dashboard UI  (port 5173, proxies /api -> :8001)
npm install     # first time only
npm run dev
```

Open http://localhost:5173.

> The MCP server (`mcp_server.app` on port 8000) is separate and unaffected — the
> dashboard talks only to the REST layer on 8001.

## Screens

| Route | Screen | Source |
|-------|--------|--------|
| `/` | Overview KPIs + recent activity | `GET /api/stats`, `GET /api/scans` |
| `/feed` | Scan feed (filter, expand → masked matches) | `GET /api/scans` |
| `/scan` | Interactive scanner (text / document / image) | `POST /api/scan[...]` |
| `/analytics` | Decisions, detectors, severity, clients | `GET /api/stats` |
| `/detectors` | Detector catalog | `GET /api/detectors` |
| `/policy` | Detector × severity → action matrix | `GET /api/policy` |

## Notes

- **Masked-only invariant:** the UI never shows raw sensitive values — only masked
  values (`AKIA****`) and detector type names, matching the backend guarantee.
- **Chart colors** use the `dataviz` skill's validated status + categorical palettes
  (pass CVD / contrast checks in light and dark).
- Set `DASHBOARD_CORS_ORIGINS` on the API to allow additional origins (defaults to the
  Vite dev origin).
