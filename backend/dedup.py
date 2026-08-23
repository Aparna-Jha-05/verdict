"""Local embeddings + Chroma for semantic near-duplicates and similarity.

Domain-agnostic: the signature is built from whichever pack is active. Heavy deps
(sentence-transformers, chromadb) are imported lazily and guarded so the rest of
the backend runs without them (only semantic features degrade). NO LLM here.
"""

from __future__ import annotations

import os
from typing import Optional

from packs.base import DomainPack, identity_signature, semantic_signature
from schema import Extraction, Flag

_SIM_THRESHOLD = float(os.environ.get("DEDUP_SIM_THRESHOLD", "0.90"))
_CHROMA_DIR = os.environ.get("CHROMA_DIR", os.path.join(os.path.dirname(__file__), "chroma_store"))
_COLLECTION = "documents"

_model = None
_collection = None
_unavailable: Optional[str] = None


def _ensure():
    global _model, _collection, _unavailable
    if _model is not None and _collection is not None:
        return True
    if _unavailable is not None:
        return False
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        import chromadb  # type: ignore

        _model = SentenceTransformer("all-MiniLM-L6-v2")
        client = chromadb.PersistentClient(path=_CHROMA_DIR)
        _collection = client.get_or_create_collection(name=_COLLECTION, metadata={"hnsw:space": "cosine"})
        return True
    except Exception as e:
        _unavailable = str(e)
        return False


def embed(text: str) -> Optional[list]:
    """Normalized embedding vector, or None if the model isn't available."""
    if not text or not _ensure():
        return None
    return _model.encode([text], normalize_embeddings=True)[0].tolist()


def cosine(a: list, b: list) -> float:
    return sum(x * y for x, y in zip(a, b))  # both normalized


# Pure-Python lexical fallback (no deps) so similarity works on the free tier
# even without the embedding model. Deterministic term-frequency cosine.
import math
import re
from collections import Counter

_STOP = {"the", "a", "an", "and", "or", "of", "to", "in", "for", "with", "on",
         "you", "we", "our", "will", "is", "are", "be", "as", "at", "by"}


def _tokens(s: str) -> list:
    return [t for t in re.findall(r"[a-z0-9+#.]+", (s or "").lower()) if t not in _STOP and len(t) > 1]


def lexical_cosine(a: str, b: str) -> float:
    ca, cb = Counter(_tokens(a)), Counter(_tokens(b))
    if not ca or not cb:
        return 0.0
    common = set(ca) & set(cb)
    dot = sum(ca[t] * cb[t] for t in common)
    na = math.sqrt(sum(v * v for v in ca.values()))
    nb = math.sqrt(sum(v * v for v in cb.values()))
    return dot / (na * nb) if na and nb else 0.0


def check_duplicate(ext: Extraction, pack: DomainPack) -> Optional[Flag]:
    if not _ensure():
        return Flag(check="semantic_duplicate", severity="info",
                    reason=f"Semantic dedup unavailable in this environment ({_unavailable}); "
                           "relying on exact-identity check only.")
    sig = semantic_signature(ext, pack)
    if not sig.strip():
        return None
    vec = embed(sig)
    if vec is None:
        return None
    try:
        res = _collection.query(query_embeddings=[vec], n_results=3, where={"domain": pack.name})
    except Exception as e:
        return Flag(check="semantic_duplicate", severity="info", reason=f"Dedup query failed: {e}")

    ids = (res.get("ids") or [[]])[0]
    distances = (res.get("distances") or [[]])[0]
    metadatas = (res.get("metadatas") or [[]])[0]
    my_identity = identity_signature(ext, pack)

    for _id, dist, meta in zip(ids, distances, metadatas):
        similarity = 1.0 - float(dist)
        if similarity >= _SIM_THRESHOLD:
            prior_identity = str((meta or {}).get("identity", "")).strip()
            if my_identity and prior_identity and my_identity == prior_identity:
                continue  # same identity -> exact-duplicate path handles it
            ref = str((meta or {}).get("ref", _id))
            return Flag(check="semantic_duplicate", severity="high",
                        reason=(f"Near-duplicate (similarity {similarity:.2f}) of previously approved "
                                f"{pack.label.lower()} {ref}; possible resubmission with altered details."))
    return None


def add_to_index(ext: Extraction, pack: DomainPack, ledger_id: int) -> None:
    if not _ensure():
        return
    sig = semantic_signature(ext, pack)
    vec = embed(sig)
    if vec is None:
        return
    ref = ext.value(pack.identity_fields[0]) if pack.identity_fields else str(ledger_id)
    try:
        _collection.upsert(
            ids=[f"{pack.name}-{ledger_id}"],
            embeddings=[vec],
            metadatas=[{"domain": pack.name, "identity": identity_signature(ext, pack), "ref": ref, "ledger_id": ledger_id}],
            documents=[sig],
        )
    except Exception:
        pass
