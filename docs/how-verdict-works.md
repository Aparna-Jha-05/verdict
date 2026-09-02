# How Credence Works — In Plain Words

A guide to your own application: what it does, what every piece of the tech stack
means, and — most importantly — **where we used AI, where we deliberately did not,
and how the non-AI parts actually work.**

Read this top to bottom. No prior knowledge assumed.

---

## 1. The whole thing in one paragraph

Credence takes an invoice — a PDF, a scan, or a photo from a phone — and does four
things: (1) it **reads** the invoice using an AI vision model that looks at the
image and pulls out the important fields; (2) it **checks the math and the rules**
using plain, ordinary computer code (no AI); (3) it **looks for fraud** using more
plain code that compares this invoice against a memory of past invoices; and (4) it
shows everything to a **human**, who edits if needed and clicks **Approve**. The one
clever idea holding it together: *the AI is only allowed to read. It is never allowed
to decide.* All the deciding is done by predictable, rule-based code.

---

## 2. The journey of one invoice (step by step)

Imagine you drop `invoice.pdf` into Credence. Here's what happens, in order:

1. **Upload.** The file lands on our server.
2. **Ingest (make it a picture).** A PDF isn't an image, and a photo already is.
   We convert *everything* into a single page image so the next step always gets
   the same kind of input. If it was a PDF, we also quietly read its hidden
   "metadata" (more on that later — it matters for fraud).
3. **Extract (the AI reads it).** We send the page image to a **vision model** — an
   AI that can look at a picture and understand it. We ask it to return the invoice
   number, date, vendor, bank account, line items, subtotal, tax, and total — plus,
   for each field, *how confident it is* and *where on the page it found it*.
4. **Validate (check the math).** Plain code adds up the numbers. Do the line items
   sum to the subtotal? Does subtotal + tax equal the total? Is the date real and
   not in the future? No AI here — just arithmetic.
5. **Escalate if needed.** If the AI said "I'm not confident," or the reading looked
   broken, we automatically re-do step 3 with a **stronger, more expensive AI model**.
   We only pay for the expensive model when the cheap one struggled.
6. **Fraud check.** More plain code looks for three danger signs: a tampered PDF, a
   vendor whose bank account suddenly changed, and a near-duplicate of an invoice we
   already paid.
7. **Human gate.** The reviewer sees every field (boxed on the image), every math
   check (green or red), and every fraud flag (with a plain-English reason). They
   fix anything wrong and click **Approve**.
8. **Ledger + memory.** On approval, we save the invoice to our records and add it to
   the "memory" so the *next* duplicate or bank-change can be caught.

That's the entire loop: **read → check → catch fraud → approve → remember.**

---

## 3. The tech stack, explained like you're five

These are the tools we used. Here's what each one actually *is* and why it's there.

### Backend (the "brain" on the server)

- **Python** — the programming language the whole brain is written in. Readable,
  great for this kind of work.
- **FastAPI** — a tool that turns our Python code into a **web service**: it lets the
  website talk to the brain over the internet using simple messages like "here's a
  file, process it" (`/process`) or "approve this" (`/approve`). Think of it as the
  reception desk that takes requests and hands back answers.
- **PyMuPDF** (also called `fitz`) — the tool that opens PDFs. We use it to (a) turn
  a PDF page into an image, and (b) read the PDF's hidden metadata for fraud checks.
- **Pillow** — an image toolkit. It resizes and cleans up photos so they're not too
  huge before we send them to the AI.
