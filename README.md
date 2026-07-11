# Guardian: AI Security Gateway & Governance Platform

<p align="center">
  <strong>Proactive, real-time security and data loss prevention (DLP) layer for LLM agents and AI assistants.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" alt="Python 3.11+" />
  <img src="https://img.shields.io/badge/Frontend-Vite%20%7C%20React-646CFF?logo=vite&logoColor=white" alt="Frontend: Vite + React" />
  <img src="https://img.shields.io/badge/Protocol-Model%20Context%20Protocol%20(MCP)-blue" alt="MCP Protocol" />
  <img src="https://img.shields.io/badge/Styling-TailwindCSS%20%7C%20shadcn-38B2AC?logo=tailwindcss&logoColor=white" alt="Tailwind CSS" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License" />
</p>

---

## Overview

**Guardian** is an automated AI governance and security gateway that sits between human users and AI assistants (such as OpenAI ChatGPT, Anthropic Claude Desktop, or custom agent runtimes). 

By establishing a **"Scan First, Respond Second"** paradigm through the [Model Context Protocol (MCP)](https://modelcontextprotocol.io), Guardian intercepts chat prompts, source code files, documents, and images *before* they are ingested by the language model.

Guardian prevents:
- **API Key & Secret Leakage:** AWS, GCP, GitHub, Slack tokens, private keys, `.env` variables.
- **Financial & PII Exposure:** Credit card numbers (Luhn checked), CVV/CVC, US Social Security Numbers (SSN), Indian Aadhaar cards.
- **Prompt Injection & Jailbreaks:** Heuristic adversarial pattern matching and trained ML stealth classifiers.
- **Document & Image Exploits:** Off-canvas text, tiny/zero-size fonts, white-on-white text in PDFs, and steganographic/OCR prompt injections in images.

---

## Network & Port Map

When running Guardian locally, the services operate on the following ports:

| Service | Port | Local URL | Description |
|---|---|---|---|
| **Frontend Dashboard** | `5173` | `http://localhost:5173` | React + Vite security console, live scan feed, manual scanner, and policy matrix. |
| **Dashboard REST API** | `8001` | `http://localhost:8001` | Starlette REST service reading/writing `audit/scans.db` and proxying detector operations. |
| **MCP Security Server** | `8000` | `http://localhost:8000/mcp` | FastMCP ASGI server exposing `scan_prompt`, `scan_document`, and `scan_image_url`. |
| **Ngrok Web Inspector** | `4040` | `http://localhost:4040` | Ngrok traffic inspector when tunneling local MCP or Frontend to the public internet. |
| **Documentation (Mintlify)** | `3000` | `http://localhost:3000` | Mintlify documentation server (also proxied through Vite at `http://localhost:5173/docs`). |

> **Frontend Proxy Routing:** The Vite dev server (`:5173`) automatically proxies `/api/*` to the REST backend (`:8001`) and `/docs/*` to the Mintlify server (`:3000`), so you can interact with the complete platform directly from `http://localhost:5173`.

---

## System Architecture

```
                                  +-----------------------------+
                                  |   AI Assistant / LLM Host   |
                                  |  (ChatGPT / Claude Desktop) |
                                  +--------------+--------------+
                                                 | MCP Request
                                                 v
+--------------------------+          +-------------------------+
|    Guardian Dashboard    |  /api    |   FastMCP Server (:8000)|
|    (React / Vite :5173)  +--------->|  (mcp_server/app.py)    |
+------------+-------------+          +------------+------------+
             |                                     |
             | Reads / Writes                      v
             v                        +-------------------------+
+--------------------------+          |   Core Scanner Engine   |
|   REST API Layer (:8001) |          |   (core/scanner.py)     |
+------------+-------------+          +------------+------------+
             |                                     |
             v                                     v
+--------------------------+          +-------------------------+
|   Audit DB (SQLite)      |<---------+   Detector Registry     |
|   audit/scans.db         | (Masked) |   - API Keys & Secrets  |
+--------------------------+          |   - Credit Cards & PII  |
                                      |   - Prompt Injections   |
                                      |   - Document & OCR ML   |
                                      +------------+------------+
                                                   |
                                                   v
                                      +-------------------------+
                                      |   Policy Engine         |
                                      |   (policy/policies.yaml)|
                                      |   ALLOW / WARN / BLOCK  |
                                      +-------------------------+
```

### Core Architecture Invariants
- **Zero-Secret Propagation:** Raw matched sensitive values are **never** persisted, logged, or returned past the detection phase. All logs, audit databases, API responses, and UI components exclusively expose masked strings (e.g. `AKIA****************`) and character span offsets.
- **Strict Layer Separation:** The core detection pipeline (`core/`, `detectors/`, `policy/`, `audit/`) is pure Python and strictly decoupled from the MCP transport and HTTP frameworks.

---

## Quickstart: Running Guardian

### Option A: One-Click Unified Runner (Recommended)

You can launch all components (REST API, MCP Server, Frontend Dev Server, and Ngrok Tunnel) concurrently using either the Python runner or Windows batch script:

#### Using PowerShell / Terminal:
```bash
# Run everything concurrently (API :8001, MCP :8000, Frontend :5173, Ngrok :8000)
python run.py

# Or skip ngrok if you only test locally
python run.py --no-ngrok

# Or route ngrok to the frontend UI instead of MCP
python run.py --ngrok-port 5173
```

#### Using Windows Command Prompt / Double-Click:
- Run `run.bat` to launch all services in dedicated command windows.
- Run `kill.bat` to cleanly shut down all services and free ports `8001`, `8000`, `5173`, and `4040`.

---

### Option B: Manual Service-by-Service Startup

If you prefer running services independently in separate terminal windows:

#### 1. Setup Python Virtual Environment
```bash
# From workspace root
python -m venv .venv
.\.venv\Scripts\activate      # On Windows (source .venv/bin/activate on Linux/macOS)

cd ai-security-gateway
pip install -e ".[dev]"
```

#### 2. Start the Backend REST API (Port 8001)
```bash
cd ai-security-gateway
# In PowerShell:
$env:AUTH_ENABLED="false"
$env:POLICY_FILE_PATH="policy/policies.yaml"
python -m uvicorn api.app:app --host 127.0.0.1 --port 8001 --reload
```

#### 3. Start the MCP Server (Port 8000)
```bash
cd ai-security-gateway
# In PowerShell:
$env:AUTH_ENABLED="false"
$env:POLICY_FILE_PATH="policy/policies.yaml"
python -m uvicorn mcp_server.app:app --host 0.0.0.0 --port 8000 --reload
```

#### 4. Start the Frontend Dashboard (Port 5173)
```bash
cd frontend
npm install
npm run dev
```
Open **[http://localhost:5173](http://localhost:5173)** in your browser.

---

## Connecting to AI Assistants

### 1. Connecting to ChatGPT (Web)
1. Start the MCP server and expose port 8000 using Ngrok:
   ```bash
   ngrok http 8000
   ```
2. Copy the public HTTPS forwarding URL (e.g., `https://xyz-your-tunnel.ngrok-free.app`).
3. In ChatGPT:
   - Navigate to **Settings → Connected Apps** (or **Plugins / Add MCP Connector**).
   - Server Name: `Guardian Security Gateway`
   - Server URL: `https://xyz-your-tunnel.ngrok-free.app/mcp`
4. Test in a new chat:
   > *"Scan this prompt for security leaks: 'My AWS key is AKIA1234567890EXAMPLE and SSN is 000-12-3456'"*
5. Check your terminal logs or Dashboard Scan Feed (`http://localhost:5173/feed`) to inspect the intercepted scan.

### 2. Connecting to Claude Desktop (macOS / Windows)
Add the local stdio runner to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "guardian": {
      "command": "e:\\Udbhaw_Work\\Udbhaw_Work\\Guardian\\.venv\\Scripts\\python.exe",
      "args": [
        "e:\\Udbhaw_Work\\Udbhaw_Work\\Guardian\\ai-security-gateway\\mcp_server\\run_stdio.py"
      ],
      "env": {
        "PYTHONPATH": "e:\\Udbhaw_Work\\Udbhaw_Work\\Guardian\\ai-security-gateway",
        "POLICY_FILE_PATH": "e:\\Udbhaw_Work\\Udbhaw_Work\\Guardian\\ai-security-gateway\\policy\\policies.yaml"
      }
    }
  }
}
```

---

## Policy Matrix & Decision Engine

Guardian evaluates all detected matches across configurable policies defined in [`ai-security-gateway/policy/policies.yaml`](ai-security-gateway/policy/policies.yaml):

| Detected Entity | Severity | Default Policy Action | Description |
|---|---|---|---|
| **API Keys & Secrets** | `CRITICAL` | `BLOCK` | Excludes AWS, GCP, GitHub, Slack tokens, private keys. |
| **Prompt Injection** | `CRITICAL` / `HIGH` | `BLOCK` | Blocks jailbreaks and prompt override attempts. |
| **Credit / Debit Cards** | `HIGH` | `WARN_CONFIRM` | Flags Luhn-valid card numbers for user confirmation. |
| **National IDs** | `HIGH` | `WARN_CONFIRM` | Flags US SSN, Indian Aadhaar numbers. |
| **CVV / CVC Codes** | `HIGH` | `WARN_CONFIRM` | Flags card verification codes. |
| **Clean Prompts / Files** | `LOW` | `ALLOW` | Passes cleanly through without friction. |

---

## Frontend Dashboard Screens

The dashboard (`http://localhost:5173`) surfaces real-time metrics and administration controls:

