import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// Dev server proxies:
//  - /api  -> Guardian dashboard REST layer (uvicorn on :8001)
//  - /docs -> the Mintlify docs site (mint dev on :3000), so both apps live on :5173.
//
// Mintlify's client-side router doesn't know it's mounted under /docs — once its JS loads,
// clicking any in-page link navigates to its bare page path (e.g. /connect/chatgpt, not
// /docs/connect/chatgpt). Those bare paths must ALSO be proxied, or Vite's SPA fallback
// serves the dashboard's index.html for them and React Router 404s (no matching route).
// The docs.json nav groups are proxied here by their top-level segment. The former
// "detectors/*" group was renamed to "what-we-detect/*" specifically to avoid colliding
// with this dashboard's own /detectors route (src/pages/Detectors.jsx) — do not add a
// bare "/detectors" proxy rule, or it will shadow that page.
const MINTLIFY_TARGET = "http://localhost:3000";
const mintlifyProxy = { target: MINTLIFY_TARGET, changeOrigin: true };

// Bare top-level segments used by docs/docs.json's nav groups (see that file's
// "navigation.groups[].pages" prefixes) — keep this list in sync if groups are renamed.
const MINTLIFY_BARE_PREFIXES = [
  "/getting-started",
  "/connect",
  "/how-scanning-works",
  "/results",
  "/what-we-detect",
  "/privacy-trust",
  "/troubleshooting",
  "/glossary",
];

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
      },
      "/docs": {
        ...mintlifyProxy,
        rewrite: (p) => p.replace(/^\/docs/, "") || "/",
      },
      "/_next": mintlifyProxy,
      "/favicons": mintlifyProxy,
      "/sitemap.xml": mintlifyProxy,
      "/llms.txt": mintlifyProxy,
      "/robots.txt": mintlifyProxy,
      ...Object.fromEntries(MINTLIFY_BARE_PREFIXES.map((p) => [p, mintlifyProxy])),
    },
  },
});