- **Pydantic** — a "shape checker." When the AI gives us data back, Pydantic makes
  sure it has the right shape (numbers are numbers, fields aren't missing). If the AI
  returns junk, Pydantic catches it and we trigger the stronger model.
- **httpx** — the tool that makes the actual internet call *to* the AI service.
- **SQLite** — a tiny, file-based **database**. It's our permanent record book: every
  approved invoice, every vendor's bank account, and the activity log all live here.
  "Database" just means "organized memory that survives restarts."
- **sentence-transformers** + **all-MiniLM-L6-v2** — this is the *only* other piece
  of AI, and it runs **on our own server, for free** (no internet call). Its job:
  turn a chunk of text into a list of numbers that captures its *meaning*. This
  powers the "near-duplicate" fraud check (explained in §5).
- **Chroma** — a **vector store**: a special database built to hold those
  meaning-numbers and quickly find the closest matches. It's how we ask "have we seen
  an invoice that *means* almost the same thing as this one?"

### Frontend (the website you click on)

- **Next.js** — the framework the website is built with (based on React). It's what
  renders the pages, the upload box, the panels.
- **React** — the underlying library for building interactive interfaces.
- **Tailwind CSS** — a styling system; it's how we made the cosmic violet/gold look.
- **lucide-react** — the icon set (the little shield, checkmark, upload icons).
- **TypeScript** — JavaScript with a safety net that catches mistakes before they ship.

### The AI gateway

- **OpenRouter / AI Pipe** — a "middleman" service that gives us access to many AI
  models (like GPT-4o) through one door, with one key. We send an image, it returns
  the AI's reading. Our key lives in a secret environment variable, never in the code.

### Where it lives (deployment)

- **Docker** — a way to package the backend with everything it needs so it runs the
  same anywhere. Like shipping the kitchen, not just the recipe.
- **Render** — the cloud host running the backend (the brain).
- **Vercel** — the cloud host running the frontend (the website).
- **GitHub** — where the code is stored and version-tracked.

---

## 4. The ONE place we used AI, and why

**Only step 3 — reading the invoice — uses a large AI model.** We send the page
image to a **vision-language model** (a "VLM": an AI that understands both pictures
and words) and it returns the fields.

Why AI here? Because *reading a messy real-world document is genuinely hard*. A phone
photo is skewed, a scan is blurry, every vendor's invoice looks different. Old-school
"OCR" (optical character recognition) breaks on these. A modern vision model handles
them gracefully. This is the part that *should* be AI.

**But here's the crucial design choice:** the AI's answer is treated as a *claim*, not
a *fact*. It's a smart guess that still has to survive the checks below. The AI is
never asked "is this invoice fraudulent?" or "should we pay?" — because AI can be
confidently wrong, and you can't audit *why* it decided something.

---

## 5. Where we did NOT use AI — and how those parts actually work

This is the heart of the product. Three whole layers run with **zero AI** — just
ordinary, predictable code. The word for this is **deterministic**: same input always
gives the same output, and you can trace exactly *why* it did what it did.

### 5a. Validation — "does the paperwork add up?" (pure arithmetic)

No AI. Just math on the numbers the AI extracted. Six checks:

1. **Totals reconcile** — do the line items add up to the subtotal?
2. **Tax math** — does subtotal + tax equal the total?
3. **Line-item math** — for each row, does quantity × unit price = amount?
4. **Required fields present** — is the invoice number, date, vendor, and total there?
5. **Date sanity** — is the date real, not in the future, not absurdly old?
6. **Currency present** — did we detect a currency?

Each check returns pass/fail with a plain reason ("Subtotal 1080.00 + tax 86.40 =
1166.40, but total says 999.99"). If a wrong-total invoice comes in, *the AI happily
reads it* — but this arithmetic catches the lie. **That's the pitch: the model
believed the document; our code didn't.**

### 5b. Fraud detection — "should we be suspicious?" (three deterministic checks)

Still no AI. Every result is a **"flag for human review"** — we never declare an
invoice "authentic" or "safe to pay," because over-claiming safety is how automated
systems cause real damage. We surface evidence; the human decides.

**Check A — PDF metadata forensics.** Every PDF secretly records which software made
it and when. We read that hidden data and flag it if:
- it was made/edited with an *image editor* (Photoshop, Canva) instead of accounting
  software — a sign someone doctored it;
- the "modified" date is *before* the "created" date (impossible — a tampering tell);
- the file was created long *after* the invoice's own date (a "recently forged old
  invoice" tell).
(For photos, there's no PDF metadata, so we just note "photo/scan path" — not a flag.)

**Check B — vendor bank-account change.** This is the single most common real-world
invoice fraud: a scammer emails a fake invoice from a real vendor with *their own*
bank account. Credence remembers every vendor's bank account from past approvals (in
SQLite). When a new invoice arrives, it looks up that vendor and, if the bank account
is different from before, raises a loud flag: *"Bank account for {vendor} differs from
the previously approved account."* It's just a database lookup and a string
comparison — but it catches the most expensive fraud there is.

**Check C — duplicate detection (two kinds).**
- *Exact duplicate:* have we already approved an invoice with this exact number? A
  simple database check. Blocks obvious double-payments.
- *Near-duplicate (this is where the small local AI helps):* a clever fraudster
  resubmits an already-paid invoice with **one digit changed** in the invoice number,
  hoping the exact-match check misses it. It does. So we also compare by *meaning*:
  we build a text signature from the vendor + total + date + line items, and turn it
  into a list of numbers called an **embedding** (using the small, free,
  on-server model). Two invoices that *mean* the same thing produce *nearly identical*
  number-lists — even if the invoice number differs. We measure how close two
  embeddings are (a score called **cosine similarity**), and if they're ~90%+ alike
  but the invoice numbers differ, we flag a possible resubmission.

  > Note: this embedding is a tiny, local, general-purpose model — not the big
  > document-reading AI. It never "decides" anything; it only measures text
  > similarity, which is a mathematical operation. That's why we still call this
  > layer deterministic and AI-free in spirit.

### 5c. Why deterministic matters (say this to a mentor)

- **Auditable** — every flag can be explained from stored facts and simple rules. You
  can point at exactly why.
- **Reproducible** — run it a thousand times, get the same answer.
- **Un-foolable by prompt tricks** — you can't "convince" arithmetic to ignore a bad
  total the way you might jailbreak an AI.
- **This separation IS the product.** Anyone can make an AI read a PDF. The value is
  everything that verifies what the AI believed.

---

## 6. Escalation — being smart about cost

We use a cheap, fast AI model by default. We only switch to the stronger, pricier
model when the cheap one **says it's unsure**, **returns broken data**, or **produces
a reading that fails a check in a way that looks like a misread** (rather than a real
problem with the invoice).

Important subtlety: escalation fixes *reading mistakes*, not *document problems*. A
genuinely bad invoice (wrong total, changed bank account) **still fails** after
escalation — because the stronger model reads it correctly, and the deterministic
layers still catch the real issue. The industry name for this is *intelligent
inference layering*: don't brute-force everything with the biggest model; escalate by
confidence.

---

## 7. The app you click through

- **Dashboard** — the overview: how many invoices processed, approved, flagged; the
  escalation rate; a confidence breakdown; and a live activity feed.
- **Review** — the main workspace: the invoice image with boxes on every field, the
  editable fields, the validation checklist, the fraud flags, and the Approve button.
- **Ledger** — the record book: every approved invoice, searchable.
- **Audit** — the timeline: every action (read, flag, escalate, approve), so nothing
  is invisible.
- **Guided tour** — a stepped walkthrough that loads each demo sample for you.
- **Command palette** (press ⌘K / Ctrl+K) — jump to any view or run any sample.
- **Connection footer** — shows whether the backend is awake (the free host "sleeps"
  when idle and takes ~40 seconds to wake).

---

## 8. Deployment, plainly

- The **backend** is packaged with **Docker** and runs on **Render** (free tier). On
  a fresh start it auto-loads two "prior invoices" so the fraud demos work instantly.
- The **frontend** runs on **Vercel** (free tier) and is told the backend's address
  through one setting (`NEXT_PUBLIC_API_BASE`).
- The **code** lives on **GitHub**. Push to GitHub → Render and Vercel automatically
  rebuild. That's why every change we make goes live on its own.
- **Free-tier trade-off:** the backend sleeps when idle, so the *first* request after
  a quiet spell is slow (~40s). Warm it up right before a demo.

---

## 9. Mini-glossary

| Term | Plain meaning |
|---|---|
| **VLM / vision model** | An AI that looks at a picture and understands it |
| **OCR** | Old text-from-image tech; brittle on messy scans (we skip it) |
| **Deterministic** | Predictable code: same input → same output, fully explainable |
| **Bounding box (bbox)** | The rectangle marking where a field sits on the page |
| **Embedding** | A list of numbers capturing the *meaning* of some text |
| **Cosine similarity** | A score (0–1) for how alike two embeddings are |
| **Vector store** | A database built to search those meaning-numbers fast (Chroma) |
| **Database** | Organized memory that survives restarts (SQLite) |
| **API / endpoint** | A web address the site calls to make the brain do something |
| **Metadata** | Hidden "data about the file" (who made a PDF, when) |
| **Escalation** | Retrying with a stronger AI model only when the cheap one struggles |
| **Deploy** | Put the app on the internet so others can use it |
| **Docker** | A box that packages the app so it runs the same everywhere |

---

## 10. The one sentence to remember

**Credence uses AI to *read* documents and ordinary, auditable code to *decide* about
them — and keeps a human in charge of every approval.** Everything else is detail.
