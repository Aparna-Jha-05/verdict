"""Pre-seed the ledger with the 'prior approved' records the fraud demos need
(bank-change #4 and near-duplicate #5), now as generic multi-domain records.
Safe to run on every empty startup.
"""

from __future__ import annotations

from datetime import datetime, timezone

import dedup
import store
from packs import get_pack
from packs.base import identity_signature
from schema import ExtractedField, ExtractedTable, Extraction, TableRow


def _invoice(number, vendor, date, bank, subtotal, tax, total, items) -> Extraction:
    fields = [
        ExtractedField(key="invoice_number", label="Invoice Number", value=number, confidence="high"),
        ExtractedField(key="invoice_date", label="Invoice Date", value=date, confidence="high"),
        ExtractedField(key="vendor_name", label="Vendor", value=vendor, confidence="high"),
        ExtractedField(key="vendor_bank_account", label="Bank Account", value=bank, confidence="high"),
        ExtractedField(key="currency", label="Currency", value="USD", confidence="high"),
        ExtractedField(key="subtotal", label="Subtotal", value=str(subtotal), confidence="high"),
        ExtractedField(key="tax", label="Tax", value=str(tax), confidence="high"),
        ExtractedField(key="total", label="Total", value=str(total), confidence="high"),
    ]
    rows = [TableRow(cells={"description": d, "quantity": str(q), "unit_price": str(u), "amount": str(a)})
            for (d, q, u, a) in items]
    tables = [ExtractedTable(name="line_items", label="Line Items",
                             columns=["description", "quantity", "unit_price", "amount"], rows=rows)]
    return Extraction(domain="invoice", fields=fields, tables=tables, overall_confidence="high")


def _approve(ext: Extraction) -> int:
    pack = get_pack(ext.domain)
    record = {
        "domain": ext.domain,
        "ref": ext.value("invoice_number"),
        "party": ext.value("vendor_name"),
        "account": ext.value("vendor_bank_account"),
        "identity": identity_signature(ext, pack),
        "amount": ext.number("total"),
        "doc_date": ext.value("invoice_date"),
        "fields": {f.key: f.value for f in ext.fields},
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "mock_action": "queued for payment (seed)",
    }
    ledger_id = store.add_record(record)
    dedup.add_to_index(ext, pack, ledger_id)
    return ledger_id


def seed_if_empty() -> bool:
    try:
        store.init_db()
        if store.all_records():
            return False
        main()
        return True
    except Exception as e:
        print(f"seed_if_empty skipped: {e}")
        return False


def main() -> None:
    store.init_db()
    meridian = _invoice("INV-2026-410", "Meridian Logistics", "2026-04-05", "ACCT-4444333322",
                        1500.00, 120.00, 1620.00, [("Freight haul - Route A", 1, 1500.00, 1500.00)])
    print(f"seeded prior Meridian Logistics invoice (id {_approve(meridian)})")

    stellar = _invoice("INV-7788", "Stellar Freight", "2026-05-10", "ACCT-7777888899",
                       2050.00, 164.00, 2214.00,
                       [("Ocean shipping container", 2, 950.00, 1900.00), ("Customs handling", 1, 150.00, 150.00)])
    print(f"seeded prior Stellar Freight invoice (id {_approve(stellar)})")
    print("seed complete.")


if __name__ == "__main__":
    main()
