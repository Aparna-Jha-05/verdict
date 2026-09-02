"""Ask Credence — a grounded assistant behind the search bar.

It answers questions about the user's own data (counts, credits, flags) and about
how the platform works. A deterministic intent layer handles the common questions
instantly and always works; open-ended questions try the LLM (grounded on live
stats) and fall back gracefully when the model/credits are unavailable.
"""

from __future__ import annotations

import os
import re
from typing import Optional

import httpx

import accounts
import store

# Short knowledge base — plain-language explanations the assistant can cite.
_KB = {
    "models": (
        "Credence uses three kinds of intelligence: a vision AI (gpt-4o-mini, "
        "escalating to gpt-4o) that reads the document; a local ML embedding model "
        "(all-MiniLM-L6-v2) for meaning-matching (duplicates, résumé↔JD); and a "
        "robust z-score statistic for anomaly detection. The AI only reads — "
        "deterministic code and a human decide."
    ),
    "fraud": (
        "The fraud/integrity layer is pure code, no LLM. It checks PDF metadata for "
        "tampering, flags when a vendor's bank account differs from history, and "
        "detects duplicates. Every result is a flag for a human, never a verdict."
    ),
    "anomaly": (
        "The anomaly signal is a robust median/MAD z-score over past approved "
        "amounts. It flags 'this is unusually large versus history' and explains "
        "itself (e.g. +1.2σ). It's statistics, not a black-box model."
    ),
    "duplicate": (
        "Duplicate detection uses embeddings to catch a resubmitted document even "
        "when a number was changed — exact-match checks miss that, meaning-matching "
        "doesn't."
    ),
    "resume": (
        "For résumés we match against a pasted job description: we extract skills "
        "from both and show which required skills the candidate has and which are "
        "missing — a signal for the recruiter, never an auto-decision."
    ),
    "validation": (
        "Validation is deterministic code: it checks the math reconciles, required "
        "fields are present, and dates are sane. Same answer every time."
    ),
    "escalation": (
        "A cheap fast model runs by default; if it's unsure (low confidence) Credence "
        "automatically retries with a stronger model. You pay for the big model only "
        "when needed."
    ),
    "usp": (
        "Across every document type the common thread is the same: Credence is a "
        "trust layer. It doesn't just extract — it verifies with explainable code, "
        "flags fraud and anomalies, keeps an audit trail, and puts a human in "
        "charge. That verification-and-trust layer is the unique selling point."
    ),
}

_DOMAIN_HELP = (
    "Credence handles invoices, receipts, résumés, purchase orders, contracts, ID "
    "documents and bank statements today — one engine, more domains added over time."
)


def _stat_answer(user: dict) -> dict:
    s = store.stats()
    return s


