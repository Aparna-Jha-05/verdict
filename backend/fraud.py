"""Fraud / tamper layer — deterministic. NO LLM.

Every result is a *flag for human review*, never a verdict of "authentic",
"verified", or "safe to pay". Three checks:

  A. PDF metadata forensics (PDFs only)
  B. Vendor bank-detail change (uses the SQLite ledger)
  C. Semantic near-duplicate (delegated to dedup.py: embeddings + Chroma)
     plus an exact invoice-number hard duplicate block (uses the ledger).
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Optional

import store
from dedup import check_duplicate
from schema import Extraction, Flag, FraudResult

# Producer/creator strings that suggest an image editor / generic tool rather
# than accounting or PDF-generation software. Heuristic, case-insensitive.
_SUSPICIOUS_PRODUCERS = [
    "photoshop",
    "gimp",
    "canva",
    "paint",
    "pixlr",
    "illustrator",
    "coreldraw",
    "inkscape",
    "snagit",
    "screenshot",
    "figma",
]
# Producers we consider benign accounting / office / PDF tooling.
_BENIGN_PRODUCERS = [
    "quickbooks",
    "xero",
    "sap",
    "oracle",
    "sage",
    "acrobat",
    "pdfkit",
    "reportlab",
    "libreoffice",
    "microsoft",
    "word",
    "excel",
    "tcpdf",
    "fpdf",
    "wkhtmltopdf",
    "prince",
    "latex",
    "pdftex",
    "chromium",
    "skia",
    "quartz",
]


def _parse_pdf_date(raw: str) -> Optional[datetime]:
    """Parse a PDF date string like 'D:20240115120000+00'00''."""
    if not raw:
        return None
    s = raw.strip()
    if s.startswith("D:"):
        s = s[2:]
    m = re.match(r"(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?", s)
    if not m:
        return None
    y = int(m.group(1))
    mo = int(m.group(2) or 1)
    d = int(m.group(3) or 1)
    hh = int(m.group(4) or 0)
    mm = int(m.group(5) or 0)
    ss = int(m.group(6) or 0)
    try:
        return datetime(y, mo, d, hh, mm, ss)
    except ValueError:
        return None


def _pdf_metadata_forensics(metadata: Optional[dict], ext: Extraction) -> list[Flag]:
    flags: list[Flag] = []
    if metadata is None:
        flags.append(
            Flag(
                check="pdf_metadata",
                severity="info",
                reason="No document metadata available — photo/scan path.",
            )
        )
        return flags

    producer = (metadata.get("producer") or "").strip()
    creator = (metadata.get("creator") or "").strip()
    blob = f"{producer} {creator}".lower()

    matched_suspicious = [p for p in _SUSPICIOUS_PRODUCERS if p in blob]
    if matched_suspicious:
        flags.append(
            Flag(
                check="pdf_metadata",
                severity="high",
                reason=(
                    "PDF was produced/edited with image-editing software "
                    f"({', '.join(matched_suspicious)}); accounting software is "
                    f"expected. Producer='{producer}', Creator='{creator}'."
                ),
            )
        )

    created = _parse_pdf_date(metadata.get("creationDate", ""))
    modified = _parse_pdf_date(metadata.get("modDate", ""))

    if created is None:
        flags.append(
            Flag(
                check="pdf_metadata",
                severity="medium",
                reason="PDF creation date is missing from metadata.",
            )
        )
    if created and modified and modified < created:
        flags.append(
            Flag(
                check="pdf_metadata",
                severity="high",
                reason=(
                    f"PDF modification date ({modified.date()}) precedes its "
                    f"creation date ({created.date()}) — metadata inconsistency."
                ),
            )
        )

    # Creation suspiciously recent relative to the stated (old) invoice date.
    inv_d = _parse_invoice_date(ext.invoice_date.value)
    if created and inv_d:
        gap_days = (created.date() - inv_d).days
        if gap_days > 120:
            flags.append(
                Flag(
                    check="pdf_metadata",
                    severity="medium",
                    reason=(
                        f"Invoice dated {inv_d.isoformat()} but the PDF file was "
                        f"created {gap_days} days later ({created.date()}); a "
                        "supposedly old invoice generated recently warrants review."
                    ),
                )
            )
    return flags


def _parse_invoice_date(s: str) -> Optional[date]:
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _bank_detail_change(ext: Extraction) -> Optional[Flag]:
    vendor = ext.vendor_name.value.strip()
    account = ext.vendor_bank_account.value.strip()
    if not vendor or not account:
        return None
    prior = store.last_bank_account_for_vendor(vendor)
    if prior and _norm_account(prior) != _norm_account(account):
        return Flag(
            check="bank_detail_change",
            severity="high",
            reason=(
                f"Bank account for {vendor} differs from the previously approved "
                f"account (was ...{_tail(prior)}, now ...{_tail(account)}). This is "
                "the most common real-world AP fraud — verify with the vendor."
            ),
        )
    return None


def _norm_account(a: str) -> str:
    return re.sub(r"[\s-]", "", (a or "").strip())


def _tail(a: str) -> str:
    a = _norm_account(a)
    return a[-4:] if len(a) >= 4 else a


def _exact_duplicate(ext: Extraction) -> Optional[Flag]:
    inv = ext.invoice_number.value.strip()
    prior = store.invoice_number_exists(inv)
    if prior:
        return Flag(
            check="exact_duplicate",
            severity="high",
            reason=(
                f"Invoice number {inv} was already approved on "
                f"{prior.get('approved_at', 'a prior date')} — hard duplicate block."
            ),
        )
    return None


def run_fraud_checks(ext: Extraction, pdf_metadata: Optional[dict]) -> FraudResult:
    flags: list[Flag] = []

    # A. PDF metadata forensics (also emits the info note for image uploads).
    flags.extend(_pdf_metadata_forensics(pdf_metadata, ext))

    # B. Vendor bank-detail change.
    bank_flag = _bank_detail_change(ext)
    if bank_flag:
        flags.append(bank_flag)

    # C. Duplicates: exact hard-block + semantic near-duplicate.
    exact = _exact_duplicate(ext)
    if exact:
        flags.append(exact)
    dup = check_duplicate(ext)
    if dup:
        flags.append(dup)

    # "passed" == no actionable flags. Info-only notes don't fail the layer.
    actionable = [f for f in flags if f.severity in ("high", "medium", "low")]
    return FraudResult(passed=len(actionable) == 0, flags=flags)
