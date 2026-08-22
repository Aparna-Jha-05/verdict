"""Extraction: vision-first. Send the page image to an AI Pipe vision model and
get schema-constrained JSON with per-field value/confidence/source/bbox.

No OCR. The image goes straight to the VLM. Parsing is defensive: models wrap
JSON in prose or fences, so we recover the JSON object before pydantic sees it.
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional

import httpx

from schema import EXTRACTION_SCHEMA_HINT, Extraction

AIPIPE_BASE = os.environ.get("AIPIPE_BASE", "https://aipipe.org").rstrip("/")
# OpenAI-compatible chat-completions route via AI Pipe's OpenRouter passthrough.
CHAT_ROUTE = os.environ.get("AIPIPE_CHAT_ROUTE", "/openrouter/v1/chat/completions")

# Defaults are overridable via env so the live AI Pipe model list can be honored
# without a code change (see spec §13).
DEFAULT_MODEL = os.environ.get("AIPIPE_VISION_MODEL", "openai/gpt-4o-mini")
ESCALATION_MODEL = os.environ.get("AIPIPE_ESCALATION_MODEL", "openai/gpt-4o")

_TIMEOUT = float(os.environ.get("AIPIPE_TIMEOUT", "90"))

SYSTEM_PROMPT = (
    "You are an invoice extraction engine. You are given an image of a single "
    "invoice page. Read it directly from the image (do not assume OCR text is "
    "provided). Return ONLY a valid JSON object matching the schema below. No "
    "prose, no markdown, no code fences.\n\n"
    "For every scalar field return: value, confidence (high|medium|low), source "
    "(the raw text exactly as it appears on the document), and bbox (normalized "
    "[x0,y0,x1,y1], each between 0 and 1, top-left origin). Bounding boxes are "
    "approximate but must still be returned; if you truly cannot locate a field, "
    "use [0,0,0,0] and still fill value/source. Dates as YYYY-MM-DD. Numbers as "
    "plain numbers (no currency symbols) for subtotal/tax/total and line items. "
    "Set overall_confidence to your honest overall read quality.\n\n"
    "SCHEMA:\n" + EXTRACTION_SCHEMA_HINT
)


class ExtractionError(Exception):
    """Raised when the model call fails or JSON cannot be recovered/validated."""


def _token() -> str:
    tok = os.environ.get("AIPIPE_TOKEN")
    if not tok:
        raise ExtractionError("AIPIPE_TOKEN is not set in the environment.")
    return tok


def _recover_json(text: str) -> dict:
    """Pull the first balanced JSON object out of a possibly-noisy response."""
    if not text:
        raise ExtractionError("Empty model response.")
    # Strip code fences if present.
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    # Find the first '{' and balance braces to the matching '}'.
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
                candidate = text[start : i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError as e:
                    raise ExtractionError(f"Malformed JSON: {e}") from e
    raise ExtractionError("Unbalanced JSON object in model response.")


def _call_vision(image_b64: str, model: str) -> str:
    """One chat-completions call with a base64 image block. Returns raw content."""
    payload = {
        "model": model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract this invoice into the schema JSON.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}"
                        },
                    },
                ],
            },
        ],
    }
    headers = {
        "Authorization": f"Bearer {_token()}",
        "Content-Type": "application/json",
    }
    url = f"{AIPIPE_BASE}{CHAT_ROUTE}"
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(url, json=payload, headers=headers)
    except httpx.HTTPError as e:
        raise ExtractionError(f"AI Pipe request failed: {e}") from e
    if resp.status_code >= 400:
        raise ExtractionError(
            f"AI Pipe returned {resp.status_code}: {resp.text[:300]}"
        )
    try:
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as e:
        raise ExtractionError(f"Unexpected AI Pipe response shape: {e}") from e


def extract(image_b64: str, model: Optional[str] = None) -> Extraction:
    """Run one extraction pass. Raises ExtractionError on failure/parse error."""
    model = model or DEFAULT_MODEL
    raw = _call_vision(image_b64, model)
    obj = _recover_json(raw)
    try:
        return Extraction.model_validate(obj)
    except Exception as e:  # pydantic ValidationError and friends
        raise ExtractionError(f"Schema validation failed: {e}") from e
