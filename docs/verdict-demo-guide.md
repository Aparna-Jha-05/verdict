# Verdict — Live Demo & Q&A Guide

*Plain-language guide to the whole application as it stands now. Written so you
can present it, and answer anything a mentor or judge throws at you, without
needing to open the code.*

**Live app:** https://verdict-three-ashen.vercel.app
**Code:** https://github.com/Aparna-Jha-05/verdict
**API docs:** https://invoice-intelligence-api-yhax.onrender.com/docs

---

## 1. What Verdict is, in one breath

Verdict is a **platform that turns any document into a trustworthy decision.** You
upload a document — an invoice, a receipt, a résumé, an ID, a contract, a bank
statement — an AI vision model *reads* it, then plain rule-based code *checks* it
for mistakes and fraud, some machine-learning adds *warning signals*, and finally a
**human approves** it. It's one engine that works across many document types, and
you only pay for the document types you actually use.

> **The one idea to remember:** *the AI is only allowed to read. It is never allowed
> to decide.* All the deciding is done by predictable code and a human. That's what
> makes it safe to put in front of real money and real hiring.

---

## 2. Everything it can do right now (in plain words)

**Reads any document (vision-first, no OCR).**
We send a picture of the page to a vision AI model and ask it what it sees. Because
it looks at the *image*, it doesn't care about layout — a clean PDF, a crooked phone
photo, or an unusual template all work. There are no rigid templates to break.

**Works across 8 document types (and more can be added).**
Invoice · Receipt · Résumé · Purchase Order · Contract · ID Document · Bank
Statement · plus a Generic fallback for anything else. Each type is a small
"pack" that describes its fields and its rules. Adding a new type = adding a pack,
not rebuilding the app. You can pick the type, or let it **auto-detect**.

**Never drops a field it's never seen before.**
Every document type has its known fields, *plus* an open "additional fields"
bucket. If a résumé has a "Publications" section or an invoice has a field we
didn't expect, it's captured and shown to the human — never silently thrown away.

**Escalates the hard cases automatically.**
A cheap, fast model runs by default. If it's unsure (low confidence) or the page is
messy, Verdict automatically retries with a stronger model. You pay for the
expensive model only when you actually need it.

**Checks the document with plain code (no AI).**
- *Validation* — does the math add up? Are required fields present? Are dates real?
- *Integrity / fraud* — has a vendor's bank account changed since last time? Is this
  a duplicate? Was the PDF edited in image software? For IDs, do the checksums pass?

These checks are ordinary, predictable code. They give the same answer every time
and can't be talked out of it.

**Adds machine-learning *signals* (not decisions).**
- *Anomaly score* — "this amount is unusually large compared to this vendor's
  history." It learns the normal range from past approved documents and flags
  outliers. (Uses a robust statistic so it works even with little history.)
- *Résumé ↔ Job-Description match* — pulls skills from both and shows which required
  skills the candidate has and which are missing, using meaning-based matching.
- *Duplicate detection* — uses "embeddings" (meaning-numbers) to catch a resubmitted
  document even if a number was changed.

Every ML output is a **signal for the human**, never an automatic yes/no.

**Shows its work on the document.**
Each extracted value has a box drawn on the page image. Hover a field and its
source lights up. You can *see* where every number came from.

**Keeps a human in charge.**
Nothing is finalized until a person reviews the fields, the checks, and the flags,
edits anything that's wrong, and clicks **Approve.** Approval fires a mock action
(e.g. "queued for payment" / "shortlisted"), downloads a CSV, and writes to a
permanent ledger — which then blocks future duplicates.

**Is a real product, with accounts and billing.**
- Sign up, log in, or start an **instant free trial** in one click.
- Free trial = credits usable on *any* document type, to experiment.
- Then **buy credits only for the document type you need** — not the whole suite.
- **Enterprise** accounts get a shared credit pool and can create member accounts
  in bulk. Every document processed spends one credit.

