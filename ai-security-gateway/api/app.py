"""
api/app.py
----------
Standalone Starlette ASGI app exposing a small JSON/REST + CORS surface for the
Guardian dashboard frontend. It reuses the existing MCP tool handlers and the
pure core/policy layers — no detection or policy logic lives here.

Run (dev):
    uvicorn api.app:app --host 0.0.0.0 --port 8001 --reload

The MCP server (mcp_server.app) is untouched and keeps running on its own port.

SECURITY INVARIANT: responses expose only masked values / detector type names —
never raw sensitive text — exactly as the underlying handlers already guarantee.
"""

from __future__ import annotations

import base64
import os
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

load_dotenv()

from core.scanner import scan_prompt as core_scan  # noqa: E402
from mcp_server.tools.scan_document_tool import handle_scan_document  # noqa: E402
from mcp_server.tools.scan_image_url_tool import handle_scan_image_url  # noqa: E402
from mcp_server.tools.scan_prompt_tool import _POLICY_META, _build_human_message  # noqa: E402

from api import db  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_POLICY_PATH = Path(os.getenv("POLICY_FILE_PATH", str(_ROOT / "policy" / "policies.yaml")))


# ── Detector catalog metadata (static reference for the Detectors screen) ─────
# Grounded in the actual registered detectors + document pipeline.
_DETECTOR_CATALOG: list[dict] = [
    {
        "name": "api_key", "icon": "🔑", "label": "Credentials / API Key", "category": "text",
        "description": "AWS/GCP/Azure/Stripe keys, GitHub tokens, and PEM private keys. "
                       "Shannon-entropy filtered to drop placeholders.",
        "severities": ["critical"],
        "match_types": ["aws_access_key", "aws_secret_key", "gcp_api_key",
                        "azure_subscription_key", "stripe_secret_key",
                        "stripe_publishable_key", "github_token", "private_key_pem"],
    },
    {
        "name": "credit_card", "icon": "💳", "label": "Payment Data / Credit Card", "category": "text",
        "description": "13–19 digit card numbers, validated with the Luhn checksum.",
        "severities": ["high"],
        "match_types": ["visa", "amex", "discover", "mastercard", "generic_card"],
    },
    {
        "name": "cvv", "icon": "🔢", "label": "Card CVV / CVC", "category": "text",
        "description": "CVV/CVC/CID codes appearing near a payment context label.",
        "severities": ["high"],
        "match_types": ["cvv_3_digit", "cvv_4_digit"],
    },
    {
        "name": "national_id", "icon": "🪪", "label": "National Identifier", "category": "text",
        "description": "US SSN (SSA rules), India Aadhaar (Verhoeff), and India PAN.",
        "severities": ["high"],
        "match_types": ["us_ssn", "in_aadhaar", "in_pan"],
    },
    {
        "name": "financial", "icon": "🏦", "label": "Financial Info", "category": "text",
        "description": "India GSTIN, IFSC codes, and bank account numbers.",
        "severities": ["high", "medium", "low"],
        "match_types": ["in_gstin", "in_ifsc", "bank_account"],
    },
    {
        "name": "env_file", "icon": "📄", "label": "Environment / Secrets File", "category": "text",
        "description": "Secret env-var assignments, .env path references, and bulk KEY=VALUE blocks.",
        "severities": ["critical", "high"],
        "match_types": ["secret_env_var", "env_file_path", "env_file_content"],
    },
    {
        "name": "prompt_injection", "icon": "🚨", "label": "Prompt Injection / Jailbreak", "category": "text",
        "description": "LLM jailbreak / injection attempts, detected by a trained ML model "
                       "(whole-text and line-by-line).",
        "severities": ["high"],
        "match_types": ["jailbreak"],
    },
    {
        "name": "pdf_prompt_injection", "icon": "📕", "label": "PDF Prompt Injection", "category": "document",
        "description": "Hidden injection instructions in PDFs — tiny fonts, white-on-white text, "
                       "off-page text — combined with ML classification.",
        "severities": ["critical", "high", "medium"],
        "match_types": ["ml_injection", "hidden_text", "suspicious_metadata"],
    },
    {
        "name": "image_prompt_injection", "icon": "🖼️", "label": "Image Prompt Injection", "category": "document",
        "description": "OCR + ML detection of prompt injection text hidden inside images.",
        "severities": ["critical", "high", "medium"],
        "match_types": ["ml_injection", "ocr_error"],
    },
    {
        "name": "zip_env_leak", "icon": "🗜️", "label": "ZIP Secrets Leak", "category": "document",
        "description": "ZIP archives containing .env or other secret files "
                       "(root-level = critical, nested = high).",
        "severities": ["critical", "high"],
        "match_types": ["env_file_in_zip"],
    },
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _json(data, status: int = 200) -> JSONResponse:
    return JSONResponse(data, status_code=status)


async def _read_json(request: Request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}


# ── Routes ───────────────────────────────────────────────────────────────────

async def health(request: Request) -> JSONResponse:
    return _json({"status": "ok", "service": "guardian-dashboard-api"})


async def scan_text(request: Request) -> JSONResponse:
    body = await _read_json(request)
    text = (body.get("text") or "").strip()
    if not text:
        return _json({"error": "Field 'text' is required and must be non-empty."}, status=400)

    client_name = body.get("client_name") or "dashboard"
    result = core_scan(text)  # ScanResult (masked matches only)
    matched_types = result.matched_detector_names

    response = {
        "decision": result.decision,
        "matched_types": matched_types,
        "reason": result.reason,
        "match_count": len(result.matches),
        "human_message": _build_human_message(
            result.decision, matched_types, result.reason, len(result.matches),
            matches=result.matches,
        ),
        # Masked match detail for the findings table — no raw values.
        "matches": [
            {
                "detector_name": m.detector_name,
                "severity": m.severity,
                "masked_value": m.masked_value,
                "match_type": m.match_type,
                "span": list(m.span),
            }
            for m in result.matches
        ],
    }

    try:
        db.insert_scan(result, text_length=len(text), client_name=client_name)
    except Exception:  # noqa: BLE001 — feed persistence is best-effort, never blocks a scan
        pass

    return _json(response)


async def scan_document(request: Request) -> JSONResponse:
    body = await _read_json(request)
    content_b64 = body.get("content_base64")
    filename = body.get("filename")
    if not content_b64 or not filename:
        return _json({"error": "Fields 'content_base64' and 'filename' are required."}, status=400)

    resp = await handle_scan_document(content_b64, filename)
    try:
        raw_len = len(base64.b64decode(content_b64, validate=True))
    except Exception:
        raw_len = len(content_b64)
    try:
        db.insert_document_scan(resp, text_length=raw_len,
                                client_name=body.get("client_name") or "dashboard")
    except Exception:  # noqa: BLE001
        pass
    return _json(resp)


async def scan_image(request: Request) -> JSONResponse:
    body = await _read_json(request)
    image_url = body.get("image_url")
    if not image_url:
        return _json({"error": "Field 'image_url' is required."}, status=400)
    filename = body.get("filename") or "uploaded_image.png"

    resp = await handle_scan_image_url(image_url, filename)
    try:
        db.insert_document_scan(resp, text_length=0,
                                client_name=body.get("client_name") or "dashboard")
    except Exception:  # noqa: BLE001
        pass
    return _json(resp)


async def list_scans(request: Request) -> JSONResponse:
    qp = request.query_params

    def _int(name: str, default: int) -> int:
        try:
            return int(qp.get(name, default))
        except (TypeError, ValueError):
            return default

    data = db.query_scans(
        limit=min(_int("limit", 50), 500),
        offset=max(_int("offset", 0), 0),
        decision=qp.get("decision") or None,
        severity=qp.get("severity") or None,
        client=qp.get("client") or None,
        search=qp.get("search") or None,
    )
    return _json(data)


async def stats(request: Request) -> JSONResponse:
    return _json(db.aggregate_stats())


async def detectors(request: Request) -> JSONResponse:
    # Include the display metadata the tool layer already keeps, for parity.
    meta = {name: {"icon": icon, "label": label} for name, (icon, label) in _POLICY_META.items()}
    return _json({"detectors": _DETECTOR_CATALOG, "policy_meta": meta})


async def policy(request: Request) -> JSONResponse:
    if not _POLICY_PATH.exists():
        return _json({"error": f"Policy file not found at {_POLICY_PATH}"}, status=404)
    with open(_POLICY_PATH, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    return _json({
        "aggregation_rule": cfg.get("aggregation_rule"),
        "detectors": cfg.get("detectors", {}),
        "defaults": cfg.get("defaults", {}),
        "severities": ["critical", "high", "medium", "low"],
        "actions": ["ALLOW", "WARN_CONFIRM", "BLOCK"],
    })


# ── App ──────────────────────────────────────────────────────────────────────

_CORS_ORIGINS = [
    o.strip() for o in os.getenv(
        "DASHBOARD_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",") if o.strip()
]

routes = [
    Route("/api/health", health, methods=["GET"]),
    Route("/api/scan", scan_text, methods=["POST"]),
    Route("/api/scan/document", scan_document, methods=["POST"]),
    Route("/api/scan/image", scan_image, methods=["POST"]),
    Route("/api/scans", list_scans, methods=["GET"]),
    Route("/api/stats", stats, methods=["GET"]),
    Route("/api/detectors", detectors, methods=["GET"]),
    Route("/api/policy", policy, methods=["GET"]),
]

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=_CORS_ORIGINS,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    ),
]


@asynccontextmanager
async def _lifespan(app: Starlette):
    db.init_db()
    yield


app = Starlette(routes=routes, middleware=middleware, lifespan=_lifespan)