- **`/` Overview:** High-level KPIs (Total scans, blocked threats, active detectors, average latency).
- **`/feed` Scan Feed:** Real-time stream of scans with expandable rows displaying masked matches, severities, and timestamps.
- **`/scan` Manual Scanner:** Interactive test playground for scanning text prompts, uploaded documents (PDF, TXT, CSV), and images.
- **`/analytics` Analytics:** Visual distributions of decisions, top triggered detectors, and client types.
- **`/detectors` Catalog:** Directory of all loaded detector modules and their active configurations.
- **`/policy` Policy Matrix:** Interactive matrix visualizing `detector × severity` policy mappings.

---

## Testing & Quality Assurance

Run the test suite across core, detectors, policy engine, and MCP integrations:

```bash
cd ai-security-gateway
pytest

# Run detector-specific unit tests
pytest tests/test_detectors

# Run with verbose output
pytest -v

# Run linter
ruff check .
```

---

## Repository Structure

```
Guardian/
├── README.md                    # Project documentation & overview
├── run.py                       # Unified multi-service process runner (CLI)
├── run.bat                      # Windows launcher for API, MCP, Frontend, & Ngrok
├── kill.bat                     # Windows cleanup script to terminate running ports
├── requirements.txt             # Workspace Python dependencies
│
├── ai-security-gateway/         # Backend MCP Gateway & REST API
│   ├── api/                     # REST API layer (port 8001) for dashboard
│   ├── audit/                   # SQLite audit store (scans.db) & structured logger
│   ├── core/                    # Pipeline runner (scanner.py) & Pydantic models
│   ├── detectors/               # Auto-registered detector modules
│   │   ├── api_key.py           # AWS, GCP, GitHub, Slack token scanner
│   │   ├── credit_card.py       # Luhn-verified credit card detector
│   │   ├── national_id.py       # US SSN, Indian Aadhaar detector
│   │   ├── prompt_injection.py  # Prompt injection & jailbreak heuristic engine
│   │   └── document_utils/      # PDF & OCR-based image injection classifiers
│   ├── mcp_server/              # FastMCP server (port 8000) & tools
│   ├── models/                  # ML models & training scripts for stealth injection
│   ├── policy/                  # YAML policy engine (policies.yaml)
│   └── tests/                   # Pytest test suite
│
├── frontend/                    # Web Management Console (port 5173)
│   ├── src/
│   │   ├── pages/               # Overview, Feed, Scan, Analytics, Detectors, Policy
│   │   ├── components/          # Reusable UI components & charts
│   │   └── lib/                 # API client utilities & formatting helpers
│   ├── package.json
│   └── vite.config.js           # Dev server with /api and /docs reverse proxies
│
└── docs/                        # Mintlify documentation source
```

---

## License

This project is licensed under the MIT License.
