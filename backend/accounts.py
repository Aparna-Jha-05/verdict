"""Accounts, credits & billing (demo-grade).

Models the Credence platform's commercial layer:
  - a shared FREE-TRIAL credit pool usable across ALL domains,
  - per-domain PAID credit balances (buy only the domain you need),
  - ENTERPRISE orgs with a shared pooled balance and bulk member accounts.

This is a demo/hackathon implementation: passwords are salted+hashed with stdlib
PBKDF2 (no third-party crypto), and "purchases" are mocked — there is no real
payment processing. It is not production-hardened auth.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from store import DB_PATH

TRIAL_CREDITS = float(os.environ.get("TRIAL_CREDITS", "25"))
ENTERPRISE_POOL = float(os.environ.get("ENTERPRISE_POOL", "500"))
COST_PER_DOC = float(os.environ.get("COST_PER_DOC", "1"))


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_accounts() -> None:
    with _conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orgs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                pooled_credits REAL DEFAULT 0,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                name TEXT,
                password_hash TEXT,
                salt TEXT,
                account_type TEXT,     -- trial | paid | enterprise_admin | enterprise_member
                org_id INTEGER,
                trial_credits REAL DEFAULT 0,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entitlements (
                user_id INTEGER,
                domain TEXT,
                credits REAL DEFAULT 0,
                PRIMARY KEY (user_id, domain)
            )
            """
        )
        conn.commit()


# --------------------------- password hashing ---------------------------

def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()


def _verify(password: str, salt: str, expected: str) -> bool:
    return secrets.compare_digest(_hash(password, salt), expected)


# --------------------------- user CRUD ---------------------------

def get_user_by_email(email: str) -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE lower(email) = ?", (email.strip().lower(),)).fetchone()
    return dict(row) if row else None


def get_user(user_id: int) -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def create_user(email: str, password: str, name: str, account_type: str = "trial",
                org_id: Optional[int] = None, trial_credits: float = 0.0) -> dict:
    if get_user_by_email(email):
        raise ValueError("An account with that email already exists.")
    salt = secrets.token_hex(16)
    with _conn() as conn:
        cur = conn.execute(
            """INSERT INTO users (email, name, password_hash, salt, account_type, org_id, trial_credits, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (email.strip().lower(), name.strip() or email.split("@")[0], _hash(password, salt), salt,
             account_type, org_id, trial_credits, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        uid = int(cur.lastrowid)
    return get_user(uid)  # type: ignore


def authenticate(email: str, password: str) -> Optional[dict]:
    u = get_user_by_email(email)
    if not u or not _verify(password, u["salt"], u["password_hash"]):
        return None
    return u


# --------------------------- credits / billing ---------------------------

def _entitlements(user_id: int) -> dict[str, float]:
    with _conn() as conn:
        rows = conn.execute("SELECT domain, credits FROM entitlements WHERE user_id = ?", (user_id,)).fetchall()
    return {r["domain"]: float(r["credits"]) for r in rows}


def balances(user: dict) -> dict:
    ents = _entitlements(user["id"])
    org = None
    if user.get("org_id"):
        with _conn() as conn:
            row = conn.execute("SELECT * FROM orgs WHERE id = ?", (user["org_id"],)).fetchone()
        org = dict(row) if row else None
    return {
        "account_type": user["account_type"],
        "trial_credits": float(user.get("trial_credits") or 0),
        "domain_credits": ents,
        "org": {"name": org["name"], "pooled_credits": float(org["pooled_credits"])} if org else None,
        "cost_per_doc": COST_PER_DOC,
    }


def can_afford(user: dict, domain: str) -> bool:
    if user.get("org_id"):
        with _conn() as conn:
            row = conn.execute("SELECT pooled_credits FROM orgs WHERE id = ?", (user["org_id"],)).fetchone()
        return bool(row and float(row["pooled_credits"]) >= COST_PER_DOC)
    if _entitlements(user["id"]).get(domain, 0) >= COST_PER_DOC:
        return True
    return float(user.get("trial_credits") or 0) >= COST_PER_DOC


def charge(user: dict, domain: str) -> tuple[bool, str]:
    """Deduct one document's cost. Returns (ok, source)."""
    with _conn() as conn:
        # Enterprise: draw from the org pool.
        if user.get("org_id"):
            row = conn.execute("SELECT pooled_credits FROM orgs WHERE id = ?", (user["org_id"],)).fetchone()
            if row and float(row["pooled_credits"]) >= COST_PER_DOC:
                conn.execute("UPDATE orgs SET pooled_credits = pooled_credits - ? WHERE id = ?", (COST_PER_DOC, user["org_id"]))
                conn.commit()
                return True, "organization pool"
            return False, "organization pool exhausted"
        # Paid: prefer the specific domain's credits.
        row = conn.execute("SELECT credits FROM entitlements WHERE user_id = ? AND domain = ?", (user["id"], domain)).fetchone()
        if row and float(row["credits"]) >= COST_PER_DOC:
            conn.execute("UPDATE entitlements SET credits = credits - ? WHERE user_id = ? AND domain = ?", (COST_PER_DOC, user["id"], domain))
            conn.commit()
            return True, f"{domain} credits"
        # Trial: shared pool across all domains.
        u = conn.execute("SELECT trial_credits FROM users WHERE id = ?", (user["id"],)).fetchone()
        if u and float(u["trial_credits"]) >= COST_PER_DOC:
            conn.execute("UPDATE users SET trial_credits = trial_credits - ? WHERE id = ?", (COST_PER_DOC, user["id"]))
            conn.commit()
            return True, "free trial"
    return False, "insufficient credits"


def purchase(user: dict, domain: str, credits: float) -> dict:
    """Mock purchase — add per-domain credits and mark the account paid."""
    with _conn() as conn:
        conn.execute(
            """INSERT INTO entitlements (user_id, domain, credits) VALUES (?,?,?)
               ON CONFLICT(user_id, domain) DO UPDATE SET credits = credits + excluded.credits""",
            (user["id"], domain, credits),
        )
        if user["account_type"] == "trial":
            conn.execute("UPDATE users SET account_type = 'paid' WHERE id = ?", (user["id"],))
        conn.commit()
    return balances(get_user(user["id"]))  # type: ignore


# --------------------------- enterprise ---------------------------

def create_org(name: str, admin_email: str, admin_password: str, admin_name: str,
               pool: float = ENTERPRISE_POOL) -> dict:
    with _conn() as conn:
        cur = conn.execute("INSERT INTO orgs (name, pooled_credits, created_at) VALUES (?,?,?)",
                           (name.strip(), pool, datetime.now(timezone.utc).isoformat()))
        conn.commit()
        org_id = int(cur.lastrowid)
    admin = create_user(admin_email, admin_password, admin_name, account_type="enterprise_admin", org_id=org_id)
    return {"org_id": org_id, "admin": admin}


def add_members(org_id: int, members: list[dict]) -> list[dict]:
    """Bulk-provision member accounts under an org. members: [{email,name,password}]."""
    created = []
    for m in members:
        try:
            u = create_user(m["email"], m.get("password") or secrets.token_urlsafe(8),
                            m.get("name", ""), account_type="enterprise_member", org_id=org_id)
            created.append({"email": u["email"], "name": u["name"], "status": "created"})
        except ValueError as e:
            created.append({"email": m.get("email"), "status": f"skipped: {e}"})
    return created
