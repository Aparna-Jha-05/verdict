"""Semantic near-duplicate detection — embeddings + Chroma. NO LLM.

A text signature is built from the key invoice fields, embedded locally with
all-MiniLM-L6-v2 (no API dependency), and compared against already-approved
invoices in a persistent Chroma collection. Catches resubmissions where only
the invoice number was altered — exact-match checks miss those, embeddings don't.

The heavy deps (sentence-transformers, chromadb) are imported lazily and guarded
so the rest of the backend still runs if they are unavailable in a given env.
"""

from __future__ import annotations

import os
from typing import Optional

from schema import Extraction, Flag, _to_float

_SIM_THRESHOLD = float(os.environ.get("DEDUP_SIM_THRESHOLD", "0.90"))
_CHROMA_DIR = os.environ.get(
    "CHROMA_DIR", os.path.join(os.path.dirname(__file__), "chroma_store")
)
_COLLECTION = "approved_invoices"

# Lazily-initialized singletons.
_model = None
_collection = None
_unavailable_reason: Optional[str] = None


def _ensure_backend():
    """Load the embedding model + Chroma collection once. Returns True on success."""
    global _model, _collection, _unavailable_reason
    if _collection is not None and _model is not None:
        return True
    if _unavailable_reason is not None:
        return False
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        import chromadb  # type: ignore

        _model = SentenceTransformer("all-MiniLM-L6-v2")
        client = chromadb.PersistentClient(path=_CHROMA_DIR)
        _collection = client.get_or_create_collection(
            name=_COLLECTION, metadata={"hnsw:space": "cosine"}
        )
        return True
    except Exception as e:  # missing deps, download failure, etc.
        _unavailable_reason = str(e)
        return False


def build_signature(ext: Extraction) -> str:
    """Order-insensitive text signature from the fields that define an invoice."""
    descs = sorted(
        (li.description or "").strip().lower() for li in ext.line_items if li.description
    )
    total = _to_float(ext.total.value)
    parts = [
        f"vendor:{ext.vendor_name.value.strip().lower()}",
        f"total:{total if total is not None else ''}",
        f"date:{ext.invoice_date.value.strip()}",
        f"items:{'|'.join(descs)}",
    ]
    return " ".join(parts)


def _embed(text: str):
    return _model.encode([text], normalize_embeddings=True)[0].tolist()


def check_duplicate(ext: Extraction) -> Optional[Flag]:
    """Return a Flag if this invoice is a semantic near-duplicate of an approved one."""
    invoice_number = ext.invoice_number.value.strip()
    if not _ensure_backend():
        return Flag(
            check="semantic_duplicate",
            severity="info",
            reason=(
                "Semantic dedup unavailable in this environment "
                f"({_unavailable_reason}); relying on exact invoice-number check only."
            ),
        )
    sig = build_signature(ext)
    try:
        res = _collection.query(query_embeddings=[_embed(sig)], n_results=3)
    except Exception as e:
        return Flag(
            check="semantic_duplicate",
            severity="info",
            reason=f"Dedup query failed: {e}",
        )

    ids = (res.get("ids") or [[]])[0]
    distances = (res.get("distances") or [[]])[0]
    metadatas = (res.get("metadatas") or [[]])[0]

    for _id, dist, meta in zip(ids, distances, metadatas):
        # Chroma cosine "distance" = 1 - cosine_similarity.
        similarity = 1.0 - float(dist)
        if similarity >= _SIM_THRESHOLD:
            prior_num = str((meta or {}).get("invoice_number", "")).strip()
            if prior_num and prior_num == invoice_number:
                continue  # same number handled by the exact-match hard block
            return Flag(
                check="semantic_duplicate",
                severity="high",
                reason=(
                    f"Near-duplicate (similarity {similarity:.2f}) of previously "
                    f"approved invoice {prior_num or _id}; possible resubmission "
                    "with an altered invoice number."
                ),
            )
    return None


def add_to_index(ext: Extraction, ledger_id: int) -> None:
    """Register an approved invoice's embedding so future dedup can see it."""
    if not _ensure_backend():
        return
    sig = build_signature(ext)
    try:
        _collection.upsert(
            ids=[f"ledger-{ledger_id}"],
            embeddings=[_embed(sig)],
            metadatas=[
                {
                    "invoice_number": ext.invoice_number.value.strip(),
                    "vendor_name": ext.vendor_name.value.strip(),
                    "ledger_id": ledger_id,
                }
            ],
            documents=[sig],
        )
    except Exception:
        # Indexing is best-effort; never break approval on a vector-store hiccup.
        pass