**Feels like an app, not a script.**
Dashboard with live stats and a domain gallery · Review screen · searchable Ledger
· Audit trail of every action · Billing page · a guided tour built for demos · a
command palette (⌘K) · light/dark themes · a live "backend online" indicator.

---

## 3. How one document flows through it (step by step)

1. **Upload** — you drop a file and pick a type (or auto-detect). For résumés you
   also paste the job description to match against.
2. **Ingest** — any file becomes a page image; for PDFs we also read hidden
   metadata (used later for tamper checks).
3. **Read (AI)** — the vision model returns the fields it sees, each with a
   confidence level and a box on the page.
4. **Escalate if unsure (AI)** — low confidence? Retry with a stronger model.
5. **Validate (code)** — math, required fields, dates.
6. **Check integrity (code)** — fraud/tamper/duplicate/checksum checks.
7. **Add ML signals** — anomaly score, skill match, duplicate similarity.
8. **Human reviews & approves** — edit, then approve → mock action + CSV + ledger.
9. **Charge** — one credit is spent (only after a successful read).

Steps 3–4 are AI. Steps 5–6 are plain code. Step 7 is ML *signals*. Step 8 is a
human. That separation is the whole point.

---

## 4. The tech stack in plain words (and where AI is / isn't)

| Piece | What it is | Is it AI? |
|---|---|---|
| **Next.js** | The website/app you click around in | No |
| **FastAPI** | The backend brain that runs the pipeline | No |
| **Vision model** (via OpenRouter) | Reads the document image | ✅ Yes — the AI |
| **Confidence escalation** | Retries a stronger model when unsure | ✅ AI routing |
| **Validation & integrity code** | Math, fraud rules, checksums | ❌ No — plain code |
| **Anomaly scorer** | Flags unusually large amounts vs history | ✅ ML (statistics) |
| **Skill matcher / duplicate finder** | Embeddings for meaning-matching | ✅ ML |
| **SQLite** | Remembers approved documents, vendors, accounts | No |
| **Render + Vercel** | Where it's hosted online | No |

**Where we deliberately use NO AI:** the parts that decide whether something is
*correct* or *fraudulent*. A language model should never be the one saying "yes,
$1,080 + $86 = $1,166" or "yes, pay this." Those are done by code you can audit.

---

## 5. The live demo (what to click, what to say)

> **Warm it up first:** open the app once ~40 seconds before you present, so the
> free-tier backend is awake. Click **Try instantly** to get a trial account.

1. **Clean invoice** → fields fill in green, boxes on the page. Hover "Total."
   *"It reads the document and shows exactly where every number came from."*
2. **Phone photo** → the ⚡ *escalated* badge appears, then it reads correctly.
   *"Same code path for a crooked photo — and it upgrades to a stronger model only
   when it's unsure."*
3. **Wrong total** → the model reads it fine, but Validation throws a red flag.
   *"The AI believed the document. Our plain-code check didn't. That's the safety
   net."*
4. **Changed bank** → Integrity flags the bank-account change vs history, and you
   can draft a vendor verification email in one click.
   *"This is the most common real invoice fraud in the world — and it never reaches
   payment."*
5. **Résumé ↔ JD** → switch the type to Résumé, paste a job description, upload.
   Show the skills matched and missing.
   *"Same engine, totally different document. It matches the candidate to the job by
   meaning, and a recruiter decides."*
6. **Approve one, then show Ledger + Audit + Billing.**
   *"Human-approved, logged, and it now blocks duplicates. And it's a real product —
   free trial, then pay only for the document type you need, with enterprise
   accounts for teams."*

The arc: **read anything → escalate → verify → catch fraud → match → approve → get
paid.**

---

## 6. Q&A — likely questions, plain answers

**Q: Why not just use ChatGPT / Claude / Gemini directly?**
Those are a brilliant brain with no memory, no guarantees, and no paper trail. A
chatbot will *confidently* say totals add up when they don't, forgets every past
document, gives you text you have to re-parse, and can't show a regulator an audit
trail. Verdict adds the memory (a ledger of past approvals for fraud/duplicate
checks), the guarantees (deterministic math), the workflow (human approval, CSV,
audit), cost control (cheap model by default), and it's safe from prompt-injection
because the *deciding* layer never touches an LLM. It's the system around the brain.

