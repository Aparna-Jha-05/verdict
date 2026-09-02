# Credence — Revenue, Robustness & the Multi-Domain Platform

*A written response to the mentors' feedback. Three questions, answered:*
1. **How does Credence make money?** (the revenue model)
2. **What happens when a document has new fields or a new format we've never seen?** (robustness)
3. **How do we grow from invoices into many domains?** (the platform upgrade)

Read this top to bottom before we build — every technical choice below is downstream of these three answers.

---

## Part 1 — The revenue model (the money question)

### The reframe that wins the room
We do **not** sell "an app that reads documents." Everyone can read a document with an LLM. We sell **verified decisions and prevented fraud.** That reframe changes the pricing conversation from *cost-per-page* (a race to zero) to *value-per-catch* (insurance pricing).

> **The one-liner for the pitch:** *"We're not a cost center. We're insurance that pays for itself the first time it stops a fraudulent payment."*

### Four stacked revenue streams
A serious document-AI business rarely has one price. Credence stacks four, so it captures both small teams and enterprises:

| # | Stream | How it works | Why it exists |
|---|--------|--------------|---------------|
| A | **Usage / per-document** | Pay per document processed (metered credits) | Aligns our price with our own AI cost; frictionless for small users |
| B | **SaaS subscription tiers** | Monthly plan bundling a document quota + features | Predictable recurring revenue (MRR) — what investors and judges look for |
| C | **Domain packs (add-ons)** | Enable *Resume*, *Tax*, *Expenses* packs on top of the base | Land-and-expand: sell invoices first, upsell the rest |
| D | **Enterprise / API / on-prem** | Volume contracts, API access, private deployment, SLAs | Large B2B deals; ERP/ATS integrations |

### Unit economics (why the margin is real)
| Item | Figure | Notes |
|------|--------|-------|
| Default extraction cost | ~**$0.002–0.004** / page | Small vision model (gpt-4o-mini-class) |
| Escalation cost | ~$0.01–0.03, but only ~**10%** of docs | Strong model runs only on low confidence |
| Embeddings (dedup) | **$0.00** | Runs locally — no API |
| Deterministic layers | **$0.00** | Pure Python |
| **Blended cost of goods** | **~$0.005 / document** | |
| **Price (usage)** | **$0.10 – 0.25 / document** | **~95%+ gross margin at the unit level** |

### The ROI story (the number that closes)
Vendor-impersonation / business-email-compromise fraud — exactly the **changed-bank-account** case Credence catches — averages **tens of thousands of dollars per incident** (commonly $30k–$120k). 

> **One prevented fraudulent payment pays for years of subscription.** That is the entire economic argument, and Credence *demonstrably* catches it on stage.

### Suggested pricing table (concrete, for the slide)
| Plan | Price | Includes |
|------|-------|----------|
| **Free** | $0 | 50 documents/mo · invoices only · validation + basic fraud |
| **Pro** | $49/mo | 1,000 documents/mo · full fraud layer · CSV export · 1 domain pack |
| **Business** | $199/mo | 5,000 documents/mo · all domain packs · audit export · API access |
| **Enterprise** | Custom | Unlimited volume · on-prem/VPC · ERP/ATS integrations · SLA |

### Who pays (ideal customers)
- **SMB finance / accounts-payable teams** — invoices, receipts, expense reports.
- **Staffing agencies & HR teams** — resume screening at volume.
- **Accounting & bookkeeping firms** — process documents for many clients.
- **Procurement teams** — POs, three-way match, vendor verification.

Each is a different *domain pack* on the **same engine** — which is exactly what Part 3 makes possible.

---

## Part 2 — New fields, new formats (the robustness question)

The mentors asked the right question: *"What if a new invoice or resume shows up with fields we've never seen, in a format we've never seen?"* Here is the honest, layered answer.

### Layer 1 — New *layouts* are already free
Credence is **vision-first, no OCR templates.** We send the page image to the model and ask *what fields it sees* — we never say *where to look.* So a brand-new invoice layout, a different bank's statement, a resume in an unusual template… all Just Work, because we never hard-coded positions. **This is the single biggest robustness advantage of the no-OCR design, and it's already built.**

### Layer 2 — New *fields* → an adaptive, open schema
Today each domain has a fixed schema (invoice_number, total, …). We upgrade it to **core fields + an open catch-all**:

```
{
  ...known core fields...,
  "additional_fields": [
    { "label": "PO Number",      "value": "PO-4471", "confidence": "high", "bbox": [...] },
    { "label": "GST Breakdown",  "value": "...",      "confidence": "medium", "bbox": [...] }
  ]
}
```

**Rule: nothing the model sees is thrown away.** Anything outside the known schema lands in `additional_fields` with its own confidence and bounding box, and is shown to the human. A field we've never seen becomes *visible*, not *lost*.

