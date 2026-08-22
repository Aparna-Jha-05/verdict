"""Validation layer — deterministic correctness rules. NO LLM. Ever.

Pure Python over the parsed Extraction. Each rule returns pass/fail + a
human-readable reason. Run all, collect results. This layer answers "is the
document internally consistent?", not "is it fraudulent" (that's fraud.py).
"""

from __future__ import annotations

from datetime import date, datetime

from schema import Check, Extraction, ValidationResult, _to_float

_TOL = 0.01
_MAX_AGE_YEARS = 25


def _num(field) -> float | None:
    """Best-effort float from a Field_/NumberField."""
    return _to_float(getattr(field, "value", None))


def _check_totals_reconcile(ext: Extraction) -> Check:
    line_sum = sum((li.amount or 0.0) for li in ext.line_items)
    subtotal = _num(ext.subtotal)
    if not ext.line_items:
        return Check(
            rule="Totals reconcile",
            passed=False,
            reason="No line items extracted, cannot reconcile against subtotal.",
        )
    if subtotal is None:
        return Check(
            rule="Totals reconcile",
            passed=False,
            reason="Subtotal is missing.",
        )
    ok = abs(line_sum - subtotal) <= _TOL
    return Check(
        rule="Totals reconcile",
        passed=ok,
        reason=(
            f"Line items sum to {line_sum:.2f} and subtotal is {subtotal:.2f}."
            if ok
            else f"Line items sum to {line_sum:.2f} but subtotal is {subtotal:.2f} "
            f"(off by {abs(line_sum - subtotal):.2f})."
        ),
    )


def _check_tax_math(ext: Extraction) -> Check:
    subtotal = _num(ext.subtotal)
    tax = _num(ext.tax)
    total = _num(ext.total)
    if subtotal is None or total is None:
        return Check(
            rule="Tax math",
            passed=False,
            reason="Subtotal or total missing; cannot verify subtotal + tax = total.",
        )
    tax = tax or 0.0
    expected = subtotal + tax
    ok = abs(expected - total) <= _TOL
    return Check(
        rule="Tax math",
        passed=ok,
        reason=(
            f"{subtotal:.2f} + {tax:.2f} = {total:.2f}."
            if ok
            else f"Subtotal {subtotal:.2f} + tax {tax:.2f} = {expected:.2f}, "
            f"but total says {total:.2f}."
        ),
    )


def _check_line_item_math(ext: Extraction) -> Check:
    if not ext.line_items:
        return Check(
            rule="Line-item math",
            passed=False,
            reason="No line items to check.",
        )
    bad = []
    for i, li in enumerate(ext.line_items, start=1):
        expected = (li.quantity or 0.0) * (li.unit_price or 0.0)
        if abs(expected - (li.amount or 0.0)) > _TOL:
            label = li.description.strip() or f"row {i}"
            bad.append(
                f"'{label}': {li.quantity} x {li.unit_price} = {expected:.2f} "
                f"but amount is {li.amount:.2f}"
            )
    ok = not bad
    return Check(
        rule="Line-item math",
        passed=ok,
        reason=(
            "Every line item's quantity x unit price equals its amount."
            if ok
            else "Mismatched line item(s): " + "; ".join(bad) + "."
        ),
    )


def _check_required_fields(ext: Extraction) -> Check:
    missing = []
    if not ext.invoice_number.value.strip():
        missing.append("invoice_number")
    if not ext.invoice_date.value.strip():
        missing.append("invoice_date")
    if not ext.vendor_name.value.strip():
        missing.append("vendor_name")
    if _num(ext.total) is None:
        missing.append("total")
    ok = not missing
    return Check(
        rule="Required fields present",
        passed=ok,
        reason=(
            "invoice_number, invoice_date, vendor_name and total are all present."
            if ok
            else "Missing required field(s): " + ", ".join(missing) + "."
        ),
    )


def _parse_date(s: str) -> date | None:
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d %b %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _check_date_sanity(ext: Extraction) -> Check:
    raw = ext.invoice_date.value
    d = _parse_date(raw)
    if d is None:
        return Check(
            rule="Date sanity",
            passed=False,
            reason=f"Invoice date '{raw}' does not parse as a real date.",
        )
    today = date.today()
    if d > today:
        return Check(
            rule="Date sanity",
            passed=False,
            reason=f"Invoice date {d.isoformat()} is in the future.",
        )
    if d.year < today.year - _MAX_AGE_YEARS:
        return Check(
            rule="Date sanity",
            passed=False,
            reason=f"Invoice date {d.isoformat()} is implausibly old.",
        )
    return Check(
        rule="Date sanity",
        passed=True,
        reason=f"Invoice date {d.isoformat()} is valid and not in the future.",
    )


def _check_currency(ext: Extraction) -> Check:
    ok = bool(ext.currency.value.strip())
    return Check(
        rule="Currency present",
        passed=ok,
        reason=(
            f"Currency '{ext.currency.value.strip()}' present."
            if ok
            else "No currency detected on the invoice."
        ),
    )


def validate(ext: Extraction) -> ValidationResult:
    checks = [
        _check_totals_reconcile(ext),
        _check_tax_math(ext),
        _check_line_item_math(ext),
        _check_required_fields(ext),
        _check_date_sanity(ext),
        _check_currency(ext),
    ]
    return ValidationResult(passed=all(c.passed for c in checks), checks=checks)
