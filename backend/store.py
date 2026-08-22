"""SQLite persistence: the approval ledger + vendor bank-account history.

The ledger is the source of truth for two fraud checks:
  - bank-detail-change (vendor -> last approved bank account)
  - exact/near duplicate (invoice numbers already approved)

Chroma handles the semantic-dedup vector side (see dedup.py); this module owns
the relational side only. No LLM here.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

DB_PATH = os.environ.get("INVOICES_DB", os.path.join(os.path.dirname(__file__), "invoices.db"))


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT,
                vendor_name TEXT,
                vendor_bank_account TEXT,
                invoice_date TEXT,
                currency TEXT,
                subtotal REAL,
                tax REAL,
                total REAL,
                line_items_json TEXT,
                approved_at TEXT,
                mock_action TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ledger_vendor ON ledger(vendor_name)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ledger_invnum ON ledger(invoice_number)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT,
                type TEXT,            -- processed | approved | flagged | escalated
                invoice_number TEXT,
                vendor_name TEXT,
                summary TEXT,
                severity TEXT,        -- high | medium | low | info | ok
                meta_json TEXT
            )
            """
        )
        conn.commit()


def _norm_vendor(name: str) -> str:
    return (name or "").strip().lower()


def last_bank_account_for_vendor(vendor_name: str) -> Optional[str]:
    """Most recent non-empty bank account previously approved for this vendor."""
    with _conn() as conn:
        row = conn.execute(
            """
            SELECT vendor_bank_account FROM ledger
            WHERE lower(trim(vendor_name)) = ?
              AND trim(coalesce(vendor_bank_account,'')) <> ''
            ORDER BY id DESC LIMIT 1
            """,
            (_norm_vendor(vendor_name),),
        ).fetchone()
    return row["vendor_bank_account"] if row else None


def invoice_number_exists(invoice_number: str, vendor_name: str = "") -> Optional[dict]:
    """Return the prior ledger row if this exact invoice number was approved."""
    inv = (invoice_number or "").strip()
    if not inv:
        return None
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM ledger WHERE trim(invoice_number) = ? ORDER BY id DESC LIMIT 1",
            (inv,),
        ).fetchone()
    return dict(row) if row else None


def add_invoice(record: dict) -> int:
    """Insert an approved invoice. `record` is a flat dict of ledger columns."""
    with _conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO ledger (
                invoice_number, vendor_name, vendor_bank_account, invoice_date,
                currency, subtotal, tax, total, line_items_json, approved_at, mock_action
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                record.get("invoice_number", ""),
                record.get("vendor_name", ""),
                record.get("vendor_bank_account", ""),
                record.get("invoice_date", ""),
                record.get("currency", ""),
                record.get("subtotal"),
                record.get("tax"),
                record.get("total"),
                json.dumps(record.get("line_items", [])),
                record.get("approved_at", datetime.now(timezone.utc).isoformat()),
                record.get("mock_action", ""),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def all_invoices() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM ledger ORDER BY id DESC").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["line_items"] = json.loads(d.pop("line_items_json") or "[]")
        except (json.JSONDecodeError, TypeError):
            d["line_items"] = []
        out.append(d)
    return out


def log_activity(
    type: str,
    invoice_number: str = "",
    vendor_name: str = "",
    summary: str = "",
    severity: str = "info",
    meta: dict | None = None,
) -> None:
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO activity (ts, type, invoice_number, vendor_name, summary, severity, meta_json)
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                type,
                invoice_number,
                vendor_name,
                summary,
                severity,
                json.dumps(meta or {}),
            ),
        )
        conn.commit()


def recent_activity(limit: int = 100) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM activity ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["meta"] = json.loads(d.pop("meta_json") or "{}")
        except (json.JSONDecodeError, TypeError):
            d["meta"] = {}
        out.append(d)
    return out


def stats() -> dict:
    """Aggregate counters for the dashboard KPI row."""
    with _conn() as conn:
        def count(type: str) -> int:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM activity WHERE type = ?", (type,)
            ).fetchone()
            return int(row["c"]) if row else 0

        processed = count("processed")
        flagged = count("flagged")
        escalated = count("escalated")
        # Approved reflects the ledger (includes seeded priors) so the KPI tile
        # agrees with the Ledger view.
        approved_row = conn.execute("SELECT COUNT(*) AS c FROM ledger").fetchone()
        approved = int(approved_row["c"]) if approved_row else 0

        conf_rows = conn.execute(
            """
            SELECT json_extract(meta_json,'$.confidence') AS conf, COUNT(*) AS c
            FROM activity WHERE type='processed' GROUP BY conf
            """
        ).fetchall()
    conf_dist = {"high": 0, "medium": 0, "low": 0}
    for r in conf_rows:
        key = (r["conf"] or "").lower()
        if key in conf_dist:
            conf_dist[key] += int(r["c"])
    return {
        "processed": processed,
        "approved": approved,
        "flagged": flagged,
        "escalated": escalated,
        "escalation_rate": round(escalated / processed, 3) if processed else 0.0,
        "confidence_distribution": conf_dist,
    }


def approved_invoices_for_dedup() -> list[dict]:
    """Lightweight rows the dedup layer uses to rebuild/query signatures."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, invoice_number, vendor_name, invoice_date, total, line_items_json FROM ledger"
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["line_items"] = json.loads(d.pop("line_items_json") or "[]")
        except (json.JSONDecodeError, TypeError):
            d["line_items"] = []
        out.append(d)
    return out
