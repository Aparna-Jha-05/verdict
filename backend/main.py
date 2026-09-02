"""FastAPI app: multi-domain document intelligence.

Routes are domain-agnostic. /process resolves a DomainPack (explicit or
auto-detected), runs ingest → extract → route(escalate) → validate → integrity
→ optional similarity, and logs the activity trail. /approve writes a generic
ledger record and indexes it for future duplicate detection.
"""

from __future__ import annotations

import csv
import io
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import accounts
import assistant
import auth
import dedup
import store
from extract import classify
from ingest import ingest
from match import three_way_match
from packs import all_domains, get_pack
from packs.base import identity_signature
from packs.library import ALL_PACKS
from route import process as route_process
from schema import Extraction, ProcessResponse

app = FastAPI(title="Verdict — Document Intelligence", version="3.0.0")

_origins_env = os.environ.get("CORS_ORIGINS", "*")
_origins = ["*"] if _origins_env.strip() == "*" else [o.strip() for o in _origins_env.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware, allow_origins=_origins, allow_credentials=False,
    allow_methods=["*"], allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    store.init_db()
    accounts.init_accounts()
    if os.environ.get("AUTO_SEED", "1") != "0":
        import seed
        if seed.seed_if_empty():
            print("Ledger was empty — seeded demo prior-records.")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "verdict-document-intelligence"}


@app.get("/domains")
def domains_endpoint() -> dict:
    return {"domains": [d.model_dump() for d in all_domains()]}


@app.get("/industries")
def industries_endpoint() -> dict:
    from packs.registry import all_industries
    return {"industries": all_industries()}


# ------------------------- accounts / billing -------------------------

def _public(user: dict) -> dict:
    return {"id": user["id"], "email": user["email"], "name": user["name"],
            "account_type": user["account_type"], "org_id": user.get("org_id")}


def _auth_payload(user: dict) -> dict:
    return {"token": auth.make_token(user["id"]), "user": _public(user),
            "billing": accounts.balances(user)}


class SignupRequest(BaseModel):
    email: str
    password: str
    name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


@app.post("/auth/signup")
def signup(req: SignupRequest) -> dict:
    """Create an account and start a free trial (credits usable on any domain)."""
    try:
        user = accounts.create_user(req.email, req.password, req.name,
                                    account_type="trial", trial_credits=accounts.TRIAL_CREDITS)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _auth_payload(user)


@app.post("/auth/guest")
def guest() -> dict:
    """One-click instant free trial — provisions a throwaway trial account."""
    import secrets as _s
    email = f"guest-{_s.token_hex(4)}@verdict.trial"
    user = accounts.create_user(email, _s.token_urlsafe(12), "Guest (trial)",
                                account_type="trial", trial_credits=accounts.TRIAL_CREDITS)
    return _auth_payload(user)


