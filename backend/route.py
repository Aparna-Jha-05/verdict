"""Escalation / routing — "intelligent inference layering".

Cheap vision model by default; escalate to a stronger model only on failure:
low overall confidence, a JSON parse/validation failure at extraction time, or a
validation rule that looks like an extraction error rather than a document defect.

Escalation fixes *extraction* mistakes. It does NOT fix *document* problems — a
genuinely wrong total or a changed bank account must still fail after escalation.
Fraud + dedup always run once, after extraction has settled.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from extract import DEFAULT_MODEL, ESCALATION_MODEL, ExtractionError, extract
from fraud import run_fraud_checks
from schema import Extraction, FraudResult, ValidationResult
from validate import validate

# Validation rules whose failure suggests the model misread the page (worth a
# stronger model), versus rules that indicate a real document defect (don't
# escalate — the answer won't change and we'd just burn tokens).
_EXTRACTION_ERROR_RULES = {
    "Required fields present",
    "Currency present",
    "Line-item math",
}


@dataclass
class RouteResult:
    extraction: Extraction
    validation: ValidationResult
    fraud: FraudResult
    model_used: str
    escalated: bool
    error: Optional[str] = None


def _should_escalate(
    extraction: Optional[Extraction],
    validation: Optional[ValidationResult],
    parse_failed: bool,
) -> bool:
    if parse_failed:
        return True
    if extraction is not None and extraction.overall_confidence == "low":
        return True
    if validation is not None and not validation.passed:
        failed_rules = {c.rule for c in validation.checks if not c.passed}
        if failed_rules & _EXTRACTION_ERROR_RULES:
            return True
    return False


def process(image_b64: str, pdf_metadata: Optional[dict]) -> RouteResult:
    """Run the full extract -> validate -> (escalate?) -> fraud pipeline."""
    model_used = DEFAULT_MODEL
    escalated = False
    parse_failed = False
    extraction: Optional[Extraction] = None
    validation: Optional[ValidationResult] = None

    # --- First pass: default model ---
    try:
        extraction = extract(image_b64, model=DEFAULT_MODEL)
        validation = validate(extraction)
    except ExtractionError:
        parse_failed = True

    # --- Escalation decision ---
    if _should_escalate(extraction, validation, parse_failed):
        try:
            extraction = extract(image_b64, model=ESCALATION_MODEL)
            validation = validate(extraction)
            model_used = ESCALATION_MODEL
            escalated = True
            parse_failed = False
        except ExtractionError as e:
            # Escalation itself failed. If the first pass also failed, surface a
            # clean error; otherwise fall back to the first pass's result.
            if extraction is None or validation is None:
                return RouteResult(
                    extraction=Extraction(),
                    validation=ValidationResult(passed=False, checks=[]),
                    fraud=FraudResult(passed=False, flags=[]),
                    model_used=ESCALATION_MODEL,
                    escalated=True,
                    error=f"Both extraction passes failed: {e}",
                )

    if extraction is None or validation is None:
        return RouteResult(
            extraction=Extraction(),
            validation=ValidationResult(passed=False, checks=[]),
            fraud=FraudResult(passed=False, flags=[]),
            model_used=model_used,
            escalated=escalated,
            error="Extraction failed and could not be recovered.",
        )

    # --- Fraud + dedup always run once, after extraction is settled ---
    fraud = run_fraud_checks(extraction, pdf_metadata)

    return RouteResult(
        extraction=extraction,
        validation=validation,
        fraud=fraud,
        model_used=model_used,
        escalated=escalated,
    )