def answer(question: str, user: dict) -> dict:
    q = (question or "").strip().lower()
    if not q:
        return {"answer": "Ask me about your documents, flags, credits, or how any check works.",
                "suggestions": _SUGGESTIONS}

    s = store.stats()
    bill = accounts.balances(user)

    # ---- data intents ----
    if re.search(r"\bflag", q):
        return _reply(f"You have {s['flagged']} flagged item(s) across all processing so far. "
                      "Open the Audit view and filter to 'flagged' to see them.", nav="/audit")
    if re.search(r"process|read|extract", q) and re.search(r"how many|count|number", q):
        return _reply(f"{s['processed']} document(s) processed so far.")
    if re.search(r"approv", q):
        return _reply(f"{s['approved']} record(s) approved and in the ledger.", nav="/ledger")
    if re.search(r"escalat", q) and re.search(r"how many|rate|often", q):
        return _reply(f"Escalation rate is {round(s['escalation_rate']*100)}% — "
                      "the stronger model was needed on that share of documents.")
    if re.search(r"credit|balance|how much.*left|trial", q):
        if bill.get("org"):
            return _reply(f"Your organization pool has {bill['org']['pooled_credits']} credits.", nav="/billing")
        if bill["account_type"] == "trial":
            return _reply(f"You have {bill['trial_credits']} free-trial credits, usable on any domain. "
                          "Buy per-domain credits on the Billing page when you're ready.", nav="/billing")
        owned = ", ".join(f"{k}: {v}" for k, v in bill["domain_credits"].items()) or "none yet"
        return _reply(f"Per-domain credits — {owned}.", nav="/billing")

    # ---- knowledge intents ----
    if re.search(r"\bmodel|which ai|gpt|ml\b|machine learning", q):
        return _reply(_KB["models"])
    if re.search(r"anomaly|outlier|unusual", q):
        return _reply(_KB["anomaly"])
    if re.search(r"duplicat|near.dup|resubmit", q):
        return _reply(_KB["duplicate"])
    if re.search(r"r[eé]sum|cv|job descr|skill", q):
        return _reply(_KB["resume"])
    if re.search(r"fraud|tamper|bank|integrity", q):
        return _reply(_KB["fraud"])
    if re.search(r"valid|reconcile|math|total", q):
        return _reply(_KB["validation"])
    if re.search(r"escalat|confidence|routing", q):
        return _reply(_KB["escalation"])
    if re.search(r"usp|unique|differentiat|stand ?out|why.*you|special", q):
        return _reply(_KB["usp"])
    if re.search(r"domain|document type|what.*process|what.*handle|what can", q):
        return _reply(_DOMAIN_HELP, nav="/review")
    if re.search(r"^\s*(hi|hello|hey)\b|what can you do|help", q):
        return _reply("I'm Credence's assistant. Ask me things like 'how many flagged?', "
                      "'what's my credit balance?', 'how does the anomaly check work?', or "
                      "'what's our unique selling point?'.", suggestions=_SUGGESTIONS)

    # ---- open-ended: try the LLM grounded on live facts, else fall back ----
    llm = _try_llm(question, s, bill)
    if llm:
        return _reply(llm)
    return _reply(
        "I can answer that best about your data and how Credence works. Try asking about "
        "flags, credits, the models, or a specific check (fraud, anomaly, duplicate, résumé).",
        suggestions=_SUGGESTIONS,
    )


_SUGGESTIONS = [
    "How many items did we flag?",
    "What's my credit balance?",
    "How does the anomaly check work?",
    "What is our unique selling point?",
]


def _reply(text: str, nav: Optional[str] = None, suggestions: Optional[list] = None) -> dict:
    out = {"answer": text}
    if nav:
        out["nav"] = nav
    if suggestions:
        out["suggestions"] = suggestions
    return out


def _try_llm(question: str, stats: dict, bill: dict) -> Optional[str]:
    """Best-effort grounded LLM answer. Returns None on any failure."""
    try:
        import extract  # reuse provider config + key
        key = extract._API_KEY  # noqa: SLF001
        if not key:
            return None
        grounding = (
            f"Live facts: processed={stats['processed']}, approved={stats['approved']}, "
            f"flagged={stats['flagged']}, escalation_rate={stats['escalation_rate']}. "
            f"Account={bill['account_type']}, trial_credits={bill['trial_credits']}. "
            "Credence reads documents with a vision AI, verifies them with deterministic "
            "code + ML signals, and keeps a human approval gate. Domains: invoice, "
            "receipt, resume, purchase_order, contract, id_document, bank_statement."
        )
        payload = {
            "model": os.environ.get("ASSISTANT_MODEL", extract.DEFAULT_MODEL),
            "temperature": 0.3,
            "max_tokens": 220,
            "messages": [
                {"role": "system", "content":
                 "You are Credence's in-app assistant. Answer in 1-3 short sentences, "
                 "plain language, grounded in the facts provided. If you don't know, say "
                 "what the user could check in the app. Context: " + grounding},
                {"role": "user", "content": question},
            ],
        }
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        if extract.OPENROUTER_KEY:
            headers["HTTP-Referer"] = "https://verdict-three-ashen.vercel.app"
            headers["X-Title"] = "Credence"
        url = f"{extract.AIPIPE_BASE}{extract.CHAT_ROUTE}"
        with httpx.Client(timeout=30) as client:
            r = client.post(url, json=payload, headers=headers)
        if r.status_code >= 400:
            return None
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None
