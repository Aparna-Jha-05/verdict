"""FastAPI app: routes + CORS. Wires ingest -> route(extract/validate/escalate)
-> fraud/dedup, plus the human approval gate (/approve) and the ledger (/log).
"""

from __future__ import annotations

import csv
import io
import os
from datetime import datetime, timezone

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import dedup
import store
from ingest import ingest
from match import three_way_match
from route import process
from schema import Extraction, ProcessResponse, _to_float

app = FastAPI(title="Invoice Intelligence Pipeline", version="1.0.0")

# CORS: allow the Vercel origin(s). Comma-separated list in env, or "*" default.
_origins_env = os.environ.get("CORS_ORIGINS", "*")
_origins = ["*"] if _origins_env.strip() == "*" else [
    o.strip() for o in _origins_env.split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    store.init_db()
    # Auto-seed the "prior approved" invoices the fraud demos depend on, but only
    # on a fresh/empty ledger so real approvals are never duplicated. Opt out
    # with AUTO_SEED=0.
    if os.environ.get("AUTO_SEED", "1") != "0":
        import seed

        if seed.seed_if_empty():
            print("Ledger was empty — seeded demo prior-invoices.")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "invoice-intelligence"}


@app.post("/process", response_model=ProcessResponse)
async def process_endpoint(file: UploadFile = File(...)) -> ProcessResponse:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file upload.")
    try:
        ing = ingest(data, file.filename or "upload", file.content_type or "")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Ingestion failed: {e}")

    result = process(ing["page_image_b64"], ing["pdf_metadata"])
    if result.error:
        raise HTTPException(status_code=502, detail=result.error)

    # --- Audit trail ---
    ext = result.extraction
    inv = ext.invoice_number.value.strip()
    vendor = ext.vendor_name.value.strip()
    actionable = [f for f in result.fraud.flags if f.severity in ("high", "medium", "low")]
    store.log_activity(
        "processed",
        invoice_number=inv,
        vendor_name=vendor,
        summary=f"Extracted {vendor or 'invoice'} ({ext.overall_confidence} confidence)",
        severity="ok" if result.validation.passed and not actionable else "medium",
        meta={
            "confidence": ext.overall_confidence,
            "escalated": result.escalated,
            "model": result.model_used,
            "validation_passed": result.validation.passed,
            "flags": len(actionable),
        },
    )
    if result.escalated:
        store.log_activity(
            "escalated",
            invoice_number=inv,
            vendor_name=vendor,
            summary=f"Escalated to {result.model_used} on low confidence",
            severity="info",
        )
    for f in actionable:
        store.log_activity(
            "flagged",
            invoice_number=inv,
            vendor_name=vendor,
            summary=f.reason,
            severity=f.severity,
            meta={"check": f.check},
        )

    return ProcessResponse(
        extraction=result.extraction,
        validation=result.validation,
        fraud=result.fraud,
        model_used=result.model_used,
        escalated=result.escalated,
        page_image_b64=ing["page_image_b64"],
        source_type=ing["source_type"],
    )


class ApproveRequest(BaseModel):
    extraction: Extraction
    mock_action: str = "queued for payment"


@app.post("/approve")
def approve_endpoint(req: ApproveRequest) -> dict:
    ext = req.extraction
    record = {
        "invoice_number": ext.invoice_number.value.strip(),
        "vendor_name": ext.vendor_name.value.strip(),
        "vendor_bank_account": ext.vendor_bank_account.value.strip(),
        "invoice_date": ext.invoice_date.value.strip(),
        "currency": ext.currency.value.strip(),
        "subtotal": _to_float(ext.subtotal.value),
        "tax": _to_float(ext.tax.value),
        "total": _to_float(ext.total.value),
        "line_items": [li.model_dump() for li in ext.line_items],
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "mock_action": req.mock_action,
    }
    ledger_id = store.add_invoice(record)
    # Register the embedding so future dedup can catch resubmissions.
    dedup.add_to_index(ext, ledger_id)
    store.log_activity(
        "approved",
        invoice_number=record["invoice_number"],
        vendor_name=record["vendor_name"],
        summary=f"Approved — {req.mock_action}",
        severity="ok",
        meta={"ledger_id": ledger_id, "total": record["total"]},
    )

    csv_row = _csv_row(record)

    return {
        "ledger_id": ledger_id,
        "mock_action": {
            "status": "fired",
            "action": req.mock_action,
            "message": f"Invoice {record['invoice_number']} {req.mock_action}.",
        },
        "csv_row": csv_row,
    }


def _csv_row(record: dict) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "invoice_number",
            "vendor_name",
            "invoice_date",
            "currency",
            "subtotal",
            "tax",
            "total",
            "approved_at",
            "mock_action",
        ]
    )
    writer.writerow(
        [
            record["invoice_number"],
            record["vendor_name"],
            record["invoice_date"],
            record["currency"],
            record["subtotal"],
            record["tax"],
            record["total"],
            record["approved_at"],
            record["mock_action"],
        ]
    )
    return buf.getvalue()


@app.get("/log")
def log_endpoint() -> dict:
    return {"invoices": store.all_invoices()}


@app.get("/stats")
def stats_endpoint() -> dict:
    return store.stats()


@app.get("/activity")
def activity_endpoint(limit: int = 100) -> dict:
    return {"activity": store.recent_activity(limit=limit)}


@app.post("/match")
def match_endpoint(req: ApproveRequest) -> dict:
    """STRETCH: three-way match the extraction against seeded POs + receipts."""
    return three_way_match(req.extraction)


@app.post("/draft-vendor-query")
def draft_vendor_query(req: ApproveRequest) -> dict:
    """Deterministic 'RFI-style' verification message a reviewer can send to a
    vendor when a fraud flag fires. No LLM — a filled template from the facts."""
    ext = req.extraction
    vendor = ext.vendor_name.value.strip() or "Vendor"
    inv = ext.invoice_number.value.strip() or "(unknown number)"
    bank = ext.vendor_bank_account.value.strip()
    total = ext.total.value.strip()
    currency = ext.currency.value.strip()

    prior_bank = store.last_bank_account_for_vendor(vendor)
    bank_changed = bool(prior_bank and prior_bank.replace(" ", "") != bank.replace(" ", ""))

    lines = [
        f"Subject: Verification required before payment — invoice {inv}",
        "",
        f"Hello {vendor} accounts team,",
        "",
        f"Before we release payment on invoice {inv}"
        + (f" ({currency} {total})" if total else "")
        + ", our controls flagged the following for confirmation:",
        "",
    ]
    if bank_changed:
        lines.append(
            f"  • The bank account on this invoice (ending {bank[-4:] if len(bank) >= 4 else bank}) "
            f"differs from the account we have on file from a previously approved invoice. "
            f"Please confirm, from a known contact, that your banking details have changed."
        )
    else:
        lines.append(
            f"  • Please confirm the remittance bank account ending "
            f"{bank[-4:] if len(bank) >= 4 else bank or '(not provided)'} is correct."
        )
    lines += [
        "",
        "We will hold this invoice in review until we receive written confirmation.",
        "",
        "Thank you,",
        "Accounts Payable",
    ]
    return {"draft": "\n".join(lines), "bank_changed": bank_changed}
