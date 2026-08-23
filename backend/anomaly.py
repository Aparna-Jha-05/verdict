"""Unsupervised anomaly scoring over historical records (no LLM).

A robust outlier detector on the headline amount: it compares this document's
amount against the distribution of previously approved amounts (for the same
party when we have enough history, else the whole domain) using a median/MAD
robust z-score — resistant to the small, skewed samples real ledgers start with.

Output is a SIGNAL for the human ("this is unusually large vs history"), never an
auto-decision. As more documents are approved, the baseline sharpens.
"""

from __future__ import annotations

import math
from typing import Optional

from packs.base import DomainPack
from schema import AnomalyResult, Extraction

_MIN_SAMPLES = 3


def _median(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def _robust_z(x: float, hist: list[float]) -> Optional[float]:
    """Median/MAD z-score. Falls back to std if MAD is zero."""
    if len(hist) < _MIN_SAMPLES:
        return None
    med = _median(hist)
    mad = _median([abs(h - med) for h in hist])
    if mad > 1e-9:
        return 0.6745 * (x - med) / mad  # 0.6745 makes MAD ~ std for normal data
    mean = sum(hist) / len(hist)
    var = sum((h - mean) ** 2 for h in hist) / len(hist)
    std = math.sqrt(var)
    if std < 1e-9:
        return 0.0
    return (x - mean) / std


def score(ext: Extraction, pack: DomainPack, store) -> Optional[AnomalyResult]:
    if not pack.amount_field:
        return None
    amount = ext.number(pack.amount_field)
    if amount is None:
        return None

    party = ext.value(pack.party_field) if pack.party_field else ""
    party_hist = store.amounts(pack.name, party) if party else []
    domain_hist = store.amounts(pack.name)

    scope = "this party's history"
    hist = party_hist
    if len(hist) < _MIN_SAMPLES:
        hist = domain_hist
        scope = f"all {pack.label.lower()} history"

    z = _robust_z(amount, hist)
    features = [{"name": f"{pack.label} amount", "detail": f"{amount:,.2f}"}]

    if z is None:
        return AnomalyResult(
            score=0.0, level="learning",
            reason=(f"Only {len(domain_hist)} prior {pack.label.lower()}(s) on record — "
                    "the anomaly baseline sharpens as more are approved."),
            features=features,
        )

    az = abs(z)
    # Map |z| to a 0..1 score via a smooth logistic centered near z≈3.
    anomaly_score = 1.0 / (1.0 + math.exp(-(az - 3.0)))
    features.append({"name": "Robust z-score", "detail": f"{z:+.1f} vs {scope}"})
    features.append({"name": "Baseline", "detail": f"median {_median(hist):,.0f} over {len(hist)} records"})

    if az >= 3.5:
        level, reason = "high", (f"Amount {amount:,.2f} is a strong outlier ({z:+.1f}σ) versus {scope}. "
                                 "Recommend a closer look before approval.")
    elif az >= 2.0:
        level, reason = "elevated", (f"Amount {amount:,.2f} is somewhat unusual ({z:+.1f}σ) versus {scope}.")
    else:
        level, reason = "normal", (f"Amount {amount:,.2f} is in the normal range ({z:+.1f}σ) versus {scope}.")

    return AnomalyResult(score=round(anomaly_score, 3), level=level, reason=reason, features=features)
