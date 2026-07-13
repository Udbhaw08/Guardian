# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository overview

This repo contains **Guardian**, an AI-agent governance project, currently in Phase 1. Two things live here:

- [`ai-security-gateway/`](ai-security-gateway/) — the only code that currently exists: an MCP server ("AI Security Gateway" / early "Guardian Connector") that scans prompts and documents for sensitive data and prompt injection before they reach an AI assistant (Claude/ChatGPT).
- [`PRD/`](PRD/) and [`G-TAP_Project_Blueprint.md`](G-TAP_Project_Blueprint.md) — planning docs for the full Guardian product (Core governance engine, Connector, Console dashboard, policy packs). Read [`PRD/00-MASTER-PRD.md`](PRD/00-MASTER-PRD.md) before making architectural decisions — it defines a hard split between "Phase 1 web/apps risk" (data exfiltration/DLP — what `ai-security-gateway` implements) and "Phase 2 codebase/IDE risk" (destructive shell/infra commands — not built yet, see `05-M5`). Do not blend these two policy models.

All actual code work happens inside `ai-security-gateway/`.

## Commands

You can run all components (REST API, MCP server, Frontend, and Ngrok) concurrently using the unified runner script or Windows batch file from the workspace root:

```bash
# Run everything concurrently (MCP on 8000, API on 8001, Frontend on 5173, Ngrok on 8000)
python run.py       # Or double-click / run: run.bat

# Expose frontend via ngrok instead of MCP
python run.py --ngrok-port 5173    # Or: run.bat --ngrok-port 5173

# Skip running ngrok
python run.py --no-ngrok           # Or: run.bat --no-ngrok
```

Alternatively, you can run components individually (assuming `cd ai-security-gateway` first, with `../.venv` active):

```bash
# Install (editable, with dev deps)
pip install -e ".[dev]"

# Run all tests
pytest

# Run one test file / one test
pytest tests/test_detectors/test_credit_card.py
pytest tests/test_detectors/test_credit_card.py::test_visa_detected -v

# Run tests by directory (mirrors architecture: core, detectors, policy_engine, mcp_server)
pytest tests/test_core
pytest tests/test_detectors
pytest tests/test_policy_engine
pytest tests/test_mcp_server

# Lint (config in pyproject.toml, line-length 100, py311)
ruff check .

# Run the MCP server over HTTP (Streamable HTTP transport at /mcp), no auth, for local testing
$env:AUTH_ENABLED="false"      # PowerShell
uvicorn mcp_server.app:app --host 0.0.0.0 --port 8000 --reload

# Run the MCP server over stdio (used by Claude Desktop config) — forces AUTH_ENABLED=false itself
python mcp_server/run_stdio.py

# Expose locally for ChatGPT/Claude Web custom connector testing
ngrok http 8000
```

Deployment target is Render (`ai-security-gateway/render.yaml`); production must run with `AUTH_ENABLED=true` (real OAuth) — never deploy with auth disabled.

## Architecture

The gateway is a **layered pipeline**, and the layering is enforced by comment-documented constraints in the source, not just convention — respect them when editing:

```
MCP client (Claude/ChatGPT)
  -> mcp_server/app.py            (Starlette/FastMCP ASGI app, tool registration, auth)
  -> mcp_server/tools/*.py        (translates MCP tool args <-> core dicts; no detection logic)
  -> core/scanner.py              (scan_prompt: the single protocol-agnostic entrypoint)
  -> detectors/registry.py        (auto-discovers and runs every registered detector)
  -> policy/engine.py             (aggregates DetectorMatch list -> one PolicyDecision via policy/policies.yaml)
  -> audit/logger.py              (structured JSON audit log, masked values only, to stdout)
  -> ScanResult returned up the chain
```

Layering rules (see the module docstrings for the canonical statement — `core/`, `detectors/`, `policy/`, `audit/` all repeat this):

