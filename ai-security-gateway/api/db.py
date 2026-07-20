"""
api/db.py
---------
Pure SQLite helper for the dashboard REST layer, backed by audit/scans.db
(table `scan_events`). This is the ONLY place the dashboard reads/writes that
table.

SECURITY INVARIANT: only masked values are ever persisted here — the same
`masked_value`/span data the audit logger already emits. Raw sensitive values
never touch this module.

No MCP / Starlette / transport imports here — this module is pure Python and
depends only on core.models for typing.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.models import ScanResult

# ── DB location ──────────────────────────────────────────────────────────────
# api/ lives directly under the ai-security-gateway root, so parent.parent is
# that root and audit/scans.db sits beside it.
_DB_PATH = Path(__file__).resolve().parent.parent / "audit" / "scans.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS scan_events (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id        TEXT,
    scanned_at        TEXT NOT NULL,
    decision          TEXT NOT NULL CHECK (decision IN ('ALLOW','WARN_CONFIRM','BLOCK')),
    reason            TEXT NOT NULL,
    highest_severity  TEXT,
    match_count       INTEGER NOT NULL DEFAULT 0,
    matched_detectors TEXT NOT NULL DEFAULT '[]',
    matches_json      TEXT NOT NULL DEFAULT '[]',
    text_length       INTEGER NOT NULL DEFAULT 0,
    client_name       TEXT
);
CREATE INDEX IF NOT EXISTS idx_scan_events_scanned_at ON scan_events (scanned_at DESC);
CREATE INDEX IF NOT EXISTS idx_scan_events_decision ON scan_events (decision);
CREATE INDEX IF NOT EXISTS idx_scan_events_client_name ON scan_events (client_name);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db() -> None:
    """Ensure the DB file and schema exist (idempotent). Called once at startup."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect()
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


# ── Writes ───────────────────────────────────────────────────────────────────

def insert_scan(result: ScanResult, text_length: int, client_name: str = "dashboard") -> int:
    """Persist a text ScanResult (masked matches only). Returns the new row id."""
    safe_matches = [
        {
            "detector": m.detector_name,
            "match_type": m.match_type,
            "severity": m.severity,
            "masked_value": m.masked_value,
            "span": list(m.span),
        }
        for m in result.matches
    ]
    highest = None
    if result.matches:
        from core.models import SEVERITY_RANK

        highest = max((m.severity for m in result.matches), key=lambda s: SEVERITY_RANK[s])

    return _insert_row(
        scanned_at=result.scanned_at.isoformat(),
        decision=result.decision,
        reason=result.reason,
        highest_severity=highest,
        match_count=len(result.matches),
        matched_detectors=result.matched_detector_names,
        matches_json=safe_matches,
        text_length=text_length,
        client_name=client_name,
    )


def insert_document_scan(
    resp: dict[str, Any],
    text_length: int,
    client_name: str = "dashboard",
) -> int:
    """Persist a document/image scan (the flat dict returned by the doc handlers)."""
    matched = resp.get("matched_types", []) or []
    severity = resp.get("severity") or None
    confidence = resp.get("confidence")
    # Document handlers don't expose per-match objects; store the stealth flags as context.
    matches_json = [
        {
            "detector": (matched[0] if matched else "document"),
            "match_type": ", ".join(resp.get("stealth_flags", []) or []),
            "severity": severity or "",
            "masked_value": "",
            "span": [0, text_length],
            "confidence": confidence,
        }
    ] if resp.get("decision") != "ALLOW" else []

    return _insert_row(
        scanned_at=datetime.now(tz=timezone.utc).isoformat(),
        decision=resp.get("decision", "ALLOW"),
        reason=resp.get("reason", ""),
        highest_severity=severity,
        match_count=int(resp.get("match_count", 0) or 0),
        matched_detectors=matched,
        matches_json=matches_json,
        text_length=text_length,
        client_name=client_name,
    )


