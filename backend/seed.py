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

    # A spread of historical invoices so the anomaly detector has a real baseline
    # (and the near-duplicate/vector store has more to compare against).
    history = [
        ("INV-3001", "Orbit Supplies", "2026-03-02", "ACCT-1010101010", 222.00, 17.76, 239.76,
         [("Printer paper (box)", 6, 37.00, 222.00)]),
        ("INV-3002", "Orbit Supplies", "2026-03-19", "ACCT-1010101010", 331.00, 26.48, 357.48,
         [("Toner cartridge", 2, 165.50, 331.00)]),
        ("INV-3050", "Zephyr Parts", "2026-03-25", "ACCT-2020202020", 420.00, 33.60, 453.60,
         [("Bearing set", 8, 52.50, 420.00)]),
        ("INV-3051", "Zephyr Parts", "2026-04-08", "ACCT-2020202020", 560.00, 44.80, 604.80,
         [("Hydraulic hose", 4, 140.00, 560.00)]),
        ("INV-3100", "Halcyon Media", "2026-04-14", "ACCT-3030303030", 690.00, 55.20, 745.20,
         [("Design retainer", 1, 690.00, 690.00)]),
        ("INV-3101", "Halcyon Media", "2026-04-27", "ACCT-3030303030", 810.00, 64.80, 874.80,
         [("Video edit", 1, 810.00, 810.00)]),
    ]
    for row in history:
        _approve(_invoice(*row))
    print(f"seeded {len(history)} baseline invoices for anomaly detection")
    print("seed complete.")


if __name__ == "__main__":
    main()
