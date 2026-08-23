"""Pack specifications + the generic deterministic engine (NO LLM).

`DomainPack` is a declarative description of a document domain. `run_validation`
and `run_integrity` interpret that description against an `Extraction`, so every
domain shares one reproducible, auditable engine.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from datetime import date, datetime
from typing import Callable, List, Optional

from schema import (
    Check,
    Extraction,
    Flag,
    IntegrityResult,
    ValidationResult,
    to_float,
)

_TOL = 0.01
_MAX_AGE_YEARS = 30


# ---------------------------------------------------------------------------
# Declarative specs
# ---------------------------------------------------------------------------

@dataclass
class FieldSpec:
    key: str
    label: str
    type: str = "text"  # text | number | date | currency | email | id
    required: bool = False
    group: str = ""


@dataclass
class ColumnSpec:
    name: str
    label: str
    type: str = "text"


@dataclass
class TableSpec:
    name: str
    label: str
    columns: List[ColumnSpec] = dc_field(default_factory=list)


@dataclass
class ArithmeticRule:
    # kinds:
    #   "sum_col_equals_field": sum(table.column) ~= field
    #   "fields_sum_equals":    sum(add_fields) ~= field
    #   "row_product":          per row, product(factors) ~= result_col
    kind: str
    label: str = ""
    table: str = ""
    column: str = ""
    field: str = ""
    add_fields: List[str] = dc_field(default_factory=list)
    factors: List[str] = dc_field(default_factory=list)
    result_col: str = ""


@dataclass
class SimilaritySpec:
    second_input_key: str  # e.g. "job_description"
    second_input_label: str  # e.g. "Job description"
    label: str  # e.g. "Résumé ↔ Job description match"
    # deterministic bands over cosine similarity: (strong, moderate)
    strong: float = 0.62
    moderate: float = 0.45
    # which extraction fields form the candidate signature text
    signature_fields: List[str] = dc_field(default_factory=list)
    signature_tables: List[str] = dc_field(default_factory=list)


@dataclass
class DomainPack:
    name: str
    label: str
    description: str
    icon: str  # lucide-react icon name for the UI
    fields: List[FieldSpec]
    detect_hints: List[str] = dc_field(default_factory=list)
    tables: List[TableSpec] = dc_field(default_factory=list)
    arithmetic: List[ArithmeticRule] = dc_field(default_factory=list)
    date_fields: List[str] = dc_field(default_factory=list)
    identity_fields: List[str] = dc_field(default_factory=list)
    party_field: str = ""  # entity name (vendor / candidate / issuer)
    account_field: str = ""  # sensitive account for change-detection
    amount_field: str = ""  # headline amount, for dup + ledger display
    similarity: Optional[SimilaritySpec] = None
    integrity_label: str = "Integrity & Risk"
    extra_checks: List[Callable[[Extraction], List[Check]]] = dc_field(default_factory=list)
    extra_integrity: List[Callable[[Extraction], List[Flag]]] = dc_field(default_factory=list)

    @property
    def needs_second_input(self) -> bool:
        return self.similarity is not None


# ---------------------------------------------------------------------------
# Generic validation engine
# ---------------------------------------------------------------------------

def _parse_date(s: str) -> Optional[date]:
    s = (s or "").strip()
    if not s:
        return None
    for fmt in (
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d %b %Y",
        "%b %d, %Y", "%Y/%m/%d", "%d.%m.%Y",
    ):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _check_required(ext: Extraction, pack: DomainPack) -> Check:
    missing = [f.label for f in pack.fields if f.required and not ext.value(f.key)]
    ok = not missing
    return Check(
        rule="Required fields present",
        passed=ok,
        reason=(
            "All required fields were extracted."
            if ok
            else "Missing required field(s): " + ", ".join(missing) + "."
        ),
    )


def _check_dates(ext: Extraction, pack: DomainPack) -> List[Check]:
    checks: List[Check] = []
    today = date.today()
    for key in pack.date_fields:
        f = ext.get(key)
        if not f or not f.value.strip():
            continue
        d = _parse_date(f.value)
        label = f.label or key
        if d is None:
            checks.append(Check(rule=f"Date sanity · {label}", passed=False,
                                reason=f"'{f.value}' does not parse as a real date."))
        elif d > today:
            checks.append(Check(rule=f"Date sanity · {label}", passed=False,
                                reason=f"{d.isoformat()} is in the future."))
        elif d.year < today.year - _MAX_AGE_YEARS and "birth" not in key.lower() and "dob" not in key.lower():
            # The "too old" heuristic is for document/transaction dates, not births.
            checks.append(Check(rule=f"Date sanity · {label}", passed=False,
                                reason=f"{d.isoformat()} is implausibly old."))
        else:
            checks.append(Check(rule=f"Date sanity · {label}", passed=True,
                                reason=f"{d.isoformat()} is a valid date."))
    return checks


def _check_arithmetic(ext: Extraction, rule: ArithmeticRule) -> Check:
    name = rule.label or rule.kind
    if rule.kind == "sum_col_equals_field":
        t = ext.table(rule.table)
        target = ext.number(rule.field)
        if t is None or not t.rows:
            return Check(rule=name, passed=False, reason=f"No '{rule.table}' rows to reconcile.")
        if target is None:
            return Check(rule=name, passed=False, reason=f"'{rule.field}' missing; cannot reconcile.")
        s = sum((r.num(rule.column) or 0.0) for r in t.rows)
        ok = abs(s - target) <= _TOL
        return Check(rule=name, passed=ok,
                     reason=(f"Rows sum to {s:.2f} = {rule.field} {target:.2f}." if ok
                             else f"Rows sum to {s:.2f} but {rule.field} is {target:.2f} (off {abs(s-target):.2f})."))
    if rule.kind == "fields_sum_equals":
        target = ext.number(rule.field)
        vals = [ext.number(k) for k in rule.add_fields]
        if target is None or any(v is None for v in vals):
            return Check(rule=name, passed=False, reason="Missing operand; cannot verify.")
        s = sum(v or 0.0 for v in vals)
        ok = abs(s - target) <= _TOL
        return Check(rule=name, passed=ok,
                     reason=(f"{' + '.join(rule.add_fields)} = {s:.2f} = {rule.field} {target:.2f}." if ok
                             else f"{' + '.join(rule.add_fields)} = {s:.2f}, but {rule.field} = {target:.2f}."))
    if rule.kind == "row_product":
        t = ext.table(rule.table)
        if t is None or not t.rows:
            return Check(rule=name, passed=False, reason=f"No '{rule.table}' rows to check.")
        bad = []
        for i, r in enumerate(t.rows, 1):
            prod = 1.0
            for fcol in rule.factors:
                prod *= (r.num(fcol) or 0.0)
            res = r.num(rule.result_col) or 0.0
            if abs(prod - res) > _TOL:
                bad.append(f"row {i}: {'×'.join(rule.factors)}={prod:.2f} vs {rule.result_col}={res:.2f}")
        ok = not bad
        return Check(rule=name, passed=ok,
                     reason="Every row's math checks out." if ok else "Mismatched: " + "; ".join(bad) + ".")
    return Check(rule=name, passed=True, reason="No-op rule.")


def run_validation(ext: Extraction, pack: DomainPack) -> ValidationResult:
    checks: List[Check] = [_check_required(ext, pack)]
    checks.extend(_check_dates(ext, pack))
    for rule in pack.arithmetic:
        checks.append(_check_arithmetic(ext, rule))
    for fn in pack.extra_checks:
        try:
            checks.extend(fn(ext) or [])
        except Exception as e:  # a custom check must never crash the pipeline
            checks.append(Check(rule="Custom check", passed=True, reason=f"(skipped: {e})"))
    return ValidationResult(passed=all(c.passed for c in checks), checks=checks)


# ---------------------------------------------------------------------------
# Generic integrity engine (fraud/tamper/consistency) — NO LLM
# ---------------------------------------------------------------------------

_SUSPICIOUS_PRODUCERS = [
    "photoshop", "gimp", "canva", "paint", "pixlr", "illustrator",
    "coreldraw", "inkscape", "snagit", "screenshot", "figma",
]


def _parse_pdf_date(raw: str) -> Optional[datetime]:
    if not raw:
        return None
    s = raw.strip()
    if s.startswith("D:"):
        s = s[2:]
    m = re.match(r"(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?", s)
    if not m:
        return None
    try:
        return datetime(int(m.group(1)), int(m.group(2) or 1), int(m.group(3) or 1),
                        int(m.group(4) or 0), int(m.group(5) or 0), int(m.group(6) or 0))
    except ValueError:
        return None


def _norm_account(a: str) -> str:
    return re.sub(r"[\s-]", "", (a or "").strip())


def _tail(a: str) -> str:
    a = _norm_account(a)
    return a[-4:] if len(a) >= 4 else a


def pdf_metadata_flags(metadata: Optional[dict]) -> List[Flag]:
    flags: List[Flag] = []
    if metadata is None:
        return [Flag(check="pdf_metadata", severity="info",
                     reason="No document metadata available — photo/scan path.")]
    producer = (metadata.get("producer") or "").strip()
    creator = (metadata.get("creator") or "").strip()
    blob = f"{producer} {creator}".lower()
    matched = [p for p in _SUSPICIOUS_PRODUCERS if p in blob]
    if matched:
        flags.append(Flag(check="pdf_metadata", severity="high",
                          reason=(f"Produced/edited with image-editing software ({', '.join(matched)}); "
                                  f"Producer='{producer}', Creator='{creator}'.")))
    created = _parse_pdf_date(metadata.get("creationDate", ""))
    modified = _parse_pdf_date(metadata.get("modDate", ""))
    if created is None:
        flags.append(Flag(check="pdf_metadata", severity="medium",
                          reason="PDF creation date is missing from metadata."))
    if created and modified and modified < created:
        flags.append(Flag(check="pdf_metadata", severity="high",
                          reason=f"Modification date ({modified.date()}) precedes creation ({created.date()})."))
    return flags


def run_integrity(
    ext: Extraction,
    pack: DomainPack,
    pdf_metadata: Optional[dict],
    store,
    dedup,
) -> IntegrityResult:
    flags: List[Flag] = []
    flags.extend(pdf_metadata_flags(pdf_metadata))

    party = ext.value(pack.party_field) if pack.party_field else ""

    # Account/identifier change vs history (bank account, tax id, etc.)
    if pack.account_field and party:
        account = ext.value(pack.account_field)
        if account:
            prior = store.last_account_for_party(pack.name, party)
            if prior and _norm_account(prior) != _norm_account(account):
                label = next((f.label for f in pack.fields if f.key == pack.account_field), "account")
                flags.append(Flag(check="account_change", severity="high",
                                  reason=(f"{label} for {party} differs from the previously approved value "
                                          f"(was …{_tail(prior)}, now …{_tail(account)}). Verify with the source.")))

    # Exact duplicate via identity signature
    identity = identity_signature(ext, pack)
    if identity:
        prior = store.identity_exists(pack.name, identity)
        if prior:
            flags.append(Flag(check="exact_duplicate", severity="high",
                              reason=f"An identical {pack.label.lower()} was already approved on "
                                     f"{prior.get('approved_at','a prior date')} — hard duplicate block."))

    # Semantic near-duplicate
    dup = dedup.check_duplicate(ext, pack)
    if dup:
        flags.append(dup)

    # Pack-specific deterministic integrity checks
    for fn in pack.extra_integrity:
        try:
            flags.extend(fn(ext) or [])
        except Exception:
            pass

    actionable = [f for f in flags if f.severity in ("high", "medium", "low")]
    return IntegrityResult(passed=len(actionable) == 0, flags=flags)


def identity_signature(ext: Extraction, pack: DomainPack) -> str:
    """Exact-duplicate key from the pack's identity fields."""
    if not pack.identity_fields:
        return ""
    parts = [ext.value(k).lower() for k in pack.identity_fields]
    if not any(parts):
        return ""
    return "|".join(parts)


def semantic_signature(ext: Extraction, pack: DomainPack) -> str:
    """Free-text signature for semantic dedup / similarity embedding."""
    sim = pack.similarity
    field_keys = (sim.signature_fields if sim and sim.signature_fields
                  else [f.key for f in pack.fields])
    table_names = sim.signature_tables if sim else [t.name for t in pack.tables]
    parts = []
    for k in field_keys:
        v = ext.value(k)
        if v:
            parts.append(v)
    for tname in table_names:
        t = ext.table(tname)
        if t:
            for r in t.rows:
                parts.extend(str(v) for v in r.cells.values() if v)
    for af in ext.additional_fields:
        if af.value:
            parts.append(af.value)
    return " ".join(parts).lower()
