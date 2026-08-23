"""STRETCH: three-way match (invoice / PO domains) vs seeded POs + receipts.
Deterministic, NO LLM. Reads the generic Extraction via its accessors.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from schema import Extraction, to_float

_DATA_DIR = os.path.join(os.path.dirname(__file__), "sample_data")
_TOL = 0.01


def _load(name: str) -> list[dict]:
    path = os.path.join(_DATA_DIR, name)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return []
    return data if isinstance(data, list) else []


def _find_po(pos: list[dict], ext: Extraction) -> Optional[dict]:
    vendor = ext.value("vendor_name").lower()
    cands = [p for p in pos if str(p.get("vendor_name", "")).strip().lower() == vendor]
    if not cands:
        return None
    total = ext.number("total")
    if total is None:
        return cands[0]
    return min(cands, key=lambda p: abs((to_float(p.get("total")) or 0.0) - total))


def three_way_match(ext: Extraction) -> dict:
    pos = _load("pos.json")
    receipts = _load("receipts.json")
    flags: list[dict] = []

    po = _find_po(pos, ext)
    if po is None:
        flags.append({"check": "purchase_order", "severity": "high",
                      "reason": f"No purchase order found for vendor '{ext.value('vendor_name')}'."})
    else:
        inv_total = ext.number("total")
        po_total = to_float(po.get("total"))
        if inv_total is not None and po_total is not None and abs(inv_total - po_total) > _TOL:
            flags.append({"check": "amount_mismatch", "severity": "high",
                          "reason": f"Invoice total {inv_total:.2f} ≠ PO {po.get('po_number')} total {po_total:.2f}."})

    receipt = None
    if po and po.get("po_number"):
        receipt = next((r for r in receipts if str(r.get("po_number", "")) == str(po.get("po_number"))), None)
    if receipt is None:
        flags.append({"check": "goods_receipt", "severity": "medium",
                      "reason": "No goods receipt found for this document."})
    else:
        received = {str(li.get("description", "")).strip().lower(): to_float(li.get("quantity"))
                    for li in receipt.get("line_items", [])}
        t = ext.table("line_items")
        if t:
            for r in t.rows:
                key = (r.cells.get("description", "")).strip().lower()
                qty = r.num("quantity")
                if key in received and received[key] is not None and qty is not None:
                    if abs(qty - received[key]) > 0.001:
                        flags.append({"check": "quantity_mismatch", "severity": "high",
                                      "reason": f"Line '{r.cells.get('description')}': invoiced {qty} but {received[key]} received."})

    return {
        "matched_po": po.get("po_number") if po else None,
        "matched_receipt": receipt.get("receipt_number") if receipt else None,
        "passed": len(flags) == 0,
        "flags": flags,
    }
