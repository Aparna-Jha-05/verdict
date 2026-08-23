"""SQLite persistence: a generic approval ledger across all domains, plus
party→account history, exact-identity lookups, an activity trail, and KPI stats.
No LLM. Records store the full extracted field set as JSON for the Ledger view.
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
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT,
                ref TEXT,
                party TEXT,
                account TEXT,
                identity TEXT,
                amount REAL,
                doc_date TEXT,
                fields_json TEXT,
                approved_at TEXT,
                mock_action TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rec_domain_party ON records(domain, party)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rec_identity ON records(domain, identity)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT, type TEXT, domain TEXT, ref TEXT, party TEXT,
                summary TEXT, severity TEXT, meta_json TEXT
            )
            """
        )
        conn.commit()


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def last_account_for_party(domain: str, party: str) -> Optional[str]:
    with _conn() as conn:
        row = conn.execute(
            """
            SELECT account FROM records
            WHERE domain = ? AND lower(trim(party)) = ? AND trim(coalesce(account,'')) <> ''
            ORDER BY id DESC LIMIT 1
            """,
            (domain, _norm(party)),
        ).fetchone()
    return row["account"] if row else None


def identity_exists(domain: str, identity: str) -> Optional[dict]:
    ident = (identity or "").strip()
    if not ident:
        return None
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM records WHERE domain = ? AND trim(identity) = ? ORDER BY id DESC LIMIT 1",
            (domain, ident),
        ).fetchone()
    return dict(row) if row else None


def amounts(domain: str, party: str = "") -> list[float]:
    """Historical approved amounts for a domain (optionally one party). Feeds
    the anomaly detector."""
    with _conn() as conn:
        if party:
            rows = conn.execute(
                "SELECT amount FROM records WHERE domain=? AND lower(trim(party))=? AND amount IS NOT NULL",
                (domain, _norm(party)),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT amount FROM records WHERE domain=? AND amount IS NOT NULL", (domain,)
            ).fetchall()
    return [float(r["amount"]) for r in rows]


def add_record(record: dict) -> int:
    with _conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO records (domain, ref, party, account, identity, amount, doc_date,
                                 fields_json, approved_at, mock_action)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                record.get("domain", "generic"),
                record.get("ref", ""),
                record.get("party", ""),
                record.get("account", ""),
                record.get("identity", ""),
                record.get("amount"),
                record.get("doc_date", ""),
                json.dumps(record.get("fields", {})),
                record.get("approved_at", datetime.now(timezone.utc).isoformat()),
                record.get("mock_action", ""),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def all_records() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM records ORDER BY id DESC").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        try:
            d["fields"] = json.loads(d.pop("fields_json") or "{}")
        except (json.JSONDecodeError, TypeError):
            d["fields"] = {}
        out.append(d)
    return out


# --------------------------- activity + stats ---------------------------

def log_activity(type: str, domain: str = "", ref: str = "", party: str = "",
                 summary: str = "", severity: str = "info", meta: dict | None = None) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO activity (ts, type, domain, ref, party, summary, severity, meta_json) VALUES (?,?,?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), type, domain, ref, party, summary, severity, json.dumps(meta or {})),
        )
        conn.commit()


def recent_activity(limit: int = 100) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM activity ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
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
    with _conn() as conn:
        def count(type: str) -> int:
            row = conn.execute("SELECT COUNT(*) AS c FROM activity WHERE type = ?", (type,)).fetchone()
            return int(row["c"]) if row else 0

        processed = count("processed")
        flagged = count("flagged")
        escalated = count("escalated")
        approved_row = conn.execute("SELECT COUNT(*) AS c FROM records").fetchone()
        approved = int(approved_row["c"]) if approved_row else 0
        dom_rows = conn.execute(
            "SELECT domain, COUNT(*) AS c FROM activity WHERE type='processed' GROUP BY domain"
        ).fetchall()
        conf_rows = conn.execute(
            "SELECT json_extract(meta_json,'$.confidence') AS conf, COUNT(*) AS c FROM activity WHERE type='processed' GROUP BY conf"
        ).fetchall()
    conf_dist = {"high": 0, "medium": 0, "low": 0}
    for r in conf_rows:
        key = (r["conf"] or "").lower()
        if key in conf_dist:
            conf_dist[key] += int(r["c"])
    domains = {r["domain"] or "generic": int(r["c"]) for r in dom_rows}
    return {
        "processed": processed,
        "approved": approved,
        "flagged": flagged,
        "escalated": escalated,
        "escalation_rate": round(escalated / processed, 3) if processed else 0.0,
        "confidence_distribution": conf_dist,
        "by_domain": domains,
    }
