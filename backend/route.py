"""Escalation/routing + similarity, domain-parameterized.

Cheap model by default; escalate to a stronger model on parse failure, low
confidence, or missing required fields (an extraction-type error). Validation and
integrity run through the generic deterministic engine. Similarity (e.g. résumé↔JD)
is a deterministic cosine over local embeddings — the model never scores the match.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import dedup
import store
from extract import DEFAULT_MODEL, ESCALATION_MODEL, ExtractionError, extract
from packs.base import DomainPack, run_integrity, run_validation, semantic_signature
from schema import (
    Extraction,
    IntegrityResult,
    SimilarityResult,
    ValidationResult,
)


@dataclass
class RouteResult:
    extraction: Extraction
    validation: ValidationResult
    integrity: IntegrityResult
    similarity: Optional[SimilarityResult]
    model_used: str
    escalated: bool
    error: Optional[str] = None


def _should_escalate(ext: Optional[Extraction], val: Optional[ValidationResult], parse_failed: bool) -> bool:
    if parse_failed:
        return True
    if ext is not None and ext.overall_confidence == "low":
        return True
    if val is not None:
        for c in val.checks:
            if c.rule == "Required fields present" and not c.passed:
                return True
    return False


def _similarity(ext: Extraction, pack: DomainPack, second_input: Optional[str]) -> Optional[SimilarityResult]:
    if not pack.similarity or not second_input or not second_input.strip():
        return None
    spec = pack.similarity
    cand = semantic_signature(ext, pack)
    a = dedup.embed(cand)
    b = dedup.embed(second_input)
    if a is not None and b is not None:
        score = max(0.0, min(1.0, dedup.cosine(a, b)))
        strong, moderate, method = spec.strong, spec.moderate, "semantic embeddings"
    else:
        # Free-tier fallback: pure-Python lexical cosine (term overlap).
        score = dedup.lexical_cosine(cand, second_input)
        strong, moderate, method = 0.40, 0.22, "keyword overlap"
    if score >= strong:
        verdict = "Strong match"
    elif score >= moderate:
        verdict = "Moderate match"
    else:
        verdict = "Weak match"
    return SimilarityResult(score=round(score, 3), label=spec.label, verdict=verdict,
                            detail=f"{score:.0%} similarity to the {spec.second_input_label.lower()} (via {method}).")


def process(image_b64: str, pack: DomainPack, pdf_metadata: Optional[dict],
            second_input: Optional[str] = None) -> RouteResult:
    model_used = DEFAULT_MODEL
    escalated = False
    parse_failed = False
    ext: Optional[Extraction] = None
    val: Optional[ValidationResult] = None

    try:
        ext = extract(image_b64, pack, model=DEFAULT_MODEL)
        val = run_validation(ext, pack)
    except ExtractionError:
        parse_failed = True

    if _should_escalate(ext, val, parse_failed):
        try:
            ext = extract(image_b64, pack, model=ESCALATION_MODEL)
            val = run_validation(ext, pack)
            model_used = ESCALATION_MODEL
            escalated = True
            parse_failed = False
        except ExtractionError as e:
            if ext is None or val is None:
                return RouteResult(
                    extraction=Extraction(domain=pack.name),
                    validation=ValidationResult(passed=False, checks=[]),
                    integrity=IntegrityResult(passed=False, flags=[]),
                    similarity=None, model_used=ESCALATION_MODEL, escalated=True,
                    error=f"Both extraction passes failed: {e}",
                )

    if ext is None or val is None:
        return RouteResult(
            extraction=Extraction(domain=pack.name),
            validation=ValidationResult(passed=False, checks=[]),
            integrity=IntegrityResult(passed=False, flags=[]),
            similarity=None, model_used=model_used, escalated=escalated,
            error="Extraction failed and could not be recovered.",
        )

    integrity = run_integrity(ext, pack, pdf_metadata, store, dedup)
    similarity = _similarity(ext, pack, second_input)

    return RouteResult(extraction=ext, validation=val, integrity=integrity,
                       similarity=similarity, model_used=model_used, escalated=escalated)
