# Guardian — End-to-End Test Kit

Everything in this folder is for manually verifying that a scan triggered from
ChatGPT (via the MCP connector / ngrok tunnel) actually reaches the dashboard
frontend. Every prompt and file below was run directly through the real
detector/scanner code in this repo before being included here — the expected
decision and detector(s) are not guesses.

## How to use this

1. Start both backends and the frontend as usual (`uvicorn mcp_server.app:app --port 8000 --reload`,
   `uvicorn api.app:app --port 8001 --reload`, `npm run dev` in `frontend/`, `ngrok http 8000`).
2. In ChatGPT (with the connector pointed at your ngrok URL), paste one prompt at a time from
   [`text-prompts.md`](text-prompts.md), or upload one file at a time from this folder.
3. Watch the backend terminal for `db_insert_ok row_id=N` right after the scan completes —
   that confirms the write landed in `audit/scans.db`.
4. Open the dashboard (Overview / Feed / Analytics). New scans now appear automatically within
   ~15s (background polling was added for this) — no manual refresh needed. The Feed page also
   has a manual refresh button (↻) if you don't want to wait.
5. Compare what shows up against the "Expected" column below.

## Text prompts (`scan_prompt` tool) — paste directly into chat

See [`text-prompts.md`](text-prompts.md) for the exact strings to paste, one at a time, and the
decision/detector each one is validated to produce.

## Files (`scan_document` / `scan_image_url` tools) — upload in chat

| File | Type | Expected decision | Notes |
|---|---|---|---|
| `malicious_hidden_text.pdf` | PDF | **BLOCK** (critical) | Visible cover text + a real injection instruction hidden at 2pt font, white-on-white, at the bottom of the page. Trips `tiny_font` + `white_on_white` stealth flags AND the ML classifier. |
| `clean_report.pdf` | PDF | **ALLOW** | Plain visible business text only, no hidden layers. |
| `malicious_hidden_image.png` | Image | **BLOCK** (critical) | Visible "Employee Handbook" text plus a near-invisible light-grey injection line, calibrated to survive the OCR contrast-boost pipeline (`_preprocess_for_ocr`) but be very hard to spot with the naked eye. |
| `clean_image.png` | Image | **ALLOW** | Same visible text, no hidden line. |
| `project_with_root_env.zip` | ZIP | **BLOCK** (critical) | Contains a root-level `.env` with fake secrets. |
| `project_with_nested_env.zip` | ZIP | **BLOCK** (high) | Contains `backend/config/.env` — nested, so high not critical. |
| `project_clean.zip` | ZIP | **ALLOW** | `README.md`, `app.py`, `requirements.txt` only. |

**Important — how ChatGPT actually sends files to this MCP server:** per the tool docstrings in
`mcp_server/app.py`, ChatGPT does NOT send raw file bytes for PDFs/ZIPs. It's instructed to
extract the text (or, for ZIPs, list the filenames) itself and pass that as the `content` string.
Images are the exception — ChatGPT gives the tool a URL and `scan_image_url` downloads and OCRs
the actual bytes, so the hidden text in `malicious_hidden_image.png` only works if ChatGPT
truly can't "see" it, which is what it's calibrated for.

If ChatGPT ever seems to skip or shortcut a file (e.g. summarizes it without calling the tool,
or claims it can't process it), you can force the same code path by pasting the **fallback text**
in [`text-prompts.md`](text-prompts.md) under "Document fallback / ZIP listing" — that's the exact
string ChatGPT would have sent for that file.

## What this validated / fixed along the way

- Found and fixed a real bug: `scan_document`'s text-fallback path (used whenever a client sends
  extracted text instead of raw bytes — the normal ChatGPT path for PDFs) referenced an undefined
  variable (`ml_confidence` instead of `max_conf`) and crashed with `NameError` on every call. This
  would have silently broken every PDF/image scan sent as plain text. Fixed in
  `mcp_server/tools/scan_document_tool.py`.
- The ML prompt-injection classifier is tuned aggressively — several of the credential/secret
  prompts below also trip `prompt_injection` alongside their primary detector. That's real model
  behavior, not a mistake in the prompt; the table notes where it happens.
