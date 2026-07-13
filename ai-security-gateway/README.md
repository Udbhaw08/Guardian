# AI Security Gateway

AI Security Gateway is an MCP-based security layer that scans user prompts before they are processed by an AI assistant.

The gateway detects sensitive data, credentials, payment information, national identifiers, and prompt-injection attempts. Based on configured policies, it returns one of three decisions:

- `ALLOW`
- `WARN_CONFIRM`
- `BLOCK`

The project can be connected to ChatGPT as a custom MCP plugin through an ngrok public tunnel.
# AI Security Gateway — Connecting to ChatGPT

## Local Testing (via Ngrok)

**Terminal 1 — Start the server:**
```powershell
cd ai-security-gateway
$env:AUTH_ENABLED="false"
uvicorn mcp_server.app:app --host 0.0.0.0 --port 8000
```

**Terminal 2 — Expose publicly:**
```bash
ngrok http 8000
# Gives you: https://abc1-23-45.ngrok-free.app
```

**In ChatGPT:**
1. Go to **Plugins → Add plugin** (or Settings → Connected Apps → MCP)
2. Name it: `AI Security Gateway`
3. URL: `https://abc1-23-45.ngrok-free.app/mcp`
4. Connect it with chatgpt and try this in new chat : "Scan this for security issues: "My SSN is 372-79-5190."
5. check terminal logs, you can see our toll got called.

---

## Production (Render)

1. Deploy to Render (see `render.yaml`)
2. In ChatGPT, use: `https://your-app.onrender.com/mcp`

---

## Policy Reference

| Prompt contains | Decision |
|---|---|
| AWS / GCP / GitHub API key | 🚫 BLOCK |
| Credit card number | ⚠️ WARN — user can Allow or Deny |
| SSN / Aadhaar | ⚠️ WARN — user can Allow or Deny |
| Safe text | ✅ ALLOW |

---

## Current Features

The gateway currently supports:

- API key and credential detection
- Credit and debit card detection
- CVV and CVC detection
- SSN and Aadhaar detection
- Prompt-injection and jailbreak detection
- YAML-based security policies
- Masked audit logging
- MCP integration with ChatGPT
- Automatic detector discovery
- Unit and integration testing

---

## Architecture

```text
User
  |
  v
ChatGPT
  |
  v
MCP Server (/mcp)
  |
  v
scan_prompt Tool
  |
  v
Core Scanner
  |
  v
Detector Registry
  |
  +-- API Key Detector
  +-- Credit Card Detector
  +-- CVV Detector
  +-- National ID Detector
  +-- Prompt Injection Detector
  |
  v
Policy Engine
  |
  v
Audit Logger
  |
  v
ALLOW / WARN_CONFIRM / BLOCK
  |
  v
Response returned to ChatGPT