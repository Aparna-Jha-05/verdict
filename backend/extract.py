"""Vision-first extraction, domain-parameterized.

The prompt and output schema are built from whichever DomainPack is active, so
one code path serves every document type. Parsing is defensive and always fills
`additional_fields` — anything the model sees that isn't in the pack schema is
captured, never dropped (the "new fields we've never seen" guarantee).
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional

import httpx

from packs.base import DomainPack
from schema import ExtractedField, ExtractedTable, Extraction, TableRow

# ---- Provider selection: OpenRouter direct (preferred) or AI Pipe ----
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY")
if OPENROUTER_KEY:
    _DEFAULT_BASE = "https://openrouter.ai"
    _DEFAULT_ROUTE = "/api/v1/chat/completions"
    _API_KEY = OPENROUTER_KEY
else:
    _DEFAULT_BASE = "https://aipipe.org"
    _DEFAULT_ROUTE = "/openrouter/v1/chat/completions"
    _API_KEY = os.environ.get("AIPIPE_TOKEN")

AIPIPE_BASE = os.environ.get("AIPIPE_BASE", _DEFAULT_BASE).rstrip("/")
CHAT_ROUTE = os.environ.get("AIPIPE_CHAT_ROUTE", _DEFAULT_ROUTE)
DEFAULT_MODEL = os.environ.get("AIPIPE_VISION_MODEL", "openai/gpt-4o-mini")
ESCALATION_MODEL = os.environ.get("AIPIPE_ESCALATION_MODEL", "openai/gpt-4o")
_TIMEOUT = float(os.environ.get("AIPIPE_TIMEOUT", "90"))


class ExtractionError(Exception):
    pass


def _token() -> str:
    if not _API_KEY:
        raise ExtractionError(
            "No LLM API key set. Set OPENROUTER_API_KEY (OpenRouter) or AIPIPE_TOKEN (AI Pipe)."
        )
    return _API_KEY


def _schema_hint(pack: DomainPack) -> str:
    fields = {
        f.key: {"value": "", "confidence": "high|medium|low", "source": "", "bbox": [0, 0, 0, 0]}
        for f in pack.fields
    }
    tables = {}
    for t in pack.tables:
        row = {c.name: "" for c in t.columns}
        row["bbox"] = [0, 0, 0, 0]
        row["confidence"] = "high|medium|low"
        tables[t.name] = [row]
    template = {
        "fields": fields,
        "tables": tables,
        "additional_fields": [
            {"label": "", "value": "", "confidence": "high|medium|low", "bbox": [0, 0, 0, 0]}
        ],
        "overall_confidence": "high|medium|low",
    }
    return json.dumps(template, indent=2)


def _system_prompt(pack: DomainPack) -> str:
    return (
        f"You are a document extraction engine. The image is a single page of a "
        f"{pack.label} ({pack.description}). Read it directly from the image. Return "
        f"ONLY a valid JSON object matching the schema below — no prose, no code fences.\n\n"
        "For every scalar field return value, confidence (high|medium|low), source (the raw "
        "text as seen), and bbox (normalized [x0,y0,x1,y1], 0..1, top-left origin; approximate "
        "but always returned). Dates as YYYY-MM-DD. Numbers as plain numbers.\n\n"
        "IMPORTANT: any meaningful field you see on the document that is NOT in the schema must "
        "be added to 'additional_fields' with a short label — never discard information.\n\n"
        "SCHEMA:\n" + _schema_hint(pack)
    )


def _recover_json(text: str) -> dict:
    if not text:
        raise ExtractionError("Empty model response.")
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    start = text.find("{")
    if start == -1:
        raise ExtractionError("No JSON object found in model response.")
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError as e:
                    raise ExtractionError(f"Malformed JSON: {e}") from e
    raise ExtractionError("Unbalanced JSON object in model response.")


def _call(image_b64: str, model: str, system: str, user: str) -> str:
    payload = {
        "model": model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                ],
            },
        ],
    }
    headers = {"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"}
    if OPENROUTER_KEY:
        headers["HTTP-Referer"] = os.environ.get("OPENROUTER_REFERER", "https://verdict-three-ashen.vercel.app")
        headers["X-Title"] = "Verdict Document Intelligence"
    url = f"{AIPIPE_BASE}{CHAT_ROUTE}"
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(url, json=payload, headers=headers)
    except httpx.HTTPError as e:
        raise ExtractionError(f"AI Pipe request failed: {e}") from e
    if resp.status_code >= 400:
        raise ExtractionError(f"AI Pipe returned {resp.status_code}: {resp.text[:300]}")
    try:
        return resp.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as e:
        raise ExtractionError(f"Unexpected AI Pipe response shape: {e}") from e


def _parse(obj: dict, pack: DomainPack) -> Extraction:
    field_specs = {f.key: f for f in pack.fields}
    table_specs = {t.name: t for t in pack.tables}

    fields = []
    raw_fields = obj.get("fields") or {}
    extras = list(obj.get("additional_fields") or [])
    for key, spec in field_specs.items():
        cell = raw_fields.get(key) or {}
        if not isinstance(cell, dict):
            cell = {"value": cell}
        fields.append(ExtractedField(
            key=key, label=spec.label, type=spec.type,
            value=cell.get("value", ""), confidence=cell.get("confidence", "low"),
            source=cell.get("source", ""), bbox=cell.get("bbox", [0, 0, 0, 0]),
        ))
    # Any model-returned field keys not in the schema become additional_fields.
    for key, cell in raw_fields.items():
        if key not in field_specs and isinstance(cell, dict) and cell.get("value"):
            extras.append({"label": key, "value": cell.get("value"),
                           "confidence": cell.get("confidence", "low"), "bbox": cell.get("bbox", [0, 0, 0, 0])})

    tables = []
    raw_tables = obj.get("tables") or {}
    for name, spec in table_specs.items():
        rows_in = raw_tables.get(name) or []
        rows = []
        cols = [c.name for c in spec.columns]
        for r in rows_in:
            if not isinstance(r, dict):
                continue
            cells = {c: str(r.get(c, "")) for c in cols}
            rows.append(TableRow(cells=cells, bbox=r.get("bbox", [0, 0, 0, 0]),
                                 confidence=r.get("confidence", "low")))
        tables.append(ExtractedTable(name=name, label=spec.label, columns=cols, rows=rows))

    additional = []
    for e in extras:
        if isinstance(e, dict) and e.get("value"):
            additional.append(ExtractedField(
                key="extra:" + str(e.get("label", "")).strip().lower().replace(" ", "_"),
                label=str(e.get("label", "")), value=e.get("value", ""),
                confidence=e.get("confidence", "low"), bbox=e.get("bbox", [0, 0, 0, 0]),
            ))

    return Extraction(
        domain=pack.name, fields=fields, tables=tables, additional_fields=additional,
        overall_confidence=obj.get("overall_confidence", "low"),
    )


def extract(image_b64: str, pack: DomainPack, model: Optional[str] = None) -> Extraction:
    model = model or DEFAULT_MODEL
    raw = _call(image_b64, model, _system_prompt(pack), f"Extract this {pack.label} into the schema JSON.")
    return _parse(_recover_json(raw), pack)


def classify(image_b64: str, candidates: list[str]) -> str:
    """Ask the cheap model which domain this document is. Returns a pack name."""
    system = (
        "You classify a document image into exactly one category. Reply with ONLY the "
        "category name, nothing else. Categories: " + ", ".join(candidates) + "."
    )
    try:
        raw = _call(image_b64, DEFAULT_MODEL, system, "Which category is this document?")
    except ExtractionError:
        return "generic"
    guess = re.sub(r"[^a-z_]", "", (raw or "").strip().lower().replace(" ", "_"))
    for c in candidates:
        if c in guess:
            return c
    return "generic"


def embed_text(text: str) -> Optional[list]:
    """Local embedding for similarity (resume↔JD). Returns None if unavailable."""
    from dedup import embed  # lazy: heavy deps guarded there
    return embed(text)