- `core/`, `detectors/`, `policy/`, `audit/` must **never** import anything from `mcp_server/`, `mcp`, `starlette`, `uvicorn`, or any auth/transport type. These layers are pure Python: they must work identically whether called from an MCP tool, a test, or a future non-MCP integration.
- `core/models.py` (Pydantic models: `DetectorMatch`, `PolicyDecision`, `ScanResult`, `Severity`, `Decision`) is the shared data contract across every layer.
- Raw sensitive values are never stored, logged, or returned anywhere past a detector — only `masked_value` (see `DetectorMatch`) and span offsets propagate outward. This invariant is intentional and load-bearing; don't add a code path that surfaces raw matched text.

**Adding a new detector** requires zero edits to `scanner.py` or `registry.py`:
1. Create `detectors/my_detector.py`, subclass `BaseDetector` (`detectors/base.py`), implement `detect(text) -> list[DetectorMatch]`.
2. Decorate the class with `@register("my_detector")` from `detectors/registry.py`.
3. Add an entry for `my_detector` to `policy/policies.yaml` (severity -> action mapping); unlisted detectors/severities fall back to the `defaults` block.

`detectors/registry.py` auto-imports every module in `detectors/` (except `base.py`/`registry.py` themselves) on first use via `load_all_detectors()` — that's how new detector files get picked up with no explicit import anywhere.

Two tool surfaces exist today (`mcp_server/app.py`):
- `scan_prompt(text)` — text-only scanning, routes to `core/scanner.py`.
- `scan_document(file_b64, filename)` — PDF/image scanning for hidden prompt injection (tiny fonts, white-on-white text, off-page text, OCR-extractable-but-invisible text), routed through `mcp_server/tools/scan_document_tool.py` to `detectors/document_utils/pdf_prompt_injection.py` or `image_prompt_injection.py`. This path uses a trained ML model (`models/injection_model.pkl`, built by `models/train.py`) alongside rule-based `stealth_rules.py`/`classifier.py`, and returns a `DocumentScanResult` (different shape from `ScanResult` — do not conflate the two).

Policy decisions (`policy/policies.yaml`, validated at load by `policy/schema.py`) use one aggregation rule today: `highest_severity` — across all matches in a scan, the single match with the highest-ranked action (`BLOCK` > `WARN_CONFIRM` > `ALLOW`) wins for the whole scan. The policy file path is overridable via `POLICY_FILE_PATH` env var and is cached for the process lifetime (`lru_cache`) — changing it requires a restart, by design.

Auth (`mcp_server/auth.py`) is a pure OAuth 2.1 **resource-server** verifier: it validates Bearer JWTs against an external IdP's JWKS (`AUTH_JWKS_URI`, `AUTH_ISSUER_URL`, `AUTH_AUDIENCE`, optional `MCP_REQUIRED_SCOPE`), never issues tokens itself. Toggle with `AUTH_ENABLED` env var; `run_stdio.py` (used for the Claude Desktop local integration) forces it off unconditionally since stdio has no HTTP-level auth story.

Tests mirror the architecture 1:1 under `tests/` (`test_core/`, `test_detectors/`, `test_policy_engine/`, `test_mcp_server/`). `tests/conftest.py` resets `DETECTOR_REGISTRY` before every test to prevent cross-test pollution — keep this in mind if a detector test seems to see stale/extra detectors.

<!-- code-review-graph MCP tools -->
## MCP Tools: code-review-graph

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
code-review-graph MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
you structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes` or `query_graph` instead of Grep
- **Understanding impact**: `get_impact_radius` instead of manually tracing imports
- **Code review**: `detect_changes` + `get_review_context` instead of reading entire files
- **Finding relationships**: `query_graph` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview` + `list_communities`

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool | Use when |
|------|----------|
| `detect_changes` | Reviewing code changes — gives risk-scored analysis |
| `get_review_context` | Need source snippets for review — token-efficient |
| `get_impact_radius` | Understanding blast radius of a change |
| `get_affected_flows` | Finding which execution paths are impacted |
| `query_graph` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes` | Finding functions/classes by name or keyword |
| `get_architecture_overview` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes` for code review.
3. Use `get_affected_flows` to understand impact.
4. Use `query_graph` pattern="tests_for" to check coverage.