def _insert_row(
    *,
    scanned_at: str,
    decision: str,
    reason: str,
    highest_severity: str | None,
    match_count: int,
    matched_detectors: list[str],
    matches_json: list[dict[str, Any]],
    text_length: int,
    client_name: str,
) -> int:
    conn = _connect()
    try:
        cur = conn.execute(
            """
            INSERT INTO scan_events
                (request_id, scanned_at, decision, reason, highest_severity,
                 match_count, matched_detectors, matches_json, text_length, client_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                None,
                scanned_at,
                decision,
                reason,
                highest_severity,
                match_count,
                json.dumps(matched_detectors),
                json.dumps(matches_json),
                text_length,
                client_name,
            ),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


# ── Reads ────────────────────────────────────────────────────────────────────

def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    for key in ("matched_detectors", "matches_json"):
        try:
            d[key] = json.loads(d.get(key) or "[]")
        except (json.JSONDecodeError, TypeError):
            d[key] = []
    return d


def query_scans(
    *,
    limit: int = 50,
    offset: int = 0,
    decision: str | None = None,
    severity: str | None = None,
    client: str | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    """Paginated, filtered feed of scan_events (newest first)."""
    where: list[str] = []
    params: list[Any] = []
    if decision:
        where.append("decision = ?")
        params.append(decision)
    if severity:
        where.append("highest_severity = ?")
        params.append(severity)
    if client:
        where.append("client_name = ?")
        params.append(client)
    if search:
        where.append("(reason LIKE ? OR matched_detectors LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    conn = _connect()
    try:
        total = conn.execute(
            f"SELECT COUNT(*) FROM scan_events {where_sql}", params
        ).fetchone()[0]
        rows = conn.execute(
            f"""
            SELECT * FROM scan_events
            {where_sql}
            ORDER BY scanned_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()
    finally:
        conn.close()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_row_to_dict(r) for r in rows],
    }


def aggregate_stats() -> dict[str, Any]:
    """Aggregate metrics for the Overview + Analytics screens."""
    conn = _connect()
    try:
        total = conn.execute("SELECT COUNT(*) FROM scan_events").fetchone()[0]

        decision_counts = {
            r["decision"]: r["n"]
            for r in conn.execute(
                "SELECT decision, COUNT(*) AS n FROM scan_events GROUP BY decision"
            ).fetchall()
        }

        severity_counts = {
            (r["highest_severity"] or "none"): r["n"]
            for r in conn.execute(
                "SELECT highest_severity, COUNT(*) AS n FROM scan_events GROUP BY highest_severity"
            ).fetchall()
        }

        client_counts = {
            (r["client_name"] or "unknown"): r["n"]
            for r in conn.execute(
                "SELECT client_name, COUNT(*) AS n FROM scan_events GROUP BY client_name"
            ).fetchall()
        }

        # Per-detector frequency — matched_detectors is a JSON array per row.
        detector_counts: dict[str, int] = {}
        for r in conn.execute("SELECT matched_detectors FROM scan_events"):
            try:
                for name in json.loads(r["matched_detectors"] or "[]"):
                    detector_counts[name] = detector_counts.get(name, 0) + 1
            except (json.JSONDecodeError, TypeError):
                continue

        # Decisions-over-time, bucketed by day.
        timeseries_rows = conn.execute(
            """
            SELECT substr(scanned_at, 1, 10) AS day, decision, COUNT(*) AS n
            FROM scan_events
            GROUP BY day, decision
            ORDER BY day ASC
            """
        ).fetchall()
    finally:
        conn.close()

    timeseries: dict[str, dict[str, Any]] = {}
    for r in timeseries_rows:
        day = r["day"]
        bucket = timeseries.setdefault(
            day, {"date": day, "ALLOW": 0, "WARN_CONFIRM": 0, "BLOCK": 0, "total": 0}
        )
        bucket[r["decision"]] = r["n"]
        bucket["total"] += r["n"]

    blocked = decision_counts.get("BLOCK", 0)
    warned = decision_counts.get("WARN_CONFIRM", 0)
    threats = blocked + warned

    return {
        "total_scans": total,
        "decisions": {
            "ALLOW": decision_counts.get("ALLOW", 0),
            "WARN_CONFIRM": warned,
            "BLOCK": blocked,
        },
        "threats_detected": threats,
        "block_rate": round(blocked / total, 4) if total else 0.0,
        "severity": severity_counts,
        "clients": client_counts,
        "detectors": detector_counts,
        "top_detector": (
            max(detector_counts, key=detector_counts.get) if detector_counts else None
        ),
        "timeseries": sorted(timeseries.values(), key=lambda b: b["date"]),
    }
