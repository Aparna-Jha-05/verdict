"""Generic, domain-agnostic extraction schema + result envelopes.

The platform reads ANY document type. A domain pack (see packs/) declares which
fields and tables to ask for; the model fills them in. Everything here is generic
so the same engine serves invoices, receipts, resumes, contracts, IDs, and more.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

Confidence = Literal["high", "medium", "low"]
BBox = List[float]  # [x0, y0, x1, y1], each 0..1, top-left origin


def _default_bbox() -> BBox:
    return [0.0, 0.0, 0.0, 0.0]


def _coerce_conf(v) -> Confidence:
    if not v:
        return "low"
    v = str(v).lower().strip()
    return v if v in ("high", "medium", "low") else "low"


def _coerce_bbox(v) -> BBox:
    if not isinstance(v, (list, tuple)) or len(v) != 4:
        return _default_bbox()
    try:
        return [float(x) for x in v]
    except (TypeError, ValueError):
        return _default_bbox()


class ExtractedField(BaseModel):
    """One extracted scalar with provenance. `key` is stable; `label` is display."""

    key: str
    label: str = ""
    value: str = ""
    confidence: Confidence = "low"
    source: str = ""
    bbox: BBox = Field(default_factory=_default_bbox)
    type: str = "text"  # text | number | date | currency | email | id
    group: str = ""  # optional UI grouping

    @field_validator("value", mode="before")
    @classmethod
    def _v(cls, v):
        return "" if v is None else str(v)

    @field_validator("confidence", mode="before")
    @classmethod
    def _c(cls, v):
        return _coerce_conf(v)

    @field_validator("bbox", mode="before")
    @classmethod
    def _b(cls, v):
        return _coerce_bbox(v)

    @property
    def number(self) -> Optional[float]:
        return to_float(self.value)


class TableRow(BaseModel):
    cells: Dict[str, str] = Field(default_factory=dict)
    bbox: BBox = Field(default_factory=_default_bbox)
    confidence: Confidence = "low"

    @field_validator("cells", mode="before")
    @classmethod
    def _cells(cls, v):
        if not isinstance(v, dict):
            return {}
        return {str(k): ("" if val is None else str(val)) for k, val in v.items()}

    @field_validator("bbox", mode="before")
    @classmethod
    def _b(cls, v):
        return _coerce_bbox(v)

    @field_validator("confidence", mode="before")
    @classmethod
    def _c(cls, v):
        return _coerce_conf(v)

    def num(self, col: str) -> Optional[float]:
        return to_float(self.cells.get(col))


class ExtractedTable(BaseModel):
    name: str
    label: str = ""
    columns: List[str] = Field(default_factory=list)
    rows: List[TableRow] = Field(default_factory=list)


class Extraction(BaseModel):
    domain: str = "generic"
    fields: List[ExtractedField] = Field(default_factory=list)
    tables: List[ExtractedTable] = Field(default_factory=list)
    additional_fields: List[ExtractedField] = Field(default_factory=list)
    overall_confidence: Confidence = "low"

    @field_validator("overall_confidence", mode="before")
    @classmethod
    def _c(cls, v):
        return _coerce_conf(v)

    # -- convenience accessors used by the deterministic engine --
    def get(self, key: str) -> Optional[ExtractedField]:
        for f in self.fields:
            if f.key == key:
                return f
        return None

    def value(self, key: str) -> str:
        f = self.get(key)
        return f.value.strip() if f else ""

    def number(self, key: str) -> Optional[float]:
        f = self.get(key)
        return f.number if f else None

    def table(self, name: str) -> Optional[ExtractedTable]:
        for t in self.tables:
            if t.name == name:
                return t
        return None


# ---------------------------------------------------------------------------
# Result envelopes
# ---------------------------------------------------------------------------

class Check(BaseModel):
    rule: str
    passed: bool
    reason: str


class ValidationResult(BaseModel):
    passed: bool
    checks: List[Check]


class Flag(BaseModel):
    check: str
    severity: Literal["high", "medium", "low", "info"]
    reason: str


class IntegrityResult(BaseModel):
    passed: bool
    flags: List[Flag]


class SimilarityResult(BaseModel):
    score: float  # 0..1
    label: str  # e.g. "Resume ↔ Job description match"
    verdict: str  # human-readable band, deterministic threshold
    detail: str = ""


class DomainInfo(BaseModel):
    name: str
    label: str
    description: str
    icon: str
    needs_second_input: bool = False
    second_input_label: str = ""
    integrity_label: str = "Integrity & Risk"


class ProcessResponse(BaseModel):
    domain: str
    domain_label: str
    integrity_label: str
    extraction: Extraction
    validation: ValidationResult
    integrity: IntegrityResult
    similarity: Optional[SimilarityResult] = None
    model_used: str
    escalated: bool
    page_image_b64: str
    source_type: str


# ---------------------------------------------------------------------------
# Shared numeric coercion — "$1,234.56", "1.234,56", "(50.00)"
# ---------------------------------------------------------------------------

def to_float(v) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return None
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1]
    cleaned = "".join(ch for ch in s if ch.isdigit() or ch in ".,-")
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts[-1]) == 2 and len(parts) == 2:
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    try:
        f = float(cleaned)
    except ValueError:
        return None
    return -f if negative else f


# Back-compat alias (older modules imported _to_float)
_to_float = to_float