### Layer 3 — Confidence-gated, never silently decided
New or uncertain fields arrive with **low/medium confidence** and are surfaced for human review. The deterministic layers only run rules on fields they *understand*; an unknown field is displayed and flagged, never fed into a silent auto-decision. Unknowns degrade to "human, please look" — they never crash and never get rubber-stamped.

### Layer 4 — Unknown *document type* → auto-detect + generic fallback
A cheap first pass classifies **what kind of document this is** (invoice? resume? receipt?) and routes it to the right **domain pack**. If it matches nothing, a **generic pack** still extracts every field it can and flags *"unrecognized document type — human review."* We always produce something useful; we never hard-fail.

### Layer 5 — Schema versioning
Schemas evolve. Every processed/approved record stores the **schema version** it was captured under, so old ledger entries stay valid and reproducible as we add fields. Auditability survives change.

> **Summary:** new format → handled by design (no templates). New fields → captured in the open schema and shown to a human. New document type → detected and routed, or gracefully sent to a human via the generic pack. **We generalize instead of breaking.**

---

## Part 3 — The multi-domain platform (the upgrade)

### Architecture: one engine, pluggable domain packs
We refactor Credence's spine into a **domain-agnostic engine** (ingest → extract → verify → human gate → ledger) plus swappable **domain packs.** A pack is a small declaration:

```
DomainPack:
  name                # "invoice" | "resume" | "receipt" | ...
  core_schema         # the known fields
  validation_rules    # deterministic checks (NO LLM)
  integrity_checks    # deterministic fraud/consistency checks (NO LLM)
  similarity_input?   # OPTIONAL second input to match against (resume↔JD)
```

Adding a domain = **writing a pack, not rewriting the engine.** The two verification layers, the escalation router, the human gate, the ledger, and the audit trail are all shared.

### A domain switcher in the UI
A dropdown (and the command palette) lets the user pick the domain, or "Auto-detect." Each pack renders the same review UI — fields, validation, integrity flags, approve — so the experience is identical across domains.

### Candidate domains (researched, ranked by fit)
Each is the same pattern — *AI reads, deterministic rules decide, human approves* — with a domain-specific twist:

| Domain | What it extracts | Deterministic checks | Similarity/ML twist | Revenue angle |
|--------|------------------|----------------------|---------------------|----------------|
| **Invoices** *(live)* | numbers, vendor, bank | math, totals, dates | near-duplicate embeddings | AP teams, finance |
| **Receipts / expenses** | merchant, amount, category | policy limits, per-diem caps, duplicates | duplicate embeddings | expense management |
| **Résumés ↔ job description** | skills, roles, dates, education | timeline gaps, overlap, date sanity | **resume↔JD semantic match** | staffing / HR (huge) |
| **Purchase orders** | line items, quantities, totals | three-way match vs invoice + receipt | — | procurement |
| **Tax forms** (W-2/1099/GST) | IDs, amounts, boxes | cross-field math, ID checksums | — | accounting firms |
| **IDs / KYC** (passport, license) | name, number, expiry | MRZ checksum, expiry, format regex | face/text consistency (optional) | fintech onboarding |
| **Contracts** | parties, dates, amounts, terms | required-clause presence, date logic | clause↔playbook match | legal ops |
| **Research papers** | claims, citations, figures | citation-format integrity, "claim without citation" | **claim↔evidence match** | academia / R&D |
| **Insurance claims** | claimant, amount, policy | policy-limit checks, duplicate claims | duplicate embeddings | insurers |
| **Bank statements** | transactions, balances | running-balance reconciliation | anomaly flags | lending / underwriting |

**Recommended second domain: Résumé ↔ Job Description.** It's the most different from invoices (so it *proves* the platform is general), it has a massive market (staffing), and it showcases the one new capability — **similarity matching** — cleanly.

### Where ML appears across domains (recap of our earlier discussion)
- **Vision model (generative AI):** every domain, **reading only.**
- **Embeddings (small trained model):** only in *similarity* domains (resume↔JD, claim↔evidence, duplicates) — it produces a **number**, and a **rule** decides what the number means.
- **Trained decision classifiers (black-box "hire/no-hire", "fraud score"):** **deliberately avoided** — they can't explain themselves, and explainability is our whole value proposition.

---

## Part 4 — What we build next (concrete plan)

1. **Adaptive schema** — add `additional_fields[]` to extraction so no field is ever dropped.
2. **Engine/pack refactor** — pull invoice-specific logic into an `invoice` pack behind a `DomainPack` interface; keep the shared engine untouched.
3. **Domain auto-detection** — a cheap classify-first step + a generic fallback pack.
4. **Second domain: Résumé ↔ JD** — proves the platform and introduces the `similarity_input` capability (embeddings again, now for matching).
5. **UI: domain switcher** — dropdown + command palette + per-domain review rendering.
6. **Pricing surface** — a simple plan/usage indicator in the app to make the revenue model tangible for judges.

**Sequencing note:** revenue framing and the resume domain are the two highest-leverage items for the pitch. If we do only two things, do those.