**Q: How will it make money?**
Reframe from "cost per page" to "value per catch." Four stacked streams: pay-per-
document, monthly SaaS plans, per-domain credit packs, and enterprise contracts. Our
cost is ~half a cent per document; we can price at 10–25 cents. And the closer: one
prevented bank-change fraud (typically $30k–$120k) pays for years of subscription.
We're not a cost center — we're insurance that pays for itself.

**Q: What if a new document arrives with fields or a format we've never seen?**
Three protections. (1) Because we read the *image*, new layouts already work — no
templates to break. (2) Any unexpected field lands in the "additional fields" bucket
and is shown to the human — nothing is dropped. (3) If it's a whole new document
*type*, auto-detect routes it, or a generic fallback still reads it and flags
"unrecognized — human review." We generalize instead of breaking.

**Q: Someone's résumé doesn't follow a normal design — will they be skipped?**
No — and this is a strength. Old keyword-based screeners reject good candidates for
unusual formatting. Verdict reads the image, so any layout works; unusual sections
are captured, not lost; a hard-to-read résumé escalates to a stronger model and then
goes to a human. Nobody is filtered out by the machine alone.

**Q: This is an AI/ML competition — is your project actually AI/ML?**
Yes, heavily. The core is a multimodal vision AI. On top: confidence-based model
routing, embeddings for duplicate detection and résumé-to-job matching, and an
anomaly-detection model for fraud signals. The *only* non-AI parts are the final
correctness/fraud rules — and using plain code there, instead of an LLM, is a
maturity signal: we know where an AI's guess is not good enough.

**Q: Will you use ML in the new domains too?**
Yes, in two bounded roles: the vision model reads every document, and embeddings do
meaning-matching where it helps (résumé↔JD, claim↔evidence, duplicates). We
deliberately avoid black-box "hire/no-hire" or "fraud score" classifiers for the
final call, because they can't explain themselves — and explainability is our whole
value.

**Q: What if the AI extracts something wrong?**
Three nets: low confidence auto-escalates to a stronger model; the deterministic
checks catch wrong numbers regardless of how confident the AI was; and the human
edits any field before approving.

**Q: Why "flag for review" instead of "fraud detected"?**
On purpose. We never claim a document is authentic or fraudulent — we surface
evidence and let a human decide. Over-claiming is how automated systems create
liability. We flag; people decide.

**Q: Does it scale / is it expensive?**
The cheap model handles the common case; only unsure documents pay for the strong
one. Duplicate/skill matching runs locally with no API cost. It runs on free hosting
today and costs about half a cent per document.

**Q: Is the login/payment real?**
It's a working demo of the full model — accounts, free trial, per-domain credits,
enterprise pools, bulk accounts — with mock billing (no real card charged). Wiring a
real payment provider is a small, well-understood next step.

**Q: What's next?**
More domains (insurance claims, tax forms, medical bills), a three-way purchase-order
match, and richer ML signals. The pack design means each new domain is additive.

---

## 7. Quick reference

- **Instant demo account:** the **Try instantly** button (no signup).
- **Free trial:** 25 credits, usable on any document type.
- **If a document fails with a "credits" error:** that's the *OpenRouter* account
  (the AI provider) needing a small top-up, or a free vision model set on the
  backend — it is **not** a bug in Verdict. Everything except the live AI read
  (dashboard, ledger, audit, billing, tour) still works without it.
- **First request is slow (~40s):** the free-tier backend was asleep and is waking.
  Warm it up before presenting.

**The single sentence, if you only get one:** *"Verdict reads any document with AI,
verifies it with code you can trust, flags fraud with machine learning, and keeps
the final decision with a human — one platform, many document types, pay only for
what you use."*