@app.post("/auth/login")
def login(req: LoginRequest) -> dict:
    user = accounts.authenticate(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return _auth_payload(user)


@app.get("/auth/me")
def me(user: dict = Depends(auth.current_user)) -> dict:
    return {"user": _public(user), "billing": accounts.balances(user)}


@app.get("/billing")
def billing(user: dict = Depends(auth.current_user)) -> dict:
    return accounts.balances(user)


class PurchaseRequest(BaseModel):
    domain: str
    credits: float = 100


@app.post("/billing/purchase")
def purchase(req: PurchaseRequest, user: dict = Depends(auth.current_user)) -> dict:
    """Mock purchase of per-domain credits — buy only the domain you need."""
    if req.credits <= 0:
        raise HTTPException(status_code=400, detail="Credit amount must be positive.")
    return accounts.purchase(user, req.domain, req.credits)


class OrgSignupRequest(BaseModel):
    org_name: str
    admin_email: str
    admin_password: str
    admin_name: str = ""


@app.post("/org/signup")
def org_signup(req: OrgSignupRequest) -> dict:
    """Create an enterprise organization with a shared credit pool + an admin."""
    try:
        res = accounts.create_org(req.org_name, req.admin_email, req.admin_password, req.admin_name)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return _auth_payload(res["admin"])


class Member(BaseModel):
    email: str
    name: str = ""
    password: str = ""


class MembersRequest(BaseModel):
    members: list[Member]


@app.post("/org/members")
def org_members(req: MembersRequest, user: dict = Depends(auth.current_user)) -> dict:
    """Bulk-provision member accounts under the admin's org (enterprise)."""
    if user["account_type"] != "enterprise_admin" or not user.get("org_id"):
        raise HTTPException(status_code=403, detail="Only an enterprise admin can add members.")
    created = accounts.add_members(user["org_id"], [m.model_dump() for m in req.members])
    return {"created": created}


@app.post("/process", response_model=ProcessResponse)
async def process_endpoint(
    file: UploadFile = File(...),
    domain: str = Form("auto"),
    second_input: str = Form(""),
    user: dict = Depends(auth.current_user),
) -> ProcessResponse:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file upload.")
    try:
        ing = ingest(data, file.filename or "upload", file.content_type or "")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Ingestion failed: {e}")

    if domain in ("", "auto"):
        candidates = [p.name for p in ALL_PACKS if p.name != "generic"]
        domain = classify(ing["page_image_b64"], candidates)
    pack = get_pack(domain)

    # Gate on credits (free-trial pool, per-domain credits, or org pool).
    if not accounts.can_afford(user, pack.name):
        raise HTTPException(
            status_code=402,
            detail=f"Out of credits for {pack.label}. Buy {pack.label} credits to continue.",
        )

    result = route_process(ing["page_image_b64"], pack, ing["pdf_metadata"], second_input or None)
    if result.error:
        raise HTTPException(status_code=502, detail=result.error)

    # Only charge once extraction actually succeeded.
    accounts.charge(user, pack.name)

    ext = result.extraction
    ref = _ref(ext, pack)
    party = ext.value(pack.party_field) if pack.party_field else ""
    actionable = [f for f in result.integrity.flags if f.severity in ("high", "medium", "low")]

    store.log_activity("processed", domain=pack.name, ref=ref, party=party,
                       summary=f"Read {pack.label.lower()} · {party or ref or 'document'} ({ext.overall_confidence})",
                       severity="ok" if result.validation.passed and not actionable else "medium",
                       meta={"confidence": ext.overall_confidence, "escalated": result.escalated,
                             "model": result.model_used, "validation_passed": result.validation.passed,
                             "flags": len(actionable)})
    if result.escalated:
        store.log_activity("escalated", domain=pack.name, ref=ref, party=party,
                           summary=f"Escalated to {result.model_used} on low confidence", severity="info")
    for f in actionable:
        store.log_activity("flagged", domain=pack.name, ref=ref, party=party,
                           summary=f.reason, severity=f.severity, meta={"check": f.check})
    if result.anomaly and result.anomaly.level in ("elevated", "high"):
        store.log_activity("flagged", domain=pack.name, ref=ref, party=party,
                           summary=result.anomaly.reason,
                           severity="high" if result.anomaly.level == "high" else "medium",
                           meta={"check": "anomaly", "score": result.anomaly.score})

    return ProcessResponse(
        domain=pack.name, domain_label=pack.label, integrity_label=pack.integrity_label,
        extraction=ext, validation=result.validation, integrity=result.integrity,
        similarity=result.similarity, anomaly=result.anomaly,
        model_used=result.model_used, escalated=result.escalated,
        page_image_b64=ing["page_image_b64"], source_type=ing["source_type"],
    )


class ApproveRequest(BaseModel):
    domain: str
    extraction: Extraction
    mock_action: str = "approved & logged"


@app.post("/approve")
def approve_endpoint(req: ApproveRequest, user: dict = Depends(auth.current_user)) -> dict:
    pack = get_pack(req.domain)
    ext = req.extraction
    ref = _ref(ext, pack)
    record = {
        "domain": pack.name,
        "ref": ref,
        "party": ext.value(pack.party_field) if pack.party_field else "",
        "account": ext.value(pack.account_field) if pack.account_field else "",
        "identity": identity_signature(ext, pack),
        "amount": ext.number(pack.amount_field) if pack.amount_field else None,
        "doc_date": (ext.value(pack.date_fields[0]) if pack.date_fields else ""),
        "fields": {f.key: f.value for f in ext.fields},
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "mock_action": req.mock_action,
    }
    ledger_id = store.add_record(record)
    dedup.add_to_index(ext, pack, ledger_id)
    store.log_activity("approved", domain=pack.name, ref=ref, party=record["party"],
                       summary=f"Approved — {req.mock_action}", severity="ok",
                       meta={"ledger_id": ledger_id, "amount": record["amount"]})
    return {
        "ledger_id": ledger_id,
        "mock_action": {"status": "fired", "action": req.mock_action,
                        "message": f"{pack.label} {ref or ''} {req.mock_action}."},
        "csv_row": _csv_row(ext),
    }


@app.get("/log")
def log_endpoint() -> dict:
    return {"records": store.all_records()}


class AskRequest(BaseModel):
    question: str


@app.post("/assistant")
def assistant_endpoint(req: AskRequest, user: dict = Depends(auth.current_user)) -> dict:
    """Ask Verdict — grounded answers about your data and how the platform works."""
    return assistant.answer(req.question, user)


@app.get("/stats")
def stats_endpoint() -> dict:
    return store.stats()


@app.get("/activity")
def activity_endpoint(limit: int = 100) -> dict:
    return {"activity": store.recent_activity(limit=limit)}


@app.post("/match")
def match_endpoint(req: ApproveRequest) -> dict:
    return three_way_match(req.extraction)


@app.post("/draft-query")
def draft_query(req: ApproveRequest) -> dict:
    pack = get_pack(req.domain)
    ext = req.extraction
    party = ext.value(pack.party_field) if pack.party_field else "the counterparty"
    ref = _ref(ext, pack) or "(unknown reference)"
    account = ext.value(pack.account_field) if pack.account_field else ""
    prior = store.last_account_for_party(pack.name, party) if pack.account_field else None
    changed = bool(prior and prior.replace(" ", "") != account.replace(" ", ""))
    lines = [
        f"Subject: Verification required — {pack.label.lower()} {ref}",
        "",
        f"Hello {party},",
        "",
        f"Before we proceed with {pack.label.lower()} {ref}, our controls flagged the following:",
        "",
    ]
    if pack.account_field and changed:
        tail = account[-4:] if len(account) >= 4 else account
        lines.append(f"  • The account on file (ending {tail}) differs from a previously approved value. "
                     "Please confirm this change from a known, trusted contact.")
    else:
        lines.append("  • Please confirm the key details above are correct and current.")
    lines += ["", "We will hold this in review until we receive written confirmation.", "", "Thank you,", "Verdict Review"]
    return {"draft": "\n".join(lines), "changed": changed}


# --------------------------- helpers ---------------------------

def _ref(ext: Extraction, pack) -> str:
    for key in (pack.identity_fields or []):
        v = ext.value(key)
        if v:
            return v
    if pack.party_field:
        return ext.value(pack.party_field)
    return ""


def _csv_row(ext: Extraction) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    keys = [f.key for f in ext.fields]
    writer.writerow(["domain"] + keys)
    writer.writerow([ext.domain] + [ext.value(k) for k in keys])
    return buf.getvalue()
