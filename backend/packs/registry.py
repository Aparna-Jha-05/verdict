"""Registry: look up packs by name, list them for the UI, and heuristically
detect a domain from text (used as a fallback for auto-detect)."""

from __future__ import annotations

from typing import List

from schema import DomainInfo

from .base import DomainPack
from .library import ALL_PACKS, GENERIC

REGISTRY = {p.name: p for p in ALL_PACKS}


def get_pack(name: str) -> DomainPack:
    """Return the named pack, or the generic fallback for unknown names."""
    if not name or name in ("auto", "generic"):
        return REGISTRY.get(name, GENERIC) if name in REGISTRY else GENERIC
    return REGISTRY.get(name, GENERIC)


def all_domains() -> List[DomainInfo]:
    infos = []
    for p in ALL_PACKS:
        infos.append(
            DomainInfo(
                name=p.name,
                label=p.label,
                description=p.description,
                icon=p.icon,
                needs_second_input=p.needs_second_input,
                second_input_label=(p.similarity.second_input_label if p.similarity else ""),
                integrity_label=p.integrity_label,
            )
        )
    return infos


def detect_domain(text: str) -> str:
    """Score a document's raw text against each pack's hints. Fallback only —
    the primary path asks the vision model to classify (see extract.classify)."""
    t = (text or "").lower()
    best, best_score = "generic", 0
    for p in ALL_PACKS:
        score = sum(1 for h in p.detect_hints if h in t)
        if score > best_score:
            best, best_score = p.name, score
    return best if best_score > 0 else "generic"
