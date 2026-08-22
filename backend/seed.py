"""Pre-seed the ledger (and Chroma) with the 'prior approved' invoices that the
bank-change (#4) and near-duplicate (#5) demo scenarios depend on.

Run after make_samples.py, before demoing:
    python seed.py
Idempotent-ish: it clears prior seeded rows for these two vendors first.
"""

from __future__ import annotations

from datetime import datetime, timezone

import dedup
import store
from schema import Extraction, Field_, LineItem, NumberField


def _ext(number, vendor, date, bank, currency, subtotal, tax, total, items) -> Extraction:
    e = Extraction()
    e.invoice_number = Field_(value=number, confidence="high")
    e.vendor_name = Field_(value=vendor, confidence="high")
    e.invoice_date = Field_(value=date, confidence="high")
    e.vendor_bank_account = Field_(value=bank, confidence="high")
    e.currency = Field_(value=currency, confidence="high")
    e.subtotal = NumberField(value=str(subtotal), confidence="high")
    e.tax = NumberField(value=str(tax), confidence="high")
    e.total = NumberField(value=str(total), confidence="high")
    e.line_items = [
        LineItem(description=d, quantity=q, unit_price=u, amount=a, confidence="high")
        for (d, q, u, a) in items
    ]
    e.overall_confidence = "high"
    return e


def _approve(ext: Extraction) -> int:
    record = {
        "invoice_number": ext.invoice_number.value,
        "vendor_name": ext.vendor_name.value,
        "vendor_bank_account": ext.vendor_bank_account.value,
        "invoice_date": ext.invoice_date.value,
        "currency": ext.currency.value,
        "subtotal": float(ext.subtotal.value),
        "tax": float(ext.tax.value),
        "total": float(ext.total.value),
        "line_items": [li.model_dump() for li in ext.line_items],
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "mock_action": "queued for payment (seed)",
    }
    ledger_id = store.add_invoice(record)
    dedup.add_to_index(ext, ledger_id)
    return ledger_id


def main() -> None:
    store.init_db()

    # Prior invoice for the changed-bank scenario: Meridian Logistics on the
    # ORIGINAL (legitimate) bank account. changed_bank.pdf uses a different one.
    meridian = _ext(
        number="INV-2026-410",
        vendor="Meridian Logistics",
        date="2026-04-05",
        bank="ACCT-4444333322",
        currency="USD",
        subtotal=1500.00,
        tax=120.00,
        total=1620.00,
        items=[("Freight haul - Route A", 1, 1500.00, 1500.00)],
    )
    mid = _approve(meridian)
    print(f"seeded prior Meridian Logistics invoice (ledger id {mid})")

    # Prior invoice for the near-duplicate scenario: Stellar Freight INV-7788.
    # near_duplicate.pdf is INV-7789 with identical everything else.
    stellar = _ext(
        number="INV-7788",
        vendor="Stellar Freight",
        date="2026-05-10",
        bank="ACCT-7777888899",
        currency="USD",
        subtotal=2050.00,
        tax=164.00,
        total=2214.00,
        items=[
            ("Ocean shipping container", 2, 950.00, 1900.00),
            ("Customs handling", 1, 150.00, 150.00),
        ],
    )
    sid = _approve(stellar)
    print(f"seeded prior Stellar Freight invoice (ledger id {sid})")

    print("seed complete.")


if __name__ == "__main__":
    main()
