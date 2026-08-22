"""Ingestion: unify every upload to a page image before extraction.

PDF  -> rasterize page 1 with PyMuPDF (fitz) at ~180 DPI, and read the PDF
        metadata dict for the fraud layer.
Image-> pass through untouched (the phone-photo / scan path).

Returns a dict the rest of the pipeline consumes; extra PDF pages are rendered
and kept available but only page 1 drives extraction for this MVP.
"""

from __future__ import annotations

import base64
import io
from typing import Optional, TypedDict

from PIL import Image

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover - surfaced clearly at runtime
    fitz = None

# 180 DPI: legible for the VLM without ballooning the base64 payload.
_RENDER_DPI = 180
_MAX_EDGE = 2200  # cap the long edge so huge phone photos don't blow up tokens


class IngestResult(TypedDict):
    page_image_bytes: bytes
    page_image_b64: str
    source_type: str  # "pdf" | "image"
    pdf_metadata: Optional[dict]
    extra_pages_b64: list  # additional PDF pages, if any


def _png_b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _downscale_png(data: bytes) -> bytes:
    """Cap the long edge; re-encode as PNG. No-op if already small."""
    try:
        img = Image.open(io.BytesIO(data))
    except Exception:
        return data
    img = img.convert("RGB") if img.mode not in ("RGB", "L") else img
    w, h = img.size
    longest = max(w, h)
    if longest > _MAX_EDGE:
        scale = _MAX_EDGE / longest
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def _render_pdf(data: bytes) -> tuple[bytes, list, dict]:
    if fitz is None:
        raise RuntimeError("PyMuPDF (fitz) is not installed; cannot rasterize PDF.")
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        metadata = dict(doc.metadata or {})
        zoom = _RENDER_DPI / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        pages_png: list[bytes] = []
        for page in doc:
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            pages_png.append(pix.tobytes("png"))
        if not pages_png:
            raise RuntimeError("PDF has no renderable pages.")
        return pages_png[0], pages_png[1:], metadata
    finally:
        doc.close()


def ingest(file_bytes: bytes, filename: str, content_type: str = "") -> IngestResult:
    """Normalize an upload to a page image (+ PDF metadata when applicable)."""
    name = (filename or "").lower()
    ctype = (content_type or "").lower()

    is_pdf = name.endswith(".pdf") or "pdf" in ctype or file_bytes[:5] == b"%PDF-"

    if is_pdf:
        page1, extra, metadata = _render_pdf(file_bytes)
        page1 = _downscale_png(page1)
        return IngestResult(
            page_image_bytes=page1,
            page_image_b64=_png_b64(page1),
            source_type="pdf",
            pdf_metadata=metadata,
            extra_pages_b64=[_png_b64(_downscale_png(p)) for p in extra],
        )

    # Image path: normalize to PNG for a consistent downstream contract.
    png = _downscale_png(file_bytes)
    return IngestResult(
        page_image_bytes=png,
        page_image_b64=_png_b64(png),
        source_type="image",
        pdf_metadata=None,
        extra_pages_b64=[],
    )
