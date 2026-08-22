"""Pydantic models + the extraction JSON schema.

Single source of truth for the shape the vision model must return and the shape
the deterministic layers consume. Kept lenient on parsing (models are messy) but
strict enough that downstream code can trust field names and types.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

Confidence = Literal["high", "medium", "low"]

# Normalized bbox: [x0, y0, x1, y1], each 0..1, top-left origin.
BBox = List[float]


def _default_bbox() -> BBox:
    return [0.0, 0.0, 0.0, 0.0]


class Field_(BaseModel):
    """A single extracted scalar field with provenance."""

    value: str = ""
    confidence: Confidence = "low"
    source: str = ""
    bbox: BBox = Field(default_factory=_default_bbox)

    @field_validator("value", mode="before")
    @classmethod
    def _coerce_value(cls, v):
        if v is None:
            return ""
        return str(v)

    @field_validator("confidence", mode="before")
    @classmethod
    def _coerce_conf(cls, v):
        if not v:
            return "low"
        v = str(v).lower().strip()
        return v if v in ("high", "medium", "low") else "low"

    @field_validator("bbox", mode="before")
    @classmethod
    def _coerce_bbox(cls, v):
        if not isinstance(v, (list, tuple)) or len(v) != 4:
            return _default_bbox()
        try:
            return [float(x) for x in v]
        except (TypeError, ValueError):
            return _default_bbox()


class NumberField(Field_):
    """Like Field_ but exposes a parsed float via .number."""

    @property
    def number(self) -> Optional[float]:
        return _to_float(self.value)


class LineItem(BaseModel):
    description: str = ""
    quantity: float = 0.0
    unit_price: float = 0.0
    amount: float = 0.0
    confidence: Confidence = "low"
    bbox: BBox = Field(default_factory=_default_bbox)

    @field_validator("quantity", "unit_price", "amount", mode="before")
    @classmethod
    def _coerce_num(cls, v):
        f = _to_float(v)
        return f if f is not None else 0.0

    @field_validator("confidence", mode="before")
    @classmethod
    def _coerce_conf(cls, v):
        if not v:
            return "low"
        v = str(v).lower().strip()
        return v if v in ("high", "medium", "low") else "low"

    @field_validator("bbox", mode="before")
    @classmethod
    def _coerce_bbox(cls, v):
        if not isinstance(v, (list, tuple)) or len(v) != 4:
            return _default_bbox()
        try:
            return [float(x) for x in v]
        except (TypeError, ValueError):
            return _default_bbox()


class Extraction(BaseModel):
    invoice_number: Field_ = Field(default_factory=Field_)
    invoice_date: Field_ = Field(default_factory=Field_)
    vendor_name: Field_ = Field(default_factory=Field_)
    vendor_bank_account: Field_ = Field(default_factory=Field_)
    currency: Field_ = Field(default_factory=Field_)
    line_items: List[LineItem] = Field(default_factory=list)
    subtotal: NumberField = Field(default_factory=NumberField)
    tax: NumberField = Field(default_factory=NumberField)
    total: NumberField = Field(default_factory=NumberField)
    overall_confidence: Confidence = "low"

    @field_validator("overall_confidence", mode="before")
    @classmethod
    def _coerce_conf(cls, v):
        if not v:
            return "low"
        v = str(v).lower().strip()
        return v if v in ("high", "medium", "low") else "low"


# ---------------------------------------------------------------------------
# Result envelopes for the deterministic layers + the /process response
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


class FraudResult(BaseModel):
    passed: bool  # True == no flags raised (still "flag for review", never "authentic")
    flags: List[Flag]


class ProcessResponse(BaseModel):
    extraction: Extraction
    validation: ValidationResult
    fraud: FraudResult
    model_used: str
    escalated: bool
    page_image_b64: str
    source_type: str


# ---------------------------------------------------------------------------
# The JSON schema string handed to the vision model (kept as a literal so the
# prompt and the pydantic model can't silently drift in intent).
# ---------------------------------------------------------------------------

EXTRACTION_SCHEMA_HINT = """{
  "invoice_number": {"value":"", "confidence":"high|medium|low", "source":"", "bbox":[0,0,0,0]},
  "invoice_date":   {"value":"YYYY-MM-DD", "confidence":"high|medium|low", "source":"", "bbox":[0,0,0,0]},
  "vendor_name":    {"value":"", "confidence":"high|medium|low", "source":"", "bbox":[0,0,0,0]},
  "vendor_bank_account": {"value":"", "confidence":"high|medium|low", "source":"", "bbox":[0,0,0,0]},
  "currency":       {"value":"", "confidence":"high|medium|low", "source":"", "bbox":[0,0,0,0]},
  "line_items": [
    {"description":"", "quantity":0, "unit_price":0.0, "amount":0.0, "confidence":"high|medium|low", "bbox":[0,0,0,0]}
  ],
  "subtotal": {"value":0.0, "confidence":"high|medium|low", "source":"", "bbox":[0,0,0,0]},
  "tax":      {"value":0.0, "confidence":"high|medium|low", "source":"", "bbox":[0,0,0,0]},
  "total":    {"value":0.0, "confidence":"high|medium|low", "source":"", "bbox":[0,0,0,0]},
  "overall_confidence": "high|medium|low"
}"""


# ---------------------------------------------------------------------------
# Shared numeric coercion — invoices carry "$1,234.56", "1.234,56", "(50.00)".
# ---------------------------------------------------------------------------

def _to_float(v) -> Optional[float]:
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
    # Strip currency symbols / letters / spaces, keep digits, separators, sign.
    cleaned = "".join(ch for ch in s if ch.isdigit() or ch in ".,-")
    if not cleaned:
        return None
    # Decide decimal separator: if both present, the last one is the decimal.
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        # Ambiguous: treat comma as decimal only if it looks like one (,dd)
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
