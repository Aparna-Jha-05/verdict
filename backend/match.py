"""STRETCH: three-way match — invoice vs purchase orders vs goods receipts.

Deterministic, NO LLM. Seeded from sample_data/pos.json and receipts.json.
Matches on PO number when present, else falls back to vendor. Flags:
  - no matching purchase order
  - no goods receipt
  - amount mismatch (invoice total vs PO total, tolerance)
  - quantity mismatch (received qty vs invoiced qty per line)
"""

from __future__ import annotations

import json
import os
from typing import Optional

from schema import Extraction, _to_float

_DATA_DIR = os.path.join(os.path.dirname(__file__), "sample_data")
_AMOUNT_TOL = 0.01


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
    vendor = ext.vendor_name.value.strip().lower()
    # No PO number in the schema, so match on vendor (+ nearest total if many).
    candidates = [p for p in pos if str(p.get("vendor_name", "")).strip().lower() == vendor]
    if not candidates:
        return None
    total = _to_float(ext.total.value)
    if total is None:
        return candidates[0]
    return min(candidates, key=lambda p: abs((_to_float(p.get("total")) or 0.0) - total))


def _find_receipt(receipts: list[dict], po: Optional[dict], ext: Extraction) -> Optional[dict]:
    if po and po.get("po_number"):
        for r in receipts:
            if str(r.get("po_number", "")) == str(po.get("po_number")):
                return r
    vendor = ext.vendor_name.value.strip().lower()
    for r in receipts:
        if str(r.get("vendor_name", "")).strip().lower() == vendor:
            return r
    return None


def three_way_match(ext: Extraction) -> dict:
    pos = _load("pos.json")
    receipts = _load("receipts.json")

    flags: list[dict] = []
    po = _find_po(pos, ext)
    receipt = _find_receipt(receipts, po, ext)

    if po is None:
        flags.append(
            {
                "check": "purchase_order",
                "severity": "high",
                "reason": f"No purchase order found for vendor '{ext.vendor_name.value.strip()}'.",
            }
        )
    else:
        inv_total = _to_float(ext.total.value)
        po_total = _to_float(po.get("total"))
        if inv_total is not None and po_total is not None and abs(inv_total - po_total) > _AMOUNT_TOL:
            flags.append(
                {
                    "check": "amount_mismatch",
                    "severity": "high",
                    "reason": (
                        f"Invoice total {inv_total:.2f} does not match PO "
                        f"{po.get('po_number')} total {po_total:.2f}."
                    ),
                }
            )

    if receipt is None:
        flags.append(
            {
                "check": "goods_receipt",
                "severity": "medium",
                "reason": "No goods receipt found for this invoice.",
            }
        )
    else:
        # Quantity match per line, keyed by description.
        received = {
            str(li.get("description", "")).strip().lower(): _to_float(li.get("quantity"))
            for li in receipt.get("line_items", [])
        }
        for li in ext.line_items:
            key = (li.description or "").strip().lower()
            if key in received and received[key] is not None:
                if abs((li.quantity or 0.0) - received[key]) > 0.001:
                    flags.append(
                        {
                            "check": "quantity_mismatch",
                            "severity": "high",
                            "reason": (
                                f"Line '{li.description}': invoiced {li.quantity} but "
                                f"{received[key]} were received."
                            ),
                        }
                    )

    return {
        "matched_po": po.get("po_number") if po else None,
        "matched_receipt": receipt.get("receipt_number") if receipt else None,
        "passed": len(flags) == 0,
        "flags": flags,
    }
